---
title: "值追踪器"
description: "可动画化的数字：它不显示任何东西，更新器读取它，因此一个动画可以移动多个 mobject。"
---

# 值追踪器


<video src="../../films/ValueTrackersHero.mp4" autoplay loop muted playsinline controls></video>

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

值追踪器保存一个数字但不显示任何东西。用
`tracker.animate.set_value(10)` 动画化其数字；在更新器中或
[always_redraw][manimgx.always_redraw] 调用的函数中用 `tracker.get_value()` 读取它。
追踪器的一个动画然后
移动每个读取它的 mobject。

::: manimgx.ValueTracker
    options:
      heading_level: 2

::: manimgx.ComplexValueTracker
    options:
      heading_level: 2