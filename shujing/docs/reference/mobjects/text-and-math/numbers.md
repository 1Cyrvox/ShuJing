---
title: "数字"
description: "以固定位数小数书写的数字、整数，以及跟随追踪器的命名值。"
---

# 数字

```python fold title="影片代码"
import manimgx as m


class NumbersHero(m.Scene):
    def construct(self) -> None:
        number = m.DecimalNumber(0, num_decimal_places=2, font_size=96, color=m.YELLOW)
        variable = m.Variable(0, m.MathTex("x"), num_decimal_places=2).scale(1.5)
        tracker = variable.tracker
        m.VGroup(number, variable).arrange(m.DOWN, buff=1)

        def follow(mobject: m.DecimalNumber) -> None:
            mobject.set_value(tracker.get_value())

        number.add_updater(follow)
        self.add(number, variable)
        self.play(tracker.animate.set_value(3.14), run_time=2)
        self.wait()
```

数字是知道其值的文字。[set_value][manimgx.DecimalNumber.set_value] 在
原位显示另一个值，外观不变，因此数字可以在场景播放时计数：
通过在每帧设置它的[更新器](../../updaters/index.md)，或通过
[ChangeDecimalToValue][manimgx.ChangeDecimalToValue]。

::: manimgx.DecimalNumber
    options:
      heading_level: 2

::: manimgx.Integer
    options:
      heading_level: 2

::: manimgx.Variable
    options:
      heading_level: 2

## 计数到某个值

::: manimgx.ChangeDecimalToValue
    options:
      heading_level: 3

::: manimgx.ChangingDecimal
    options:
      heading_level: 3