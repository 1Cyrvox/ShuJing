---
title: "强调"
description: "将视线引向某个 mobject：指示它、圈住它、闪烁某个点、摆动它、眨眼它。"
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

这些动画短暂地改变某个 mobject，然后将其恢复原状：当语音讲解它时，它们将观众的视线
引向它。

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
