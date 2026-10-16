---
title: "数学"
description: "由 ManimGX 排版的 LaTeX 或 Typst 公式，以及公式的组成部分，用于着色、移动和匹配。"
---

# 数学

```python fold title="影片代码"
import manimgx as m


class MathHero(m.Scene):
    def construct(self) -> None:
        before = m.MathTex("a^2", "+", "b^2", "=", "c^2", font_size=96)
        after = m.MathTex("a^2", "=", "c^2", "-", "b^2", font_size=96)
        before[2].set_color(m.YELLOW)
        after[4].set_color(m.YELLOW)
        self.play(m.Write(before))
        self.play(m.TransformMatchingTex(before, after))
        self.wait()
```

[MathTex][manimgx.MathTex] 排版以 LaTeX 书写的公式：分数、根号、求和与积分、矩阵、
`cases`、希腊字母。请用原始字符串 `r"..."` 书写，以便 Python 保留其反斜杠。LaTeX 宏包和
`\def` 不起作用；ManimGX 不认识的命令会以其名称中止场景。

为 `MathTex` 提供多个字符串，每个字符串都是公式的一个组成部分，可单独着色、移动或制作
动画：`MathTex("a^2", "+", "b^2")[2]` 是 b²。在两个公式中以相同方式书写的部分，可通过
[TransformMatchingTex][manimgx.TransformMatchingTex] 相互变换。

[Tex][manimgx.Tex] 是包含公式的文本，公式位于 `$` 符号之间。如果你熟悉 Typst，可直接
书写：[Typst][manimgx.Typst] 接受 Typst 标记，[MathTypst][manimgx.MathTypst] 接受以
Typst 数学语法书写的公式。

::: manimgx.MathTex
    options:
      heading_level: 2

::: manimgx.MathTexPart
    options:
      heading_level: 2

::: manimgx.Tex
    options:
      heading_level: 2

::: manimgx.Typst
    options:
      heading_level: 2

::: manimgx.MathTypst
    options:
      heading_level: 2

## 排版文本的组成部分

每个文本和公式都由字形组成，正如 Typst 所排版的那样：每个字形知道自己绘制的是源文本中的
哪些字符。Typst 无法排版的源文本会以 Typst 的错误中止场景。

::: manimgx.mobjects.text.TypstGlyph
    options:
      heading_level: 3

::: manimgx.drawing.typesetting.TypstError
    options:
      heading_level: 3

::: manimgx.mobject.Pivot
