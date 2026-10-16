---
title: "图像与 SVG"
description: "来自图像文件或像素数组的图片，以及从 SVG 文件读取的绘图，其形状为路径。"
---

# 图像与 SVG

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

图像是位于矩形上的图片：从文件（PNG、JPEG 等）读取，或由像素数组生成。它像任何
mobject 一样移动、缩放、旋转和淡入淡出；其像素保持自身不变。SVG 绘图则不同：其
形状变为路径，每条路径都是一个可着色、移动和绘制的部分，作为 ManimGX 自身的
形状。

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
