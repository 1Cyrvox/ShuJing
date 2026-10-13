---
title: "圆和弧"
description: "圆、圆点、椭圆和弧，以及由它们构成的环和扇形。"
---

# 圆和弧


<img src="../../../films/CirclesAndArcs.webp" alt="CirclesAndArcs" />

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

圆是绕一整圈的弧。弧是圆的一部分：从起始
角度逆时针经过一个角度。圆点是小的填充圆，用于标记一个点。
环是两个圆之间的区域，环或圆盘的一片是扇形。

弧的末端可以像线一样有箭头：参见 ](lines-and-arrows.md#_2)。

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