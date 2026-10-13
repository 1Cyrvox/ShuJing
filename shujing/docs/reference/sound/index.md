---
title: "声音"
description: "来自文件或时间函数的声音，经变换后放入视频：伴随动画、在任意时刻或贯穿整个视频。"
---

# 声音

```python fold title="影片代码"
import manimgx as m
import numpy as np


class SoundHero(m.Scene):
    def construct(self) -> None:
        def tone(t: np.ndarray) -> np.ndarray:
            return 0.3 * np.sin(2 * np.pi * 440 * t) * np.exp(-3 * t)

        dots = m.VGroup(
            *[m.Dot(radius=0.25, color=m.YELLOW) for _ in range(4)]
        ).arrange(buff=1)
        for dot in dots:
            self.play(
                m.FadeIn(dot, scale=2), m.Sound.of(tone, duration=0.5), run_time=0.5
            )
        self.wait()
```

声音从文件读取（WAV、MP3、AAC、FLAC 等常见格式），或由
时间函数生成。ManimGX 将每个声音放置在视频中的时刻，并将它们混合为
一条音轨。

将声音与动画一起传给 `play`，它会与动画同时开始。要在任意时刻
开始一个声音，添加它：场景继续进行，声音同时播放。声音播放
到结束，或直到你停止添加它时返回的剪辑。

声音的方法创建变换后的声音：更安静或更响、淡入或淡出、裁剪、循环、
加速、声像偏移，或在语音下压低。

::: manimgx.Sound
    options:
      heading_level: 2

::: manimgx.Scene.add_sound
    options:
      heading_level: 2

::: manimgx.audio.sound.Clip
    options:
      heading_level: 2