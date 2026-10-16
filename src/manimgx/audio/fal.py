"""fal.ai 的文本转语音模型，作为声音使用：`Fal(model, **settings)`。

[fal](https://fal.ai) 在一套 API 和一个密钥背后运行文本转语音模型。`Fal` 支持以下
模型：

| 模型 | 其设置 | 单词时间 |
| --- | --- | --- |
| `fal-ai/elevenlabs/tts/eleven-v3`（默认） | [`ElevenV3`][manimgx.audio.fal.ElevenV3] | 由模型给出 |
| `fal-ai/minimax/speech-2.8-hd` | [`MiniMax`][manimgx.audio.fal.MiniMax] | 估算 |
| `google/gemini-3.8-flash-tts` | [`Gemini`][manimgx.audio.fal.Gemini] | 估算 |
| `fal-ai/inworld-tts` | [`Inworld`][manimgx.audio.fal.Inworld] | 估算 |
| `fal-ai/qwen-3-tts/text-to-speech/1.7b` | [`Qwen`][manimgx.audio.fal.Qwen] | 估算 |

每个模型接受各自的设置，按模型进行类型标注：类型检查器知道某个模型接受哪些设置
以及哪些取值（比如它的声音），而 `Fal` 在构造时会检查设置名称是否合法。密钥取自
`FAL_KEY`（fal 的控制台会提供一个），或通过 `key=` 传入；它从不在缓存中命名声音。
"""

import json
import math
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Literal, Unpack, overload

from typing_extensions import TypedDict

from manimgx.audio.sound import Speech, timed

# ── the models' settings, as their schemas on fal have them ────────────────────────────────


class ElevenV3(TypedDict, total=False, closed=True):
    """ElevenLabs 的 Eleven v3（`fal-ai/elevenlabs/tts/eleven-v3`）的设置，该模型会为
    其单词计时。其文本可携带音频标签：`[whispers]`、`[laughs]`、`[excited]`……"""

    voice: str
    """ElevenLabs 声音库中某个声音的名称或 ID：Aria、Roger、Sarah、Laura、Charlie、
    George、Callum、River、Liam、Charlotte、Alice、Matilda、Will、Jessica、Eric、Chris、
    Brian、Daniel、Lily、Bill……（默认 "Rachel"）。"""
    stability: float
    """声音的稳定程度，从 0（富有表现力）到 1（稳定）（默认 0.5）。"""
    language_code: str | None
    """语言，以 ISO 639-1 代码表示（"en"、"de"……）（默认：文本自身的语言）。"""
    apply_text_normalization: Literal["auto", "on", "off"]
    """数字等内容在朗读前是否拼读出来（默认 "auto"：由模型自行判断）。"""


class MiniMaxVoice(TypedDict, total=False):
    """一个 MiniMax 声音及其说话方式。"""

    voice_id: str
    """声音：Wise_Woman、Friendly_Person、Inspirational_girl、Deep_Voice_Man、Calm_Woman、
    Casual_Guy、Lively_Girl、Patient_Man、Young_Knight、Determined_Man、Lovely_Girl、
    Decent_Boy、Imposing_Manner、Elegant_Man、Abbess、Sweet_Girl_2、Exuberant_Girl，或
    克隆声音的 ID（默认 "Wise_Woman"）。"""
    speed: float
    """语速，从 0.5 到 2（默认 1）。"""
    vol: float
    """音量，从 0.01 到 10（默认 1）。"""
    pitch: int
    """音高，以半音为单位，从 -12 到 12（默认 0）。"""
    emotion: (
        Literal["happy", "sad", "angry", "fearful", "disgusted", "surprised", "neutral"]
        | None
    )
    """说话时带有的情绪（默认：按文本语气而定）。"""
    english_normalization: bool
    """英文数字是否朗读得更仔细、稍慢一些（默认 False）。"""


class MiniMaxAudio(TypedDict, total=False):
    """MiniMax 生成的音频。"""

    sample_rate: Literal[8000, 16000, 22050, 24000, 32000, 44100]
    """每秒采样数（默认 32000）。"""
    bitrate: Literal[32000, 64000, 128000, 256000]
    """每秒比特数，用于 MP3（默认 128000）。"""
    format: Literal["mp3", "flac"]
    """文件格式（默认 "mp3"）。"""
    channel: Literal[1, 2]
    """声道数：1（单声道）或 2（立体声）（默认 1）。"""


