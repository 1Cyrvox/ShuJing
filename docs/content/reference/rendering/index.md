---
title: "渲染"
description: "制作视频：命令行、场景制作所用的配置，以及从 Python 渲染。"
---

# 渲染

```python fold title="影片代码"
import manimgx as m


class RenderingHero(m.Scene):
    def construct(self) -> None:
        commands = m.Code(
            code_string="manimgx render scene.py\nmanimgx preview scene.py\nmanimgx inspect scene.py\nmanimgx present scene.py",
            language="bash",
            background="window",
        ).scale(1.2)
        self.play(m.FadeIn(commands))
        self.wait()
```

`manimgx` 命令生成场景的视频，一个 MP4 文件，位于场景文件旁边。它还在你编辑时于窗口中播放场景，检查观众会看到的问题，绘制静帧，并将其作为幻灯片呈现。配置设置视频的尺寸、帧率和背景。从 Python 中，场景渲染为一个影片，程序可以保留它、在窗口中播放它，或写入它。

<div class="grid cards mx-cards" markdown>

-   ![](film:RenderingHero)

    [**命令行**](command-line.md)

    ---

    `manimgx render`、`preview`、`inspect` 和 `present`，以及它们的选项。

-   ![](film:ConfigurationHero)

    [**配置**](configuration.md)

    ---

    视频的尺寸和帧率、它的背景，以及帧以单位计的尺寸。

-   ![](film:FromPythonHero)

    [**从 Python**](from-python.md)

    ---

    从程序中渲染场景：它的影片、它的帧、它的声音和它的字幕。

</div>
