"""影片：一个场景的帧，由播放器绘制——每个对象一个视图和一条记录（`feed`）——
以及它的播放、声音、分段和字幕。形状与画笔按内容为键，仅抵达播放器一次；与前一帧
相同的帧会延长前者，除非它开启一个分段（一个关键帧）。帧送往视频、送往回调（由回调
绘制它想要的那些），或不送往任何地方（它们的记录仍会被创建）；每一次播放，在它结束
时，送往一个回调。声音在视频写入时被混入。
"""

import contextlib
import json
import os
from collections.abc import Callable
from dataclasses import asdict, dataclass
from fractions import Fraction
from typing import TYPE_CHECKING, Final, Literal, cast, get_args
from warnings import deprecated

from manimgx import _engine
from manimgx.animation import clock
from manimgx.config import config
from manimgx.rendering import feed
from manimgx.rendering.feed import CameraView, Feeder

if TYPE_CHECKING:
    import numpy as np

    from manimgx.animation.timeline import Animation
    from manimgx.audio.sound import Clip
    from manimgx.drawing.geometry import Path
    from manimgx.mobject import Mobject
    from manimgx.scene import Camera


X264Preset = Literal[
    "ultrafast",
    "superfast",
    "veryfast",
    "faster",
    "fast",
    "medium",
    "slow",
    "slower",
    "veryslow",
    "placebo",
]
"""x264 的预设，从最快到最慢。"""

DEFAULT_ENCODER_PRESET: Final[X264Preset] = cast(
    X264Preset, _engine.DEFAULT_ENCODER_PRESET
)
"""原生编码器的默认预设，由 Python 与命令行共用。"""
DEFAULT_ENCODER_CRF: Final[float] = _engine.DEFAULT_ENCODER_CRF
"""原生编码器的默认恒定速率因子。"""


class Frame:
    """影片的一帧，由影片发出时所示：显示为视频的第 `index` 到
    `index + repeat - 1` 帧。

    世界保持静止的一帧只发出一次，显示 `repeat` 次。它的像素仅在
    被请求时才绘制，由 [`pixels`][manimgx.rendering.film.Frame.pixels] 完成。

    Args:
        index: 它在影片中的位置：它作为首帧显示时的帧号。
        repeat: 它显示的帧数。
        draw: 绘制其像素的函数。
        key: 它是否开启影片的一个分段。
    """

    __slots__ = ("_draw", "index", "key", "repeat")

    def __init__(
        self, index: int, repeat: int, draw: Callable[[], bytes], key: bool = False
    ) -> None:
        self.index = index
        """它在影片中的位置：它作为首帧显示时的帧号，从
        0 起计。"""
        self.repeat = repeat
        """它显示的帧数：大于 1 表示一次保持。"""
        self.key = key
        """它是否开启影片的一个 [分段][manimgx.rendering.film.Section]：其前一分段
        结束时所停留的画面。"""
        self._draw = draw

    def pixels(self) -> bytes:
        """立即绘制该帧。

        绘制即一帧的代价：只为要保留的帧请求，且在影片发出下一帧之前。

        Returns:
            它的像素：RGBA，每通道一个字节，自顶向下逐行排列。
        """
        return self._draw()


type FrameSink = Callable[[Frame], object]
"""一个函数，影片发出每一帧时将其交给它，参数为一个
[`Frame`][manimgx.rendering.film.Frame]（见 [`Scene.render`][manimgx.Scene.render]）；其返回值
被忽略。它可以抛出 [`Cut`][manimgx.rendering.film.Cut] 以在此处结束影片。"""


@dataclass(frozen=True, slots=True)
class Play:
    """场景的一次播放或等待，由其影片所保留：它的编号、起止时刻，
    以及场景代码播放它的位置。"""

    index: int
    """它的编号，从 0 起计：播放与等待一并计数。"""
    start: Fraction
    """它开始的时刻，以场景时间的秒计，精确。"""
    end: Fraction
    """它结束的时刻，以场景时间的秒计，精确。"""
    where: tuple[str, int] | None
    """场景代码播放它的位置：manimgx 之外最内层调用的文件与行号；
    若无则为 None。"""