class MiniMaxLoudness(TypedDict, total=False):
    """MiniMax 如何均衡音频响度。"""

    enabled: bool
    """是否启用（默认 True）。"""
    target_loudness: float
    """目标响度，以 LUFS 为单位，从 -70 到 -10（默认 -18）。"""
    target_range: float
    """响度范围，以 LU 为单位，从 0 到 20（默认 8）。"""
    target_peak: float
    """最高峰值，以 dBTP 为单位，从 -3 到 0（默认 -0.5）。"""


class MiniMaxTimbre(TypedDict, total=False):
    """MiniMax 如何改变声音本身。"""

    pitch: int
    """更高或更低，从 -100 到 100（默认 0）。"""
    intensity: int
    """更强或更弱，从 -100 到 100（默认 0）。"""
    timbre: int
    """音色的色彩，从 -100 到 100（默认 0）。"""


class MiniMaxPronunciation(TypedDict, total=False):
    """MiniMax 如何读特定词语。"""

    tone_list: list[str]
    """每个词及其发音：`"text/(pronunciation)"`（中文声调 1 到 5：
    `"燕少飞/(yan4)(shao3)(fei1)"`）。"""


class MiniMax(TypedDict, total=False, closed=True):
    """MiniMax Speech 2.8 HD（`fal-ai/minimax/speech-2.8-hd`）的设置。其文本可携带
    停顿 `<#0.5#>`（以秒为单位）以及感叹词：`(laughs)`、`(sighs)`、`(coughs)`、
    `(clears throat)`、`(gasps)`、`(sniffs)`、`(groans)`、`(yawns)`。"""

    voice_setting: MiniMaxVoice
    """声音及其说话方式（[`MiniMaxVoice`][manimgx.audio.fal.MiniMaxVoice]）。"""
    audio_setting: MiniMaxAudio
    """生成的音频（[`MiniMaxAudio`][manimgx.audio.fal.MiniMaxAudio]）。"""
    language_boost: (
        Literal[
            "Chinese",
            "Chinese,Yue",
            "English",
            "Arabic",
            "Russian",
            "Spanish",
            "French",
            "Portuguese",
            "German",
            "Turkish",
            "Dutch",
            "Ukrainian",
            "Vietnamese",
            "Indonesian",
            "Japanese",
            "Italian",
            "Korean",
            "Thai",
            "Polish",
            "Romanian",
            "Greek",
            "Czech",
            "Finnish",
            "Hindi",
            "Bulgarian",
            "Danish",
            "Hebrew",
            "Malay",
            "Slovak",
            "Swedish",
            "Croatian",
            "Hungarian",
            "Norwegian",
            "Slovenian",
            "Catalan",
            "Nynorsk",
            "Afrikaans",
            "auto",
        ]
        | None
    )
    """模型所关注的一种语言或方言（默认：无）。"""
    normalization_setting: MiniMaxLoudness
    """如何均衡响度
    （[`MiniMaxLoudness`][manimgx.audio.fal.MiniMaxLoudness]）。"""
    voice_modify: MiniMaxTimbre | None
    """如何改变声音本身（[`MiniMaxTimbre`][manimgx.audio.fal.MiniMaxTimbre]）。"""
    pronunciation_dict: MiniMaxPronunciation | None
    """如何读特定词语
    （[`MiniMaxPronunciation`][manimgx.audio.fal.MiniMaxPronunciation]）。"""


class Gemini(TypedDict, total=False, closed=True):
    """Google 的 Gemini 3.8 Flash TTS（`google/gemini-3.8-flash-tts`）的设置。其文本可
    携带发声事件：`<laugh>`、`<sigh>`。"""

    voice: Literal[
        "Achernar",
        "Achird",
        "Algenib",
        "Algieba",
        "Alnilam",
        "Aoede",
        "Autonoe",
        "Callirrhoe",
        "Charon",
        "Despina",
        "Enceladus",
        "Erinome",
        "Fenrir",
        "Gacrux",
        "Iapetus",
        "Kore",
        "Laomedeia",
        "Leda",
        "Orus",
        "Pulcherrima",
        "Puck",
        "Rasalgethi",
        "Sadachbia",
        "Sadaltager",
        "Schedar",
        "Sulafat",
        "Umbriel",
        "Vindemiatrix",
        "Zephyr",
        "Zubenelgenubi",
    ]
    """声音（默认 "Kore"）。"""
    style_instructions: str | None
    """以文字描述如何朗读，例如："Warm and unhurried, like a patient teacher."（默认：
    无）。"""


