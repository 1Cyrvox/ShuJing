---
title: "组"
description: "由其他 mobject 组成的 mobject，以及添加、移除、排列和排序 mobject 组成部分的方法。"
---

# 组


<img src="../../films/GroupsHero.webp" alt="GroupsHero" />

```python fold title="影片代码"
import manimgx as m


class GroupsHero(m.Scene):
    def construct(self) -> None:
        shapes = m.VGroup(
            m.Circle(color=m.BLUE, fill_opacity=0.5),
            m.Square(color=m.GREEN, fill_opacity=0.5),
            m.Triangle(color=m.YELLOW, fill_opacity=0.5),
            m.Star(color=m.RED, fill_opacity=0.5),
        )
        shapes.arrange(buff=0.6)
        self.play(m.LaggedStart(*[m.Create(shape) for shape in shapes], lag_ratio=0.2))
        self.play(shapes.animate.arrange_in_grid(rows=2, buff=0.6))
        self.play(shapes.animate.arrange(m.DOWN, buff=0.3).scale(0.6))
        self.play(shapes.animate.set_color(m.TEAL))
        self.wait()
```

mobject 可以容纳其他 mobject，即其组成部分。组不容纳其他东西：它的组成部分就是
它所展示的内容。移动、缩放、着色或动画化一个组，每个组成部分都会随之变化。

`m.VGroup` 和 `m.Group` 是同一个类，有两个名称：Manim CE 的代码两种写法都有。
组是其组成部分的列表：`group[0]` 是第一个，`group[1:3]` 是第二个和第三个
组成的组，`len(group)` 计数，`for part in group:` 遍历它们。每个 mobject 的
组成部分都以相同方式工作：公式的项、图的坐标轴。

::: manimgx.Group
    options:
      heading_level: 2

::: manimgx.VGroup
    options:
      heading_level: 2

## 添加和移除组成部分

::: manimgx.Mobject.add_to_back
    options:
      heading_level: 3

::: manimgx.Mobject.insert
    options:
      heading_level: 3

::: manimgx.Mobject.remove
    options:
      heading_level: 3

::: manimgx.Mobject.get_family
    options:
      heading_level: 3

::: manimgx.Mobject.family_members_with_points
    options:
      heading_level: 3

## 排列组成部分

::: manimgx.Mobject.arrange
    options:
      heading_level: 3

::: manimgx.Mobject.arrange_in_grid
    options:
      heading_level: 3

## 排序组成部分

::: manimgx.Mobject.sort
    options:
      heading_level: 3

::: manimgx.Mobject.shuffle
    options:
      heading_level: 3

::: manimgx.Mobject.invert
    options:
      heading_level: 3

## 命名组成部分

::: manimgx.VDict
    options:
      heading_level: 3

::: manimgx.index_labels
    options:
      heading_level: 3