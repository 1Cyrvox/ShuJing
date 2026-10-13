---
title: "图"
description: "坐标轴、数轴和带有自身坐标的平面、函数和数据的图像，以及向量场。"
---

# 图 { #manimgx.mobjects.plotting }

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

坐标轴是带有自身坐标的 mobject。坐标轴上的一个点是其数值所在的位置，
而非画面的位置：[c2p][manimgx.Axes.coords_to_point] 将坐标轴的坐标
转换为画面的点，用于在图上放置任何东西。坐标轴也以自身坐标
绘制图：函数的图、曲线、图下面积、斜率。

数轴是单条坐标轴。数平面是带网格的坐标轴，除非你指定大小，
否则会填满画面。向量场在平面的每个点绘制一个方向。

<div class="grid cards mx-cards" markdown>

-   ![](film:AxesHero)

    [**坐标轴**](axes.md)

    ---

    坐标轴、其坐标、标签和数字，以及到某点的连线。

-   ![](film:PlottingHero)

    [**绘图**](plotting.md)

    ---

    坐标轴上函数的图：其标签、下方面积、斜率、
    导数。

-   ![](film:NumberLinesHero)

    [**数轴**](number-lines.md)

    ---

    单条坐标轴：刻度、数字和标签，均匀或对数刻度。

-   ![](film:PlanesHero)

    [**平面**](planes.md)

    ---

    坐标网格：数平面、复平面、极坐标平面。

-   ![](film:CurvesHero)

    [**曲线**](curves.md)

    ---

    函数的图、参数曲线和隐式曲线，使用画面自身
    坐标。

-   ![](film:ChartsHero)

    [**图表**](charts.md)

    ---

    柱状图，以及概率的样本空间。

-   ![](film:VectorFieldsHero)

    [**向量场**](vector-fields.md)

    ---

    每个点的向量：箭头、流线，以及场携带的 mobject。

</div>