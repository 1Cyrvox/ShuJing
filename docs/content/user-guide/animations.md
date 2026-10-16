# 动画

动画随时间改变 mobject。[基础](the-basics.md)展示了用于显示和隐藏 mobject 的动画。本页展示如何为任何变化制作动画、如何设定动画的时间，以及如何同时播放多个动画。

## 为任何变化制作动画

在方法前加上 `.animate`，`self.play` 就会将该方法所产生的变化制作成动画：

```python
import manimgx as m


class Changes(m.Scene):
    def construct(self) -> None:
        square = m.Square()
        self.play(m.Create(square))
        self.play(square.animate.shift(3 * m.RIGHT))
        self.play(square.animate.rotate(45 * m.DEGREES))
        self.play(square.animate.set_fill(m.BLUE, opacity=1))
        self.play(square.animate.scale(0.5).move_to(m.ORIGIN))
```

不加 `.animate` 时，`square.shift(3 * m.RIGHT)` 会立即移动正方形，没有动画。加上 `.animate` 时，正方形会在一秒内移动到那里。你可以在 `.animate` 之后链式连接多个变化，如最后一行所示，它们会同时发生。

## 将一个 mobject 变为另一个

`m.ReplacementTransform` 将一个 mobject 变为另一个：

```python
import manimgx as m


class SquareIntoCircle(m.Scene):
    def construct(self) -> None:
        square = m.Square(color=m.BLUE, fill_opacity=0.5)
        circle = m.Circle(color=m.PINK, fill_opacity=0.5)
        self.play(m.Create(square))
        self.play(m.ReplacementTransform(square, circle))
        self.play(circle.animate.shift(2 * m.UP))
```

之后，`circle` 在视频中，而 `square` 不在。`m.Transform(square, circle)` 看起来一样，但它将 `square` 变为圆的形状并将其保留在视频中：之后，你移动的是 `square`，而不是 `circle`。

## 设定动画时间

大多数动画耗时一秒。要选择时长，请给出 `run_time`，单位为秒：

```py
self.play(m.Create(circle), run_time=3)
```

其 `rate_func` 设定它在每一刻的速度。默认的 `m.smooth` 开始时缓慢，然后加速，最后再缓慢结束。`m.linear` 保持匀速。在下方选择一个来查看它的运动方式：

<div class="mx-rates" data-rates="smooth linear rush_into rush_from there_and_back double_smooth running_start lingering ease_in_out_sine ease_in_back ease_out_elastic ease_out_bounce"></div>

```py
self.play(square.animate.shift(3 * m.RIGHT), rate_func=m.linear)
```

[速率函数][manimgx.animation.easing]参考文档列出了所有这些函数。

## 同时播放动画

给 `self.play` 多个动画，它们会同时播放。播放时长与最长的动画相同：

```python
import manimgx as m


class Together(m.Scene):
    def construct(self) -> None:
        circle = m.Circle()
        words = m.Text("A circle")
        words.next_to(circle, m.DOWN)
        self.play(m.Create(circle), m.Write(words))
        self.play(circle.animate.set_fill(m.RED, opacity=1), m.FadeOut(words))
```

## 依次播放动画

`m.LaggedStart` 在前一个动画之后稍晚一点启动每个动画。其 `lag_ratio` 设定何时启动：0.5 表示在前一个动画完成一半时启动下一个。

```python
import manimgx as m


class InTurn(m.Scene):
    def construct(self) -> None:
        circle = m.Circle()
        square = m.Square()
        triangle = m.Triangle()
        shapes = m.VGroup(circle, square, triangle)
        shapes.arrange(m.RIGHT, buff=1)
        self.play(
            m.LaggedStart(
                m.Create(circle), m.Create(square), m.Create(triangle), lag_ratio=0.5
            )
        )
```

`m.Succession` 在一次播放中依次播放其动画。当各步骤是更大播放的一部分时使用它：例如，在书写标题的同时分三步移动一个形状。

[参考文档](../reference/animations/index.md)展示了每种动画。

## 下一步

[文本和数学](text-and-math.md)将展示如何书写文字和公式，以及如何为它们制作动画。
