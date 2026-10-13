# 位置

你决定每个 mobject 的位置。ManimGX 不会替你排列：它将每个 mobject 放到你给定的位置。本页介绍位置如何运作。

## 画框

画框是视频显示的矩形。位置以单位衡量，画框的短边为 8 个单位，无论宽屏还是竖屏：

=== "16:9"

    ```python fold title="The figure's code"
    import manimgx as m


    class FrameWide(m.Scene):
        def construct(self) -> None:
            self.add(frame_figure())


    def frame_figure() -> m.VGroup:
        w, h = m.config.frame_width / 2, m.config.frame_height / 2
        grid = m.NumberPlane(
            background_line_style={"stroke_color": m.GREY_D, "stroke_width": 1},
            axis_config={"stroke_color": m.GREY_B, "stroke_width": 2},
        )
        center = m.Dot(color=m.YELLOW)
        center_label = m.MathTex("[0, 0, 0]", font_size=30, color=m.YELLOW)
        center_label.next_to(center, m.DR, buff=0.1)
        edges = m.VGroup(
            m.MathTex(f"y = {h:g}", font_size=34).next_to([0, h, 0], m.DOWN, buff=0.2),
            m.MathTex(f"y = {-h:g}", font_size=34).next_to([0, -h, 0], m.UP, buff=0.2),
            m.MathTex(f"x = {w:.1f}", font_size=34).next_to([w, 0, 0], m.LEFT, buff=0.2),
            m.MathTex(f"x = {-w:.1f}", font_size=34).next_to([-w, 0, 0], m.RIGHT, buff=0.2),
        )
        for label in edges:
            label.add_background_rectangle(opacity=1, buff=0.08)
        square = m.DashedVMobject(
            m.Square(side_length=8, color=m.BLUE, stroke_width=3), num_dashes=64
        )
        return m.VGroup(grid, square, center, center_label, edges)
    ```

=== "9:16"

    ```python fold title="The figure's code"
    import manimgx as m

    m.config.pixel_width, m.config.pixel_height = 1080, 1920


    class FrameTall(m.Scene):
        def construct(self) -> None:
            self.add(frame_figure())


    def frame_figure() -> m.VGroup:
        w, h = m.config.frame_width / 2, m.config.frame_height / 2
        grid = m.NumberPlane(
            background_line_style={"stroke_color": m.GREY_D, "stroke_width": 1},
            axis_config={"stroke_color": m.GREY_B, "stroke_width": 2},
        )
        center = m.Dot(color=m.YELLOW)
        center_label = m.MathTex("[0, 0, 0]", font_size=30, color=m.YELLOW)
        center_label.next_to(center, m.DR, buff=0.1)
        edges = m.VGroup(
            m.MathTex(f"y = {h:.1f}", font_size=34).next_to([0, h, 0], m.DOWN, buff=0.2),
            m.MathTex(f"y = {-h:.1f}", font_size=34).next_to([0, -h, 0], m.UP, buff=0.2),
            m.MathTex(f"x = {w:g}", font_size=34).next_to([w, 0, 0], m.LEFT, buff=0.2),
            m.MathTex(f"x = {-w:g}", font_size=34).next_to([-w, 0, 0], m.RIGHT, buff=0.2),
        )
        for label in edges:
            label.add_background_rectangle(opacity=1, buff=0.08)
        square = m.DashedVMobject(
            m.Square(side_length=8, color=m.BLUE, stroke_width=3), num_dashes=64
        )
        return m.VGroup(grid, square, center, center_label, edges)
    ```

位置是一个点，写成三个数字：`[x, y, 0]`。

- 画框的中心是 `[0, 0, 0]`。
- `x` 向右增长，`y` 向上增长。
- 第三个数字是深度，用于 3D。在平面场景中，它为 0。

视频默认为宽屏（16:9），除非你将其设为竖屏（9:16）。要设为竖屏，在
`import manimgx as m` 之后加上这行：

