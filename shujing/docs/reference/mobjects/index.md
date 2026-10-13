---
title: "Mobject"
description: "视频所展示的内容。每个 mobject 在画面中都有位置、大小、样式和组成部分。"
---

# Mobject

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

mobject 是视频展示的任何东西：一个形状、一段文字、一个公式、一张图。创建一个 mobject
并不会显示它：将其[添加][manimgx.Scene.add]到场景中，或者[播放][manimgx.Scene.play]一个
将其引入的动画。

每个 mobject 都有三样东西：

- **点**，决定其位置和形状。它们以单位度量：画面的短边
  为 8 个单位，其中心是点 `[0, 0, 0]`。
- **样式**：其描边和填充的颜色与不透明度。
- **组成部分**，它们也是 mobject：一个组的成员、一个公式的项、一张图的坐标轴。
  你对一个 mobject 所做的操作，也会作用于其所有组成部分。

每个 mobject 都能执行前几页所讲述的操作，无论其种类如何：被放置、调整大小和旋转、设置样式、
分组和复制。之后的页面讲述每种特定的 mobject。

## 每个 mobject 都能做的事

<div class="grid cards mx-cards" markdown>

-   ![](film:PositionsHero)

    [**位置**](positions.md)

    ---

    点和方向，以及放置 mobject 的方法：到某个点、相对于另一个
    mobject、到画面边缘。

-   ![](film:SizeAndAngleHero)

    [**大小和角度**](size-and-angle.md)

    ---

    缩放、拉伸、旋转和翻转 mobject，或通过函数移动每个点。

-   ![](film:StyleHero)

    [**样式**](style.md)

    ---

    描边和填充、颜色和不透明度、渐变，以及遮挡关系。

-   ![](film:ColorsHero)

    [**颜色**](colors.md)

    ---

    命名颜色，以及创建、混合和选择颜色的函数。

-   ![](film:GroupsHero)

    [**组**](groups.md)

    ---

    由 mobject 组成的 mobject：添加、移除、排列和排序组成部分。

-   ![](film:CopiesAndStatesHero)

    [**副本与状态**](copies-and-states.md)

    ---

    复制 mobject、保存其状态以便返回，以及准备一个要移动到的状态。

-   ![](film:PathsHero)

    [**路径**](paths.md)

    ---

    构成形状的曲线：绘制自定义路径，以及沿路径查找点。

</div>

## Mobject 的种类

<div class="grid cards mx-cards" markdown>

-   ![](film:LinesAndArrows)

    [**形状**](shapes/index.md)

    ---

    线和箭头、圆和弧、多边形，以及由其他形状组合而成的形状。

-   ![](film:AnnotationsHero)

    [**标注**](annotations.md)

    ---

    花括号、标签、边框、下划线和角标：指向其他 mobject 的标注。

-   ![](film:TextAndMathHero)

    [**文字和数学**](text-and-math/index.md)

    ---

    文字、公式和数字，由 ManimGX 内部的 Typst 排版。

-   ![](film:GraphsHero)

    [**图**](graphs/index.md)

    ---

    坐标轴、数轴和平面、函数和数据的图像、向量场。

-   ![](film:NetworksHero)

    [**网络**](networks.md)

    ---

    由边连接的顶点，自动布局，可生长和变化。

-   ![](film:MatricesAndTablesHero)

    [**矩阵和表格**](matrices-and-tables.md)

    ---

    行列中的条目，位于括号之间或线条之间。

-   ![](film:ImagesAndSvgHero)

    [**图片和 SVG**](images-and-svg.md)

    ---

    来自文件或像素数组的图片，以及从 SVG 文件读取的绘图。

-   ![](film:PointCloudsHero)

    [**点云**](point-clouds.md)

    ---

    以点形式绘制的 mobject，每个点都是自身颜色的圆点。

</div>

## Mobject 类

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