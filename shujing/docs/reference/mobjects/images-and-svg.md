---
title: "图片和 SVG"
description: "来自图片文件或像素数组的图片，以及从 SVG 文件读取的绘图，其形状为路径。"
---

# 图片和 SVG

```python fold title="影片代码"
import manimgx as m
import numpy as np


class ImagesAndSvgHero(m.Scene):
    def construct(self) -> None:
        x = np.linspace(-1, 1, 64)
        pixels = np.zeros((64, 64, 3), dtype=np.uint8)
        pixels[..., 0] = 255 * (x[None, :] + 1) / 2
        pixels[..., 2] = 255 * (x[:, None] + 1) / 2
        image = m.ImageMobject(pixels).scale_to_fit_height(4)
        image.set_resampling_algorithm(m.RESAMPLING_ALGORITHMS["nearest"])
        self.play(m.FadeIn(image))
        self.play(image.animate.rotate(m.PI / 8).scale(0.8))
        self.wait()
```

图片是绘制在矩形上的图像：从文件读取（PNG、JPEG 等），或由
像素数组创建。它可以像任何 mobject 一样移动、缩放、旋转和淡入淡出；其像素保持不变。
SVG 绘图则不同：其形状变为路径，每个都是可着色、移动和绘制的组成部分，
成为 ManimGX 自有的形状。

::: manimgx.ImageMobject
    options:
      heading_level: 2

::: manimgx.RESAMPLING_ALGORITHMS
    options:
      heading_level: 3

::: manimgx.constants.Resampling
    options:
      heading_level: 3

::: manimgx.SVGMobject
    options:
      heading_level: 2

::: manimgx.mobjects.svg.PathOptions
    options:
      heading_level: 3