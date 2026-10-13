# 声音与语音

视频可以有声音：与动画一起的声音、贯穿整段视频的背景音乐，或解说的语音。ManimGX 将每个声音放到视频中的对应时刻，并将它们混合成一条音轨。

## 随动画播放声音

[`Sound`][manimgx.Sound] 从文件读取声音：WAV、MP3、AAC、FLAC 等常见格式。将它与动画一起传给 `self.play`，它会随动画开始：

```py
self.play(m.FadeIn(dot), m.Sound("click.wav"))
```

要在任意时刻开始声音而不带动画，使用 `self.add_sound`：声音播放时场景继续进行。

```py
self.add_sound(m.Sound("theme.mp3"))
```

声音会播放到结束。在 `self.play` 中，播放持续到声音结束；
`self.add_sound` 不会等待。要在声音结束前停止它，保存 `add_sound`
返回的内容：`music = self.add_sound(...)`，然后 `music.stop(fade=2)`。

## 改变声音

声音的方法产生改变后的声音：此处为降低 18 分贝的音乐，淡入 2 秒并播放到视频结束。循环的声音永不结束，所以用
`add_sound` 启动它：`self.play` 会拒绝它。

```py
music = self.add_sound(m.Sound("theme.mp3").gain(-18).fade_in(2).loop())
```

[`Sound`][manimgx.Sound] 参考展示了每种改变。

## 说一行

[`say`][manimgx.Scene.say] 用场景的语音说出一行，并在说话时播放动画。将每个动画的文字放在方括号中，并按相同顺序给出动画。语音不会读出方括号：


<video src="../films/Derivative.mp4" autoplay loop muted playsinline controls></video>

```python
import manimgx as m


class Derivative(m.Scene):
    def construct(self) -> None:
        square = m.MathTex("x^2", font_size=96).shift(2 * m.LEFT)
        derivative = m.MathTex("2x", font_size=96).shift(2 * m.RIGHT)
        self.add(square)
        self.say(
            "The derivative of [x squared] is [two x].",
            m.Indicate(square),
            m.Write(derivative),
        )
```

每个动画从其第一个词开始。场景会等到该行结束，所以各行不会重叠。如果你改变文字，动画会跟随新的文字。

## 语音

默认语音是 ElevenLabs 的 Eleven v3，位于 [fal.ai](https://fal.ai)。它需要你的
fal.ai 密钥放在 `FAL_KEY` 环境变量中。要选择不同的语音，在场景类中、`construct` 旁边设置
`voice`：

```py
voice = m.voices.Fal(
    "fal-ai/minimax/speech-2.8-hd",
    voice_setting={"voice_id": "Calm_Woman", "emotion": "happy"},
)
```

[`Fal`][manimgx.audio.fal.Fal] 可用 [五个模型][manimgx.audio.fal] 说话，你的编辑器会显示每个模型的设置。任何其他文本转语音服务也可以作为语音：语音是从文本到 [`Speech`][manimgx.Speech] 的函数。对于对话，给
`say` 指定一行的语音：`self.say("Hello!", voice=other)`。

ManimGX 将语音内容保存在场景文件旁边名为 `voice/` 的文件夹中。因此场景无需服务即可再次渲染，甚至离线也行，只有改动的行才会再次请求服务。要为某行使用你自己的录音，将其放在该行音频的位置，使用相同的名称。

## 字幕

语音所说的内容会成为视频的字幕。`manimgx render` 将它们作为字幕（`.srt`）写到视频旁边，视频播放器和视频网站都能读取。
[`add_subcaption`][manimgx.Scene.add_subcaption] 添加你自己的字幕。

## 下一步

[渲染与分享](rendering.md)介绍制作视频、检查视频并分享它的方式。