class Inworld(TypedDict, total=False, closed=True):
    """Inworld TTS-1.5 Max（`fal-ai/inworld-tts`）的设置，每行最多可朗读 2,000 个
    字符。"""

    voice: Literal[
        "Loretta (en)",
        "Darlene (en)",
        "Marlene (en)",
        "Hank (en)",
        "Evelyn (en)",
        "Celeste (en)",
        "Pippa (en)",
        "Tessa (en)",
        "Liam (en)",
        "Callum (en)",
        "Hamish (en)",
        "Abby (en)",
        "Graham (en)",
        "Rupert (en)",
        "Mortimer (en)",
        "Snik (en)",
        "Anjali (en)",
        "Saanvi (en)",
        "Arjun (en)",
        "Claire (en)",
        "Oliver (en)",
        "Simon (en)",
        "Elliot (en)",
        "James (en)",
        "Serena (en)",
        "Gareth (en)",
        "Vinny (en)",
        "Lauren (en)",
        "Jessica (en)",
        "Ethan (en)",
        "Tyler (en)",
        "Jason (en)",
        "Chloe (en)",
        "Veronica (en)",
        "Victoria (en)",
        "Miranda (en)",
        "Sebastian (en)",
        "Victor (en)",
        "Malcolm (en)",
        "Kayla (en)",
        "Nate (en)",
        "Jake (en)",
        "Brian (en)",
        "Amina (en)",
        "Kelsey (en)",
        "Derek (en)",
        "Grant (en)",
        "Evan (en)",
        "Alex (en)",
        "Ashley (en)",
        "Craig (en)",
        "Deborah (en)",
        "Dennis (en)",
        "Edward (en)",
        "Elizabeth (en)",
        "Hades (en)",
        "Julia (en)",
        "Pixie (en)",
        "Mark (en)",
        "Olivia (en)",
        "Priya (en)",
        "Ronald (en)",
        "Sarah (en)",
        "Shaun (en)",
        "Theodore (en)",
        "Timothy (en)",
        "Wendy (en)",
        "Dominus (en)",
        "Hana (en)",
        "Clive (en)",
        "Carter (en)",
        "Blake (en)",
        "Luna (en)",
        "Yichen (zh)",
        "Xiaoyin (zh)",
        "Xinyi (zh)",
        "Jing (zh)",
        "Erik (nl)",
        "Katrien (nl)",
        "Lennart (nl)",
        "Lore (nl)",
        "Alain (fr)",
        "Hélène (fr)",
        "Mathieu (fr)",
        "Étienne (fr)",
        "Johanna (de)",
        "Josef (de)",
        "Gianni (it)",
        "Orietta (it)",
        "Asuka (ja)",
        "Satoshi (ja)",
        "Hyunwoo (ko)",
        "Minji (ko)",
        "Seojun (ko)",
        "Yoona (ko)",
        "Szymon (pl)",
        "Wojciech (pl)",
        "Heitor (pt)",
        "Maitê (pt)",
        "Diego (es)",
        "Lupita (es)",
        "Miguel (es)",
        "Rafael (es)",
        "Svetlana (ru)",
        "Elena (ru)",
        "Dmitry (ru)",
        "Nikolai (ru)",
        "Riya (hi)",
        "Manoj (hi)",
        "Yael (he)",
        "Oren (he)",
        "Nour (ar)",
        "Omar (ar)",
    ]
    """声音，及其所属语言（默认 "Craig (en)"）。"""
    sample_rate_hertz: Literal[8000, 16000, 24000, 32000, 40000, 48000]
    """每秒采样数（默认 48000）。"""


