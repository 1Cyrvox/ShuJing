# 从 Manim CE 迁移而来

ManimGX 拥有 [Manim Community Edition](https://www.manim.community) 的 API：它的场景、mobject、动画和常量，名称与参数都相同。大多数 Manim CE 代码在把 `manim` 替换为 `manimgx` 后即可在 ManimGX 上运行。但 ManimGX 自行决定这些代码的行为。本页说明二者不同之处。

## 导入与渲染

- 每个名称都在包中：`import manimgx as m`，然后使用 `m.Circle`，或 `from manimgx import *`。Manim CE 的模块并不存在：应写   `from manimgx import polylabel`，而非 `from manimgx.utils.polylabel import polylabel`。
- 用 `manimgx render scene.py MyScene` 渲染。Manim CE 的质量标志（`-ql`、`-qh`、…）变为 `-r`（`--resolution`）和 `--fps`。`manimgx inspect` 生成故事板并在不生成视频的情况下检查 2D 布局。参见 [渲染与分享](rendering.md)。
- 你无需安装 LaTeX。`Tex` 和 `MathTex` 会将其 LaTeX 转换为 [Typst](https://typst.app)，再由引擎排版。LaTeX 宏包和 `\def` 不会被转换。

## 取景框

横屏视频的取景框与 Manim CE 相同：高 8 个单位，宽约 14.2 个单位。竖屏视频的取景框（9:16）宽 8 个单位、高约 14.2 个单位，而 Manim CE 中为宽 4.5 个单位：在 ManimGX 中，取景框的短边为 8 个单位，除非你设置了 `config.frame_height`。因此，为横屏视频制作的场景只要停留在中间的 8 × 8 正方形内，就能适配竖屏视频。

## 时间与动画

- 每一帧都展示场景在该帧精确时刻的状态，在 play 和 wait 中均如此，且适用于任何帧率。视频以场景结束时的最后一帧收尾。
- 更新器获取自上次调用以来的精确时间。当动画播放其 mobject 时，它们继续运行。接收 `dt` 的更新器运行在各自的时钟上，因此模拟在任何帧率下都给出相同结果。
- `.animate` 在其动画开始时应用其调用。在 `Succession` 中，每个 `.animate` 从前一个结束之处开始。
- 旋转把 mobject 当作一个刚体绕某一点转动。
- 同一 mobject 同时开始的动画会合并：它们的运动相加。

参见 [动画](animations.md) 和 [更新器](updaters.md)。

## 每个事物只有一个名称

对于大多数 Manim CE 中有两个名称的事物，ManimGX 只保留一个名称。另一个仍然可用，但你的编辑器会将其标记为已弃用，并指出应使用的名称：

- `MovingCameraScene` 即 `Scene`：每个场景的相机都可移动。
- `ApplyMethod(square.scale, 2)`、`ScaleInPlace(square, 2)` 和 `FadeToColor(square, m.RED)` 即 `.animate`：`square.animate.scale(2)`、`square.animate.set_color(m.RED)`。
- `arrange_submobjects` 即 `arrange`，`rotate_about_origin(angle)` 即 `rotate(angle, about_point=m.ORIGIN)`，`get_edge_center(m.UP)` 即 `get_top()`。
- `PGroup` 即 `Group`，单数形式的 `add_foreground_mobject` 即 `add_foreground_mobjects`。

`VGroup` 和 `Group` 也是同一个类，`c2p` 即 `coords_to_point`，但这两个名称在 Manim 代码中随处可见，因此都保留。本文档使用 `VGroup` 和 `c2p`。

## 类型

每个关键字参数都有类型，`.animate` 链也是如此。因此像 [ty](https://docs.astral.sh/ty/) 这样的类型检查器能在渲染前发现这些错误：ManimGX 中不存在的名称、某个 mobject 或动画不接受的关键字（`m.Circle(colour=m.BLUE)`），或类型错误的参数。当场景运行时，大多数 mobject 和动画会忽略它们不接受的关键字，因此只有 ty 能告诉你某个拼写错误的关键字。通过 `.animate`，ty 只识别 ManimGX 自身的方法。要对你自己类的方法做动画，请给 `.animate` 传一个函数：`box.animate(lambda b: b.grow(2))`。[快速入门](quickstart.md#2) 介绍了如何在编辑器中配置 ty。

## 声音、幻灯片与语音旁白

ManimGX 无需插件即可完成 manim-voiceover 和 manim-slides 的工作：

- [`add_sound`][manimgx.Scene.add_sound] 将声音放入视频。[`Sound`][manimgx.Sound] 也可以作为某次 play 的一部分。
- 语音旁白写作 `self.say("The derivative of [x squared] is [two x].", anim1, anim2)`。每段动画在其方括号内的文字期间播放，场景会等到台词结束。这取代了 `with self.voiceover(...) as tracker:`、书签以及 `run_time=tracker.duration`。任何文本转语音服务都可以作为语音。
- [`next_section`][manimgx.Scene.next_section] 开始同一段视频中的一个分段，而非单独的文件。`manimgx present` 将各分段作为幻灯片展示。请用 `self.next_section()` 代替 `self.next_slide()`，用 `"presentation.loop"` 代替 `loop=True`。`notes=` 的用法与以往相同。
- [`add_subcaption`][manimgx.Scene.add_subcaption] 添加字幕。`manimgx render` 会把它们以字幕形式写到视频旁边。

参见 [声音与语音](sound-and-voice.md) 和 [渲染与分享](rendering.md#_7)。
