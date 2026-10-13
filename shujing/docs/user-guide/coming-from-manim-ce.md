# 从 Manim CE 迁移

ManimGX 拥有 [Manim Community Edition](https://www.manim.community) 的 API：它的场景、mobject、动画和常量，名称和参数都相同。大多数 Manim CE 代码在将 `manim` 替换为 `manimgx` 后即可在 ManimGX 上运行。但 ManimGX 决定这些代码的行为。本页介绍不同之处。

## 导入与渲染

- 每个名称都在包中：`import manimgx as m`，然后用 `m.Circle`，或
  `from manimgx import *`。Manim CE 的模块不在其中：应写
  `from manimgx import polylabel`，而非 `from manimgx.utils.polylabel import polylabel`。
- 用 `manimgx render scene.py MyScene` 渲染。Manim CE 的质量标志（`-ql`、`-qh`、
  …）变为 `-r`（`--resolution`）和 `--fps`。`manimgx inspect` 编写分镜并检查 2D 布局，不生成视频。参见
  [渲染与分享](rendering.md)。
- 你不需要安装 LaTeX。`Tex` 和 `MathTex` 将其 LaTeX 转换为
  [Typst](https://typst.app)，由引擎排版。LaTeX 宏包和 `\def` 不会转换。

## 画框

宽屏视频的画框与 Manim CE 相同：高 8 个单位，宽约 14.2。竖屏视频的画框（9:16）宽 8 个单位、高约 14.2，而 Manim CE 的为宽 4.5：在 ManimGX 中，画框的短边为 8 个单位，除非你设置 `config.frame_height`。因此，为宽屏视频制作的场景，只要它保持在中间 8 × 8 的正方形内，就能适配竖屏。

## 时间与动画

- 每一帧在播放和等待中都以其精确时间展示场景，适用于任意帧率。视频以场景结束时的最后一帧结尾。
- 更新器获取自上次调用以来的精确时间。当动画播放其 mobject 时，它们继续运行。接受 `dt` 的更新器运行在各自的时钟上，因此模拟在任意帧率下都给出相同结果。
- `.animate` 在其动画开始时应用其调用。在 `Succession` 中，每个
  `.animate` 从前一个结束处开始。
- 旋转将 mobject 作为一个刚体绕一个点转动。
- 同一时刻开始的同一 mobject 的动画会合并：它们的运动相加。

参见[动画](animations.md)和[更新器](updaters.md)。

## 每个事物一个名称

对于 Manim CE 命名两次的大多数事物，ManimGX 只保留一个名称。另一个仍然有效，但你的编辑器会将其标记为弃用，并指出应使用的名称：

- `MovingCameraScene` 即 `Scene`：每个场景的相机都能移动。
- `ApplyMethod(square.scale, 2)`、`ScaleInPlace(square, 2)` 和
  `FadeToColor(square, m.RED)` 即 `.animate`：`square.animate.scale(2)`、
  `square.animate.set_color(m.RED)`。
- `arrange_submobjects` 即 `arrange`，`rotate_about_origin(angle)` 即
  `rotate(angle, about_point=m.ORIGIN)`，`get_edge_center(m.UP)` 即 `get_top()`。
- `PGroup` 即 `Group`，单数形式的 `add_foreground_mobject` 即
  `add_foreground_mobjects`。

`VGroup` 和 `Group` 也是同一个类，`c2p` 即 `coords_to_point`，但这两个名称在 Manim 代码中随处可见，所以都保留。本文档使用 `VGroup` 和
`c2p`。

## 类型

每个关键字参数都有类型，`.animate` 链也是如此。因此 [ty](https://docs.astral.sh/ty/) 等类型检查器能在渲染前发现这些错误：ManimGX 中不存在的名称、mobject 或动画不接受的
关键字（`m.Circle(colour=m.BLUE)`），或类型错误的参数。场景运行时，大多数 mobject 和动画会忽略它们不接受的关键字，所以只有 ty 能告诉你拼错了关键字。通过
`.animate`，ty 只了解 ManimGX 自身的方法。要为你自己的类的方法制作动画，给
`.animate` 一个函数：`box.animate(lambda b: b.grow(2))`。[快速开始](quickstart.md#2-set-up-your-editor)在编辑器中设置 ty。

## 声音、幻灯片和语音旁白

ManimGX 无需插件即可完成 manim-voiceover 和 manim-slides 的工作：

- [`add_sound`][manimgx.Scene.add_sound] 将声音放入视频。
  [`Sound`][manimgx.Sound] 也可以作为播放的一部分。
- 语音旁白是 `self.say("The derivative of [x squared] is [two x].", anim1, anim2)`。
  每个动画在其方括号中的文字期间播放，场景会等待到该行结束。这取代了 `with self.voiceover(...) as tracker:`、书签和
  `run_time=tracker.duration`。任何文本转语音服务都可以作为语音。
- [`next_section`][manimgx.Scene.next_section] 开启一段视频的一个章节，而非单独文件。`manimgx present` 将章节作为幻灯片展示。用
  `self.next_section()` 代替 `self.next_slide()`，用 `"presentation.loop"` 代替
  `loop=True`。`notes=` 用法不变。
- [`add_subcaption`][manimgx.Scene.add_subcaption] 添加字幕。`manimgx render` 将
  它们作为字幕写到视频旁边。

参见[声音与语音](sound-and-voice.md)和[渲染与分享](rendering.md#present)。