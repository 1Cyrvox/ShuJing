# 声音与语音

视频可以带有声音：与动画同步的声音、贯穿整段视频的背景音乐，或用于讲解的语音。ManimGX 会将每一段声音放置在视频中对应的时刻，并将它们混合为一条音轨。

## 随动画播放声音

[`Sound`][manimgx.Sound] 从文件中读取声音：WAV、MP3、AAC、FLAC 以及其他常见格式。将其与动画一起传给 `self.play`，它会与动画同时开始：

```py
self.play(m.FadeIn(dot), m.Sound("click.wav"))
```

要在任意时刻开始一段声音而不伴随动画，可使用 `self.add_sound`：声音播放时场景继续进行。

```py
self.add_sound(m.Sound("theme.mp3"))
```

声音会播放到结束。在 `self.play` 中，播放会持续到声音结束；`self.add_sound` 不会等待。要在声音结束前停止它，请保留 `add_sound` 的返回值：`music = self.add_sound(...)`，然后调用 `music.stop(fade=2)`。

## 修改声音

声音的方法可以生成修改后的声音：这里是将音乐降低 18 分贝，淡入 2 秒并循环播放直至视频结束。循环的声音永不结束，因此要用 `add_sound` 启动它：`self.play` 会拒绝它。

```py
music = self.add_sound(m.Sound("theme.mp3").gain(-18).fade_in(2).loop())
```

[`Sound`][manimgx.Sound] 参考展示了所有修改方式。

## 说一句台词

[`say`][manimgx.Scene.say] 用场景的语音说出一句台词，并在说话的同时播放动画。把每段动画对应的文字放在方括号中，并按相同顺序给出动画。语音不会读出方括号：

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

每段动画从其对应文字的第一个词开始。场景会等到台词结束，因此台词不会重叠。如果你修改了文字，动画会跟随新的文字。

## 语音

默认语音是 [fal.ai](https://fal.ai) 上的 ElevenLabs Eleven v3。它需要在 `FAL_KEY` 环境变量中设置你的 fal.ai 密钥。要选择不同的语音，可在场景类中、紧挨着 `construct` 设置 `voice`：

```py
voice = m.voices.Fal(
    "fal-ai/minimax/speech-2.8-hd",
    voice_setting={"voice_id": "Calm_Woman", "emotion": "happy"},
)
```

[`Fal`][manimgx.audio.fal.Fal] 可使用 [五种模型][manimgx.audio.fal] 说话，你的编辑器会显示每种模型的设置。任何其他文本转语音服务也可以作为语音：语音就是一个从文本到 [`Speech`][manimgx.Speech] 的函数。对于对话，可以为某句台词单独指定语音：`self.say("Hello!", voice=other)`。

ManimGX 会把语音所说内容保存在场景文件旁一个名为 `voice/` 的文件夹中。这样即使离线、不调用服务也能再次渲染场景，且只有被修改的台词才会重新请求服务。要为某句台词使用你自己的录音，请用同名文件替换该台词对应的音频。

## 字幕

语音所说内容会成为视频的字幕。`manimgx render` 会把它们以字幕文件（`.srt`）的形式写到视频旁边，供视频播放器和视频网站读取。[`add_subcaption`][manimgx.Scene.add_subcaption] 可添加你自己的字幕。

## 下一步

[渲染与分享](rendering.md) 展示了制作视频、检查视频以及分享视频的各种方式。
