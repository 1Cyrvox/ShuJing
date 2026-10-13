---
title: "副本与状态"
description: "复制 mobject、保存其状态以便返回、准备一个要移动到的状态，或使其看起来像另一个。"
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

mobject 是场景中的一个对象：命名它的变量就命名了那个对象，对它的
修改会在其出现的所有地方生效。要拥有两个，就复制它。要修改一个 mobject
再回到原样，先保存其状态。要将变化动画化为你逐步准备好的状态，
就创建其目标。

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

## 变为另一个

::: manimgx.Mobject.become
    options:
      heading_level: 3

::: manimgx.Mobject.match_points
    options:
      heading_level: 3