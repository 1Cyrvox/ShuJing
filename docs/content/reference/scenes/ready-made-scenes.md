---
title: "现成场景"
description: "为某一类视频而制作的场景：平面上的向量、平面的线性变换，以及放大插图。"
---

# 现成场景

```python fold title="影片代码"
import manimgx as m


class ReadyMadeScenesHero(m.LinearTransformationScene):
    def construct(self) -> None:
        self.add_vector([1, 2], color=m.YELLOW)
        self.apply_matrix([[1, 1], [0, 1]])
        self.wait()
```

这些场景自带某一类视频所需的内容。向量场景从平面的原点绘制向量，并附带它们的标签和坐标。线性变换场景在一次 play 中将矩阵应用于平面及平面上的所有内容。缩放场景在插图中显示帧的放大局部。

::: manimgx.VectorScene
    options:
      heading_level: 2

::: manimgx.LinearTransformationScene
    options:
      heading_level: 2

::: manimgx.ZoomedScene
    options:
      heading_level: 2

::: manimgx.scene.ZoomedCameraConfig
    options:
      heading_level: 3

::: manimgx.mobjects.shapes.ArrowTipsBase
::: manimgx.mobjects.grid.MatrixOptions
::: manimgx.scene.LabelPlacement
::: manimgx.scene.VectorLabelOptions
::: manimgx.scene.UnitSquareOptions
