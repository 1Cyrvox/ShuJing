<p align="center">
  <a href="/">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="showcase/logo-dark.svg">
      <source media="(prefers-color-scheme: light)" srcset="showcase/logo-light.svg">
      <img alt="数境" src="showcase/logo-light.svg" width="640">
    </picture>
  </a>
</p>

<p align="center">
  <b>面向 AI 助手的极速 3D 动画引擎，兼容 <a href="https://www.manim.community">Manim Community Edition 的 API</a>。</b><br>
  由 Rust 和 wgpu 驱动。用提示词或 pip 安装。可在浏览器中运行。
</p>

<p align="center">
  <b><a href="/">文档</a></b> ·
  <a href="/user-guide/quickstart/">快速开始</a> ·
  <a href="/gallery/">示例</a> ·
  <a href="/reference/">API 参考</a>
</p>

<p align="center">
  <a href="https://pypi.org/project/manimgx/"><img alt="PyPI 版本" src="https://img.shields.io/pypi/v/manimgx?color=58c4dd&label=PyPI"></a>
  <a href="https://www.npmjs.com/package/manimgx"><img alt="npm 版本" src="https://img.shields.io/npm/v/manimgx?color=58c4dd"></a>
  <a href="https://pepy.tech/projects/manimgx"><img alt="PyPI 总下载量" src="https://img.shields.io/pepy/dt/manimgx?color=58c4dd&label=PyPI%20downloads"></a>
  <a href="https://www.npmjs.com/package/manimgx"><img alt="npm 月下载量" src="https://img.shields.io/npm/dm/manimgx?color=58c4dd&label=npm%20downloads"></a>
</p>

<p align="center">
  <a href="https://github.com/1Cyrvox/ShuJing/blob/main/examples/quadratic_formula.py"><img alt="二次公式：移动彩色矩形和方程项完成配方" src="showcase/quadratic_formula.gif" width="32%"></a>
  <a href="https://github.com/1Cyrvox/ShuJing/blob/main/examples/fourier_pi.py"><img alt="傅里叶级数：旋转箭头链画出 π 的轮廓" src="showcase/fourier_pi.gif" width="32%"></a>
  <a href="https://github.com/1Cyrvox/ShuJing/blob/main/examples/linear_maps.py"><img alt="矩阵变换平面：网格、基向量和单位正方形一起变换" src="showcase/linear_maps.gif" width="32%"></a>
  <br>
  <a href="https://github.com/1Cyrvox/ShuJing/blob/main/examples/derivative.py"><img alt="切线沿曲线滑动，斜率描绘出导数" src="showcase/derivative.gif" width="32%"></a>
  <a href="https://github.com/1Cyrvox/ShuJing/blob/main/examples/complex_maps.py"><img alt="复函数将网格弯折成抛物线、圆和射线" src="showcase/complex_maps.gif" width="32%"></a>
  <a href="https://github.com/1Cyrvox/ShuJing/blob/main/examples/lorenz_attractor.py"><img alt="洛伦兹吸引子：邻近轨迹在三维空间中分离成蝴蝶形" src="showcase/lorenz_attractor.gif" width="32%"></a>
  <br>
  <a href="https://github.com/1Cyrvox/ShuJing/blob/main/examples/heavy_top.py"><img alt="三个陀螺进动和章动，轴在球面上描绘曲线" src="showcase/heavy_top.gif" width="32%"></a>
  <a href="https://github.com/1Cyrvox/ShuJing/blob/main/examples/hopf_fibration.py"><img alt="霍普夫纤维化：彩色相连圆环形成嵌套环面，珠子沿其穿行" src="showcase/hopf_fibration.gif" width="32%"></a>
  <a href="https://github.com/1Cyrvox/ShuJing/blob/main/examples/catenoid_helicoid.py"><img alt="彩虹螺旋面弯曲成悬链面，保持内蕴曲率" src="showcase/catenoid_helicoid.gif" width="32%"></a>
</p>

