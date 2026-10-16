# 文本和数学

ManimGX 自行排版文本和公式，使用 [Typst](https://typst.app) 及其附带的字体。你无需安装 LaTeX 或字体，并且你的文本在每台电脑上看起来都一样。

## 文本

`m.Text` 完全按你书写的方式显示文本。换行符（`\n`）会开始新的一行：

```python
import manimgx as m


class Words(m.Scene):
    def construct(self) -> None:
        title = m.Text("The Pythagorean theorem", font_size=64)
        note = m.Text("for a right triangle", font_size=36, color=m.GREY_B)
        note.next_to(title, m.DOWN)
        self.play(m.Write(title))
        self.play(m.FadeIn(note))
```

- `font_size` 设定大小：默认为 48，除非你另行指定。
- `font` 设定字体：`"sans-serif"`、`"monospace"`，或你电脑上的某个字体名称。默认为 New Computer Modern，即 LaTeX 的字体。
- `t2c` 为文本的某些部分着色：`m.Text("red and blue", t2c={"red": m.RED, "blue": m.BLUE})`。

文本和其他 mobject 一样：你可以移动它、缩放它、为它着色并为其制作动画。

## 公式

`m.MathTex` 显示用 LaTeX 数学语法编写的公式。请将其写在原始字符串 `r"..."` 中，以便 Python 保留其反斜杠：

```python
import manimgx as m


class Formula(m.Scene):
    def construct(self) -> None:
        formula = m.MathTex(r"\int_0^1 x^2 \, dx = \frac{1}{3}", font_size=72)
        self.play(m.Write(formula))
```

分数、根号、求和与积分、矩阵、`cases`、希腊字母、`\mathbb` 和 `\text` 都可用。LaTeX 宏包和 `\def` 不可用。如果 ManimGX 不认识某个命令，其错误信息会指出该命令的名称。

`m.Tex` 用于包含数学内容的文本：`m.Tex(r"The area is $\pi r^2$.")`。

## 公式的各部分

给 `m.MathTex` 多个字符串，每个字符串都会成为一个可以单独着色或制作动画的部分。`formula[2]` 是第三个部分：

```python
import manimgx as m


class Parts(m.Scene):
    def construct(self) -> None:
        formula = m.MathTex("a^2", "+", "b^2", "=", "c^2", font_size=96)
        formula[2].set_color(m.YELLOW)
        self.play(m.Write(formula))
        self.play(m.Indicate(formula[2]))
```

## 将一个公式变为另一个

`m.TransformMatchingTex` 将公式的每个部分移动到另一个公式中具有相同 LaTeX 的部分。不匹配的部分会淡出和淡入：

```python
import manimgx as m


class Rearrange(m.Scene):
    def construct(self) -> None:
        before = m.MathTex("a^2", "+", "b^2", "=", "c^2", font_size=96)
        after = m.MathTex("a^2", "=", "c^2", "-", "b^2", font_size=96)
        before[2].set_color(m.YELLOW)
        after[4].set_color(m.YELLOW)
        self.play(m.Write(before))
        self.play(m.TransformMatchingTex(before, after))
        self.wait()
```

## 数字

`m.DecimalNumber(3.14)` 显示一个数字。其 `set_value` 会在原位显示另一个数字，因此数字可以在场景播放时递增或递减：[更新器](updaters.md)展示了如何操作。

## Typst

如果你熟悉 [Typst](https://typst.app)，可以直接用它书写：`m.Typst` 接受 Typst 标记，`m.MathTypst` 接受 Typst 数学语法中的公式。

```py
m.Typst("*Bold*, _italic_, and math: $sum_(k=1)^n k = (n(n+1))/2$")
```

## 下一步

[图表](graphs.md)将展示如何绘制坐标轴和绘制函数，并带有标签。
