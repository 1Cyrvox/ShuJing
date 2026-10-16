# 位置

由你来决定每个 mobject 的位置。ManimGX 不会为你排列它们：它将每个 mobject 放在你给定的位置。本页展示位置是如何工作的。

## 画面框

画面框是视频显示的矩形。位置以单位来衡量，画面框的短边为 8 个单位，无论是宽屏视频还是竖屏视频：

=== "16:9"

    ```python fold title="图形代码"
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

    ```python fold title="图形代码"
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

- 画面框的中心是 `[0, 0, 0]`。
- `x` 向右增长，`y` 向上增长。
- 第三个数字是深度，用于 3D。在平面场景中，它为 0。

视频默认是宽屏（16:9），除非你将其设为竖屏（9:16）。要设为竖屏，请在 `import manimgx as m` 之后加入这一行：

```py
m.config.pixel_width, m.config.pixel_height = 1080, 1920
```

或者将尺寸传给命令：`manimgx render scene.py -r 1080x1920`。两个画面框的中间都有相同的正方形，每边 8 个单位。你放在该正方形中的内容在两者中看起来是一样的。

## 将 mobject 放到某一点

`move_to` 将 mobject 的中心放到某一点：

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

`m.NumberPlane()` 在每个单位处画一条线，`add_coordinates` 为它们标注数字。网格有助于你在工作时查看位置。

## 方向

ManimGX 为方向提供了名称。每个名称都是一个点：

| 名称 | 点 |
| --- | --- |
| `m.RIGHT`, `m.LEFT` | `[1, 0, 0]`, `[-1, 0, 0]` |
| `m.UP`, `m.DOWN` | `[0, 1, 0]`, `[0, -1, 0]` |
| `m.UR`, `m.UL`, `m.DR`, `m.DL` | 对角线：右上 `[1, 1, 0]`，左上，右下，左下 |
| `m.ORIGIN` | `[0, 0, 0]`，即中心 |

将一个方向乘以一个数字，并将方向相加，可以构造其他点：`3 * m.RIGHT + 2 * m.UP` 即为 `[3, 2, 0]`。

要将 mobject 从其当前位置移动一定量，请使用 `shift`：`dot.shift(2 * m.LEFT)` 将点向左移动 2 个单位。

## 将 mobject 放在另一个旁边

`next_to` 将一个 mobject 放在另一个旁边，沿某个方向：

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

间距为 0.25 个单位。要更改它，请给出 `buff`：`above.next_to(square, m.UP, buff=1)`。

## 将 mobject 放到边缘

`to_edge` 将 mobject 移动到画面框的边缘，`to_corner` 将其移动到角落。它们会留出 0.5 个单位的边距：

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

因为它们会找到画面框的边缘，所以它们在宽屏和竖屏视频中都能工作。

## 将 mobject 排列成行

一个组包含多个 mobject：`m.VGroup(circle, square, triangle)`。`arrange` 将其中的 mobject 排成一行，每个紧挨着前一个，并将该行放在画面框的中间：

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

`m.RIGHT` 排成一行，`m.DOWN` 排成一列。`buff` 是它们之间的间距。一个组作为一个整体 mobject 移动：`shapes.to_edge(m.DOWN)` 会移动所有三个形状。

## 链式调用

`move_to`、`shift`、`next_to`、`to_edge` 和 `arrange` 都会返回该 mobject。因此你可以将调用一个接一个地写下去：`m.Text("A title").to_edge(m.UP)` 创建一段文本并将其移到顶部。

## 下一步

[Mobject](mobjects.md)将展示你可以放置的各类 mobject，以及如何更改它们的颜色、大小和角度。
