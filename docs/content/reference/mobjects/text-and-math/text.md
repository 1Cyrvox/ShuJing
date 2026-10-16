---
title: "文本"
description: "字体中的文字、段落、标题、项目符号列表和代码清单。"
---

# 文本

```python fold title="影片代码"
import manimgx as m


class TextHero(m.Scene):
    def construct(self) -> None:
        title = m.Text("Text", font_size=72)
        styles = m.VGroup(
            m.Text("bold", weight=m.BOLD, font_size=40),
            m.Text("italic", slant=m.ITALIC, font_size=40),
            m.Text("monospace", font="monospace", font_size=40),
            m.Text("red and blue", t2c={"red": m.RED, "blue": m.BLUE}, font_size=40),
        ).arrange(buff=0.6)
        items = m.BulletedList("one idea", "at a time", font_size=40)
        page = m.VGroup(title, styles, items).arrange(m.DOWN, buff=0.7)
        self.play(m.Write(title))
        self.play(m.LaggedStart(*[m.FadeIn(style) for style in styles], lag_ratio=0.2))
        self.play(m.Write(items))
        self.wait()
```

[Text][manimgx.Text] 按你给出的原样在字体中书写文字：换行符（`\n`）开始新的一行。其大小
为 `font_size`，默认为 48，除非你指定其他值。其组成部分是它的字符，因此 `text[0]` 是第一个
字符；`t2c` 按文字为其部分着色。

标题、项目符号列表和段落为你排列文本行，代码清单则高亮显示程序的源代码。

::: manimgx.Text
    options:
      heading_level: 2

::: manimgx.Paragraph
    options:
      heading_level: 2

::: manimgx.Title
    options:
      heading_level: 2

::: manimgx.BulletedList
    options:
      heading_level: 2

::: manimgx.Code
    options:
      heading_level: 2

::: manimgx.mobjects.code.CodeText
    options:
      heading_level: 3

## 字重与倾斜

文本的 `weight` 是其笔画粗细程度，`slant` 是其倾斜程度。

<div class="mx-constants" markdown>

::: manimgx.NORMAL
    options:
      heading_level: 3

::: manimgx.ITALIC
    options:
      heading_level: 3

::: manimgx.OBLIQUE
    options:
      heading_level: 3

::: manimgx.THIN
    options:
      heading_level: 3

::: manimgx.ULTRALIGHT
    options:
      heading_level: 3

::: manimgx.LIGHT
    options:
      heading_level: 3

::: manimgx.SEMILIGHT
    options:
      heading_level: 3

::: manimgx.BOOK
    options:
      heading_level: 3

::: manimgx.MEDIUM
    options:
      heading_level: 3

::: manimgx.SEMIBOLD
    options:
      heading_level: 3

::: manimgx.BOLD
    options:
      heading_level: 3

::: manimgx.ULTRABOLD
    options:
      heading_level: 3

::: manimgx.HEAVY
    options:
      heading_level: 3

::: manimgx.ULTRAHEAVY
    options:
      heading_level: 3

</div>

::: manimgx.mobjects.text.TypstOptions