class Qwen(TypedDict, total=False, closed=True):
    """阿里巴巴的 Qwen3-TTS 1.7B（`fal-ai/qwen-3-tts/text-to-speech/1.7b`）的设置。"""

    voice: (
        Literal[
            "Vivian",
            "Serena",
            "Uncle_Fu",
            "Dylan",
            "Eric",
            "Ryan",
            "Aiden",
            "Ono_Anna",
            "Sohee",
        ]
        | None
    )
    """声音（默认：由模型决定）。"""
    language: Literal[
        "Auto",
        "English",
        "Chinese",
        "Spanish",
        "French",
        "German",
        "Italian",
        "Japanese",
        "Korean",
        "Portuguese",
        "Russian",
    ]
    """语言（默认 "Auto"：文本自身的语言）。"""
    prompt: str | None
    """以文字描述如何朗读（而非朗读什么内容）（默认：无）。"""
    speaker_voice_embedding_file_url: str | None
    """克隆声音：由 `fal-ai/qwen-3-tts/clone-voice` 生成的说话人嵌入的 URL；它会覆盖
    `voice` 和 `prompt`（默认：无）。"""
    reference_text: str | None
    """克隆声音的录音所朗读的内容，有助于让合成声音更像原声（默认：无）。"""
    temperature: float | None
    """朗读的变化程度，大于 0 且不超过 1（默认 0.9）。"""
    top_k: int | None
    """采样：从 k 个最可能的声音中采样（默认 50）。"""
    top_p: float | None
    """采样：从累计概率达到 p 的最可能的声音中采样，0 到 1（默认 1）。"""
    repetition_penalty: float | None
    """避免自我重复的强度（默认 1.05）。"""
    subtalker_dosample: bool | None
    """第二阶段是否进行采样（默认 True）。"""
    subtalker_temperature: float | None
    """第二阶段的温度，0 到 1（默认 0.9）。"""
    subtalker_top_k: int | None
    """第二阶段的 top k（默认 50）。"""
    subtalker_top_p: float | None
    """第二阶段的 top p，0 到 1（默认 1）。"""
    max_new_tokens: int | None
    """生成声音的上限，以其编解码器的 token 数为单位，1 到 8192（此处默认 8192：fal
    自身的默认值 200 可能会把长句截断）。"""


type Model = Literal[
    "fal-ai/elevenlabs/tts/eleven-v3",
    "fal-ai/minimax/speech-2.8-hd",
    "google/gemini-3.8-flash-tts",
    "fal-ai/inworld-tts",
    "fal-ai/qwen-3-tts/text-to-speech/1.7b",
]
"""`Fal` 所使用的模型。"""


@dataclass(frozen=True, slots=True)
class _Spec:
    """模型的请求方式：文本所放入的输入字段、其设置、未显式指定时发送的默认值，
    以及始终发送的固定值。"""

    text: str
    settings: type
    defaults: tuple[tuple[str, object], ...] = ()
    fixed: tuple[tuple[str, object], ...] = ()


_MODELS: dict[str, _Spec] = {
    "fal-ai/elevenlabs/tts/eleven-v3": _Spec(
        "text", ElevenV3, fixed=(("timestamps", True),)
    ),
    "fal-ai/minimax/speech-2.8-hd": _Spec("prompt", MiniMax),
    "google/gemini-3.8-flash-tts": _Spec("prompt", Gemini),
    "fal-ai/inworld-tts": _Spec("text", Inworld),
    "fal-ai/qwen-3-tts/text-to-speech/1.7b": _Spec(
        "text", Qwen, defaults=(("max_new_tokens", 8192),)
    ),
}


