"""声音与定时语音：来源、编辑、放置与音轨混合。"""

import dataclasses
import marshal
import math
import os
from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from types import CodeType
from typing import TYPE_CHECKING, ClassVar, Self
from warnings import deprecated

import numpy as np

from manimgx.animation import clock
from manimgx.animation.easing import linear
from manimgx.animation.timeline import Animation, AnimationOptions
from manimgx.caches import Memo
from manimgx.mobject import Mobject

if TYPE_CHECKING:
    from manimgx.scene import Scene
import json
import re
from collections.abc import Sequence

RATE = 48_000
"""音轨的采样率：每秒 48,000 个采样点，与视频的声音一致。"""
CUT = 0.005
"""被截短的声音淡出所需的最短时长，以秒为单位：在波形中间截断会产生咔嗒声。"""
DUCK_ATTACK, DUCK_RELEASE = 0.15, 0.5
"""闪避声音在语音前下压所需的时间，以及在语音后回升所需的时间（秒）。"""
BITRATE = 224_000
"""音轨每个声道的比特率：AAC-LC，224 kbps。"""

type Source = str | os.PathLike[str] | bytes | np.ndarray
"""声音由什么构成：文件的路径、文件的字节（任何常见音频文件：WAV、AIFF、
MP3、AAC/M4A、Opus、Vorbis、FLAC、ALAC；视频的声音也行），或采样点（浮点数，-1 到 1：每
个声道一列）。"""

_DECODED: Memo[int, np.ndarray] = Memo(64)


@dataclass(frozen=True, slots=True)
class _Edit:
    """声音如何由其来源构成：按应用的顺序排列。"""

    start: float = 0.0  # the source trimmed to [start, end) seconds
    end: float | None = None
    speed: float = 1.0  # played faster (and higher) or slower (and lower)
    loop: float | None = None  # repeated to last this long (inf: until stopped)
    gain: float = 0.0  # in decibels
    fade_in: float = 0.0
    fade_out: float = 0.0
    pan: float = 0.0  # -1 left, 0 center, 1 right
    duck: float = 0.0  # decibels it dips by while anything speaks


