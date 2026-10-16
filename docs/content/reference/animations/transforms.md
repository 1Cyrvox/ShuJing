---
title: "变换"
description: "将一个 mobject 变为另一个：其形状和样式，逐部分或通过匹配各部分，沿直线路径或弧线进行。"
---

# 变换

```python fold title="影片代码"
import manimgx as m


class TransformsHero(m.Scene):
    def construct(self) -> None:
        square = m.Square(color=m.BLUE, fill_opacity=0.5).shift(3 * m.LEFT)
        circle = m.Circle(color=m.PINK, fill_opacity=0.5).shift(3 * m.LEFT)
        star = m.Star(color=m.YELLOW, fill_opacity=0.5).shift(3 * m.RIGHT)
        self.play(m.Create(square))
        self.play(m.ReplacementTransform(square, circle))
        self.play(m.TransformFromCopy(circle, star, path_arc=m.PI / 2))
        self.play(m.Swap(circle, star))
        self.wait()
```

变换将一个 mobject 变为另一个：其点行进到另一个的点，其样式融入另一个的样式。
[ReplacementTransform][manimgx.ReplacementTransform] 随后将另一个 mobject 放在其
位置，以便你继续使用新的 mobject；[Transform][manimgx.Transform] 保留第一个 mobject，
此时它已变为另一个的形状。要将一个公式逐部分变为另一个，匹配它们各部分：
[TransformMatchingTex][manimgx.TransformMatchingTex]。

每个点沿直线行进，除非你给定一条弧线：`path_arc=m.PI` 让每个点绕半圈行进。路径函数可
选择任何其他方式。

::: manimgx.Transform
    options:
      heading_level: 2

::: manimgx.ReplacementTransform
    options:
      heading_level: 2

::: manimgx.TransformFromCopy
    options:
      heading_level: 2

::: manimgx.ClockwiseTransform
    options:
      heading_level: 2

::: manimgx.CounterclockwiseTransform
    options:
      heading_level: 2

::: manimgx.FadeTransform
    options:
      heading_level: 2

::: manimgx.FadeTransformPieces
    options:
      heading_level: 2

## 匹配各部分

::: manimgx.TransformMatchingTex
    options:
      heading_level: 3

::: manimgx.TransformMatchingShapes
    options:
      heading_level: 3

## 交换位置

::: manimgx.Swap
    options:
      heading_level: 3

::: manimgx.CyclicReplace
    options:
      heading_level: 3

## 变换关键字

::: manimgx.animation.transform.TransformOptions
    options:
      heading_level: 3

## 路径

路径函数说明每个点如何从起点行进到终点：将一个作为 `path_func` 传入。

::: manimgx.straight_path
    options:
      heading_level: 3

::: manimgx.path_along_arc
    options:
      heading_level: 3

::: manimgx.clockwise_path
    options:
      heading_level: 3

::: manimgx.counterclockwise_path
    options:
      heading_level: 3

::: manimgx.spiral_path
    options:
      heading_level: 3

::: manimgx.path_along_circles
    options:
      heading_level: 3

::: manimgx.Path
    options:
      heading_level: 3

::: manimgx.STRAIGHT_PATH_THRESHOLD
    options:
      heading_level: 3
