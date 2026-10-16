---
title: "尺寸与角度"
description: "mobject 的大小和转向，以及缩放、拉伸、旋转、翻转和重塑它的方法。"
---

# 尺寸与角度

```python fold title="影片代码"
import manimgx as m


class SizeAndAngleHero(m.Scene):
    def construct(self) -> None:
        shapes = m.VGroup(
            *[
                m.Square(side_length=1.6, color=m.BLUE, fill_opacity=0.5)
                for _ in range(4)
            ]
        )
        shapes.arrange(buff=1.2)
        names = m.VGroup(
            m.Text("scale(1.4)", font="monospace", font_size=30),
            m.Text("rotate(PI / 4)", font="monospace", font_size=30),
            m.Text("stretch(1.6, 0)", font="monospace", font_size=30),
            m.Text("flip()", font="monospace", font_size=30),
        )
        for shape, name in zip(shapes, names, strict=True):
            name.next_to(shape, m.DOWN, buff=1.1)
        marker = m.Dot(color=m.YELLOW).move_to(shapes[3].get_corner(m.UR))
        shapes[3].add(marker)
        self.add(shapes, names)
        self.play(
            shapes[0].animate.scale(1.4),
            shapes[1].animate.rotate(m.PI / 4),
            shapes[2].animate.stretch(1.6, 0),
            shapes[3].animate.flip(),
            run_time=2,
        )
        self.wait()
```

mobject 的尺寸即其包围盒的尺寸：其[宽度][manimgx.Mobject.width]和
[高度][manimgx.Mobject.height]。大多数形状在创建时确定尺寸（圆通过 `radius`，文本通过
`font_size`）；以下方法在之后更改尺寸，默认围绕 mobject 的中心，除非你指定其他点。

角度以弧度表示：完整一圈为 `m.TAU`，半圈为 `m.PI`，`30 * m.DEGREES` 即 30 度。正角度
逆时针旋转。

## 尺寸

::: manimgx.Mobject.width
    options:
      heading_level: 3

::: manimgx.Mobject.height
    options:
      heading_level: 3

::: manimgx.Mobject.scale
    options:
      heading_level: 3

::: manimgx.Mobject.scale_to_fit_width
    options:
      heading_level: 3

::: manimgx.Mobject.scale_to_fit_height
    options:
      heading_level: 3

::: manimgx.Mobject.match_width
    options:
      heading_level: 3

::: manimgx.Mobject.match_height
    options:
      heading_level: 3

::: manimgx.Mobject.stretch
    options:
      heading_level: 3

::: manimgx.Mobject.stretch_to_fit_width
    options:
      heading_level: 3

::: manimgx.Mobject.stretch_to_fit_height
    options:
      heading_level: 3

::: manimgx.Mobject.replace
    options:
      heading_level: 3

## 角度

<div class="mx-constants" markdown>

::: manimgx.PI
    options:
      heading_level: 3

::: manimgx.TAU
    options:
      heading_level: 3

::: manimgx.DEGREES
    options:
      heading_level: 3

</div>

::: manimgx.Mobject.rotate
    options:
      heading_level: 3

::: manimgx.Mobject.flip
    options:
      heading_level: 3

::: manimgx.rotation_matrix
    options:
      heading_level: 3

## 任意变换

::: manimgx.Mobject.put_start_and_end_on
    options:
      heading_level: 3

::: manimgx.Mobject.apply_matrix
    options:
      heading_level: 3

::: manimgx.Mobject.apply_function
    options:
      heading_level: 3

::: manimgx.Mobject.apply_complex_function
    options:
      heading_level: 3

::: manimgx.Mobject.set
    options:
      heading_level: 3

::: manimgx.mobject.Pivot