type SectionType = Literal[
    "default.normal",
    "presentation.normal",
    "presentation.skip",
    "presentation.loop",
    "presentation.complete_loop",
]
"""演示如何播放一个分段（Manim 的分段类型）：`normal` 在其结束时停下，
直至演示者继续；`skip` 自行继续；`loop` 反复播放它，直至演示者继续；
`complete_loop` 亦然，但先完成当前这一轮。"""


@dataclass(frozen=True, slots=True)
class Section:
    """影片的一个分段，由 [`next_section`][manimgx.Scene.next_section] 开启：它
    持续到下一分段开启，或影片结束。"""

    name: str
    """它的名字。"""
    start: Fraction
    """它开始的时刻，以场景时间的秒计：某一帧的时刻，精确。"""
    frame: int
    """它首帧的编号：视频的一个关键帧，播放器可从此处开始。"""
    type: SectionType
    """演示如何播放它。"""
    notes: str
    """演示者在此期间所读的内容。"""


@dataclass(frozen=True, slots=True)
class Caption:
    """影片的一条字幕：`text`，自 `start` 显示至 `end`，以场景时间的秒计。"""

    start: float
    end: float
    text: str


def _wav(sound: "np.ndarray") -> bytes:
    """以 WAV 文件表示的音轨：16 位，所有浏览器均可播放。"""
    import io
    import wave

    import numpy as np

    from manimgx.audio.sound import RATE

    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(sound.shape[1])
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((np.clip(sound, -1, 1) * 32767).round().astype("<i2").tobytes())
    return out.getvalue()


type Take = Callable[[bytes], object]
"""一个函数，在影片作为 take 录制时被交给影片的 take 字节（见 [`Film`][manimgx.rendering.film.Film]）：
即 manimgx 播放器所读取的流字节——上传信息、帧与备注，随后是影片的
声音与字幕——按序逐帧送达；其返回值被忽略。它可以抛出
[`Cut`][manimgx.rendering.film.Cut] 以在此处结束影片：此后不再向其发送任何内容（由
其观看者关闭的 [`Window`][manimgx.Window] 即如此）。"""


type PlayHook = Callable[[Play, tuple[Animation, ...]], object]
"""一个函数，在影片的每次播放或等待结束时被调用（见
[`Scene.render`][manimgx.Scene.render]），参数为该 [`Play`][manimgx.rendering.film.Play] 及
其播放的动画、播放结束时世界所处的状态；其返回值被忽略。它可以抛出
[`Cut`][manimgx.rendering.film.Cut] 以在此处结束影片。"""


class Cut(Exception):
    """影片的提前结束：由帧接收器、播放钩子或 take 抛出，使场景
    在此处停止。

    影片按现状关闭：其视频（若有）写入至已发出的最后一帧。
    """


@dataclass(frozen=True, slots=True)
class Export:
    """影片视频的制作情况：视频写入完成后 [`Film.export`][manimgx.Film.export] 所
    持有的内容。"""

    seconds: float
    """视频所耗时长，以秒计：自其开始（即场景开始渲染时）至
    其文件写入完成。"""
    x264: float
    """其中花在 x264（即 H.264 编码器，运行于其独立线程）上的
    秒数。"""
    converted: float
    """视频中为编码器转换的 16 × 16 像素块所占比例，从 0
    到 1：其余的相对前一帧未发生变化，被跳过。"""
    bytes: int
    """文件的大小，以字节计。"""


