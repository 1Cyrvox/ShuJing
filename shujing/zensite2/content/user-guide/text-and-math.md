# 文本与数学

ManimGX 自行排版文字和公式，使用 [Typst](https://typst.app) 和随附的字体。你不需要安装 LaTeX 或字体，且你的文字在每台电脑上看起来都一样。

## 文字

`m.Text` 完全按你书写的方式显示文字。换行符（`\n`）开始新行：


<video src="../films/Words.mp4" autoplay loop muted playsinline controls></video>

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

- `font_size` 设定大小：默认为 48。
- `font` 设定字体：`"sans-serif"`、`"monospace"`，或你电脑上的字体名称。默认为 New Computer Modern，即 LaTeX 的字体。
- `t2c` 为文字的各部分着色：`m.Text("red and blue", t2c={"red": m.RED, "blue": m.BLUE})`。

文字和其他 mobject 一样：你可以移动、缩放、着色并为它制作动画。

## 公式

`m.MathTex` 显示用 LaTeX 数学书写的公式。用原始字符串 `r"..."` 书写，以便 Python 保留其反斜杠：


<video src="../films/Formula.mp4" autoplay loop muted playsinline controls></video>

```python
import manimgx as m


class Formula(m.Scene):
    def construct(self) -> None:
        formula = m.MathTex(r"\int_0^1 x^2 \, dx = \frac{1}{3}", font_size=72)
        self.play(m.Write(formula))
```

分数、根号、求和与积分、矩阵、`cases`、希腊字母、`\mathbb` 和
`\text` 都可用。LaTeX 宏包和 `\def` 不可用。如果 ManimGX 不认识某个命令，其错误会指出该命令。

`m.Tex` 用于包含数学的文字：`m.Tex(r"The area is $\pi r^2$.")`。

## 公式的各部分

给 `m.MathTex` 多个字符串，每个都成为一个可单独着色或制作动画的部分。`formula[2]` 是第三部分：


<video src="../films/Parts.mp4" autoplay loop muted playsinline controls></video>

```python
import manimgx as m


class Parts(m.Scene):
    def construct(self) -> None:
        formula = m.MathTex("a^2", "+", "b^2", "=", "c^2", font_size=96)
        formula[2].set_color(m.YELLOW)
        self.play(m.Write(formula))
        self.play(m.Indicate(formula[2]))
```

## 将一个公式变成另一个

`m.TransformMatchingTex` 将公式的每个部分移到另一个公式中 LaTeX 相同的部分。不匹配的部分淡出和淡入：


<video src="../films/Rearrange.mp4" autoplay loop muted playsinline controls></video>

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

`m.DecimalNumber(3.14)` 显示一个数字。其 `set_value` 在原位显示不同的数字，因此数字可在场景播放时递增或递减：[更新器](updaters.md)介绍如何操作。

## Typst

如果你了解 [Typst](https://typst.app)，可直接用它书写：`m.Typst` 接受 Typst 标记，`m.MathTypst` 接受 Typst 数学语法的公式。

```py
m.Typst("*Bold*, _italic_, and math: $sum_(k=1)^n k = (n(n+1))/2$")
```

## 下一步

[图表](graphs.md)介绍如何绘制坐标轴和函数图像，以及添加标签。