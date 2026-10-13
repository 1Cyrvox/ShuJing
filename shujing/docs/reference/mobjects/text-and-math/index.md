---
title: "文字和数学"
description: "文字、公式、数字和代码，由 ManimGX 内部的 Typst 排版，使用自带字体。"
---

# 文字和数学

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

ManimGX 自行排版文字和公式，使用 [Typst](https://typst.app) 和
自带字体：你无需安装 LaTeX 和字体，文字在每台
电脑上看起来都一样。文字是由其字形组成的 mobject，因此可以像任何
形状一样移动、缩放、着色和动画化。

用 [Text][manimgx.Text] 书写文字，用
[MathTex][manimgx.MathTex] 书写 LaTeX 公式，用 [Tex][manimgx.Tex] 书写含公式的文字，用
[Typst][manimgx.Typst] 书写 Typst 标记。可变的数字是
[DecimalNumber][manimgx.DecimalNumber]。

<div class="grid cards mx-cards" markdown>

-   ![](film:TextHero)

    [**文字**](text.md)

    ---

    字体中的文字、段落、标题、项目符号列表和代码。

-   ![](film:MathHero)

    [**数学**](math.md)

    ---

    LaTeX 或 Typst 中的公式，及其组成部分，可着色、移动和匹配。

-   ![](film:NumbersHero)

    [**数字**](numbers.md)

    ---

    以固定位数小数书写的数字，可在场景播放时变化。

</div>