# ── the voice ───────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True, init=False, repr=False)
class Fal:
    """fal.ai 上的文本转语音模型，作为声音使用：`Fal(model, **settings)`，其中
    settings 为该模型自身的设置（默认模型为
    [`ElevenV3`][manimgx.audio.fal.ElevenV3]）。

    Args:
        model: 模型在 fal 上的 ID。
        key: fal 的 API 密钥；默认取 `FAL_KEY`。
        **settings: 模型的设置。

    Examples:
        在场景类中定义一个声音：

        ```py
        voice = m.voices.Fal(
            "fal-ai/minimax/speech-2.8-hd",
            voice_setting={"voice_id": "Calm_Woman", "speed": 1.1},
        )
        ```
    """

    model: Model
    """模型在 fal 上的 ID。"""
    settings: dict[str, object]
    """模型的设置，按传入原样保存。"""
    key: str | None = field(default=None, compare=False)
    """fal 的 API 密钥，若已传入则使用之；否则在声音朗读时读取 `FAL_KEY`。"""

    @overload
    def __init__(
        self,
        model: Literal["fal-ai/elevenlabs/tts/eleven-v3"] = ...,
        /,
        *,
        key: str | None = None,
        **settings: Unpack[ElevenV3],
    ) -> None: ...
    @overload
    def __init__(
        self,
        model: Literal["fal-ai/minimax/speech-2.8-hd"],
        /,
        *,
        key: str | None = None,
        **settings: Unpack[MiniMax],
    ) -> None: ...
    @overload
    def __init__(
        self,
        model: Literal["google/gemini-3.8-flash-tts"],
        /,
        *,
        key: str | None = None,
        **settings: Unpack[Gemini],
    ) -> None: ...
    @overload
    def __init__(
        self,
        model: Literal["fal-ai/inworld-tts"],
        /,
        *,
        key: str | None = None,
        **settings: Unpack[Inworld],
    ) -> None: ...
    @overload
    def __init__(
        self,
        model: Literal["fal-ai/qwen-3-tts/text-to-speech/1.7b"],
        /,
        *,
        key: str | None = None,
        **settings: Unpack[Qwen],
    ) -> None: ...
    def __init__(
        self,
        model: Model = "fal-ai/elevenlabs/tts/eleven-v3",
        /,
        *,
        key: str | None = None,
        **settings: object,
    ) -> None:
        spec = _MODELS.get(model)
        if spec is None:
            raise ValueError(f"fal: no model {model!r} here: {', '.join(_MODELS)}")
        known = spec.settings.__annotations__
        if unknown := sorted(settings.keys() - known.keys()):
            raise TypeError(
                f"{model} takes {', '.join(known)}; not {', '.join(unknown)}"
            )
        object.__setattr__(self, "model", model)
        object.__setattr__(
            self, "settings", {k: _ordered(v) for k, v in sorted(settings.items())}
        )
        object.__setattr__(self, "key", key)

    def __repr__(self) -> str:
        """构造它的调用形式，不含密钥：即在缓存中命名它的字符串。"""
        given = "".join(f", {k}={v!r}" for k, v in self.settings.items())
        return f"Fal({self.model!r}{given})"

    def __call__(self, text: str) -> Speech:
        key = self.key or os.environ.get("FAL_KEY")
        if not key:
            raise RuntimeError(
                "no key for fal.ai: set FAL_KEY (fal's dashboard gives one), or give"
                " `key=`"
            )
        spec = _MODELS[self.model]
        body = {
            **dict(spec.defaults),
            **self.settings,
            **dict(spec.fixed),
            spec.text: text,
        }
        reply = json.loads(
            _fetch(
                f"https://fal.run/{self.model}", body, {"Authorization": f"Key {key}"}
            )
        )
        audio = _fetch(reply["audio"]["url"])  # fal keeps it days, not forever: now
        return Speech(
            audio, text=text, words=timed(text, _pieces(reply.get("timestamps")))
        )


def _ordered(value: object) -> object:
    """将 `value` 中每个字典按键排序后的结果：无论设置如何书写，同一个声音只有
    一个命名。"""
    if isinstance(value, dict):
        return {k: _ordered(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [_ordered(v) for v in value]
    return value


def _pieces(stamps: object) -> list[tuple[str, float, float]]:
    """模型对其文本的计时结果，按 fal 透传的格式，返回为文本的带时间片段：每个片段
    包含一段文本（单词或字符）、起始时间和结束时间，或 ElevenLabs 的对齐信息（字符
    及其起止时间）。若无计时信息，或时间倒序，则返回空列表：此时单词时间将被估算。"""
    pieces: list[tuple[str, float, float]] = []
    for item in stamps if isinstance(stamps, list) else ():
        if not isinstance(item, dict):
            continue
        if "characters" in item:
            pieces += [
                (str(c), float(a), float(b))
                for c, a, b in zip(
                    item["characters"],
                    item["character_start_times_seconds"],
                    item["character_end_times_seconds"],
                    strict=True,
                )
            ]
        elif {"text", "start", "end"} <= item.keys():
            pieces.append((str(item["text"]), float(item["start"]), float(item["end"])))
    starts = [a for _, a, _ in pieces]
    valid = all(0 <= a <= b and math.isfinite(b) for _, a, b in pieces)
    return pieces if valid and starts == sorted(starts) else []


def _fetch(
    url: str,
    body: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> bytes:
    """GET 请求 `url`，或将 `body` 以 JSON 形式 POST 到该 URL；返回响应的字节流
    （HTTP 错误会附带服务端返回的说明）。"""
    request = urllib.request.Request(
        url,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="GET" if body is None else "POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")[:500]
        raise RuntimeError(f"{url}: HTTP {error.code}: {detail}") from None
