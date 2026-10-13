---
title: "曲线"
description: "函数的图、参数曲线和隐式曲线，使用画面自身的坐标。"
---

# 曲线


<img src="../../../films/CurvesHero.webp" alt="CurvesHero" />

```python fold title="影片代码"
import manimgx as m
import numpy as np


def heart(t: float) -> np.ndarray:
    x = 16 * np.sin(t) ** 3
    y = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
    return np.array([x, y, 0]) / 6


class CurvesHero(m.Scene):
    def construct(self) -> None:
        graph = m.FunctionGraph(np.sin, x_range=[-6, -1], color=m.BLUE)
        curve = m.ParametricFunction(heart, t_range=[0, 2 * np.pi], color=m.RED)
        circle = m.ImplicitFunction(
            lambda x, y: (x - 4) ** 2 + y**2 - 2.25, color=m.YELLOW
        )
        self.play(m.Create(graph), m.Create(curve), m.Create(circle), run_time=3)
        self.wait()
```

这些曲线以画面自身的坐标绘制：`sin` 的图经过
画面的点 `[0, 0, 0]`。要在坐标轴上以坐标轴的坐标绘制图，请使用
[axes.plot][manimgx.Axes.plot]，它会为你创建这些曲线之一。

::: manimgx.FunctionGraph
    options:
      heading_level: 2

::: manimgx.ParametricFunction
    options:
      heading_level: 2

::: manimgx.ImplicitFunction
    options:
      heading_level: 2