class Sound(Animation[Mobject]):
    """影片播放的一段声音。

    从文件、文件字节或采样点构造一个声音；对其进行编辑（每次编辑都会生成一个新的
    声音）；将其放入场景：[`add_sound`][manimgx.Scene.add_sound] 立即启动它且
    不占用时间，而 [`play`][manimgx.Scene.play] 将其作为 play 的一部分播放，
    随后该 play 至少持续与声音一样长的时间。在组合中，它在其窗口
    打开时启动：`LaggedStart(*(AnimationGroup(FadeIn(d), click) for d in dots))` 在每个
    点出现时发出咔嗒声。它不会改变屏幕上的任何内容，且 play 的 `run_time` 不会改变它：
    声音持续其 [`duration`][manimgx.audio.sound.Sound.duration]。

    Args:
        source: 文件的路径、文件的字节或采样点：从 -1 到 1 的浮点数，每个
            声道一列（一维数组为单声道），按给定方式复制。
        rate: 采样点的速率，以每秒采样点数为单位；仅用于采样点。
    """

    defaults: ClassVar[AnimationOptions] = {"rate_func": linear}
    speaks: ClassVar[bool] = False  # speech ducks what is set to duck

    def __init__(self, source: Source, *, rate: int | None = None) -> None:
        if isinstance(source, np.ndarray) != (rate is not None):
            raise ValueError("give a rate with samples, and only with samples")
        if rate is not None and (not math.isfinite(rate) or rate <= 0):
            raise ValueError("the sample rate must be finite and positive")
        if isinstance(source, str | os.PathLike) and not Path(source).is_file():
            raise FileNotFoundError(f"no sound file at {os.fspath(source)!r}")
        if isinstance(source, np.ndarray):  # its own: the samples as they were given
            source = np.array(source, copy=True, subok=True)
        self.source = source
        self.rate = rate
        self._edit = _Edit()
        super().__init__(None)

    # ── edits: each makes a new sound ─────────────────────────────────────────
    def _but(self, **changes: float | None) -> Self:
        other = object.__new__(type(self))
        other.__dict__.update(self.__dict__)
        other._edit = dataclasses.replace(self._edit, **changes)
        other.__dict__.pop("_made", None)
        return other

    def gain(self, decibels: float) -> Self:
        """将此声音调响 `decibels` 分贝（若为负则调轻：-6 使其减半）。"""
        return self._but(gain=self._edit.gain + decibels)

    def fade_in(self, seconds: float) -> Self:
        """此声音在最初的 `seconds` 内从静音淡入。"""
        return self._but(fade_in=seconds)

    def fade_out(self, seconds: float) -> Self:
        """此声音在最后的 `seconds` 内淡出至静音。"""
        return self._but(fade_out=seconds)

    def trim(self, start: float = 0.0, end: float | None = None) -> Self:
        """此声音从 `start` 秒到 `end` 秒的部分（None：到其结尾）。"""
        return self._but(start=start, end=end)

    def loop(self, duration: float | None = None) -> Self:
        """此声音重复播放以持续 `duration` 秒；None：直到影片结束，或
        直到其片段被[停止][manimgx.audio.sound.Clip.stop]。"""
        return self._but(loop=math.inf if duration is None else duration)

    def speed(self, factor: float) -> Self:
        """此声音以 `factor` 倍速播放，如同磁带一般：更高且更短。

        结果速度必须为有限正数。
        """
        speed = self._edit.speed * factor
        if not math.isfinite(speed) or speed <= 0:
            raise ValueError("the resulting speed must be finite and positive")
        return self._but(speed=speed)

    def pan(self, position: float) -> Self:
        """将此声音从 -1（左）经 0（中）放置到 1（右）。"""
        return self._but(pan=position)

    def duck(self, decibels: float = 12) -> Self:
        """此声音在任何语音播放时下压 `decibels` 分贝（当
        [`Speech`][manimgx.audio.Speech] 播放时）：解说下的音乐。它在语音前
        `DUCK_ATTACK` 秒开始下压，在语音后 `DUCK_RELEASE` 秒回升。
        """
        return self._but(duck=decibels)

    @classmethod
    def of(
        cls, function: Callable[[np.ndarray], np.ndarray], duration: float
    ) -> "Sound":
        """由时间函数生成的声音：`function(t)`，传入其采样点的
        时间（秒，一个数组），返回它们的值（-1 到 1）。

        Examples:
            `Sound.of(lambda t: 0.3 * np.sin(2 * np.pi * 440 * t), 1)`：一秒的 A 音。
        """
        t = np.arange(round(duration * RATE)) / RATE
        return cls(np.asarray(function(t), np.float32), rate=RATE)

    # ── what it is ──────────────────────────────────────────────────────────────
    @property
    def samples(self) -> np.ndarray:
        """其在 `RATE` 下的采样点：浮点数，每个声道一列（1 或 2）。"""
        made = self.__dict__.get("_made")
        if made is None:
            made = self.__dict__["_made"] = _make(self)
        return made

    @property
    def duration(self) -> float:
        """它持续多久，以秒为单位（对于循环播放直到被停止的声音为 inf）。"""
        if self._edit.loop is not None:
            return self._edit.loop
        return len(self.samples) / RATE

    @property
    def _duration(self) -> Fraction:
        return (
            Fraction(len(self.samples), RATE)
            if self._edit.loop is None
            else super()._duration
        )

    @property
    def run_time(self) -> float:
        """其时长：声音播放与其持续时长相同。无尽声音（`loop()`）
        无法被播放：请添加它（[`add_sound`][manimgx.Scene.add_sound]），然后停止它。
        """
        if self._edit.loop == math.inf:
            raise ValueError(
                "an endless sound (loop()) never ends: add it with add_sound, and stop"
                " its clip, instead of playing it"
            )
        return self.duration

    @run_time.setter
    def run_time(self, value: float) -> None:
        pass  # a play's run_time sets its animations', not its sounds'

    # ── as an animation: it changes nothing on screen ─────────────────────────
    def begin(self) -> None: ...
    def finish(self) -> None: ...
    def clean_up_from_scene(self, scene: "Scene") -> None: ...
    def advance(self, t: Fraction) -> None: ...
    def interpolate(self, alpha: float) -> None: ...


