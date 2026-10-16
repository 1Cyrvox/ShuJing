---
title: "圆与弧"
description: "圆、点、椭圆和弧，以及由它们制成的圆环和扇形。"
---

# 圆与弧

```python fold title="影片代码"
import manimgx as m


class CirclesAndArcs(m.Scene):
    def construct(self) -> None:
        shapes = m.VGroup(
            m.Circle(color=m.BLUE),
            m.Dot(radius=0.3, color=m.YELLOW),
            m.Ellipse(width=2.6, height=1.4, color=m.GREEN),
            m.Arc(radius=1, start_angle=0, angle=3 * m.PI / 2, color=m.RED),
            m.Annulus(inner_radius=0.5, outer_radius=1, color=m.TEAL),
            m.Sector(radius=1.1, angle=2 * m.PI / 3, color=m.GOLD),
        )
        names = ["Circle", "Dot", "Ellipse", "Arc", "Annulus", "Sector"]
        cells = m.VGroup()
        for shape, name in zip(shapes, names, strict=True):
            label = m.Text(name, font="monospace", font_size=30)
            cells.add(m.VGroup(shape, label.next_to(shape, m.DOWN, buff=0.4)))
        cells.arrange_in_grid(rows=2, buff=(1.2, 0.8))
        self.play(m.LaggedStart(*[m.Create(cell[0]) for cell in cells], lag_ratio=0.15))
        self.play(m.FadeIn(m.VGroup(*[cell[1] for cell in cells])))
        self.wait()
```

圆是一段绕了一整圈的弧。弧是圆的一部分：从一个起始角开始，逆时针转过一定角度。点是一个小的实心圆，用于标记一个位置。圆环是两个圆之间的区域，而圆环或圆盘的一片是一个扇形。

弧的末端如同线一样可以带有箭头尖端：参见 [线与箭头](lines-and-arrows.md#_3)。

::: manimgx.Circle
    options:
      heading_level: 2

::: manimgx.Dot
    options:
      heading_level: 2

::: manimgx.Ellipse
    options:
      heading_level: 2

::: manimgx.Arc
    options:
      heading_level: 2

::: manimgx.ArcBetweenPoints
    options:
      heading_level: 2

::: manimgx.Annulus
    options:
      heading_level: 2

::: manimgx.AnnularSector
    options:
      heading_level: 2

::: manimgx.Sector
    options:
      heading_level: 2

::: manimgx.mobjects.shapes.ArcOptions
::: manimgx.mobjects.shapes.SectorOptions
