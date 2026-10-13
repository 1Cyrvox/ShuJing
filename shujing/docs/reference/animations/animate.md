---
title: "动画化一个改变"
description: "在方法前加 `.animate`，play 便会动画化该方法所做的改变；或将 mobject 移动到目标，或恢复到保存的状态。"
---

# 动画化一个改变

```python fold title="影片代码"
import manimgx as m


class AnimateHero(m.Scene):
    def construct(self) -> None:
        square = m.Square(color=m.BLUE, fill_opacity=0.5)
        self.play(m.Create(square))
        self.play(square.animate.shift(3 * m.RIGHT).set_color(m.YELLOW))
        self.play(square.animate(run_time=2).rotate(m.PI / 2).scale(0.5))
        self.play(square.animate.move_to(m.ORIGIN).set_color(m.BLUE))
```

`square.shift(m.RIGHT)` 一次性移动方块。`square.animate.shift(m.RIGHT)` 创建一个
移动它的动画：将其传给 `play`，方块便在动画的运行时间内移动。在 `.animate` 后链式调用多个方法，
它们会同时发生。将动画关键字传给 `.animate`，如 `square.animate(run_time=2)`，来控制时长。

`.animate` 从动画开始时的 mobject 状态过渡到方法调用结束后的状态：每个点沿直线移动，
除非你指定 `path_arc`。

::: manimgx.Mobject.animate
    options:
      heading_level: 2

::: manimgx.Animate
    options:
      heading_level: 2

## 到达预备状态

::: manimgx.MoveToTarget
    options:
      heading_level: 3

::: manimgx.Restore
    options:
      heading_level: 3