@dataclass(eq=False)
class Clip:
    """影片播放的一段声音：从 `start` 开始，以场景时间的秒为单位，直到它结束
    或被停止。[`add_sound`][manimgx.Scene.add_sound] 返回它。"""

    sound: Sound
    start: Fraction
    end: Fraction | None = (
        None  # stopped: silent from here, having faded out over `fade`
    )
    fade: float = 0.0

    def stop(self, fade: float = 0.05) -> None:
        """停止声音：它从现在（场景正在计算的瞬间）起在
        `fade` 秒内淡出，此后静默。"""
        self.end, self.fade = clock.now + clock.rational(fade), fade


def _source_samples(sound: Sound) -> np.ndarray:
    """在 RATE 下的来源采样点（二维），可能是借用的；使用者不得修改它们。"""
    source = sound.source
    if isinstance(source, np.ndarray):
        data = source.astype(np.float32, copy=False).reshape(
            len(source), math.prod(source.shape[1:])
        )
        rate = sound.rate
        assert rate is not None
        return data if rate == RATE else _resample(data, rate, RATE)
    raw = source if isinstance(source, bytes) else Path(source).read_bytes()
    from manimgx._engine import digest

    key = digest(raw)
    return _DECODED.recall(key, lambda: _decode(raw))


def _decode(raw: bytes) -> np.ndarray:
    from manimgx._engine import decode_audio

    samples, channels = decode_audio(raw, RATE)
    return np.frombuffer(samples, np.float32).reshape(-1, channels)


def _resample(data: np.ndarray, rate: float, to: float) -> np.ndarray:
    """将 `rate` 处的采样点重采样到 `to`：带限的（引擎的加窗 sinc）。"""
    from manimgx._engine import resample_audio

    channels = data.shape[1]
    out = resample_audio(np.ascontiguousarray(data).tobytes(), channels, rate, to)
    return np.frombuffer(out, np.float32).reshape(-1, channels)