class Film:
    """一个场景的影片：它的帧（按发出顺序）、它的播放，以及它的声音、分段
    和字幕。

    [`Scene.render`][manimgx.Scene.render] 创建并返回一个影片。每一帧只发出一次：
    若有视频则编码入视频，若提供了 `frames` 则交予它；与前一帧相同的帧不会再次
    发出，而是延长前者。每一次播放在结束时被保留，若提供了 `plays` 则交予它。
    场景放置的声音在视频写入时混入其音轨。

    影片也可改为作为 take 录制：将引擎的工作写下——每个形状一次，随后每帧的
    视图与记录，最后是声音与字幕——供 ManimGX 的播放器随时播放：在
    [`Window`][manimgx.Window] 中、场景运行时实时播放（`manimgx preview`），或在
    浏览器中（Python 无 GPU，Pyodide 环境）。

    Args:
        video: 帧到来时编码入的 MP4 文件，若有。
        frames: 一个被交给每一帧的函数，参数为一个 [`Frame`][manimgx.rendering.film.Frame]
            （见 [`FrameSink`][manimgx.rendering.film.FrameSink]）。
        plays: 一个在每次播放结束时被调用的函数（见
            [`PlayHook`][manimgx.rendering.film.PlayHook]）。
        take: 一个在影片作为 take 录制时被逐帧交给 take 字节的函数，若有
            （见 [`Take`][manimgx.rendering.film.Take]）。
        preset: 视频编码所用的 x264 预设：越快的预设产生越大的文件。
        crf: 视频的质量，以 x264 的恒定速率因子表示，从 0 到 51：
            越低越好，默认值为 18。
    """

    def __init__(
        self,
        video: str | os.PathLike[str] | None = None,
        *,
        frames: FrameSink | None = None,
        plays: PlayHook | None = None,
        take: Take | None = None,
        preset: X264Preset = DEFAULT_ENCODER_PRESET,
        crf: float = DEFAULT_ENCODER_CRF,
    ) -> None:
        if preset not in get_args(X264Preset):
            raise ValueError(f"unknown x264 preset {preset!r}")
        if not 0 <= crf <= 51:
            raise ValueError(
                f"x264 CRF must be a finite number from 0 to 51, not {crf}"
            )
        fps = config.frame_rate
        if video is not None and fps != int(fps):
            raise ValueError(
                f"a video needs a whole number of frames per second, not {fps}"
            )
        width, height = config.pixel_width, config.pixel_height
        if video is not None and (width % 2 or height % 2):  # H.264's 4:2:0 halves both
            raise ValueError(
                f"a video needs an even width and height, not {width}x{height}"
            )
        self.fps = clock.rational(fps)
        """影片每秒的帧数：影片开始时配置所定的值。"""
        # the GPU draws the film; or its take is recorded, to be drawn by ManimGX's player: by
        # choice, or where the engine has no GPU (in Pyodide)
        self._player: _engine.Player | None = None
        self._recorder: _engine.Recorder | None = None
        drawn: _engine.Player | _engine.Recorder
        if take is None and (gpu := feed.Player) is not None:
            if video is not None or frames is not None:
                _engine.start_gpu()  # the film draws: the GPU comes up as it begins
            self._player = drawn = gpu(width, height)
            if video is not None:
                drawn.begin_export(
                    os.fspath(video), fps=int(fps), preset=preset, crf=crf
                )
        elif video is None and frames is None:
            self._recorder = drawn = _engine.Recorder(width, height, fps)
        else:
            raise ValueError(
                "a film recorded as a take is drawn by ManimGX's player, not here: it"
                " has no video or pixels"
                + ("" if feed.Player else " (this Python has no GPU)")
            )
        self._take = take
        self.feeder = Feeder(width, height, drawn)
        self.video = None if video is None else os.fspath(video)
        """正在写入的视频路径；写入完成后为 None，若无视频
        则始终为 None。"""
        self.frames = frames
        """每个已绘制的帧被交予的函数，若有。"""
        self.frame_count = 0
        """影片迄今为止的帧数，保持帧按其持续的帧数计入。"""
        self.plays: list[Play] = []
        """场景已运行的播放与等待，按顺序排列：每个为一个
        [`Play`][manimgx.rendering.film.Play]。"""
        self.sections: list[Section] = [
            Section("unnamed", Fraction(0), 0, "default.normal", "")
        ]
        """影片的分段，按顺序排列：每个为一个 [`Section`][manimgx.rendering.film.Section]，
        持续到下一分段开始。第一个分段随影片开始。"""
        self.subcaptions: list[Caption] = []
        """场景添加的字幕（见
        [`add_subcaption`][manimgx.Scene.add_subcaption]）；[`captions`]
        [manimgx.Film.captions] 会并入其语音产生的字幕。"""
        self.clips: list[Clip] = []
        """场景放置的声音，按放置顺序排列：每个为一个
        [`Clip`][manimgx.audio.sound.Clip]，自其在场景时间中的起点计。"""
        self.export: Export | None = None
        """视频的制作情况，视频写入完成后为一个
        [`Export`][manimgx.rendering.film.Export]；在此之前以及无视频时为 None。"""
        self._hook = plays
        self._pending: tuple[bytes, bytes, list[CameraView], int] | None = (
            None  # sent once it ends
        )
        self._first = 0  # the index of the pending frame
        self._key = False  # the next frame begins a section: a keyframe of its own
        self._pending_key = False  # the pending frame is one

    def soundtrack(self) -> "np.ndarray | None":
        """影片的声音：其各片段在其时长上混音的结果，采样率为
        [`RATE`][manimgx.audio.sound.RATE] 每秒采样数，每通道一列；若场景
        未放置任何声音则为 None。"""
        from manimgx.audio.sound import mix

        return mix(self.clips, self.frame_count / self.fps)

    @deprecated("ManimGX's machinery: the scene calls it", category=None)
    def section(
        self, name: str, start: Fraction, type: SectionType, notes: str
    ) -> None:
        """在下一帧处开启一个分段，该帧自 `start` 开始：场景调用它
        （见 [`next_section`][manimgx.Scene.next_section]）。尚无帧的分段
        让位于它。

        Args:
            name: 它的名字。
            start: 它开始的时刻：下一帧的时刻。
            type: 演示如何播放它。
            notes: 演示者在此期间所读的内容。
        """
        if self.sections[-1].frame == self.frame_count:
            self.sections.pop()
        self.sections.append(Section(name, start, self.frame_count, type, notes))
        self._key = True
        self._note({"section": asdict(self.sections[-1])})

    def cut(self) -> list[tuple["Clip", float]]:
        """影片结尾所截短的声音：每个片段及其损失的秒数。"""
        end = self.frame_count / self.fps
        out = []
        for clip in self.clips:
            if clip.end is None and clip.sound.duration != float("inf"):
                lost = float(clip.start) + clip.sound.duration - float(end)
                if lost > 1e-3:
                    out.append((clip, lost))
        return out

    def subtitles(self) -> str:
        """影片的 [`captions`][manimgx.Film.captions] 以 SubRip（`.srt`）
        格式表示的字幕：播放器、编辑器与视频站点在视频旁所读的内容。"""

        def stamp(t: float) -> str:
            ms = round(t * 1000)
            return f"{ms // 3_600_000:02d}:{ms // 60_000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"

        return "".join(
            f"{i}\n{stamp(c.start)} --> {stamp(c.end)}\n{c.text}\n\n"
            for i, c in enumerate(self.captions(), 1)
        )

    def captions(self) -> list[Caption]:
        """影片的字幕，按其开始时刻排序：场景添加的那些，以及其语音
        产生的那些——按所说时刻分成每行数词一行。"""
        from manimgx.audio import Speech, lines

        spoken = [
            Caption(float(clip.start) + a, float(clip.start) + b, text)
            for clip in self.clips
            if isinstance(clip.sound, Speech)
            for a, b, text in lines(clip.sound)
        ]
        return sorted(self.subcaptions + spoken, key=lambda c: c.start)

    @deprecated("ManimGX's machinery: the scene calls it", category=None)
    def played(self, play: Play, animations: "tuple[Animation, ...]") -> None:
        """保留一次已结束的播放，并连同其播放的动画交给播放钩子：
        场景在每次播放结束时调用它，参数为播放结束时世界所处的状态。

        Args:
            animations: 它所播放的内容。
        """
        # the film keeps the play, not the animations: they hold their objects' copies
        self.plays.append(play)
        if self._recorder is not None:
            self._note({"play": asdict(play)})
        if self._hook is not None:
            self._hook(play, animations)

    @deprecated("ManimGX's machinery: the scene calls it", category=None)
    def picture(self, camera: "Camera", mobjects: "list[Mobject]") -> bytes:
        """按 `camera` 当前所见绘制世界：一张图片，而非影片的一帧。

        Args:
            camera: 观看它所用的相机。
            mobjects: 所绘制的 mobject，按绘制顺序排列。

        Returns:
            它的像素：RGBA，每通道一个字节，自顶向下逐行排列。
        """
        view, records, cameras = self.feeder.frame(camera, mobjects)
        if self._player is None:
            raise RuntimeError("a film recorded as a take is drawn by ManimGX's player")
        if self._player.pressured():
            self.feeder.sweep([records, *[c[4] for c in cameras]], pressed=True)
        return self._player.render(view, records, cameras)

    @deprecated("ManimGX's machinery: the scene calls it", category=None)
    def record(
        self, camera: "Camera", mobjects: "list[Mobject]", repeat: int = 1
    ) -> None:
        """录制一帧：mobject 按 `camera` 所见，显示 `repeat`
        帧。

        场景为它计算的每一帧调用它。

        Args:
            camera: 观看该帧所用的相机。
            mobjects: 所绘制的 mobject，按绘制顺序排列（见
                [`display_list`][manimgx.Scene.display_list]）。
            repeat: 它显示的帧数。
        """
        view, records, cameras = self.feeder.frame(camera, mobjects)
        self._add(view, records, cameras, repeat)

    @deprecated("ManimGX's machinery: the scene calls it", category=None)
    def tween(
        self,
        camera: "Camera",
        mobjects: "list[Mobject]",
        leaves: "list[tuple[Mobject, list[Mobject], Path, np.ndarray, np.ndarray]]",
    ) -> None:
        """一次性录制某次播放在关键帧之间仅移动其叶子的各帧：
        场景为这类播放调用它。

        Args:
            camera: 观看这些帧所用的相机。
            mobjects: 所绘制的 mobject，按绘制顺序排列。
            leaves: 对每个移动的叶子：该叶子、其关键帧、其路径，以及每帧
                所处区间与沿路径的时间（-1 表示该条目未声明的帧）。
        """
        for view, records in self.feeder.tween(camera, mobjects, leaves):
            self._add(view, records, [], 1)

    def _add(
        self, view: bytes, records: bytes, cameras: list[CameraView], repeat: int
    ) -> None:
        pending = self._pending
        if (
            pending is not None
            and not self._key
            and pending[:3] == (view, records, cameras)
        ):
            self._pending = (view, records, cameras, pending[3] + repeat)
        else:
            self._send()
            self._pending = (view, records, cameras, repeat)
            self._first = self.frame_count
            self._pending_key, self._key = self._key, False
        self.frame_count += repeat

    def _send(self) -> None:
        pending, self._pending = self._pending, None
        if pending is None:
            return
        view, records, cameras, repeat = pending
        if self._recorder is not None:
            self._recorder.frame(view, records, repeat, cameras)
            self._flush()
        if (player := self._player) is None:
            return
        if (self.video is not None or self.frames is not None) and player.pressured():
            self.feeder.sweep([records, *[c[4] for c in cameras]], pressed=True)
        key = self._pending_key
        if self.frames is None:
            if self.video is not None:
                player.push(view, records, repeat, cameras, key)
            return
        sent = self.video is None

        def push() -> None:
            nonlocal sent
            if not sent:
                player.push(view, records, repeat, cameras, key)
                sent = True

        def draw() -> bytes:
            nonlocal sent
            if sent:
                return player.render(view, records, cameras)
            # A pixel consumer and the encoder share one completed GPU draw. Defer export
            # until the callback asks: metadata-only callbacks keep the asynchronous path.
            pixels = player.push(view, records, repeat, cameras, key, capture=True)
            sent = True
            assert pixels is not None
            return pixels

        try:
            self.frames(Frame(self._first, repeat, draw, key))
        except Cut:
            push()  # the frame that cuts a film still belongs to its video
            raise
        push()

    @deprecated("ManimGX's machinery: the scene calls it", category=None)
    def close(self) -> None:
        """关闭影片：发出其最后一帧，并写入其视频（若有）。

        [`Scene.render`][manimgx.Scene.render] 在场景结束时调用它。为最后一帧抛出的
        [`Cut`][manimgx.rendering.film.Cut] 同样会结束影片；任何其他错误将放弃视频。
        """
        try:
            with contextlib.suppress(Cut):
                self._send()
            with contextlib.suppress(Cut):  # its take cut it: it hears no more
                self._end()
        except BaseException:
            self.abort()
            raise

    def _end(self) -> None:
        """写入已关闭影片的视频（若有），并告知其 take 它如何结束。"""
        if self.video is not None and self._player is not None:
            sound = self.soundtrack()
            if sound is None:
                self.export = Export(*self._player.end_export())
            else:
                from manimgx.audio.sound import BITRATE, RATE

                channels = sound.shape[1]
                self.export = Export(
                    *self._player.end_export(
                        sound.tobytes(), channels, RATE, BITRATE * channels
                    )
                )
            self.video = None
        if self._recorder is not None:
            # what the player plays and shows beside the frames; then the take's end
            if (sound := self.soundtrack()) is not None:
                self._recorder.sound(_wav(sound))
            if captions := self.captions():
                self._note({"captions": [asdict(c) for c in captions]})
            self._recorder.end()
            self._flush()

    @deprecated("ManimGX's machinery: the scene calls it", category=None)
    def abort(self) -> None:
        """停止影片但不写入其视频；若其作为 take 录制，该 take 以
        声明其场景失败的方式结束。

        [`Scene.render`][manimgx.Scene.render] 在场景失败时调用它。
        """
        if self.video is not None and self._player is not None:
            self.video = None
            self._player.abort_export()
        if self._recorder is not None:
            # its take keeps what was made until the scene failed, and ends saying so: a player
            # drops it, unless it shows it already
            pending, self._pending = self._pending, None
            if pending is not None:
                view, records, cameras, repeat = pending
                self._recorder.frame(view, records, repeat, cameras)
            self._recorder.end(failed=True)
            with contextlib.suppress(Cut):  # cut already: it hears nothing more
                self._flush()

    def _note(self, note: dict[str, object]) -> None:
        """以 JSON 向 take 的展示者告知影片自身的记录（精确时刻
        表示为 float）：一次已结束的播放、一个分段、字幕。"""
        if self._recorder is not None:
            self._recorder.note(json.dumps(note, default=float))
            self._flush()

    def _flush(self) -> None:
        """将此后所录制的内容交给 take（若无对象可交则丢弃）；一旦
        它截断了影片，便不再向其交付任何内容。"""
        if self._recorder is not None:
            data = self._recorder.drain()
            if self._take is not None and data:
                try:
                    self._take(data)
                except Cut:
                    self._take = None
                    raise
