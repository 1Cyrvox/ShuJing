---
title: "图表"
description: "可生长和变化的柱状图，以及概率的样本空间。"
---

# 图表

```python fold title="影片代码"
import manimgx as m


class ChartsHero(m.Scene):
    def construct(self) -> None:
        chart = m.BarChart(
            [3, 5, 2, 6, 4], bar_names=["A", "B", "C", "D", "E"], y_range=[0, 8, 2]
        )
        self.play(m.Create(chart))
        self.play(chart.animate.change_bar_values([5, 2, 6, 3, 7]), run_time=2)
        self.wait()
```

柱状图是带有每个值一个柱条的坐标轴，柱条随值的变化而生长和收缩。
样本空间是一个代表所有可能结果的矩形：将其划分为
面积等于其概率的部分。

::: manimgx.BarChart
    options:
      heading_level: 2

::: manimgx.SampleSpace
    options:
      heading_level: 2