---
title: "动画"
description: "随时间改变 mobject 的内容：一次变化持续多久、它如何把握节奏，以及每一种动画。"
---

# 动画

```python fold title="影片代码"
import manimgx as m


class AnimationsHero(m.Scene):
    def construct(self) -> None:
        square = m.Square(color=m.BLUE, fill_opacity=0.5)
        circle = m.Circle(color=m.PINK, fill_opacity=0.5)
        self.play(m.Create(square))
        self.play(square.animate.shift(2 * m.LEFT).rotate(m.PI / 4))
        self.play(m.Transform(square, circle))
        self.play(m.Indicate(square))
        self.play(square.animate.set_color(m.YELLOW).shift(2 * m.RIGHT))
        self.wait()
```

动画随时间改变 mobject。[play][manimgx.Scene.play] 播放它：场景的时间在动画的
`run_time` 内运行（默认 1 秒，除非你指定其他值），每一帧显示该时刻的变化。其
`rate_func` 为其把握节奏：先慢、后快、再慢，除非你指定其他值。

方法所做的任何变化都可以动画化：在方法前加上 `.animate`，
即 `self.play(square.animate.shift(m.RIGHT))`。下面的动画实现方法无法做到的变化：
绘制一个图形、书写一段文本、将一个 mobject 变为另一个、闪烁某个点。多个动画可以在
一次 `play` 中同时播放，也可以在一个组中依次播放。

<div class="grid cards mx-cards" markdown>

-   ![](film:AnimateHero)

    [**为变化添加动画**](animate.md)

    ---

    `.animate`：任意方法调用，动画化。移动到目标，或回到已保存的状态。

-   ![](film:RateFunctionsHero)

    [**速率函数**](rate-functions.md)

    ---

    动画如何把握节奏：平滑地、匀速地、带弹跳或带摆动。

-   ![](film:AppearHero)

    [**出现与消失**](appear-and-disappear.md)

    ---

    绘制、书写、淡入和生长 mobject，并将它们再次移出。

-   ![](film:TransformsHero)

    [**变换**](transforms.md)

    ---

    将一个 mobject 变为另一个，匹配两个公式的各部分，交换位置。

-   ![](film:MoveAndDeformHero)

    [**移动与变形**](move-and-deform.md)

    ---

    绕某点旋转、沿路径移动，或让每个点经过某个函数。

-   ![](film:EmphasisHero)

    [**强调**](emphasis.md)

    ---

    吸引视线：指示、圈住、闪烁、摆动。

-   ![](film:TogetherHero)

    [**同时与依次**](together-and-in-turn.md)

    ---

    同时播放动画、依次播放，或每个在前一个之后稍后播放。

</div>

## 动画

每个动画都接受动画关键字：运行多久、如何把握节奏，以及其各部分如何依次开始。

::: manimgx.animation.timeline.AnimationOptions
    options:
      heading_level: 3
      inherited_members: true
      members: [run_time, rate_func, lag_ratio, reverse_rate_function, remover, introducer, suspend_mobject_updating, use_override, name]

::: manimgx.Animation
    options:
      heading_level: 3
