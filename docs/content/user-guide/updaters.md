# 更新器

有时一个 mobject 必须在其他对象移动时遵循某条规则：一个标签始终位于一个点上方，或一个数字显示某个点所在的位置。更新器就是维持这类规则的函数。ManimGX 会在每一帧调用它。

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

`label.add_updater(stay_above)` 会让 ManimGX 在每一帧调用 `stay_above(label)`。因此无论点移动到哪里，标签都始终位于点上方。`label.clear_updaters()` 会停止这一行为。

## 你可以动画化的数字

[`ValueTracker`][manimgx.ValueTracker] 持有一个数字。它本身不显示任何东西，但你可以对其数字进行动画，更新器也可以读取它。因此一个动画可以带动多个 mobject：

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

`x.animate.set_value(10)` 在 3 秒内将数字从 0 变为 10。`x.get_value()` 读取该数字。

## 在每一帧重新生成 mobject

`m.always_redraw` 接受一个生成 mobject 的函数，并在每一帧重新生成它。这里，当跟踪器移动时，一个点会沿图像滑动：

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

## 持续进行的运动

更新器还可以接收 `dt`：自上次运行以来经过的时间，以秒为单位。可以用它实现随时间持续进行的运动，在 play 和 wait 中都有效：

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

`dt * m.PI` 让正方形每秒转半圈。接收 `dt` 的更新器还可以模拟物理：[画廊](../gallery/index.md) 中有相关示例，例如 [旋转陀螺](../gallery/heavy-top.md)。

## 下一步

[相机与 3D](camera-and-3d.md) 展示了如何移动相机，以及如何在三维空间中制作场景。
