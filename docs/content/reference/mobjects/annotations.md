---
title: "标注"
description: "指向、框选、标注和度量其他 mobject 的元素：花括号、标签、边框、下划线、叉号和角标记。"
---

# 标注

```python fold title="影片代码"
import manimgx as m


class AnnotationsHero(m.Scene):
    def construct(self) -> None:
        formula = m.MathTex(r"a^2 + b^2 = c^2", font_size=72).shift(1.5 * m.UP)
        brace = m.Brace(formula[0][:5], m.DOWN, color=m.YELLOW)
        note = brace.get_text("the legs")
        frame = m.SurroundingRectangle(formula[0][6:], color=m.BLUE)
        a, b, c = [-1.5, -3, 0], [1.5, -3, 0], [1.5, -0.8, 0]
        triangle = m.Polygon(a, b, c, color=m.WHITE)
        right = m.RightAngle(m.Line(b, a), m.Line(b, c), length=0.35, color=m.GREEN)
        angle = m.Angle(m.Line(a, b), m.Line(a, c), radius=0.8, color=m.RED)
        self.play(m.Write(formula))
        self.play(m.GrowFromCenter(brace), m.FadeIn(note), m.Create(frame))
        self.play(m.Create(triangle), m.Create(right), m.Create(angle))
        self.wait()
```

标注指向另一个 mobject，为其加框、贴标签或度量它。大多数标注在创建时接收该
mobject 并与之贴合：与其边等长的花括号、环绕其周围的边框、其下方的线条。此后
它们不会跟随该 mobject；若要使其跟随，需用 [always_redraw][manimgx.always_redraw]
在每一帧重新绘制。

## 花括号

::: manimgx.Brace
    options:
      heading_level: 3

::: manimgx.BraceBetweenPoints
    options:
      heading_level: 3

::: manimgx.ArcBrace
    options:
      heading_level: 3

::: manimgx.BraceLabel
    options:
      heading_level: 3

::: manimgx.BraceText
    options:
      heading_level: 3

## 边框与标记

::: manimgx.SurroundingRectangle
    options:
      heading_level: 3

::: manimgx.BackgroundRectangle
    options:
      heading_level: 3

::: manimgx.mobjects.annotations.FrameOptions
    options:
      heading_level: 3

::: manimgx.Underline
    options:
      heading_level: 3

::: manimgx.Cross
    options:
      heading_level: 3

::: manimgx.AnnotationDot
    options:
      heading_level: 3

## 标签

::: manimgx.Label
    options:
      heading_level: 3

::: manimgx.LabeledDot
    options:
      heading_level: 3

::: manimgx.LabeledLine
    options:
      heading_level: 3

::: manimgx.LabeledArrow
    options:
      heading_level: 3

::: manimgx.LabeledPolygram
    options:
      heading_level: 3

## 角

::: manimgx.Angle
    options:
      heading_level: 3

::: manimgx.RightAngle
    options:
      heading_level: 3

::: manimgx.Elbow
    options:
      heading_level: 3

::: manimgx.mobject.Placement
::: manimgx.mobjects.text.TypstOptions
::: manimgx.mobjects.shapes.AngleOptions
::: manimgx.mobjects.shapes.AngleShape
