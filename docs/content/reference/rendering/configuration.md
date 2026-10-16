---
title: "配置"
description: "每个场景制作和渲染所用的配置：视频的尺寸和帧率、它的背景，以及帧以单位计的尺寸。"
---

# 配置

```python fold title="影片代码"
import manimgx as m

m.config.pixel_width, m.config.pixel_height = 1080, 1920


class ConfigurationHero(m.Scene):
    def construct(self) -> None:
        frame = m.Rectangle(
            width=m.config.frame_width - 0.2,
            height=m.config.frame_height - 0.2,
            color=m.BLUE,
        )
        square = m.Square(side_length=8, color=m.YELLOW).scale(0.97)
        label = m.Text("1080 × 1920", font_size=56)
        self.play(m.Create(frame), m.Create(square), m.Write(label))
        self.wait()
```

`m.config` 持有每个场景制作时所用的内容：视频以像素计的尺寸、它的帧率、它的背景，以及帧以单位计的尺寸。在 `import manimgx as m` 之后、场景制作之前设置它；命令行的选项也会设置它（`-r 1080x1920`、`--fps 30`）。

帧具有视频的形状，它的短边为 8 个单位：宽视频显示约 14.2 × 8 个单位，高视频显示 8 × 14.2，而中间的 8 × 8 正方形在两者中都存在。

::: manimgx.config.config
    options:
      heading_level: 2

::: manimgx.config.Config
    options:
      heading_level: 2
