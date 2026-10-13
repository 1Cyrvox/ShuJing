---
title: "同时与依次"
description: "同时播放动画、一个接一个播放，或每个在前一个之后稍迟播放；放慢或加快播放。"
---

# 同时与依次


<video src="../../films/TogetherHero.mp4" autoplay loop muted playsinline controls></video>

```python fold title="影片代码"
import manimgx as m


class TogetherHero(m.Scene):
    def construct(self) -> None:
        dots = m.VGroup(*[m.Dot(radius=0.2, color=m.YELLOW) for _ in range(6)]).arrange(
            buff=0.8
        )
        self.play(
            m.LaggedStart(*[m.GrowFromCenter(dot) for dot in dots], lag_ratio=0.3)
        )
        self.play(m.Succession(*[dot.animate.shift(m.UP) for dot in dots], run_time=2))
        self.play(m.AnimationGroup(*[dot.animate.shift(m.DOWN) for dot in dots]))
        self.wait()
```

`self.play(a, b)` 同时播放 a 和 b。组将多个动画作为一个整体播放：同时、依次，
或每个在前一个之后稍迟播放。组本身也是动画，因此组可以嵌套，组也可以在更大的 play 中播放。

::: manimgx.AnimationGroup
    options:
      heading_level: 2

::: manimgx.Succession
    options:
      heading_level: 2

::: manimgx.LaggedStart
    options:
      heading_level: 2

::: manimgx.LaggedStartMap
    options:
      heading_level: 2

::: manimgx.ChangeSpeed
    options:
      heading_level: 2

::: manimgx.Wait
    options:
      heading_level: 2

::: manimgx.Add
    options:
      heading_level: 2