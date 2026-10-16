---
title: "线与箭头"
description: "点之间的线、指示方向的箭头、从原点出发的向量，以及终止它们的箭头尖端。"
---

# 线与箭头

```python fold title="影片代码"
import manimgx as m


class LinesAndArrows(m.Scene):
    def construct(self) -> None:
        line = m.Line(m.LEFT, m.RIGHT)
        dashed = m.DashedLine(m.LEFT, m.RIGHT, color=m.BLUE)
        arrow = m.Arrow(m.LEFT, m.RIGHT, buff=0, color=m.YELLOW)
        double = m.DoubleArrow(m.LEFT, m.RIGHT, buff=0, color=m.GREEN)
        curved = m.CurvedArrow(m.LEFT, m.RIGHT, color=m.PINK)
        stealth = m.Line(m.LEFT, m.RIGHT, color=m.ORANGE).add_tip(
            tip_shape=m.StealthTip
        )
        shapes = m.VGroup(line, dashed, arrow, double, curved, stealth)
        names = m.VGroup(
            m.Text("Line", font="monospace", font_size=26),
            m.Text("DashedLine", font="monospace", font_size=26),
            m.Text("Arrow", font="monospace", font_size=26),
            m.Text("DoubleArrow", font="monospace", font_size=26),
            m.Text("CurvedArrow", font="monospace", font_size=26),
            m.Text("StealthTip", font="monospace", font_size=26),
        )
        cells = m.VGroup()
        for shape, name in zip(shapes, names, strict=True):
            name.next_to(shape, m.DOWN, buff=0.4)
            cells.add(m.VGroup(shape, name))
        cells.arrange_in_grid(rows=2, buff=(1.4, 1))
        self.play(m.LaggedStart(*[m.Create(shape) for shape in shapes], lag_ratio=0.2))
        self.play(m.FadeIn(names))
        self.wait()
```

线连接两个点。箭头是末端带有箭头尖端的线，用于指示方向；向量是从原点出发的箭头。线、箭头和弧都可以在任一端以箭头尖端结束，尖端可以是[本页末尾](#_3)列出的任何形状。

线的一端也可以是一个 mobject：此时线从该 mobject 的边缘开始延伸，从而连接两个形状而不穿过它们。

::: manimgx.Line
    options:
      heading_level: 2

::: manimgx.DashedLine
    options:
      heading_level: 2

::: manimgx.Arrow
    options:
      heading_level: 2

::: manimgx.DoubleArrow
    options:
      heading_level: 2

::: manimgx.Vector
    options:
      heading_level: 2

::: manimgx.CurvedArrow
    options:
      heading_level: 2

::: manimgx.CurvedDoubleArrow
    options:
      heading_level: 2

::: manimgx.TangentLine
    options:
      heading_level: 2

## 箭头尖端

箭头尖端是位于线、弧或箭头末端的一个小形状。箭头会自行创建其尖端；任何其他线或弧可通过 `add_tip` 添加一个。`tip_shape` 选择其形状，`tip_style` 选择其样式。

::: manimgx.TipableVMobject
    options:
      heading_level: 3
      members: [add_tip, pop_tips, get_tip, get_tips, has_tip, has_start_tip, tip, start_tip, get_start, get_end, get_length]

::: manimgx.mobjects.shapes.TippedBase
    options:
      heading_level: 3
      inherited_members: [tip_length, normal_vector, tip_style]

### 尖端形状

::: manimgx.ArrowTriangleFilledTip
    options:
      heading_level: 4

::: manimgx.ArrowTriangleTip
    options:
      heading_level: 4

::: manimgx.StealthTip
    options:
      heading_level: 4

::: manimgx.ArrowCircleFilledTip
    options:
      heading_level: 4

::: manimgx.ArrowCircleTip
    options:
      heading_level: 4

::: manimgx.ArrowSquareFilledTip
    options:
      heading_level: 4

::: manimgx.ArrowSquareTip
    options:
      heading_level: 4

::: manimgx.ArrowTip
    options:
      heading_level: 4

::: manimgx.mobjects.shapes.Arced
::: manimgx.mobject.Pivot
::: manimgx.mobjects.grid.MatrixOptions
