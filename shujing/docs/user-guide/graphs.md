# 图表

坐标轴是带有自身数字的 mobject。用它们来绘制函数图像或数据图。

## 坐标轴与图像

```python
import manimgx as m


def square(x: float) -> float:
    return x**2


class Parabola(m.Scene):
    def construct(self) -> None:
        axes = m.Axes(x_range=[-3, 3, 1], y_range=[0, 9, 3], x_length=8, y_length=5)
        axes.add_coordinates()
        graph = axes.plot(square, color=m.BLUE)
        self.play(m.Create(axes))
        self.play(m.Create(graph))
```

- `x_range=[-3, 3, 1]` 在 x 轴上放置从 −3 到 3 的数字，每隔 1 一个刻度。`y_range` 对 y 轴做同样的事。
- `x_length` 和 `y_length` 设定坐标轴的长度，以画框单位为单位。
- `add_coordinates` 在刻度处写出数字。
- `axes.plot` 绘制 `x` 的 Python 函数的图像。

## 坐标轴自身的数字

坐标轴有自己的坐标。在上图中，`x` 为 2、`y` 为 4 的点在画框中并不在 `[2, 4, 0]` 处。`axes.c2p(2, 4)`（"坐标转点"）给出它在画框中的位置。用它将 mobject 放到图上：

```python
import manimgx as m


def square(x: float) -> float:
    return x**2


class OnTheGraph(m.Scene):
    def construct(self) -> None:
        axes = m.Axes(x_range=[-3, 3, 1], y_range=[0, 9, 3], x_length=8, y_length=5)
        graph = axes.plot(square, color=m.BLUE)
        dot = m.Dot(axes.c2p(2, 4), color=m.YELLOW)
        label = m.MathTex("(2, 4)")
        label.next_to(dot, m.RIGHT)
        self.add(axes, graph, dot, label)
```

## 标签与面积

坐标轴能制作解释图表的部分：

```python
import manimgx as m


def curve(x: float) -> float:
    return x**2 / 4


class Area(m.Scene):
    def construct(self) -> None:
        axes = m.Axes(x_range=[0, 4, 1], y_range=[0, 4, 1], x_length=8, y_length=5.5)
        axes.add_coordinates()
        names = axes.get_axis_labels("x", "y")
        graph = axes.plot(curve, color=m.BLUE)
        label = axes.get_graph_label(graph, r"y = \frac{x^2}{4}", x_val=4)
        area = axes.get_area(graph, x_range=[1, 3], opacity=0.5)
        self.play(m.Create(axes), m.Write(names))
        self.play(m.Create(graph), m.Write(label))
        self.play(m.FadeIn(area))
        self.wait()
```

- `get_axis_labels` 为坐标轴命名。
- `get_graph_label` 在图像末端或 `x_val` 处写出 LaTeX 标签。
- `get_area` 填充图像下方、两个 `x` 值之间的面积。

这些方法创建新的 mobject。像示例那样将它们添加到场景中，或为它们制作动画。

`m.NumberPlane()`，即[位置](positions.md)中的网格，也是坐标轴：填满画框、使用画框自身坐标的坐标轴。[绘图参考][manimgx.mobjects.plotting]
展示了每种坐标轴和图像。

## 下一步

[更新器](updaters.md)介绍如何让一个 mobject 跟随另一个，例如沿图像移动的点。