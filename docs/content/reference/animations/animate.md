---
title: "为变化添加动画"
description: "在方法前加上 `.animate`，play 便会对该方法所产生的变化添加动画；或将 mobject 移动到目标，或回到已保存的状态。"
---

# 为变化添加动画

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

`square.shift(m.RIGHT)` 一次性移动正方形。`square.animate.shift(m.RIGHT)` 创建一个
移动它的动画：将其传给 `play`，正方形便在动画的运行时间内移动。在 `.animate` 后链式
调用多个方法，它们会同时发生。将动画关键字传给 `.animate`，即
`square.animate(run_time=2)`，来为其计时。

`.animate` 从动画开始时 mobject 的当前状态变化到调用结束后 mobject 的状态：每个点沿
直线行进，除非你给定一个 `path_arc`。

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
