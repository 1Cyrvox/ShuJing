---
title: "颜色"
description: "命名颜色、混合颜色，以及混合、反转和选择颜色的函数。"
---

# 颜色

```python fold title="影片代码"
import manimgx as m


class ColorsHero(m.Scene):
    def construct(self) -> None:
        rows = m.VGroup()
        for family in [
            "BLUE",
            "TEAL",
            "GREEN",
            "YELLOW",
            "GOLD",
            "RED",
            "MAROON",
            "PURPLE",
            "GREY",
        ]:
            row = m.VGroup(m.Text(family, font="monospace", font_size=24))
            for shade in "ABCDE":
                color = m.PALETTE[f"{family}_{shade}"]
                row.add(
                    m.Circle(radius=0.24, color=color, fill_opacity=1, stroke_width=0)
                )
            row.arrange(buff=0.16)
            rows.add(row)
        rows.arrange(m.DOWN, buff=0.16, aligned_edge=m.RIGHT)
        self.play(
            m.LaggedStart(
                *[m.FadeIn(row, shift=0.2 * m.RIGHT) for row in rows], lag_ratio=0.1
            )
        )
        self.wait()
```

颜色可以是一个名称，如 `m.BLUE`；一个十六进制代码，如 `"#58C4DD"`；或红、
绿、蓝的数值。在需要颜色的地方，三者可以互相替代：
`m.Circle(color="#58C4DD")` 等同于 `m.Circle(color=m.BLUE)`。

大多数命名颜色有五个深浅级别的色族，从 A（最浅）到 E（最深）；
色族自身的名称对应其 C 级。GRAY 和 GREY 是同一颜色的两种拼写。

## 命名颜色

::: manimgx.drawing.paint
    options:
      show_root_heading: false
      extra:
        palette: true

::: manimgx.PALETTE
    options:
      heading_level: 3

## 创建颜色

::: manimgx.ManimColor
    options:
      heading_level: 3

::: manimgx.HSV
    options:
      heading_level: 3

## 混合颜色

::: manimgx.interpolate_color
    options:
      heading_level: 3

::: manimgx.color_gradient
    options:
      heading_level: 3

::: manimgx.average_color
    options:
      heading_level: 3

::: manimgx.invert_color
    options:
      heading_level: 3

::: manimgx.colors_by_value
    options:
      heading_level: 3

## 随机选择颜色

::: manimgx.random_color
    options:
      heading_level: 3

::: manimgx.random_bright_color
    options:
      heading_level: 3

::: manimgx.RandomColorGenerator
    options:
      heading_level: 3