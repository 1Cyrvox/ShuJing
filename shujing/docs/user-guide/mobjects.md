# Mobject 对象

mobject 是能在视频中展示的任何东西。本页介绍 mobject 的种类，以及如何改变它们的颜色、大小和角度。

## 形状

```python
import manimgx as m


class Shapes(m.Scene):
    def construct(self) -> None:
        circle = m.Circle(radius=1)
        square = m.Square(side_length=2)
        rectangle = m.Rectangle(width=3, height=2)
        triangle = m.Triangle()
        star = m.Star()
        shapes = m.VGroup(circle, square, rectangle, triangle, star)
        shapes.arrange(m.RIGHT, buff=0.6)
        self.add(shapes)
```

每个形状在创建时接受其尺寸：圆接受 `radius`，正方形接受
`side_length`，矩形接受 `width` 和 `height`。不指定时，形状有默认尺寸：圆的半径为 1，正方形的边长为 2。

要创建自定义形状，给 `m.Polygon` 其顶点：
`m.Polygon([0, 0, 0], [3, 0, 0], [0, 2, 0])`。

## 线条、箭头和点

线条从一个点延伸到另一个点：

```python
import manimgx as m


class Lines(m.Scene):
    def construct(self) -> None:
        line = m.Line([-5, 1, 0], [-1, 1, 0])
        arrow = m.Arrow([1, 1, 0], [5, 1, 0])
        dashed = m.DashedLine([-5, -1, 0], [-1, -1, 0])
        dot = m.Dot([3, -1, 0])
        self.add(line, arrow, dashed, dot)
```

箭头在到达其端点前会稍作停顿，以免遮住它所指的东西。
要让它触及端点，给 `buff=0`。点是在某处的小实心圆。

## 文字与公式

`m.Text` 显示文字，`m.MathTex` 显示用 LaTeX 书写的公式：

```python
import manimgx as m


class TextAndFormula(m.Scene):
    def construct(self) -> None:
        text = m.Text("Hello, world")
        formula = m.MathTex(r"e^{i\pi} + 1 = 0")
        lines = m.VGroup(text, formula)
        lines.arrange(m.DOWN, buff=1)
        self.add(lines)
```

用原始字符串 `r"..."` 书写公式，以便 Python 保留其反斜杠。
[文本与数学](text-and-math.md)有更多内容。

## 颜色

在创建 mobject 时给定其颜色：

```python
import manimgx as m


class Colors(m.Scene):
    def construct(self) -> None:
        outline = m.Circle(color=m.BLUE)
        filled = m.Circle(color=m.BLUE, fill_opacity=0.5)
        thick = m.Circle(color=m.YELLOW, stroke_width=12)
        circles = m.VGroup(outline, filled, thick)
        circles.arrange(m.RIGHT, buff=1)
        self.add(circles)
```

- `color` 为轮廓和内部着色。
- `fill_opacity` 填充内部：0 为空，1 为实心。大多数形状默认为空，除非你填充它们。
- `stroke_width` 设定轮廓宽度：大多数形状为 4，箭头为 6，除非你另给值。

ManimGX 有颜色名称：`m.WHITE`、`m.GREY`、`m.BLUE`、`m.TEAL`、`m.GREEN`、
`m.YELLOW`、`m.GOLD`、`m.ORANGE`、`m.RED`、`m.PINK`、`m.PURPLE` 等。大多数还有五种深浅：`m.BLUE_A` 是最浅的蓝色，`m.BLUE_E` 是最深的。你也可以用十六进制代码给出颜色，如 `"#58C4DD"`。

要之后改变颜色，使用 `set_color`、`set_fill` 或 `set_stroke`：
`circle.set_fill(m.RED, opacity=1)`。

## 大小与角度

`scale` 缩放 mobject 的大小，`rotate` 逆时针旋转它：

```python
import manimgx as m


class SizeAndAngle(m.Scene):
    def construct(self) -> None:
        small = m.Square()
        small.scale(0.5)
        turned = m.Square()
        turned.rotate(45 * m.DEGREES)
        large = m.Square()
        large.scale(1.5)
        squares = m.VGroup(small, turned, large)
        squares.arrange(m.RIGHT, buff=1)
        self.add(squares)
```

`scale(2)` 使 mobject 放大到两倍，`scale(0.5)` 缩小到一半。它的中心保持不动。`45 * m.DEGREES` 是 45 度的角。

## 组

组是由其他 mobject 组成的 mobject。当你移动、缩放、着色或为组制作动画时，你是在对其中的每个 mobject 做同样的事。`group[0]` 是第一个，`group[1]` 是第二个。

```py
shapes = m.VGroup(circle, square, triangle)
shapes.set_color(m.YELLOW)  # 三个都变黄
shapes[0].scale(2)  # 圆变大
```

## 遮挡关系

后添加的 mobject 会遮住先添加的。要将 mobject 提到最前，给它更高的 z 索引：`circle.set_z_index(1)`。

[参考](../reference/mobjects/index.md)展示了每种 mobject。

## 下一步

你的 mobject 已就位。[动画](animations.md)介绍如何移动和改变它们。