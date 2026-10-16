# 渲染与分享

`manimgx` 命令用于生成场景的视频。它还能在窗口中播放场景、检查问题，并将其以幻灯片形式呈现：

| 命令 | 功能 |
| --- | --- |
| `manimgx render scene.py` | 生成视频，一个 MP4 文件。 |
| `manimgx preview scene.py` | 在窗口中播放场景，并在你每次保存时重新播放。 |
| `manimgx inspect scene.py` | 生成故事板、列出时间线，并检查 2D 布局。 |
| `manimgx present scene.py` | 生成视频，并在浏览器中以幻灯片形式展示。 |

每条命令都会把其输出文件写在场景文件旁边。如果文件中包含多个场景，可在文件后给出场景名称：`manimgx render scene.py Intro`。[命令行参考](../reference/rendering/command-line.md) 列出了所有选项。

## 渲染

```console
$ manimgx render square_to_circle.py
SquareToCircle.mp4  3.00 s, 1920x1080 at 60 fps, 0.4 MB (rendered in 0.7 s)
storyboard: SquareToCircle.storyboard.png
layout: no problems in 3 samples
```

视频以场景命名。它的分辨率为 1920 × 1080 像素，每秒 60 帧，并带有场景的声音。`-o` 可为其指定不同名称。若要快速生成草稿，可缩小尺寸：`-r 1280x720 --fps 30`。

`render` 还会生成一份故事板，包含每次改变画面的 play 结束时的画面，以及语音的字幕（`.srt`）。

### 设置

在 `import` 之后通过 `m.config` 设置视频参数：以像素为单位的尺寸 `pixel_width` 和 `pixel_height`；帧率 `frame_rate`；以及背景色 `background_color`：

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

在命令行中，`-r` 和 `--fps` 会覆盖文件中的尺寸和帧率设置。

### 竖屏视频

针对 Shorts、Reels 和 TikTok，可制作竖屏视频：1080 × 1920。将尺寸传给命令：

```sh
manimgx render scene.py -r 1080x1920
```

或者，要让该文件中的每个视频都为竖屏，可在 `import manimgx as m` 之后加入这一行：

```py
m.config.pixel_width, m.config.pixel_height = 1080, 1920
```

竖屏取景框宽 8 个单位、高约 14.2 个单位：即横屏取景框旋转后的版本。两者中间都有相同的 8 × 8 单位正方形，因此停留在该正方形内的场景在两种取景框中表现一致。[位置](positions.md#_2) 展示了这两种取景框。正方形视频 `-r 1080x1080` 则仅包含该正方形。

### 从 Python 中渲染

场景可以自行生成视频：`SquareToCircle().render("square_to_circle.mp4")` 会返回其 [`Film`][manimgx.Film] 并写入视频。若不指定路径，它会快速运行场景而不绘制画面，例如用于测试。

## 预览

`manimgx preview scene.py` 在窗口中播放场景。每次保存文件时，窗口会从同一时刻起播放新版本。如果新版本有错误，窗口会显示该错误。

窗口的按键与视频播放器相同：空格键播放和暂停，← 和 → 前后跳转 5 秒，? 显示所有按键。其时间线显示场景的每一次 play，按其代码行命名；若场景有分段，则按每一段显示。

## 检查

`manimgx inspect scene.py` 会生成故事板，并列出每次 play 的时间与代码行。它在运行场景时不编码视频，只绘制需要检查的画面：默认是每次 play 或 wait 的结束时刻。在 2D 场景中，它会检查：

- 被取景框裁掉的 mobject；
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

每个问题都按你代码中的命名方式给出 mobject 名称，例如 `title`。故事板会用红色勾勒并编号每个问题。布局问题会返回退出码 1；而提示（例如图像延伸到屏幕外）则不会。3D 场景会得到画面和时间线，布局检查标记为已跳过。

要检查特定时刻，包括动画进行中的时刻：

```sh
manimgx inspect scene.py -t 1.5,8,end
```

每个时刻选取视频播放器在该时刻显示的帧；`end` 选取最后一帧。相同的布局检查会应用于这些画面。可重复 `-t` 或用逗号分隔多个时刻。若不使用 `end`，场景会在包含最后一个所请求帧的 play 之后停止，这样即使在长视频中也能让检查保持聚焦。

画面按时间顺序写入 `<Scene>.storyboard.png`，每页六张，然后是 `<Scene>.storyboard-2.png`，依此类推。可用 `-o detail.png` 指定名称。默认检查会省略连续相同的画面；显式指定时刻则保留每一个所请求的画面。检查覆盖的是被采样的时刻，而非视频的每一帧。

## 演示

视频可以是一场演讲：它播放到某张幻灯片末尾，然后等待你继续。`self.next_section()` 开始一张新幻灯片：

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

`manimgx present talk.py` 会生成视频、在其旁边写出一个网页，并在浏览器中打开该页面。→ 或单击进入下一张幻灯片，← 返回上一张，F 全屏显示，Shift+P 打开演讲者视图，其中包含你的备注、下一张幻灯片和一个计时器。要分享演讲，请把网页和视频一起发送。`--pdf` 还会输出一份讲义，每张幻灯片对应一页。

## 嵌入网页

ManimGX 可以在网页中运行，无需服务器：页面直接根据你的场景生成并播放视频。安装 npm 包 `manimgx`，通过你的打包工具将其引入页面脚本，并把场景放入一个 `<manimgx-player>` 中：

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

播放器具有与预览窗口相同的按键。页面上的第一个视频会下载 Python（[Pyodide](https://pyodide.org)）和 ManimGX，约 26 MB；浏览器会将其保留以备后用。它需要 WebGPU：Chrome 和 Edge 113 及以上版本，或 Safari 26。目前有两件事在浏览器中尚不可用：由其他形状构造的形状（例如 `Union`），以及中文、日文和韩文文字。
