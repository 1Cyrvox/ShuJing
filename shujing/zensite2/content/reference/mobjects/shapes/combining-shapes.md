---
title: "组合形状"
description: "从旧形状创建新形状：并、交、差、带孔的形状，以及围绕点的凸包。"
---

# 组合形状


<img src="../../../films/CombiningShapes.webp" alt="CombiningShapes" />

```python fold title="影片代码"
import manimgx as m


class CombiningShapes(m.Scene):
    def construct(self) -> None:
        def pair() -> m.VGroup:
            return m.VGroup(
                m.Circle(radius=0.9).shift(0.45 * m.LEFT),
                m.Square(side_length=1.6).shift(0.45 * m.RIGHT),
            )

        made = m.VGroup()
        names = ["Union", "Intersection", "Difference", "Exclusion"]
        for kind, name in zip(
            [m.Union, m.Intersection, m.Difference, m.Exclusion], names, strict=True
        ):
            a, b = pair()
            shape = kind(a, b, color=m.BLUE, fill_opacity=0.7)
            outline = m.VGroup(a, b).set_stroke(m.GREY_B, width=2)
            label = m.Text(name, font="monospace", font_size=26).next_to(
                outline, m.DOWN, buff=0.4
            )
            made.add(m.VGroup(outline, shape, label))
        made.arrange(buff=0.6)
        self.play(m.LaggedStart(*[m.Create(cell[0]) for cell in made], lag_ratio=0.15))
        self.play(m.LaggedStart(*[m.FadeIn(cell[1:]) for cell in made], lag_ratio=0.15))
        self.wait()
```

两个形状重叠形成三个区域：只有第一个的区域、只有第二个的区域和
两者都有的区域。这些类从其中某些区域创建新路径，按你指定的方式
设置样式：原始形状保持不变。cutout 在形状中切出孔洞，convex hull
像带子一样包裹点。

::: manimgx.Union
    options:
      heading_level: 2

::: manimgx.Intersection
    options:
      heading_level: 2

::: manimgx.Difference
    options:
      heading_level: 2

::: manimgx.Exclusion
    options:
      heading_level: 2

::: manimgx.Cutout
    options:
      heading_level: 2

::: manimgx.ConvexHull
    options:
      heading_level: 2