---
title: "强调"
description: "将视线吸引到 mobject 上：指示它、圈住它、闪烁一个点、摆动它、眨眼。"
---

# 强调

```python fold title="影片代码"
import manimgx as m


class EmphasisHero(m.Scene):
    def construct(self) -> None:
        formula = m.MathTex("a^2", "+", "b^2", "=", "c^2", font_size=96)
        self.add(formula)
        self.play(m.Indicate(formula[0]))
        self.play(m.Circumscribe(formula[2], color=m.YELLOW))
        self.play(m.Flash(formula[4], color=m.YELLOW, flash_radius=0.8))
        self.play(m.Wiggle(formula))
        self.wait()
```

这些动画短暂改变 mobject，然后将其恢复原状：它们在语音讲解时将观众的视线引向该 mobject。

::: manimgx.Indicate
    options:
      heading_level: 2

::: manimgx.Circumscribe
    options:
      heading_level: 2

::: manimgx.Flash
    options:
      heading_level: 2

::: manimgx.FocusOn
    options:
      heading_level: 2

::: manimgx.Wiggle
    options:
      heading_level: 2

::: manimgx.ShowPassingFlash
    options:
      heading_level: 2

::: manimgx.ShowPassingFlashWithThinningStrokeWidth
    options:
      heading_level: 2

::: manimgx.Blink
    options:
      heading_level: 2

::: manimgx.Broadcast
    options:
      heading_level: 2