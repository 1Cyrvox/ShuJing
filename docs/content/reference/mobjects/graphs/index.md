---
title: "图形"
description: "具有自身坐标系的坐标轴、数轴和平面，其上的函数图像与数据，以及向量场。"
---

# 图形 { #manimgx.mobjects.plotting }

```python fold title="影片代码"
import manimgx as m
import numpy as np


def wave(x: float) -> float:
    return 1.5 * np.sin(x)


class GraphsHero(m.Scene):
    def construct(self) -> None:
        axes = m.Axes(x_range=[0, 7, 1], y_range=[-2, 2, 1], x_length=10, y_length=5)
        axes.add_coordinates()
        graph = axes.plot(wave, color=m.BLUE)
        area = axes.get_area(graph, x_range=[0, m.PI], opacity=0.4)
        label = axes.get_graph_label(graph, r"1.5 \sin x", x_val=2)
        self.play(m.Create(axes))
        self.play(m.Create(graph), m.Write(label))
        self.play(m.FadeIn(area))
        self.wait()
```

坐标轴是具有自身坐标系的 mobject。坐标轴上的一个点位于其数字所在之处，而非帧的坐标所在之处：[c2p][manimgx.Axes.coords_to_point] 将坐标轴的坐标转换为帧上的一个点，以便在图像上放置任何对象。坐标轴也以自身的坐标系绘制图像：函数的图像、曲线、图像下方的面积及其斜率。

数轴是单根坐标轴。数平面是带有网格的坐标轴，除非你指定其尺寸，否则它会填满帧。向量场在平面的每一点处绘制一个方向。

<div class="grid cards mx-cards" markdown>

-   ![](film:AxesHero)

    [**坐标轴**](axes.md)

    ---

    坐标轴、其坐标系、其标签与数字，以及到某点的连线。

-   ![](film:PlottingHero)

    [**绘图**](plotting.md)

    ---

    坐标轴上函数的图像：其标签、下方的面积、其斜率及其导数。

-   ![](film:NumberLinesHero)

    [**数轴**](number-lines.md)

    ---

    单根坐标轴：刻度、数字和标签，采用均匀刻度或对数刻度。

-   ![](film:PlanesHero)

    [**平面**](planes.md)

    ---

    坐标网格：数平面、复平面、极坐标平面。

-   ![](film:CurvesHero)

    [**曲线**](curves.md)

    ---

    函数图像、参数曲线和隐式曲线，使用帧自身的坐标系。

-   ![](film:ChartsHero)

    [**图表**](charts.md)

    ---

    柱状图，以及概率的样本空间。

-   ![](film:VectorFieldsHero)

    [**向量场**](vector-fields.md)

    ---

    每一点处的向量：箭头、流线，以及场携带的 mobject。

</div>
