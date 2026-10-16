---
title: "文本与数学"
description: "由 Typst 在 ManimGX 中排版的文字、公式、数字与代码，使用其内置字体。"
---

# 文本与数学

```python fold title="影片代码"
import manimgx as m


class TextAndMathHero(m.Scene):
    def construct(self) -> None:
        title = m.Text("The Pythagorean theorem", font_size=56)
        formula = m.MathTex("a^2", "+", "b^2", "=", "c^2", font_size=80)
        formula[2].set_color(m.YELLOW)
        number = m.DecimalNumber(
            3.14159, num_decimal_places=4, font_size=56, color=m.BLUE
        )
        lines = m.VGroup(title, formula, number).arrange(m.DOWN, buff=0.7)
        self.play(m.Write(title))
        self.play(m.Write(formula))
        self.play(m.FadeIn(number))
        self.wait()
```

ManimGX 自行排版文本与公式，使用 [Typst](https://typst.app) 及其内置字体：你无需安装
LaTeX 和字体，且文本在每台计算机上看起来都一样。文本是由其字形组成的 mobject，因此它可以
像任何图形一样移动、缩放、着色和制作动画。

用 [Text][manimgx.Text] 书写文字，用 [MathTex][manimgx.MathTex] 书写 LaTeX 公式，用
[Tex][manimgx.Tex] 书写含公式的文字，用 [Typst][manimgx.Typst] 书写 Typst 标记。会变化的
数字是 [DecimalNumber][manimgx.DecimalNumber]。

<div class="grid cards mx-cards" markdown>

-   ![](film:TextHero)

    [**Text**](text.md)

    ---

    字体中的文字、段落、标题、项目符号列表和代码。

-   ![](film:MathHero)

    [**Math**](math.md)

    ---

    LaTeX 或 Typst 中的公式，及其组成部分，用于着色、移动和匹配。

-   ![](film:NumbersHero)

    [**Numbers**](numbers.md)

    ---

    以设定小数位数书写的数字，可在场景播放时变化。

</div>
