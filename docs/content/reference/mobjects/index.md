---
title: "Mobjects"
description: "视频所展示的内容。每个 mobject 在画面中都有位置、尺寸、样式和组成部分。"
---

# Mobjects

```python fold title="影片代码"
import manimgx as m


class MobjectsHero(m.Scene):
    def construct(self) -> None:
        def curve(x: float) -> float:
            return 0.5 * x**2

        axes = m.Axes(x_range=[-2, 2, 1], y_range=[0, 2, 1], x_length=3.2, y_length=2.2)
        graph = axes.plot(curve, color=m.BLUE)
        kinds = m.VGroup(
            m.Square(color=m.BLUE, fill_opacity=0.5),
            m.Star(color=m.YELLOW, fill_opacity=0.5),
            m.Arrow(m.LEFT, m.RIGHT, color=m.GREEN),
            m.Text("Text", font_size=64),
            m.MathTex(r"e^{i\pi} + 1 = 0", font_size=56),
            m.VGroup(axes, graph),
        )
        kinds.arrange_in_grid(rows=2, buff=(1.2, 1))
        self.play(
            m.LaggedStart(
                *[m.FadeIn(kind, shift=0.3 * m.UP) for kind in kinds], lag_ratio=0.15
            )
        )
        self.wait()
```

mobject 是视频所展示的任何东西：一个形状、一段文本、一个公式、一张图表。创建 mobject
并不会显示它：将其[添加][manimgx.Scene.add]到场景中，或[播放][manimgx.Scene.play]一段
将其引入的动画。

每个 mobject 都有三样东西：

- **点**，决定其位置和形状。点以单位度量：画面的短边为 8 个单位，其中心为点
  `[0, 0, 0]`。
- **样式**：其描边和填充的颜色与不透明度。
- **组成部分**，它们也是 mobject：一个分组的成员、一个公式的项、一个图表的坐标轴。
  你对 mobject 所做的操作，也会作用于其所有组成部分。

无论何种类型，每个 mobject 都能完成前面几页所述的操作：放置、调整尺寸和旋转、设置样式、
分组和复制。随后的几页介绍每种类型的 mobject。

## 每个 mobject 都能做什么

<div class="grid cards mx-cards" markdown>

-   ![](film:PositionsHero)

    [**位置**](positions.md)

    ---

    点与方向，以及放置 mobject 的方法：在某一点、依据另一个 mobject、在画面边缘。

-   ![](film:SizeAndAngleHero)

    [**尺寸与角度**](size-and-angle.md)

    ---

    缩放、拉伸、旋转和翻转 mobject，或通过函数移动每个点。

-   ![](film:StyleHero)

    [**样式**](style.md)

    ---

    描边与填充、颜色与不透明度、渐变，以及覆盖关系。

-   ![](film:ColorsHero)

    [**颜色**](colors.md)

    ---

    命名颜色，以及创建、混合和选择颜色的函数。

-   ![](film:GroupsHero)

    [**分组**](groups.md)

    ---

    由 mobject 组成的 mobject：添加、移除、排列和排序组成部分。

-   ![](film:CopiesAndStatesHero)

    [**副本与状态**](copies-and-states.md)

    ---

    复制 mobject，保留其状态以便返回，以及准备一个要移动到的状态。

-   ![](film:PathsHero)

    [**路径**](paths.md)

    ---

    构成形状的曲线：绘制自定义路径，并沿路径查找点。

</div>

## mobject 的类型

<div class="grid cards mx-cards" markdown>

-   ![](film:LinesAndArrows)

    [**形状**](shapes/index.md)

    ---

    线与箭头、圆与弧、多边形，以及由其他形状构成的形状。

-   ![](film:AnnotationsHero)

    [**标注**](annotations.md)

    ---

    大括号、标签、边框、下划线和角度标记：指向其他 mobject 的元素。

-   ![](film:TextAndMathHero)

    [**文本与数学**](text-and-math/index.md)

    ---

    由 Typst 在 ManimGX 中排版的文字、公式和数字。

-   ![](film:GraphsHero)

    [**图表**](graphs/index.md)

    ---

    坐标轴、数轴和平面、函数与数据的图形、向量场。

-   ![](film:NetworksHero)

    [**网络**](networks.md)

    ---

    由边连接的顶点，自动布局，可增长和变化。

-   ![](film:MatricesAndTablesHero)

    [**矩阵与表格**](matrices-and-tables.md)

    ---

    按行列排列的元素，位于括号或线条之间。

-   ![](film:ImagesAndSvgHero)

    [**图像与 SVG**](images-and-svg.md)

    ---

    来自文件或像素的图片，以及从 SVG 文件读取的绘图。

-   ![](film:PointCloudsHero)

    [**点云**](point-clouds.md)

    ---

    以点形式绘制的 mobject，每个点都是其自身颜色的圆点。

</div>

## mobject

::: manimgx.Mobject
    options:
      heading_level: 3
      members: false

::: manimgx.Mobject.submobjects
    options:
      heading_level: 4

::: manimgx.Mobject.name
    options:
      heading_level: 4
