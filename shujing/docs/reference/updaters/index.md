---
title: "更新器"
description: "mobject 在每帧保持的规则：跟随另一个 mobject、显示数字、重绘自身，或随时间移动。"
---

# 更新器

```python fold title="影片代码"
import manimgx as m


class UpdatersHero(m.Scene):
    def construct(self) -> None:
        dot = m.Dot(color=m.YELLOW).shift(3 * m.LEFT)
        label = m.Text("dot", font_size=36)
        label.add_updater(lambda mob: mob.next_to(dot, m.UP))
        trail = m.TracedPath(dot.get_center, stroke_color=m.YELLOW, stroke_width=4)
        self.add(trail, dot, label)
        self.play(dot.animate.shift(6 * m.RIGHT), run_time=2)
        self.play(m.Rotate(dot, m.PI, about_point=m.ORIGIN), run_time=2)
        self.wait()
```

动画在其运行时间内改变 mobject。更新器在每帧改变它，只要
它被附加：在其他东西移动时保持一条规则。标签停留在圆点
上方，数字显示追踪器的位置，形状随时间旋转。

更新器是一个函数：ManimGX 在每帧用 mobject 调用它，在 play 和
wait 中都会调用。还接受 `dt` 的函数会获得自上次运行以来的时间（秒），
用于持续的运动：`lambda mob, dt: mob.rotate(dt)` 使 mobject 每秒
旋转一弧度。

## 添加更新器

::: manimgx.Mobject.add_updater
    options:
      heading_level: 3

::: manimgx.Mobject.remove_updater
    options:
      heading_level: 3

::: manimgx.Mobject.clear_updaters
    options:
      heading_level: 3

::: manimgx.Mobject.get_updaters
    options:
      heading_level: 3

::: manimgx.Mobject.suspend_updating
    options:
      heading_level: 3

::: manimgx.Mobject.resume_updating
    options:
      heading_level: 3

::: manimgx.Mobject.update
    options:
      heading_level: 3

::: manimgx.Mobject.always
    options:
      heading_level: 3

## 基于时间的更新器如何运行

ManimGX 在仿真时钟的每个刻度运行基于时间的更新器，无论帧率如何
每秒 60 次，使仿真在每个帧率下给出相同结果。流（无论时间如何
分割都做同样的事）在每帧运行；记录器（读取世界）在
所有其他东西之后运行。

::: manimgx.mobject.flow
    options:
      heading_level: 3

::: manimgx.mobject.record
    options:
      heading_level: 3

## 现成更新器

::: manimgx.always_redraw
    options:
      heading_level: 3

::: manimgx.always_rotate
    options:
      heading_level: 3

::: manimgx.always_shift
    options:
      heading_level: 3

::: manimgx.turn_animation_into_updater
    options:
      heading_level: 3

::: manimgx.cycle_animation
    options:
      heading_level: 3

## 作为动画的更新器

::: manimgx.UpdateFromFunc
    options:
      heading_level: 3

::: manimgx.UpdateFromAlphaFunc
    options:
      heading_level: 3

::: manimgx.MaintainPositionRelativeTo
    options:
      heading_level: 3

## 轨迹和边界

::: manimgx.TracedPath
    options:
      heading_level: 3

::: manimgx.AnimatedBoundary
    options:
      heading_level: 3