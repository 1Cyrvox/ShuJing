# 更新器

有时一个 mobject 必须在其他移动时遵循某条规则：标签保持在点上方，或数字显示点所在位置。更新器是保持此类规则的函数。ManimGX 在每一帧调用它。

## 跟随另一个 mobject

```python
import manimgx as m


class Follow(m.Scene):
    def construct(self) -> None:
        dot = m.Dot(color=m.YELLOW)
        label = m.Text("dot", font_size=32)

        def stay_above(mobject: m.Mobject) -> None:
            mobject.next_to(dot, m.UP)

        label.add_updater(stay_above)
        self.add(dot, label)
        self.play(dot.animate.shift(4 * m.RIGHT))
        self.play(dot.animate.shift(3 * m.DOWN))
```

`label.add_updater(stay_above)` 让 ManimGX 在每一帧调用 `stay_above(label)`。因此无论点到哪里，标签都保持在它上方。`label.clear_updaters()` 停止此行为。

## 可制作动画的数字

[`ValueTracker`][manimgx.ValueTracker] 持有一个数字。它不显示任何东西，但你可以为它的数字制作动画，更新器也可以读取它。因此一个动画可以移动多个 mobject：

```python
import manimgx as m


class Counter(m.Scene):
    def construct(self) -> None:
        x = m.ValueTracker(0)
        number = m.DecimalNumber(0, font_size=96)

        def show_x(mobject: m.DecimalNumber) -> None:
            mobject.set_value(x.get_value())

        number.add_updater(show_x)
        self.add(number)
        self.play(x.animate.set_value(10), run_time=3)
```

`x.animate.set_value(10)` 在 3 秒内将数字从 0 变为 10。
`x.get_value()` 读取它。

## 每帧重新创建 mobject

`m.always_redraw` 接受一个创建 mobject 的函数，并在每一帧重新创建它。此处，当跟踪器移动时，一个点沿着图像移动：

```python
import manimgx as m


def curve(x: float) -> float:
    return x**2 / 4


class Ride(m.Scene):
    def construct(self) -> None:
        axes = m.Axes(x_range=[0, 5, 1], y_range=[0, 7, 1], x_length=8, y_length=5)
        graph = axes.plot(curve, color=m.BLUE)
        x = m.ValueTracker(1)

        def make_dot() -> m.Dot:
            point = axes.c2p(x.get_value(), curve(x.get_value()))
            return m.Dot(point, color=m.YELLOW)

        dot = m.always_redraw(make_dot)
        self.add(axes, graph, dot)
        self.play(x.animate.set_value(4.5), run_time=3)
```

## 持续运动

更新器也可以接受 `dt`：自上次运行以来的时间，以秒为单位。用它制作随时间持续的运动，在播放和等待中均有效：

```python
import manimgx as m


class Spin(m.Scene):
    def construct(self) -> None:
        square = m.Square(color=m.BLUE, fill_opacity=0.5)

        def turn(mobject: m.Mobject, dt: float) -> None:
            mobject.rotate(dt * m.PI)

        square.add_updater(turn)
        self.add(square)
        self.wait(2)
```

`dt * m.PI` 每秒将正方形转动半圈。接受 `dt` 的更新器也可以模拟物理：[画廊](../gallery/index.md)有示例，如[陀螺](../gallery/heavy-top.md)。

## 下一步

[相机与3D](camera-and-3d.md)介绍如何移动相机，以及如何制作三维场景。