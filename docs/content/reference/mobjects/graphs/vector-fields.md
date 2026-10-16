---
title: "向量场"
description: "平面上每一点处的向量，绘制为箭头或流线，以及它所携带的 mobject。"
---

# 向量场

```python fold title="影片代码"
import manimgx as m
import numpy as np


def swirl(point: np.ndarray) -> np.ndarray:
    x, y = point[0], point[1]
    return np.array([-y, x, 0]) / 3 + np.array([0.3 * np.sin(y), 0, 0])


class VectorFieldsHero(m.Scene):
    def construct(self) -> None:
        field = m.ArrowVectorField(swirl)
        dots = m.VGroup(*[m.Dot([x, 0, 0], color=m.YELLOW) for x in [1, 2, 3]])
        self.play(m.Create(field))
        self.add(dots)
        for dot in dots:
            dot.add_updater(field.get_nudge_updater())
        self.wait(3)
```

向量场为平面上每一点赋予一个向量：一个从点到向量的函数。可以将其绘制为箭头（在网格的每一点处各一个），或绘制为流线（即粒子将遵循的路径）。场的颜色表示其强度。场还可以移动 mobject：如同水流携带一片落叶般将它们带走。

::: manimgx.VectorField
    options:
      heading_level: 2

::: manimgx.ArrowVectorField
    options:
      heading_level: 2

::: manimgx.StreamLines
    options:
      heading_level: 2

::: manimgx.animation.timeline.Untimed