def _make(sound: Sound) -> np.ndarray:
    """声音的采样点：其来源经裁剪、变速、循环，并应用增益、淡变和声像。一个
    无尽循环是它的一轮，不带淡变：混音在其片段播放期间重复它，
    并在片段开始和结束处淡变它。"""
    e = sound._edit
    data = _source_samples(sound)
    data = data[round(e.start * RATE) : None if e.end is None else round(e.end * RATE)]
    if e.speed != 1:
        data = _resample(data, RATE * e.speed, RATE)
    if e.loop is not None and math.isfinite(e.loop) and len(data):
        n = round(e.loop * RATE)
        data = np.tile(data, (-(-n // len(data)), 1))[:n]
    data = data * np.float32(10 ** (e.gain / 20))
    if e.loop != math.inf:
        _ramp(data, e.fade_in, e.fade_out)
    if e.pan:
        if data.shape[1] == 1:
            data = np.repeat(data, 2, axis=1)
        data[:, 0] *= min(1.0, 1 - e.pan)
        data[:, 1] *= min(1.0, 1 + e.pan)
    return data


def _ramp(data: np.ndarray, fade_in: float, fade_out: float) -> None:
    """就地淡变 `data` 的两端：指定长度的线性斜坡。"""
    for seconds, head in ((fade_in, True), (fade_out, False)):
        n = min(len(data), round(seconds * RATE))
        if n:
            ramp = np.linspace(0, 1, n, endpoint=False, dtype=np.float32)[:, None]
            if head:
                data[:n] *= ramp
            else:
                data[len(data) - n :] *= ramp[::-1]


def mix(clips: list[Clip], duration: Fraction) -> np.ndarray | None:
    """时长为 `duration` 秒的影片的音轨：其片段经混合，在 RATE 下（每个
    声道一列：当所有片段都是单声道且居中时为单声道）；若无片段则为 None。

    一个片段从其开始处播放，直到其声音结束、被停止或影片结束；
    被截短的声音在其停止的淡变时长内淡出，或至少 `CUT`（在波形中间截断
    会产生咔嗒声）。无尽循环在其片段开始处淡入，在其结束处淡出。
    """
    if not clips:
        return None
    total = round(duration * RATE)
    channels = max(c.sound.samples.shape[1] for c in clips)
    out = np.zeros((total, channels), np.float32)
    for clip in clips:
        at = round(clip.start * RATE)
        if at >= total:
            continue
        e, data = clip.sound._edit, clip.sound.samples
        span = (total if clip.end is None else min(total, round(clip.end * RATE))) - at
        if span <= 0:
            continue
        stop = 0.0 if clip.end is None else clip.fade
        if e.loop == math.inf and len(data):
            data = np.tile(data, (-(-span // len(data)), 1))[:span]
            _ramp(data, e.fade_in, max(e.fade_out, stop, CUT))
        elif len(data) > span:
            data = data[:span].copy()
            _ramp(data, 0, max(stop, CUT))
        if e.duck:
            data = data * _ducked(clips, e.duck, at, len(data))[:, None]
        out[at : at + len(data)] += data  # mono into each channel of stereo
    return out


def _ducked(clips: list[Clip], decibels: float, at: int, length: int) -> np.ndarray:
    """放置在采样点 `at` 处、持续 `length` 个采样点的闪避声音的增益：1，在
    `clips` 中任何语音播放时下压 `decibels` 分贝（在 10 ms 网格上平滑过渡）。"""
    low, hop = 10 ** (-decibels / 20), RATE // 100
    grid = np.arange(at, at + length + hop, hop, dtype=np.float64) / RATE
    gain = np.ones(len(grid))
    for clip in clips:
        if clip.sound.speaks:
            a = float(clip.start)
            b = a + clip.sound.duration
            if clip.end is not None:
                b = min(b, float(clip.end))
            if b <= a:
                continue
            ease_in = np.clip((grid - (a - DUCK_ATTACK)) / DUCK_ATTACK, 0, 1)
            ease_out = np.clip(((b + DUCK_RELEASE) - grid) / DUCK_RELEASE, 0, 1)
            gain = np.minimum(gain, 1 - (1 - low) * np.minimum(ease_in, ease_out))
    return np.interp(np.arange(length) / hop, np.arange(len(grid)), gain).astype(
        np.float32
    )


@dataclass(frozen=True, slots=True)
class Word:
    """语音中的一个词，以及它何时被说出：从 `start` 到 `end`，以从
    语音开始的秒数为单位。"""

    text: str
    start: float
    end: float


class Speech(Sound):
    """语音：一种知道自己说什么以及每个词何时被说出的声音。

    语音由一个 voice 返回。它像任何声音一样播放；[`Scene.say`][manimgx.Scene.say]
    还按其词语为动画计时。

    Args:
        source: 音频：文件的路径、文件的字节或采样点。
        text: 它说了什么。
        words: 每个词及其被说出的时间，如果 voice 知道；否则从
            音频中估算。
        rate: 采样点的速率；仅用于采样点。
    """

    speaks: ClassVar[bool] = True

    def __init__(
        self,
        source: Source,
        *,
        text: str,
        words: Sequence[Word] = (),
        rate: int | None = None,
    ) -> None:
        super().__init__(source, rate=rate)
        self.text = text
        self._words = tuple(words)  # the source's: before trims and speed

    @property
    def words(self) -> tuple[Word, ...]:
        """其词语，按顺序排列，以及每个词被说出的时间（以从其开始的秒数为单位）：
        voice 提供的，或从音频中估算的；裁剪或变速会随
        音频移动它们。"""
        if not self._words:
            self._words = estimate(self.text, _source_samples(self))
        e = self._edit
        if e.start == 0 and e.speed == 1 and e.end is None:
            return self._words
        end = math.inf if e.end is None else e.end
        return tuple(
            Word(w.text, (w.start - e.start) / e.speed, (w.end - e.start) / e.speed)
            for w in self._words
            if e.start <= w.start < end
        )


type Voice = Callable[[str], Speech]
"""任何能说话的东西：一个从文本到 [`Speech`][manimgx.audio.Speech] 的函数。引入任何
文本转语音：将其调用包装在一个返回 `Speech(audio, text=text)` 的函数中。"""


# ── timing ───────────────────────────────────────────────────────────────────────────────


_WORD = re.compile(r"\S+")


def estimate(text: str, samples: np.ndarray) -> tuple[Word, ...]:
    """`text` 中每个词在 `samples` 中被说出的时间，估算得出：音频的发声跨度
    按词语的字母数分配给各词，逗号或句号后的停顿会获得更多份额。"""
    words = _WORD.findall(text)
    if not words:
        return ()
    level = np.abs(samples).max(axis=1) if samples.ndim > 1 else np.abs(samples)
    hop = RATE // 100  # 10 ms
    frames = len(level) // hop
    loud = level[: frames * hop].reshape(frames, hop).max(axis=1) > 0.02
    voiced = np.flatnonzero(loud)
    if not len(voiced):
        total = len(samples) / RATE
        return tuple(
            Word(w, total * i / len(words), total * (i + 1) / len(words))
            for i, w in enumerate(words)
        )
    first, last = voiced[0], voiced[-1] + 1
    # weight: letters, plus a pause after a comma or a full stop
    weights = []
    for w in words:
        weights.append(len(w) + (6 if w[-1] in ".!?:;" else 3 if w[-1] == "," else 1))
    total_weight = sum(weights)
    edges = np.concatenate([[0], np.cumsum(weights)]) / total_weight
    span = (last - first) / 100
    times = first / 100 + edges * span
    return tuple(
        Word(
            w,
            float(times[i]),
            float(times[i + 1] - (weights[i] - len(w)) / total_weight * span),
        )
        for i, w in enumerate(words)
    )


@deprecated("ManimGX's machinery: the captions call it", category=None)
def lines(speech: Speech, width: int = 42) -> list[tuple[float, float, str]]:
    """将语音转为字幕：其词语排成每行最多 `width` 个字符的行，在句子结束时
    换行，每行从其第一个词的开始处显示到下一行的
    （或其最后一个词的结束处），以从语音开始的秒数为单位。"""
    out: list[tuple[float, float, str]] = []
    line: list[Word] = []
    for word in speech.words:
        if line and len(" ".join(w.text for w in line)) + 1 + len(word.text) > width:
            out.append((line[0].start, word.start, " ".join(w.text for w in line)))
            line = []
        line.append(word)
        if word.text[-1] in ".!?":
            out.append((line[0].start, word.end, " ".join(w.text for w in line)))
            line = []
    if line:
        out.append((line[0].start, line[-1].end, " ".join(w.text for w in line)))
    return out


# ── the script: [spans] in the text ─────────────────────────────────────────────────────

_SPAN = re.compile(r"\[([^\[\]]*)\]")


@deprecated("ManimGX's machinery: say calls it", category=None)
def spans(script: str) -> tuple[str, list[tuple[int, int]]]:
    """脚本的文本，其方括号已去除，以及每个方括号片段在该
    文本中的字符位置：`"Here is [a circle]."` 为 `("Here is a circle.", [(8, 16)])`。"""
    text, found, at = [], [], 0
    shift = 0
    for m in _SPAN.finditer(script):
        text.append(script[at : m.start()])
        begin = m.start() - shift
        found.append((begin, begin + len(m.group(1))))
        text.append(m.group(1))
        at, shift = m.end(), shift + 2
    text.append(script[at:])
    return "".join(text), found


@deprecated("ManimGX's machinery: say calls it", category=None)
def times(speech: Speech, span: tuple[int, int]) -> tuple[float, float]:
    """语音文本中 `span` 字符被说出的时间：从其第一个词的开始到
    其最后一个词的结束；空片段为其前面那个词的开始。
    """
    begin, end = span
    words = speech.words
    located = [(m.start(), m.end()) for m in _WORD.finditer(speech.text)]
    inside = [i for i, (a, b) in enumerate(located) if a < end and b > begin] or [
        next((i for i, (a, _) in enumerate(located) if a >= begin), len(words) - 1)
    ]
    first, last = inside[0], inside[-1]
    if begin == end:
        return words[first].start, words[first].start
    return words[first].start, words[last].end


# ── the cache: what a voice said, kept ──────────────────────────────────────────────────


def cached(voice: Voice, text: str, folder: Path) -> Speech:
    """`voice` 为 `text` 说出的内容：说出一次，然后保存在 `folder` 中，作为其音频和
    一个包含其词语的 JSON，以文本以及 voice 和文本的摘要命名。

    音频可以被替换（相同词语的录音，引擎能读取的任何格式，
    同名文件下）：其词语随后从它重新计时。
    """
    from manimgx._engine import digest

    identity = _identity(voice)
    key = f"{digest(identity.encode(), b'\0', text.encode()):016x}"
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]
    stem = folder / f"{slug}-{key[:10]}"
    meta = stem.with_suffix(".json")
    if meta.exists():
        record = json.loads(meta.read_text(encoding="utf-8"))
        audio = stem.with_suffix(record["suffix"]).read_bytes()
        same = record.get("audio") == f"{digest(audio):016x}"
        words = [Word(*w) for w in record["words"]] if same else []
        speech = Speech(audio, text=text, words=words)
        speech._edit = _Edit(**record.get("edit", {}))
        return speech
    speech = voice(text)
    folder.mkdir(parents=True, exist_ok=True)
    suffix, data = _stored(speech)
    stem.with_suffix(suffix).write_bytes(data)
    meta.write_text(
        json.dumps(
            {
                "text": text,
                "voice": identity,
                "suffix": suffix,
                "audio": f"{digest(data):016x}",
                "edit": dataclasses.asdict(speech._edit),
                "words": [[w.text, w.start, w.end] for w in speech._words],
            },
            indent=1,
        )
        + "\n",  # a text file, to commit
        encoding="utf-8",
    )
    return speech


def _identity(voice: Voice) -> str:
    """在缓存中命名一个 voice 的依据：决定它说什么的因素。数据类的 repr（其
    设置；某个键被排除在外）；函数的名称、其代码及其持有的纯值（在其闭包、
    其默认值以及方法所绑定对象的字段中）；其他可调用对象的类型和纯字段。纯值
    是不可变的：字符串、数字、布尔值、None，或它们的元组——是 voice 的设置，
    而非其状态（客户端、它追加内容的列表）。"""
    if hasattr(voice, "__dataclass_fields__"):
        return repr(voice)
    fn = getattr(
        voice, "__func__", voice
    )  # a bound method: its function, and its object
    code = getattr(fn, "__code__", None)
    if code is None:  # an object with __call__
        return f"{type(voice).__module__}.{type(voice).__qualname__}{_fields(voice)!r}"
    from manimgx._engine import digest

    body = digest(marshal.dumps(_code(code)))
    cells = tuple(c.cell_contents for c in getattr(fn, "__closure__", None) or ())
    defaults = getattr(fn, "__defaults__", None) or ()
    keywords = getattr(fn, "__kwdefaults__", None) or {}
    held = (
        _plain(cells),
        _plain(defaults),
        _plain(tuple(sorted(keywords.items()))),
        _fields(getattr(voice, "__self__", None)),
    )
    name = f"{getattr(fn, '__module__', '')}.{getattr(fn, '__qualname__', '')}"
    return f"{name}#{body:016x}{held!r}"


def _code(code: CodeType) -> CodeType:
    """一个 voice 的代码，去除源位置信息，包括其嵌套函数。"""
    return code.replace(
        co_filename="",
        co_firstlineno=0,
        co_linetable=b"",
        co_consts=tuple(
            _code(c) if isinstance(c, CodeType) else c for c in code.co_consts
        ),
    )


def _fields(owner: object) -> tuple[tuple[str, object], ...]:
    """一个对象的纯字段，按其名称顺序排列。"""
    plain = ((k, _plain(v)) for k, v in sorted(getattr(owner, "__dict__", {}).items()))
    return tuple((k, v) for k, v in plain if v is not _OTHER)


def _plain(value: object) -> object:
    """若 `value` 是纯值（不可变：字符串、数字、布尔值、None，或它们的元组，
    其中其他项被排除），则返回 `value`；否则返回 `_OTHER`。"""
    if value is None or isinstance(value, str | int | float | bool | bytes):
        return value
    if isinstance(value, tuple):
        return tuple(v for v in map(_plain, value) if v is not _OTHER)
    return _OTHER


_OTHER = object()  # not a plain value: left out of a voice's name


def _stored(speech: Speech) -> tuple[str, bytes]:
    source = speech.source
    if isinstance(source, bytes):
        return _sniff(source), source
    if isinstance(source, np.ndarray):
        return ".wav", _wav(_source_samples(speech))
    path = Path(source)
    return path.suffix or ".bin", path.read_bytes()


def _sniff(data: bytes) -> str:
    if data[:4] == b"RIFF":
        return ".wav"
    if data[:4] == b"fLaC":
        return ".flac"
    if data[:4] == b"OggS":
        return ".ogg"
    if data[4:8] == b"ftyp":
        return ".m4a"
    return ".mp3"


def _wav(samples: np.ndarray) -> bytes:
    """在 RATE 下的浮点采样点，作为 32 位浮点 WAV 文件。"""
    data = np.ascontiguousarray(samples, np.float32)
    channels = data.shape[1] if data.ndim > 1 else 1
    body = data.tobytes()
    header = b"".join(
        [
            b"RIFF",
            (36 + len(body)).to_bytes(4, "little"),
            b"WAVEfmt ",
            (16).to_bytes(4, "little"),
            (3).to_bytes(2, "little"),  # IEEE float
            channels.to_bytes(2, "little"),
            RATE.to_bytes(4, "little"),
            (RATE * 4 * channels).to_bytes(4, "little"),
            (4 * channels).to_bytes(2, "little"),
            (32).to_bytes(2, "little"),
            b"data",
            len(body).to_bytes(4, "little"),
        ]
    )
    return header + body


def timed(text: str, pieces: Sequence[tuple[str, float, float]]) -> tuple[Word, ...]:
    """`text` 的词语，由 voice 对其定时片段按顺序计时（其字符
    或其标记）：每个词从其第一个字母所在片段的开始到
    其最后一个字母所在片段的结束。若片段未拼出文本的字母
    （voice 将 "2" 说成 "two"）则为空：其词语随后被估算。"""
    # each letter of the pieces: its piece's times
    owner: list[tuple[float, float]] = []
    for piece, a, b in pieces:
        owner += [(a, b)] * sum(c.isalnum() for c in piece)
    letters = [c.lower() for c in text if c.isalnum()]
    spelled = [c.lower() for piece, _, _ in pieces for c in piece if c.isalnum()]
    if not letters or letters != spelled:
        return ()
    words, k = [], 0
    for m in _WORD.finditer(text):
        n = sum(c.isalnum() for c in m.group())
        if n:
            words.append(Word(m.group(), owner[k][0], owner[k + n - 1][1]))
            k += n
        else:  # punctuation: beside the preceding word, or the first following word
            at = words[-1].end if words else owner[0][0]
            words.append(Word(m.group(), at, at))
    return tuple(words)
