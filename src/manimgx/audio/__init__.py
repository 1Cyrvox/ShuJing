"""音频：可编辑的声音、带时间标注的语音，以及产生它们的嗓音。

嗓音是任意从文本到 [`Speech`][manimgx.audio.Speech] 的函数：一种知道自己的词语以及每个
词语何时被说出的声音。[`Scene.say`][manimgx.Scene.say] 通过场景的嗓音说话，并在词语所属的
时间段内播放动画：`self.say("Here is [a circle].", m.Create(circle))` 在说到 "a circle" 时
绘制圆，而影片会等待这句话说完。嗓音所说的话会被保留（`cached`），因此场景再次渲染时无需
再次说话。

ManimGX 提供的嗓音来自文本转语音服务，每个服务一个模块：[`fal`][manimgx.audio.fal]
（fal.ai 的模型，[`Fal`][manimgx.audio.fal.Fal]）。任何其他嗓音只需几行代码即可实现（参见
[`Voice`][manimgx.audio.Voice]）。
"""

from manimgx.audio.fal import Fal
from manimgx.audio.sound import (
    Speech,
    Voice,
    Word,
    cached,
    estimate,
    lines,
    spans,
    timed,
    times,
)

__all__ = [
    "Fal",
    "Speech",
    "Voice",
    "Word",
    "cached",
    "estimate",
    "lines",
    "spans",
    "timed",
    "times",
]
