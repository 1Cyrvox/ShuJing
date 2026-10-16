---
title: "值跟踪器"
description: "你动画的数字：它不显示任何内容，更新器读取它，因此一个动画可以移动多个 mobject。"
---

# 值跟踪器

```python fold title="影片代码"
import manimgx as m


def curve(x: float) -> float:
    return x**2 / 4


class ValueTrackersHero(m.Scene):
    def construct(self) -> None:
        axes = m.Axes(x_range=[0, 5, 1], y_range=[0, 7, 1], x_length=8, y_length=5)
        graph = axes.plot(curve, color=m.BLUE)
        x = m.ValueTracker(1)
        dot = m.always_redraw(
            lambda: m.Dot(axes.c2p(x.get_value(), curve(x.get_value())), color=m.YELLOW)
        )
        number = m.always_redraw(
            lambda: m.DecimalNumber(x.get_value()).next_to(dot, m.UL)
        )
        self.add(axes, graph, dot, number)
        self.play(x.animate.set_value(4.5), run_time=3)
        self.wait()
```

值跟踪器持有一个数字且不显示任何内容。用 `tracker.animate.set_value(10)` 动画它的数字；在更新器中，或在 [always_redraw][manimgx.always_redraw] 调用的函数中用 `tracker.get_value()` 读取它。跟踪器的一个动画随后移动每个读取它的 mobject。

::: manimgx.ValueTracker
    options:
      heading_level: 2

::: manimgx.ComplexValueTracker
    options:
      heading_level: 2
