---
title: "语音"
description: "解说的语音：在动画于其词语间播放时说出一句话、选择语音、读取字幕，或制作自己的语音。"
---

# 语音


<video src="../../films/VoiceHero.mp4" autoplay loop muted playsinline controls></video>

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

[say][manimgx.Scene.say] 用场景的语音说出一句话，并在说话时播放动画。将
每个动画的词语放在方括号中，以相同顺序给出动画：每个从其
第一个词开始。场景等待到该句话结束，因此
语句不会重叠；更改词语，动画跟随新的词语。

场景的语音通过文本转语音服务说话。ManimGX 将其所说保存在
场景文件旁名为 `voice/` 的文件夹中，因此场景无需服务即可再次渲染，
只有更改的语句会再次发送给服务。语音所说的内容成为视频的
字幕。

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

ManimGX 自带的语音是 fal.ai 的：`m.voices.Fal`，可选择模型及其
设置。你的编辑器会显示每个模型的设置。

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

语音是从文本到 [Speech][manimgx.Speech] 的任何函数：一种知道其
词语及每个词语何时说出的声音。任何文本转语音服务都可以成为语音。

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