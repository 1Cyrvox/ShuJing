---
title: "语音"
description: "解释的语音：在动画于其词语间播放时说出一行、选择语音、读取字幕，或制作你自己的语音。"
---

# 语音

```python fold title="影片代码"
import manimgx as m


class VoiceHero(m.Scene):
    def construct(self) -> None:
        square = m.MathTex("x^2", font_size=96).shift(2 * m.LEFT)
        derivative = m.MathTex("2x", font_size=96).shift(2 * m.RIGHT)
        arrow = m.Arrow(square.get_right(), derivative.get_left(), buff=0.4)
        script = m.Text(
            "The derivative of [x squared] is [two x].", font_size=32
        ).to_edge(m.DOWN)
        self.add(square, script)
        self.play(m.Indicate(square))
        self.play(m.GrowArrow(arrow), m.Write(derivative))
        self.wait()
```

[say][manimgx.Scene.say] 用场景的语音说出一行，并在它说话时播放动画。将每个动画的词语放在方括号中，并按相同顺序给出动画：每个从它的第一个词开始。场景等待直到该行结束，因此各行不会重叠；改变词语，动画跟随新词语。

场景的语音通过文本转语音服务说话。ManimGX 将它说的内容保存在场景文件旁边名为 `voice/` 的文件夹中，因此场景无需服务即可再次渲染，并且只有改变的行再次发送给它。语音说的内容成为视频的字幕。

::: manimgx.Scene.say
    options:
      heading_level: 2

::: manimgx.Scene.speech
    options:
      heading_level: 2

::: manimgx.Scene.voice
    options:
      heading_level: 2

::: manimgx.Speech
    options:
      heading_level: 2

## 语音

ManimGX 提供的语音是 fal.ai 的：`m.voices.Fal`，附带你选择的模型及其设置。你的编辑器显示每个模型的设置。

::: manimgx.audio.fal.Fal
    options:
      heading_level: 3

### 模型 { #manimgx.audio.fal }

::: manimgx.audio.fal.ElevenV3
    options:
      heading_level: 4

::: manimgx.audio.fal.MiniMax
    options:
      heading_level: 4

::: manimgx.audio.fal.MiniMaxVoice
    options:
      heading_level: 4

::: manimgx.audio.fal.MiniMaxAudio
    options:
      heading_level: 4

::: manimgx.audio.fal.MiniMaxLoudness
    options:
      heading_level: 4

::: manimgx.audio.fal.MiniMaxTimbre
    options:
      heading_level: 4

::: manimgx.audio.fal.MiniMaxPronunciation
    options:
      heading_level: 4

::: manimgx.audio.fal.Gemini
    options:
      heading_level: 4

::: manimgx.audio.fal.Inworld
    options:
      heading_level: 4

::: manimgx.audio.fal.Qwen
    options:
      heading_level: 4

## 字幕

::: manimgx.Scene.add_subcaption
    options:
      heading_level: 3

## 自定义语音

语音是从文本到 [Speech][manimgx.Speech] 的任意函数：一种知道它的词语以及每个词何时说出的声音。任何文本转语音服务都可以成为一个语音。

::: manimgx.audio.Voice
    options:
      heading_level: 3

::: manimgx.audio.Word
    options:
      heading_level: 3

::: manimgx.audio.timed
    options:
      heading_level: 3

::: manimgx.audio.estimate
    options:
      heading_level: 3

::: manimgx.audio.cached
    options:
      heading_level: 3