**36.2 秒的视频，仅需 3.08 秒渲染。** 在 Apple M4 Pro 上以 1080p60 渲染五个场景，数境（ManimGX）比 **ManimCE 快 90.6 倍**，比 **ManimGL 快 11.5 倍**，比 **Blender Workbench 快 18.7 倍**，从启动到输出 MP4。[如何测量](https://github.com/1Cyrvox/ShuJing/tree/main/benchmarks)：场景、设置和每次运行。

<figure class="mx-benchmark">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="images/benchmark-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="images/benchmark-light.svg">
    <img alt="总渲染时间：ManimGX 3.08 秒，ManimGL 35.28 秒，Blender Workbench 57.61 秒，ManimCE 278.83 秒，Blender EEVEE 601.40 秒" src="images/benchmark-light.svg" width="100%">
  </picture>
  <p align="center"><sub>所有引擎使用最快编码预设。越低越好。</sub></p>
</figure>

**同一场景对比。** 2.5 秒处的相连圆环，由各引擎渲染：

| 数境 / ManimGX | ManimCE | ManimGL | Blender Workbench | Blender EEVEE |
| :---: | :---: | :---: | :---: | :---: |
| ![ManimGX 渲染的八个相连圆环](images/benchmark-quality/manimgx-light.png) | ![ManimCE 渲染的八个相连圆环](images/benchmark-quality/manim_ce-light.png) | ![ManimGL 渲染的八个相连圆环](images/benchmark-quality/manimgl-light.png) | ![Blender Workbench 渲染的八个相连圆环](images/benchmark-quality/blender_workbench-light.png) | ![Blender EEVEE 渲染的八个相连圆环](images/benchmark-quality/blender_eevee-light.png) |

## 快速开始

**用提示词。** 粘贴到 Claude Code、Codex 或 Cursor 中。你的 AI 助手会处理安装：

```text
Follow https://www.aipaikj.top/llms.txt.
Install ManimGX, make a 3D animation of the solar system, and open it.
```

**用 pip。** 在 macOS、Linux 或 Windows 上安装（需要 Python 3.13+）：

```sh
pip install manimgx
```

字体、排版和视频编码已全部内置。
编辑器配置和引导式首次动画请见
[快速开始](/user-guide/quickstart/)。

## 从 Python 到 MP4

将以下代码保存为 `scene.py`：

```python
import manimgx as m


class Hello3D(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(phi=65 * m.DEGREES, theta=-45 * m.DEGREES)
        self.begin_ambient_camera_rotation(rate=0.5)
        cube = m.Cube(side_length=3, fill_opacity=0.3, stroke_width=2)
        self.play(m.Create(cube), run_time=2)
        self.wait(4)
```

渲染：

```sh
manimgx render scene.py
```

即可得到 `Hello3D.mp4`，一段 1080p60 的视频：

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="films/readme-Hello3D.svg">
    <source media="(prefers-color-scheme: light)" srcset="films/readme-Hello3D-light.svg">
    <img alt="蓝色立方体被绘制，相机绕其旋转" src="films/readme-Hello3D-light.svg#readme" width="100%">
  </picture>
</p>

## 为什么选择数境？

**面向 AI 助手时代的 3D 视频 API。** 你的 AI 助手使用
[Manim Community Edition 的 API](https://www.manim.community)
编写 Python。数境的 Rust + wgpu 引擎渲染 MP4，极速完成。

- **完全静态类型。** 关键字参数和 `.animate` 链全部有类型标注。
- **2D 与 3D 统一。** 曲面、网格和移动相机，与文本、方程
  和图表并存。
- **浏览器中运行。** `npm install manimgx`。[Pyodide](https://pyodide.org) 运行
  Python（在 Web Worker 中）；WebGPU 渲染场景。
  [嵌入场景](/user-guide/rendering/#embed-in-a-web-page)，无需渲染服务器。
- **AI 助手反馈。** [`manimgx inspect`](/user-guide/rendering/#inspect)：故事板和 2D 布局检查，在播放结束或你选定的时间点。
- **文本与数学。** 编写 LaTeX 或 Typst。无需安装 LaTeX。
- **语音同步。** 用 `self.say()` [将动画与语音对齐](/user-guide/sound-and-voice/)。

## 文档

**[www.aipaikj.top](/)** 提供指南、带源码的渲染示例
和 API 参考：

- [快速开始](/user-guide/quickstart/)：安装、配置编辑器、
  渲染你的第一个场景。
- [用户指南](/user-guide/the-basics/)：逐步学习场景、
  动画、3D、文本和声音，每次一个概念。
- [示例](/gallery/)：观看完整的影片并阅读
  生成它们的 Python 代码。
- [API 参考](/reference/)：查询类、方法
  及其类型化参数。
- [从 Manim CE 迁移](/user-guide/coming-from-manim-ce/)：
  适配现有场景，检查行为差异。

对于 AI 助手，[llms.txt](/llms.txt) 提供安装说明
和文档的 Markdown 链接。

## 站在巨人的肩膀上

[Grant Sanderson](https://www.3blue1brown.com) 创建了
[Manim](https://github.com/3b1b/manim)。数境基于
[ManimGX](https://github.com/academa-labs/manimgx)，它兼容
[Manim Community Edition](https://www.manim.community) 的 API——广泛使用的
社区维护分支。

Rust 渲染器使用 [wgpu](https://wgpu.rs) 进行原生 GPU 渲染和浏览器中的
WebGPU 渲染。其 3D 光照改编自 Google 的
[Filament](https://github.com/google/filament)：基于物理的材质、
基于图像的光照、环境光遮蔽、泛光和 AgX 色调映射。
[Typst](https://typst.app) 排版文本和数学公式，
[mitex](https://github.com/mitex-rs/mitex) 将 LaTeX 输入转换为 Typst。
[x264](https://www.videolan.org/developers/x264.html) 将原生视频导出编码为
H.264；[FFmpeg](https://ffmpeg.org) 解码导入的音频，使用
[libopus](https://opus-codec.org) 处理 Opus。

[Pyodide](https://pyodide.org) 在浏览器 Worker 中运行 Python 场景。Linux wheel
捆绑 [Mesa](https://mesa3d.org) 的 lavapipe，在没有
合适 GPU 时使用 Vulkan 在 CPU 上渲染。

## 社区

数境是由 [爱派未来科技](https://www.aipaikj.top) 维护的开源项目，是基于 [ManimGX](https://github.com/academa-labs/manimgx)（由 [Abdullah Geduk](https://geduk.io) 和 [Sina Atalay](https://sinaatalay.com) 创建）开发的中文适配衍生发行版。我们欢迎社区的贡献。

问题、Bug 报告和功能请求从
[issue](https://github.com/1Cyrvox/ShuJing/issues/new/choose) 开始。
要贡献代码，请阅读[贡献指南](https://github.com/1Cyrvox/ShuJing/blob/main/.github/CONTRIBUTING.md)
和[开发指南](/developer-guide/)。

[更新日志](/changelog/) ·
[引用数境](https://github.com/1Cyrvox/ShuJing/blob/main/CITATION.cff)

所有参与者遵守
[行为准则](https://github.com/1Cyrvox/ShuJing/blob/main/.github/CODE_OF_CONDUCT.md)。
通过[安全策略](https://github.com/1Cyrvox/ShuJing/blob/main/.github/SECURITY.md)私下报告漏洞。

## 许可证

数境自身代码继承上游 [MIT 许可证](https://github.com/1Cyrvox/ShuJing/blob/main/LICENSE)。
原生 wheel 包含 x264，整体为 GPL-3.0-or-later。

捆绑组件保留其各自许可证：参见
[第三方声明](https://github.com/1Cyrvox/ShuJing/blob/main/LICENSE-THIRD-PARTY)、
[Linux 渲染器声明](https://github.com/1Cyrvox/ShuJing/blob/main/LICENSE-LAVAPIPE)、
以及 [Noto](https://github.com/1Cyrvox/ShuJing/blob/main/fonts/manimgx-fonts/LICENSE)
和 [Noto CJK](https://github.com/1Cyrvox/ShuJing/blob/main/fonts/manimgx-fonts-cjk/LICENSE) 字体许可证。

本软件使用了 [FFmpeg](https://ffmpeg.org) 的代码，基于
[LGPL-2.1-or-later](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html) 许可证。
完整源码（包括 FFmpeg）在每个
[GitHub 发布](https://github.com/1Cyrvox/ShuJing/releases)的 `manimgx-X.Y.Z-source.tar.xz` 中。