```py
m.config.pixel_width, m.config.pixel_height = 1080, 1920
```

或在命令中给出尺寸：`manimgx render scene.py -r 1080x1920`。两个画框中间都有相同的正方形，每边 8 个单位。你放在该正方形中的内容在两者中看起来一样。

## 将 mobject 放到某点

`move_to` 将 mobject 的中心放到某点：

```python
import manimgx as m


class Points(m.Scene):
    def construct(self) -> None:
        grid = m.NumberPlane()
        grid.add_coordinates()
        yellow = m.Dot(color=m.YELLOW)
        yellow.move_to([3, 2, 0])
        blue = m.Dot(color=m.BLUE)
        blue.move_to([-4, -1, 0])
        self.add(grid, yellow, blue)
```

`m.NumberPlane()` 在每个单位处画一条线，`add_coordinates` 为它们编号。网格帮助你在工作时看清位置。

## 方向

ManimGX 有方向名称。每个名称是一个点：

| 名称 | 点 |
| --- | --- |
| `m.RIGHT`、`m.LEFT` | `[1, 0, 0]`、`[-1, 0, 0]` |
| `m.UP`、`m.DOWN` | `[0, 1, 0]`、`[0, -1, 0]` |
| `m.UR`、`m.UL`、`m.DR`、`m.DL` | 对角线：右上 `[1, 1, 0]`、左上、右下、左下 |
| `m.ORIGIN` | `[0, 0, 0]`，中心 |

将方向乘以数字、将方向相加，可得到其他点：
`3 * m.RIGHT + 2 * m.UP` 即 `[3, 2, 0]`。

要从当前位置移动 mobject 一定量，使用 `shift`：`dot.shift(2 * m.LEFT)`
将点向左移动 2 个单位。

## 将 mobject 放到另一个旁边

`next_to` 将 mobject 放到另一个旁边，沿某方向：

```python
import manimgx as m


class NextTo(m.Scene):
    def construct(self) -> None:
        square = m.Square()
        above = m.Text("above")
        above.next_to(square, m.UP)
        right = m.Text("right")
        right.next_to(square, m.RIGHT)
        self.add(square, above, right)
```

间距为 0.25 个单位。要改变它，给 `buff`：`above.next_to(square, m.UP, buff=1)`。

## 将 mobject 放到边缘

`to_edge` 将 mobject 移到画框边缘，`to_corner` 移到角落。
它们留出 0.5 个单位的边距：

```python
import manimgx as m


class Edges(m.Scene):
    def construct(self) -> None:
        title = m.Text("A title")
        title.to_edge(m.UP)
        note = m.Text("a note", font_size=32)
        note.to_corner(m.DR)
        self.add(title, note)
```

因为它们查找画框的边缘，所以在宽屏和竖屏视频中都能工作。

## 排列 mobject

组包含多个 mobject：`m.VGroup(circle, square, triangle)`。`arrange` 将其
mobject 排成一行，每个紧挨前一个，并将整行放到画框中央：

```python
import manimgx as m


class Row(m.Scene):
    def construct(self) -> None:
        circle = m.Circle()
        square = m.Square()
        triangle = m.Triangle()
        shapes = m.VGroup(circle, square, triangle)
        shapes.arrange(m.RIGHT, buff=1)
        self.add(shapes)
```

`m.RIGHT` 排成一行，`m.DOWN` 排成一列。`buff` 是它们之间的间距。组作为一个 mobject 移动：`shapes.to_edge(m.DOWN)` 移动所有三个形状。

## 链式调用

`move_to`、`shift`、`next_to`、`to_edge` 和 `arrange` 返回 mobject 本身。所以你可以将调用依次写出：`m.Text("A title").to_edge(m.UP)` 创建文字并将其移到顶部。

## 下一步

[Mobject 对象](mobjects.md)介绍你可以放置的 mobject 种类，以及如何改变它们的颜色、大小和角度。