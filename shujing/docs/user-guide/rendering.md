# 渲染与分享

`manimgx` 命令制作场景的视频。它还在窗口中播放场景、检查问题，并将其作为幻灯片展示：

| 命令 | 作用 |
| --- | --- |
| `manimgx render scene.py` | 制作视频，一个 MP4 文件。 |
| `manimgx preview scene.py` | 在窗口中播放场景，每次保存时重新播放。 |
| `manimgx inspect scene.py` | 编写分镜、列出时间线，并检查 2D 布局。 |
| `manimgx present scene.py` | 制作视频，并在浏览器中作为幻灯片展示。 |

每个命令将其文件写到场景文件旁边。如果文件包含多个场景，在文件后给出场景名称：`manimgx render scene.py Intro`。[命令行参考](../reference/rendering/command-line.md)展示了所有选项。

## 渲染

```console
$ manimgx render square_to_circle.py
SquareToCircle.mp4  3.00 s, 1920x1080 at 60 fps, 0.4 MB (rendered in 0.7 s)
storyboard: SquareToCircle.storyboard.png
layout: no problems in 3 samples
```

视频以场景命名。它是 1920 × 1080 像素，每秒 60 帧，包含场景的声音。`-o` 给它不同的名称。要快速草拟，可缩小尺寸：`-r 1280x720 --fps 30`。

`render` 还会编写分镜，包含每个改变画面的播放结束时的画面，以及语音的字幕（`.srt`）。

### 设置

在导入之后于 `m.config` 上设置视频的参数：以像素为单位的尺寸
`pixel_width` 和 `pixel_height`；`frame_rate`；以及 `background_color`：

```python
import manimgx as m

m.config.background_color = m.WHITE


class OnWhite(m.Scene):
    def construct(self) -> None:
        circle = m.Circle(radius=2, color=m.BLUE, fill_opacity=0.5)
        label = m.Text("On white", color=m.BLACK)
        label.next_to(circle, m.DOWN)
        self.play(m.Create(circle), m.Write(label))
```

在命令行中，`-r` 和 `--fps` 会覆盖文件中的尺寸和帧率。

### 竖屏视频

对于 Shorts、Reels 和 TikTok，将视频设为竖屏：1080 × 1920。在命令中给出尺寸：

```sh
manimgx render scene.py -r 1080x1920
```

或者，要让该文件的每个视频都为竖屏，在 `import manimgx as m` 之后加上这行：

```py
m.config.pixel_width, m.config.pixel_height = 1080, 1920
```

