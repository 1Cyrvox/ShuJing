---
title: "向量场"
description: "平面每个点的向量，以箭头或流线绘制，以及场携带的 mobject。"
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

向量场在平面的每个点给出一个向量：从点到向量的函数。以箭头
绘制时，在网格的每个点一个；以流线绘制时，是粒子
将遵循的路径。场的颜色表示其强度。场还可以移动 mobject：
像水流携带落叶一样携带它们。

::: manimgx.VectorField
    options:
      heading_level: 2

::: manimgx.ArrowVectorField
    options:
      heading_level: 2

::: manimgx.StreamLines
    options:
      heading_level: 2