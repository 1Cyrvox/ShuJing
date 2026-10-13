---
title: "移动与变形"
description: "绕点旋转 mobject、沿路径移动，或通过函数、矩阵或流移动每个点。"
---

# 移动与变形


<img src="../../films/MoveAndDeformHero.webp" alt="MoveAndDeformHero" />

```python fold title="影片代码"
import manimgx as m
import numpy as np


class MoveAndDeformHero(m.Scene):
    def construct(self) -> None:
        grid = m.NumberPlane(
            x_range=[-4, 4, 1], y_range=[-3, 3, 1]
        ).prepare_for_nonlinear_transform()
        self.add(grid)
        self.play(m.ApplyMatrix([[1, 1], [0, 1]], grid), run_time=2)
        self.play(
            m.ApplyFunction(
                lambda mob: mob.apply_function(
                    lambda p: p + 0.3 * np.array([np.sin(p[1]), np.sin(p[0]), 0])
                ),
                grid,
            ),
            run_time=2,
        )
        self.wait()
```

有些改变并非方法调用：绕某点持续旋转、沿路径行进、对每个点的变形。这些动画实现它们。

## 旋转与跟随

::: manimgx.Rotate
    options:
      heading_level: 3

::: manimgx.Rotating
    options:
      heading_level: 3

::: manimgx.MoveAlongPath
    options:
      heading_level: 3

## 通过函数

mobject 的每个点前往函数所发送的位置。弯曲的图像需要更多点：
先插入曲线（参见 [insert_n_curves][manimgx.VMobject.insert_n_curves]）。

::: manimgx.ApplyFunction
    options:
      heading_level: 3

::: manimgx.ApplyPointwiseFunction
    options:
      heading_level: 3

::: manimgx.ApplyMatrix
    options:
      heading_level: 3

::: manimgx.ApplyComplexFunction
    options:
      heading_level: 3

## 随时间变形

::: manimgx.Homotopy
    options:
      heading_level: 3

::: manimgx.ComplexHomotopy
    options:
      heading_level: 3

::: manimgx.ApplyWave
    options:
      heading_level: 3

::: manimgx.PhaseFlow
    options:
      heading_level: 3