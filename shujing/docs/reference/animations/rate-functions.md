---
title: "速率函数"
description: "动画如何把握节奏：平滑、匀速、急冲、弹跳或摆动。每一个速率函数，可播放可拖动。"
---

# 速率函数 { #manimgx.animation.easing }

```python fold title="影片代码"
import manimgx as m


class RateFunctionsHero(m.Scene):
    def construct(self) -> None:
        rates = [m.smooth, m.linear, m.rush_into, m.there_and_back, m.ease_out_bounce]
        names = ["smooth", "linear", "rush_into", "there_and_back", "ease_out_bounce"]
        rows = m.VGroup()
        for name in names:
            label = m.Text(name, font="monospace", font_size=28)
            dot = m.Dot(radius=0.14, color=m.YELLOW)
            rows.add(m.VGroup(label, dot))
        rows.arrange(m.DOWN, buff=0.5)
        for row in rows:
            row[0].move_to([-2.2, row.get_y(), 0], aligned_edge=m.RIGHT)
            row[1].move_to([-1.4, row.get_y(), 0])
        self.add(rows)
        self.play(
            *[
                row[1].animate(rate_func=rate).shift(7 * m.RIGHT)
                for row, rate in zip(rows, rates, strict=True)
            ],
            run_time=3,
        )
        self.wait()
```

动画从 0（起点）运行到 1（终点）。其速率函数说明在这段时间的每个时刻变化推进了多远：
对从 0 到 1 的 t 取 `rate_func(t)`。默认的
[smooth][manimgx.smooth] 先慢后快再慢；[linear][manimgx.linear]
保持匀速。将其他速率函数传给 `play` 或任意动画：
`self.play(square.animate.shift(m.RIGHT), rate_func=m.rush_into)`。

速率函数可以超过 1 再返回（用于弹跳），也可以回到 0（使动画在起点结束）。选择一个来观察其运动：

<div class="mx-rates" data-rates="smooth linear rush_into rush_from slow_into double_smooth there_and_back there_and_back_with_pause running_start lingering wiggle exponential_decay smoothstep smootherstep ease_in_back ease_in_bounce ease_in_circ ease_in_cubic ease_in_elastic ease_in_expo ease_in_out_back ease_in_out_bounce ease_in_out_circ ease_in_out_cubic ease_in_out_elastic ease_in_out_expo ease_in_out_quad ease_in_out_quart ease_in_out_quint ease_in_out_sine ease_in_quad ease_in_quart ease_in_quint ease_in_sine ease_out_back ease_out_bounce ease_out_circ ease_out_cubic ease_out_elastic ease_out_expo ease_out_quad ease_out_quart ease_out_quint ease_out_sine"></div>

## 常用速率函数

::: manimgx.smooth
    options:
      heading_level: 3

::: manimgx.linear
    options:
      heading_level: 3

::: manimgx.rush_into
    options:
      heading_level: 3

::: manimgx.rush_from
    options:
      heading_level: 3

::: manimgx.slow_into
    options:
      heading_level: 3

::: manimgx.double_smooth
    options:
      heading_level: 3

::: manimgx.there_and_back
    options:
      heading_level: 3

::: manimgx.there_and_back_with_pause
    options:
      heading_level: 3

::: manimgx.running_start
    options:
      heading_level: 3

::: manimgx.lingering
    options:
      heading_level: 3

::: manimgx.wiggle
    options:
      heading_level: 3

::: manimgx.exponential_decay
    options:
      heading_level: 3

::: manimgx.smoothstep
    options:
      heading_level: 3

::: manimgx.smootherstep
    options:
      heading_level: 3

## 缓动曲线

缓动曲线来自 Web 标准：每条曲线分别缓入（开始慢）、缓出（结束慢）或两者兼具，
各有其专属曲线。

<div class="mx-rows" markdown>

::: manimgx.ease_in_back
    options:
      heading_level: 3

::: manimgx.ease_in_bounce
    options:
      heading_level: 3

::: manimgx.ease_in_circ
    options:
      heading_level: 3

::: manimgx.ease_in_cubic
    options:
      heading_level: 3

::: manimgx.ease_in_elastic
    options:
      heading_level: 3

::: manimgx.ease_in_expo
    options:
      heading_level: 3

::: manimgx.ease_in_out_back
    options:
      heading_level: 3

::: manimgx.ease_in_out_bounce
    options:
      heading_level: 3

::: manimgx.ease_in_out_circ
    options:
      heading_level: 3

::: manimgx.ease_in_out_cubic
    options:
      heading_level: 3

::: manimgx.ease_in_out_elastic
    options:
      heading_level: 3

::: manimgx.ease_in_out_expo
    options:
      heading_level: 3

::: manimgx.ease_in_out_quad
    options:
      heading_level: 3

::: manimgx.ease_in_out_quart
    options:
      heading_level: 3

::: manimgx.ease_in_out_quint
    options:
      heading_level: 3

::: manimgx.ease_in_out_sine
    options:
      heading_level: 3

::: manimgx.ease_in_quad
    options:
      heading_level: 3

::: manimgx.ease_in_quart
    options:
      heading_level: 3

::: manimgx.ease_in_quint
    options:
      heading_level: 3

::: manimgx.ease_in_sine
    options:
      heading_level: 3

::: manimgx.ease_out_back
    options:
      heading_level: 3

::: manimgx.ease_out_bounce
    options:
      heading_level: 3

::: manimgx.ease_out_circ
    options:
      heading_level: 3

::: manimgx.ease_out_cubic
    options:
      heading_level: 3

::: manimgx.ease_out_elastic
    options:
      heading_level: 3

::: manimgx.ease_out_expo
    options:
      heading_level: 3

::: manimgx.ease_out_quad
    options:
      heading_level: 3

::: manimgx.ease_out_quart
    options:
      heading_level: 3

::: manimgx.ease_out_quint
    options:
      heading_level: 3

::: manimgx.ease_out_sine
    options:
      heading_level: 3

</div>

## 自定义

速率函数可以是任意从数值到数值的 Python 函数。以下工具可从一个速率函数构造另一个。

::: manimgx.squish_rate_func
    options:
      heading_level: 3

::: manimgx.not_quite_there
    options:
      heading_level: 3

::: manimgx.unit_interval
    options:
      heading_level: 3

::: manimgx.zero
    options:
      heading_level: 3