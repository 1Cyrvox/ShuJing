---
title: "数轴"
description: "带有刻度、数字和标签的单条坐标轴，均匀或对数刻度。"
---

# 数轴

```python fold title="影片代码"
import manimgx as m


class NumberLinesHero(m.Scene):
    def construct(self) -> None:
        line = m.NumberLine(x_range=[-3, 3, 1], length=10, include_numbers=True)
        dot = m.Dot(line.n2p(-2), radius=0.12, color=m.YELLOW)
        interval = m.UnitInterval(length=8, include_numbers=True).shift(2 * m.DOWN)
        self.play(m.Create(line))
        self.play(m.GrowFromCenter(dot))
        self.play(dot.animate.move_to(line.n2p(2.5)), run_time=2)
        self.play(m.Create(interval))
        self.wait()
```

数轴是在每个点标注数字的直线。其范围 `[start, end,
step]` 给出首尾数字和刻度间距；其长度以
画面单位度量。[n2p][manimgx.NumberLine.number_to_point] 将数字转换为
其在数轴上的点，用于将任何东西放在某个数字处。

坐标轴也是数轴：[Axes][manimgx.Axes] 的每条轴都是数轴，并接受以下
关键字参数。

::: manimgx.NumberLine
    options:
      heading_level: 2

::: manimgx.UnitInterval
    options:
      heading_level: 2

## 刻度

数轴的刻度放置其数字：均匀或按对数。通过 `scaling` 指定。

::: manimgx.LinearBase
    options:
      heading_level: 3
      inherited_members: [function, inverse_function]

::: manimgx.LogBase
    options:
      heading_level: 3
      inherited_members: [function, inverse_function]