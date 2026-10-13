---
title: "位置"
description: "mobject 在画面中的位置，以及将其移动到某个点、另一个 mobject 旁或边缘的方法。"
---

# 位置

```python fold title="影片代码"
import manimgx as m


class PositionsHero(m.Scene):
    def construct(self) -> None:
        plane = m.NumberPlane(
            background_line_style={"stroke_color": m.GREY_D, "stroke_width": 1},
            axis_config={"stroke_color": m.GREY_B, "stroke_width": 2},
        )
        self.add(plane)
        names = ["ORIGIN", "UP", "DOWN", "LEFT", "RIGHT", "UL", "UR", "DL", "DR"]
        points = [m.ORIGIN, m.UP, m.DOWN, m.LEFT, m.RIGHT, m.UL, m.UR, m.DL, m.DR]
        dots = m.VGroup()
        labels = m.VGroup()
        for name, point in zip(names, points, strict=True):
            dot = m.Dot(2.5 * point, radius=0.12, color=m.YELLOW)
            label = m.Text(name, font="monospace", font_size=30)
            label.next_to(dot, m.DOWN, buff=0.2)
            label.add_background_rectangle(opacity=1, buff=0.05)
            dots.add(dot)
            labels.add(label)
        self.play(
            m.LaggedStart(*[m.GrowFromCenter(dot) for dot in dots], lag_ratio=0.1)
        )
        self.play(m.FadeIn(labels))
        self.wait()
```

每个 mobject 在画面中都有一个位置。位置是一个点，三个数字 `[x, y, z]`，
以画面中心为原点度量。x 向右增长，y 向上增长，z
向屏幕外、朝向观察者增长。画面的短边为 8 个单位：宽屏
视频的 y 从 −4 到 4，x 从约 −7.1 到 7.1。

mobject 的位置由其包围盒决定：沿坐标轴方向围绕其绘制内容的最小
盒子。其中心、边缘和角落都是该盒子的点。以下方法读取
这些点，并移动 mobject 使其中一个到达你指定的位置。每个方法
都会带动 mobject 的组成部分，并返回 mobject 本身，因此调用可以链式使用：
`m.Text("Title").scale(1.5).to_edge(m.UP)`。

## 方向

坐标轴方向是单位向量；对角线方向是它们的和。将方向
乘以数字，并将方向相加，可以构造其他点：`3 * m.RIGHT + 2 * m.UP`
即 `[3, 2, 0]`。

<div class="mx-constants" markdown>

::: manimgx.ORIGIN
    options:
      heading_level: 3

::: manimgx.UP
    options:
      heading_level: 3

::: manimgx.DOWN
    options:
      heading_level: 3

::: manimgx.LEFT
    options:
      heading_level: 3

::: manimgx.RIGHT
    options:
      heading_level: 3

::: manimgx.UL
    options:
      heading_level: 3

::: manimgx.UR
    options:
      heading_level: 3

::: manimgx.DL
    options:
      heading_level: 3

::: manimgx.DR
    options:
      heading_level: 3

::: manimgx.IN
    options:
      heading_level: 3

::: manimgx.OUT
    options:
      heading_level: 3

::: manimgx.X_AXIS
    options:
      heading_level: 3

::: manimgx.Y_AXIS
    options:
      heading_level: 3

::: manimgx.Z_AXIS
    options:
      heading_level: 3

</div>

## mobject 的位置

以下每个方法读取 mobject 包围盒的一个点，或其一个坐标。

::: manimgx.Mobject.get_center
    options:
      heading_level: 3

::: manimgx.Mobject.get_top
    options:
      heading_level: 3

::: manimgx.Mobject.get_bottom
    options:
      heading_level: 3

::: manimgx.Mobject.get_left
    options:
      heading_level: 3

::: manimgx.Mobject.get_right
    options:
      heading_level: 3

::: manimgx.Mobject.get_corner
    options:
      heading_level: 3

::: manimgx.Mobject.get_critical_point
    options:
      heading_level: 3

::: manimgx.Mobject.get_boundary_point
    options:
      heading_level: 3

::: manimgx.Mobject.get_x
    options:
      heading_level: 3

::: manimgx.Mobject.get_y
    options:
      heading_level: 3

::: manimgx.Mobject.get_z
    options:
      heading_level: 3

::: manimgx.Mobject.boundary_box
    options:
      heading_level: 3

## 移动 mobject

::: manimgx.Mobject.move_to
    options:
      heading_level: 3

::: manimgx.Mobject.shift
    options:
      heading_level: 3

::: manimgx.Mobject.center
    options:
      heading_level: 3

::: manimgx.Mobject.set_x
    options:
      heading_level: 3

::: manimgx.Mobject.set_y
    options:
      heading_level: 3

::: manimgx.Mobject.set_z
    options:
      heading_level: 3

## 相对于另一个 mobject 放置

两个 mobject 之间的间距称为 buff。以下是常用间距大小。

<div class="mx-constants" markdown>

::: manimgx.SMALL_BUFF
    options:
      heading_level: 3

::: manimgx.MED_SMALL_BUFF
    options:
      heading_level: 3

::: manimgx.MED_LARGE_BUFF
    options:
      heading_level: 3

::: manimgx.LARGE_BUFF
    options:
      heading_level: 3

::: manimgx.DEFAULT_MOBJECT_TO_MOBJECT_BUFFER
    options:
      heading_level: 3

::: manimgx.DEFAULT_MOBJECT_TO_EDGE_BUFFER
    options:
      heading_level: 3

</div>

::: manimgx.Mobject.next_to
    options:
      heading_level: 3

::: manimgx.Mobject.align_to
    options:
      heading_level: 3

::: manimgx.Mobject.match_x
    options:
      heading_level: 3

::: manimgx.Mobject.match_y
    options:
      heading_level: 3

::: manimgx.Mobject.match_z
    options:
      heading_level: 3

## 在画面中放置 mobject

::: manimgx.Mobject.to_edge
    options:
      heading_level: 3

::: manimgx.Mobject.to_corner
    options:
      heading_level: 3

::: manimgx.Mobject.shift_onto_screen
    options:
      heading_level: 3

::: manimgx.Mobject.is_off_screen
    options:
      heading_level: 3

## 计算点

点是 NumPy 数组，因此 NumPy 可以对其进行计算。以下函数执行场景
中常见的操作。

::: manimgx.interpolate
    options:
      heading_level: 3

::: manimgx.midpoint
    options:
      heading_level: 3

::: manimgx.normalize
    options:
      heading_level: 3

::: manimgx.rotate_vector
    options:
      heading_level: 3

::: manimgx.angle_of_vector
    options:
      heading_level: 3

::: manimgx.angle_between_vectors
    options:
      heading_level: 3

::: manimgx.line_intersection
    options:
      heading_level: 3

::: manimgx.perpendicular_bisector
    options:
      heading_level: 3

::: manimgx.polylabel
    options:
      heading_level: 3

::: manimgx.inverse_interpolate
    options:
      heading_level: 3