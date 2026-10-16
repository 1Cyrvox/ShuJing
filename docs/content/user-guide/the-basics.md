# 基础

使用 ManimGX，你编写一段简短的 Python 程序，ManimGX 就会为其制作视频。本页将展示如何操作。

## 程序制作视频

这是一个 ManimGX 程序：

```python title="hello.py" show="code"
import manimgx as m


class Hello(m.Scene):
    def construct(self) -> None:
        circle = m.Circle()
        self.play(m.Create(circle))
        self.wait()
```

将其保存到名为 `hello.py` 的文件中。然后，在终端中，在同一文件夹下，运行以下命令：

```sh
manimgx render hello.py
```

ManimGX 会在文件旁边制作这个视频 `Hello.mp4`：

```python show="film"
import manimgx as m


class Hello(m.Scene):
    def construct(self) -> None:
        circle = m.Circle()
        self.play(m.Create(circle))
        self.wait()
```

这就是你使用 ManimGX 的方式：你编写一个程序，ManimGX 为其制作视频。

## 程序逐行解析

`import manimgx as m`
:   以简短的名称 `m` 为你提供 ManimGX 的全部内容：`m.Scene`、`m.Circle`、`m.Create`。

`class Hello(m.Scene):`
:   创建一个**场景**。一个场景就是一段视频。它的名称就是视频的名称：场景 `Hello` 制作 `Hello.mp4`。

`def construct(self) -> None:`
:   说明视频中发生的事情。ManimGX 从上到下运行 `construct`，每一行都按该顺序添加到视频中。

`circle = m.Circle()`
:   创建一个圆。圆是一个 **mobject**：任何你可以在视频中展示的东西都是 mobject。形状、线条、文本、公式和图表都是 mobject。但创建一个 mobject 并不会展示它：在这一行，视频仍然是空的。

`self.play(m.Create(circle))`
:   播放一个**动画**：`m.Create(circle)` 在一秒内画出圆。之后，圆就出现在视频中，并一直留在那里。

`self.wait()`
:   让画面静止一秒。所以视频总长为两秒。

## 一步一步来

每个 `self.play` 在前一个结束时开始。时间只在 `play` 和 `wait` 中流逝：

```python
import manimgx as m


class Steps(m.Scene):
    def construct(self) -> None:
        circle = m.Circle()
        words = m.Text("Hello!")
        self.play(m.Create(circle))  # 从 0 到 1 秒
        self.play(m.FadeOut(circle))  # 从 1 到 2 秒
        self.play(m.Write(words))  # 从 2 到 3 秒
        self.wait(2)  # 从 3 到 5 秒
```

这些动画用于显示和隐藏 mobject。你最常用的是：

- `m.Create(...)` 画出一个形状。
- `m.Write(...)` 写出一段文本或一个公式。
- `m.FadeIn(...)` 淡入一个 mobject。`m.FadeOut(...)` 将其淡出，并将其移除。

`self.wait(2)` 等待 2 秒。不带数字时，它等待 1 秒。

## 立即显示 mobject

要无动画地显示一个 mobject，请添加它：`self.add(circle)`。圆从那一刻起就出现在视频中。`self.remove(circle)` 会立即将其移除。

## 一个文件中的多个场景

一个文件可以包含多个场景，每个场景都是一段视频。要制作其中之一，请在文件名之后给出其名称：

```sh
manimgx render hello.py Steps
```

## 下一步

到目前为止，每个 mobject 都出现在视频的中间。[位置](positions.md)将展示如何将每个 mobject 放到你想要的位置。
