# 动画

动画随时间改变 mobject。[基础](the-basics.md)介绍了用于显示和隐藏 mobject 的动画。本页介绍如何为任意改变制作动画、如何控制动画时间，以及如何同时播放多个动画。

## 为任意改变制作动画

在方法前加上 `.animate`，`self.play` 就会为该方法产生的改变制作动画：


<video src="../films/Changes.mp4" autoplay loop muted playsinline controls></video>

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

不加 `.animate` 时，`square.shift(3 * m.RIGHT)` 会瞬间移动正方形，没有动画。加上 `.animate` 后，正方形在一秒内移动到那里。你可以在 `.animate` 后链式调用多个改变，如最后一行所示，它们会同时发生。

## 将一个 mobject 变成另一个

`m.ReplacementTransform` 将一个 mobject 变成另一个：


<video src="../films/SquareIntoCircle.mp4" autoplay loop muted playsinline controls></video>

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

之后，`circle` 在视频中，而 `square` 不在。`m.Transform(square, circle)`
看起来一样，但它将 `square` 变成圆的形状并保留在视频中：之后你移动的是 `square`，而不是 `circle`。

## 控制动画时间

大多数动画持续一秒。要选择时长，给出 `run_time`，以秒为单位：

```py
self.play(m.Create(circle), run_time=3)
```

它的 `rate_func` 设定每个时刻的速度。默认的 `m.smooth` 开始慢、加速、结束慢。`m.linear` 保持匀速。在下方选择一个来看看它的运动方式：

<div class="mx-rates" data-rates="smooth linear rush_into rush_from there_and_back double_smooth running_start lingering ease_in_out_sine ease_in_back ease_out_elastic ease_out_bounce"></div>

```py
self.play(square.animate.shift(3 * m.RIGHT), rate_func=m.linear)
```

[速率函数][manimgx.animation.easing]参考列出了全部选项。

## 同时播放动画

给 `self.play` 多个动画，它们会同时播放。播放时长等于最长动画的时长：


<video src="../films/Together.mp4" autoplay loop muted playsinline controls></video>

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

`m.LaggedStart` 在前一个动画之后稍迟启动每个动画。它的
`lag_ratio` 设定时机：0.5 表示在前一个动画进行到一半时启动下一个。


<video src="../films/InTurn.mp4" autoplay loop muted playsinline controls></video>

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

`m.Succession` 在一次播放中依次播放其动画。当这些步骤是更大播放的一部分时使用它：例如，在书写标题的同时分三步移动一个形状。

[参考](../reference/animations/index.md)展示了每个动画。

## 下一步

[文本与数学](text-and-math.md)介绍如何书写文字和公式，以及如何为它们制作动画。