# 快速开始

有两种方式开始。任选其一。

## 使用 AI 智能体

将以下内容粘贴到 Claude Code 或 Codex 中：

``` { .text .mx-prompt }
Follow https://www.aipaikj.top/llms.txt to make me a short animation of a square turning into a circle, and open it.
```

就这样。智能体会安装 ManimGX、编写代码、制作视频并打开它。要得到不同的视频，修改"make me"后面的文字即可。如果智能体请求使用网络或 GPU，请允许它。

## 手动操作

### 1. 安装 ManimGX

使用 [Python](https://www.python.org/downloads/) 3.13 或更高版本，在终端中运行：

```sh
pip install manimgx
```

它会安装 ManimGX 及其命令 `manimgx`。

### 2. 设置你的编辑器

在编辑器中设置 [ty](https://docs.astral.sh/ty/)。ty 会在你输入时检查代码。它会补全 ManimGX 的名称、显示每个名称的作用，并在你制作视频之前就为你标出许多错误。

=== "VS Code"

    安装 [ty 扩展](https://marketplace.visualstudio.com/items?itemName=astral-sh.ty)。
    Cursor、Windsurf 以及其他基于 VS Code 的编辑器在其扩展视图中也能找到它。然后为你的视频创建一个文件夹，用 **File > Open Folder** 打开它。

=== "Zed"

    Zed 内置了 ty。要启用它，打开设置文件（Mac 上按 ++cmd+alt+comma++，
    Windows 和 Linux 上按 ++ctrl+alt+comma++），并在其第一个
    `{` 之后粘贴以下内容：

    ```json
      "languages": {
        "Python": {
          "language_servers": ["ty", "!basedpyright", "..."]
        }
      },
    ```

    然后为你的视频创建一个文件夹，用 **File > Open** 打开它。

### 3. 编写场景

在你的文件夹中创建一个名为 `scene.py` 的文件，并在其中写入以下代码：


<video src="../films/SquareToCircle.mp4" autoplay loop muted playsinline controls></video>

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

打开编辑器的终端（++ctrl+grave++），运行：

```sh
manimgx preview scene.py
```

一个窗口会播放你的场景。把它放在编辑器旁边。每次保存
`scene.py` 时，窗口都会播放新版本。试试看：把 `m.PINK` 改成 `m.YELLOW`，然后保存。

### 5. 制作视频

```sh
manimgx render scene.py
```

ManimGX 会将视频 `SquareToCircle.mp4` 写到 `scene.py` 旁边。这就是第 3 步代码上方的视频。要制作竖屏视频（Shorts、Reels、TikTok），加上 `-r 1080x1920`。

你已经准备好了。接下来，[基础](the-basics.md)会解释场景如何制作视频。