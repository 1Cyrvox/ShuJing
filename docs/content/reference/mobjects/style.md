---
title: "样式"
description: "mobject 的填充与描边、它们的颜色与不透明度、渐变，以及覆盖关系。"
---

# 样式

```python fold title="影片代码"
import manimgx as m


class StyleHero(m.Scene):
    def construct(self) -> None:
        stroked = m.Circle(color=m.BLUE, stroke_width=8)
        filled = m.Circle(color=m.GREEN, fill_opacity=0.6)
        gradient = m.Circle(fill_opacity=1, stroke_width=0).set_color(
            [m.BLUE, m.YELLOW]
        )
        faint = m.Circle(color=m.RED, fill_opacity=1).fade(0.7)
        circles = m.VGroup(stroked, filled, gradient, faint).arrange(buff=0.8)
        names = m.VGroup(
            m.Text("stroke", font="monospace", font_size=24),
            m.Text("fill", font="monospace", font_size=24),
            m.Text("gradient", font="monospace", font_size=24),
            m.Text("fade", font="monospace", font_size=24),
        )
        for circle, name in zip(circles, names, strict=True):
            name.next_to(circle, m.DOWN, buff=0.5)
        self.play(
            m.LaggedStart(*[m.Create(circle) for circle in circles], lag_ratio=0.2)
        )
        self.play(m.FadeIn(names))
        self.wait()
```

形状有描边（其轮廓）和填充（其内部）。各自都有颜色和不透明度，取值从 0（不可见）到
1（完全不透明），描边还有宽度，以单位的百分之一为单位。大多数形状默认有描边无填充：设置
`fill_opacity` 来填充它们。

创建时每个 mobject 都接受相同的样式关键字，每种类型有自己的默认值（圆为红色，点为填充）。
以下方法在之后更改样式，作用于 mobject 及其所有组成部分。

::: manimgx.drawing.paint.Style
    options:
      heading_level: 2
      inherited_members: true
      members: [color, fill_color, fill_opacity, stroke_color, stroke_opacity, stroke_width, background_stroke_color, background_stroke_opacity, background_stroke_width, sheen_factor, sheen_direction, joint_type, cap_style, shade_in_3d, material, z_index, name, target]

::: manimgx.drawing.paint.Look
    options:
      heading_level: 2

## 颜色与不透明度

::: manimgx.Mobject.set_color
    options:
      heading_level: 3

::: manimgx.Mobject.set_fill
    options:
      heading_level: 3

::: manimgx.Mobject.set_stroke
    options:
      heading_level: 3

::: manimgx.Mobject.set_opacity
    options:
      heading_level: 3

::: manimgx.Mobject.fade
    options:
      heading_level: 3

::: manimgx.Mobject.fade_to
    options:
      heading_level: 3

::: manimgx.Mobject.set_style
    options:
      heading_level: 3

::: manimgx.Mobject.match_style
    options:
      heading_level: 3

::: manimgx.Mobject.match_color
    options:
      heading_level: 3

::: manimgx.Mobject.color
    options:
      heading_level: 3

::: manimgx.Mobject.fill_color
    options:
      heading_level: 3

::: manimgx.Mobject.fill_opacity
    options:
      heading_level: 3

::: manimgx.Mobject.stroke_color
    options:
      heading_level: 3

::: manimgx.Mobject.stroke_opacity
    options:
      heading_level: 3

::: manimgx.Mobject.stroke_width
    options:
      heading_level: 3

## 覆盖源颜色

文本和 SVG 绘图自带颜色。以下关键字用于覆盖这些颜色。

::: manimgx.drawing.paint.Repaint
    options:
      heading_level: 3

## 渐变与光泽

给定一个颜色列表以及某种颜色的位置，即可生成渐变：`set_color([m.BLUE,
m.YELLOW])` 在 mobject 上将一种颜色渐变为另一种。

::: manimgx.Mobject.set_color_by_gradient
    options:
      heading_level: 3

::: manimgx.Mobject.set_colors_by_radial_gradient
    options:
      heading_level: 3

::: manimgx.Mobject.set_submobject_colors_by_radial_gradient
    options:
      heading_level: 3

::: manimgx.Mobject.set_sheen
    options:
      heading_level: 3

::: manimgx.Mobject.set_sheen_direction
    options:
      heading_level: 3

## 描边的端点与角

::: manimgx.CapStyleType
    options:
      heading_level: 3

::: manimgx.LineJointType
    options:
      heading_level: 3

::: manimgx.VMobject.set_cap_style
    options:
      heading_level: 3

## 覆盖关系

后添加的 mobject 覆盖先添加的。无论添加顺序如何，z-index 较高者覆盖较低者。

::: manimgx.Mobject.set_z_index
    options:
      heading_level: 3

::: manimgx.Mobject.z_index
    options:
      heading_level: 3

::: manimgx.Mobject.add_background_rectangle
    options:
      heading_level: 3

::: manimgx.Mobject.background_rectangle
    options:
      heading_level: 3

## 类的默认值

::: manimgx.Mobject.set_default
    options:
      heading_level: 3

::: manimgx.mobject.BackgroundOptions
