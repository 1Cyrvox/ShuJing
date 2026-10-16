---
title: "副本与状态"
description: "复制一个 mobject，保存其状态以便返回，准备一个状态以便移入，或使其看起来像另一个。"
---

# 副本与状态

```python fold title="影片代码"
import manimgx as m


class CopiesAndStatesHero(m.Scene):
    def construct(self) -> None:
        square = m.Square(color=m.BLUE, fill_opacity=0.6)
        self.play(m.Create(square))
        square.save_state()
        copy = square.copy().set_color(m.YELLOW)
        self.play(copy.animate.shift(3 * m.RIGHT))
        target = square.generate_target()
        target.shift(3 * m.LEFT).rotate(m.PI / 4).set_color(m.RED)
        self.play(m.MoveToTarget(square))
        self.play(m.Restore(square))
        self.wait()
```

一个 mobject 是场景中的一个对象：命名它的变量即命名该对象，对它的更改会显示在它
所在的任何位置。要拥有两个，就复制它。要更改一个 mobject 再回到原样，先保存其
状态。要将一个更改动画化为一个你逐步准备的状态，就生成它的目标。

::: manimgx.Mobject.copy
    options:
      heading_level: 2

## 保存状态

::: manimgx.Mobject.save_state
    options:
      heading_level: 3

::: manimgx.Mobject.restore
    options:
      heading_level: 3

## 准备状态

::: manimgx.Mobject.generate_target
    options:
      heading_level: 3

::: manimgx.Mobject.target
    options:
      heading_level: 3

## 变为另一个的样子

::: manimgx.Mobject.become
    options:
      heading_level: 3

::: manimgx.Mobject.match_points
    options:
      heading_level: 3