竖屏画框宽 8 个单位、高约 14.2 个单位：即宽屏画框旋转而成。两者中间都有相同的 8 × 8 正方形，所以保持在该正方形中的场景在两者中相同。[位置](positions.md#the-frame)展示了两个画框。正方形视频
`-r 1080x1080` 就是那个正方形本身。

### 从 Python 调用

场景可以制作自己的视频：`SquareToCircle().render("square_to_circle.mp4")`
返回其 [`Film`][manimgx.Film] 并写入视频。不带路径时，它快速运行场景但不绘制，例如在测试中。

## 预览

`manimgx preview scene.py` 在窗口中播放场景。每次保存文件时，窗口从同一时刻播放新版本。如果新版本有错误，窗口会显示错误。

窗口的按键与视频播放器相同：空格播放和暂停，← 和 → 前后跳 5 秒，? 显示所有按键。其时间线显示场景的每次播放，以代码行命名，或如果场景有章节则显示每个章节。

## 检查

`manimgx inspect scene.py` 编写分镜并列出每次播放的时间与代码行。它运行场景但不编码视频，只绘制它检查的画面：默认为每次播放或等待的结束处。在 2D 场景中它检查：

- 被画框裁掉的 mobject；
- 互相覆盖的文字、穿过文字的线条或覆盖文字的填充；
- 过小而无法阅读的文字。

```console
$ manimgx inspect crowded.py
crowded.py: Crowded, 3.00 s, 2 plays
storyboard: Crowded.storyboard.png
  #0   0.00– 2.00s  crowded.py:8  Write(Text 'A title much too long for t…')
  #1   2.00– 3.00s  crowded.py:9  FadeIn(Text 'a note')
layout: 2 problems
  [1] t=2–3s (crowded.py:8)  title (Text 'A title much too long for the…'): 1.35 past the left edge, 1.35 past the right edge
  [2] t=3s (crowded.py:9)  title (Text 'A title much too long for the…') and note (Text 'a note'): texts overlap
```

每个问题以你代码中的名称命名 mobject，如 `title`。分镜用红色勾勒并为每个问题编号。布局问题返回退出码 1；提示（如图表延伸到屏幕外）则不会。3D 场景会得到画面和时间线，布局检查标记为跳过。

要检查特定时刻，包括动画过程中：

```sh
manimgx inspect scene.py -t 1.5,8,end
```

每个时间选择视频播放器在该时刻显示的帧；`end` 选择最后一帧。相同的布局检查适用于这些画面。重复 `-t` 或用逗号分隔时间。不带
`end` 时，场景在包含最后一个请求帧的播放之后停止，这使检查在长视频中保持聚焦。

画面按时间顺序写入 `<Scene>.storyboard.png`，每页六张，然后是
`<Scene>.storyboard-2.png`，依此类推。用 `-o detail.png` 选择名称。默认检查会省略连续相同的画面；显式时间保留每个请求的画面。检查覆盖采样时刻，而非视频的每一帧。

## 演示

视频可以是一场演讲：它播放到幻灯片结尾，然后等待你继续。
`self.next_section()` 开始新的幻灯片：

```python
import manimgx as m
import numpy as np


def two_sines(x: float) -> float:
    return np.sin(x) + np.sin(3 * x) / 3


class Talk(m.Scene):
    def construct(self) -> None:
        title = m.Text("Fourier series", font_size=72)
        self.play(m.Write(title))
        self.next_section("a sine", notes="Start with one sine.")
        self.play(title.animate.to_edge(m.UP))
        wave = m.FunctionGraph(np.sin, x_range=[-6, 6], color=m.BLUE)
        self.play(m.Create(wave))
        self.next_section("a sum")
        total = m.FunctionGraph(two_sines, x_range=[-6, 6], color=m.YELLOW)
        self.play(m.Transform(wave, total))
```

`manimgx present talk.py` 制作视频，在其旁边编写网页，并在浏览器中打开该页面。→ 或点击转到下一张幻灯片，← 返回，F 全屏，Shift+P 打开演讲者视图，显示你的备注、下一张幻灯片和计时器。要分享演讲，将页面和视频一起发送。`--pdf` 还会编写讲义，每张幻灯片一页。

## 嵌入网页

ManimGX 可在网页中运行，无需服务器：页面从你的场景制作视频并播放它。安装 npm 包 `manimgx`，通过你的打包器在页面脚本中导入它，并将场景放入 `<manimgx-player>`：

```html
<script type="module">
  import "manimgx";
</script>

<manimgx-player autoplay>
  <script type="text/python">
    import manimgx as m

    class Euler(m.Scene):
      def construct(self):
          circle = m.Circle(color=m.BLUE, fill_opacity=0.5)
          formula = m.MathTex(r"e^{i\pi} + 1 = 0").next_to(circle, m.DOWN)
          self.play(m.Create(circle), m.Write(formula))
  </script>
</manimgx-player>
```

播放器拥有预览窗口的按键。页面上的第一个视频会下载
Python（[Pyodide](https://pyodide.org)）和 ManimGX，约 26 MB；浏览器会保留它们供后续使用。它需要 WebGPU：Chrome 和 Edge 113 或更高版本，或 Safari 26。浏览器中尚不支持两件事：由其他形状组合而成的形状（如 `Union`），以及中文、日文和韩文文字。