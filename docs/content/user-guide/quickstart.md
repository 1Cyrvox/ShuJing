# 快速开始

有两种方式可以开始。选择其中一种。

## 使用 AI 智能体

将以下内容粘贴到 Claude Code 或 Codex 中：

``` { .text .mx-prompt }
Follow https://www.aipaikj.top/llms.txt to make me a short animation of a square turning into a circle, and open it.
```

就这样。智能体会安装 ManimGX，编写代码，制作视频并打开它。要获得不同的视频，请更改"make me"后面的文字。如果智能体请求使用网络或 GPU，请允许它。

## 手动操作

### 1. 安装 ManimGX

在 [Python](https://www.python.org/downloads/) 3.13 或更高版本中，在终端运行以下命令：

```sh
pip install manimgx
```

它会安装 ManimGX 及其命令 `manimgx`。

### 2. 设置你的编辑器

在你的编辑器中设置 [ty](https://docs.astral.sh/ty/)。ty 会在你输入时检查代码。它会补全 ManimGX 的名称，显示每个名称的作用，并在你制作视频之前为许多错误画下下划线。

=== "VS Code"

    安装 [ty 扩展](https://marketplace.visualstudio.com/items?itemName=astral-sh.ty)。Cursor、Windsurf 以及其他基于 VS Code 的编辑器也可以在它们的扩展视图中找到它。然后为你的视频创建一个文件夹，并用 **File > Open Folder** 打开它。

=== "Zed"

    Zed 内置了 ty。要启用它，请打开你的设置文件（Mac 上为 ++cmd+alt+comma++，Windows 和 Linux 上为 ++ctrl+alt+comma++），并在其第一个 `{` 之后紧接着粘贴以下行：

    ```json
      "languages": {
        "Python": {
          "language_servers": ["ty", "!basedpyright", "..."]
        }
      },
    ```

    然后为你的视频创建一个文件夹，并用 **File > Open** 打开它。

### 3. 编写场景

在你的文件夹中，创建一个名为 `scene.py` 的文件，并在其中写入以下代码：

```python title="scene.py"
import manimgx as m


class SquareToCircle(m.Scene):
    def construct(self) -> None:
        square = m.Square(side_length=3, color=m.BLUE, fill_opacity=0.5)
        circle = m.Circle(radius=1.6, color=m.PINK, fill_opacity=0.5)
        self.play(m.Create(square))
        self.play(m.Transform(square, circle))
        self.wait()
```

### 4. 预览

打开编辑器的终端（++ctrl+grave++），并运行：

```sh
manimgx preview scene.py
```

一个窗口会播放你的场景。把它放在编辑器旁边。每次保存 `scene.py` 时，窗口都会播放新版本。试一下：将 `m.PINK` 改为 `m.YELLOW`，然后保存。

### 5. 制作视频

```sh
manimgx render scene.py
```

ManimGX 会将视频 `SquareToCircle.mp4` 写入到 `scene.py` 旁边。它就是第 3 步代码上方的那个视频。要制作竖屏视频（Shorts、Reels、TikTok），请添加 `-r 1080x1920`。

你已经准备好了。接下来，[基础](the-basics.md)将解释场景如何制作视频。
