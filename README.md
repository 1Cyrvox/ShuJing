<p align="center">
  <a href="https://www.aipaikj.top">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/1Cyrvox/ShuJing/main/docs/content/showcase/logo-dark.svg">
      <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/1Cyrvox/ShuJing/main/docs/content/showcase/logo-light.svg">
      <img alt="ManimGX" src="https://raw.githubusercontent.com/1Cyrvox/ShuJing/main/docs/content/showcase/logo-light.svg" width="640">
    </picture>
  </a>
</p>

<p align="center">
  <b>面向智能体的极速 3D 动画引擎，兼容 <a href="https://www.manim.community">Manim CE 的 API</a>。</b><br>
  由 Rust 和 wgpu 驱动。用提示词或 pip 安装。可在浏览器中运行。
</p>

<p align="center">
  <b><a href="https://www.aipaikj.top">文档</a></b> ·
  <a href="https://www.aipaikj.top/user-guide/quickstart/">快速入门</a> ·
  <a href="https://www.aipaikj.top/gallery/">示例</a> ·
  <a href="https://www.aipaikj.top/reference/">API 参考</a>
</p>

<p align="center">
  <a href="https://coverage.www.aipaikj.top"><img alt="测试覆盖率" src="https://img.shields.io/endpoint?url=https%3A%2F%2Fcoverage.www.aipaikj.top%2Fbadge.json&label=coverage"></a>
  <a href="https://pypi.org/project/manimgx/"><img alt="PyPI 版本" src="https://img.shields.io/pypi/v/manimgx?color=58c4dd&label=PyPI"></a>
  <a href="https://www.npmjs.com/package/manimgx"><img alt="npm 版本" src="https://img.shields.io/npm/v/manimgx?color=58c4dd"></a>
  <a href="https://pepy.tech/projects/manimgx"><img alt="PyPI 总下载量" src="https://img.shields.io/pepy/dt/manimgx?color=58c4dd&label=PyPI%20downloads"></a>
  <a href="https://www.npmjs.com/package/manimgx"><img alt="npm 月下载量" src="https://img.shields.io/npm/dm/manimgx?color=58c4dd&label=npm%20downloads"></a>
  <a href="https://github.com/1Cyrvox/ShuJing/blob/main/LICENSE"><img alt="MIT 许可证" src="https://img.shields.io/github/license/1Cyrvox/ShuJing?color=blue&label=license"></a>
  <a href="https://github.com/1Cyrvox/ShuJing"><img alt="GitHub stars" src="https://img.shields.io/github/stars/1Cyrvox/ShuJing?color=58c4dd"></a>
</p>

<p align="center">
  <a href="https://github.com/1Cyrvox/ShuJing/blob/main/examples/quadratic_formula.py"><img alt="求根公式：通过移动彩色矩形和方程项来完成配方" src="https://raw.githubusercontent.com/1Cyrvox/ShuJing/main/docs/content/showcase/quadratic_formula.gif" width="32%"></a>
  <a href="https://github.com/1Cyrvox/ShuJing/blob/main/examples/fourier_pi.py"><img alt="傅里叶级数：一串旋转的箭头勾勒出 π 的轮廓" src="https://raw.githubusercontent.com/1Cyrvox/ShuJing/main/docs/content/showcase/fourier_pi.gif" width="32%"></a>
  <a href="https://github.com/1Cyrvox/ShuJing/blob/main/examples/linear_maps.py"><img alt="矩阵移动平面：网格、基向量箭头和单位正方形一同变换" src="https://raw.githubusercontent.com/1Cyrvox/ShuJing/main/docs/content/showcase/linear_maps.gif" width="32%"></a>
  <br>
  <a href="https://github.com/1Cyrvox/ShuJing/blob/main/examples/derivative.py"><img alt="切线沿曲线滑动，其斜率描绘出导数" src="https://raw.githubusercontent.com/1Cyrvox/ShuJing/main/docs/content/showcase/derivative.gif" width="32%"></a>
  <a href="https://github.com/1Cyrvox/ShuJing/blob/main/examples/complex_maps.py"><img alt="复函数将网格弯折成抛物线、圆和射线" src="https://raw.githubusercontent.com/1Cyrvox/ShuJing/main/docs/content/showcase/complex_maps.gif" width="32%"></a>
  <a href="https://github.com/1Cyrvox/ShuJing/blob/main/examples/lorenz_attractor.py"><img alt="洛伦兹吸引子：相邻轨迹在三维中分离，勾勒出蝴蝶形状" src="https://raw.githubusercontent.com/1Cyrvox/ShuJing/main/docs/content/showcase/lorenz_attractor.gif" width="32%"></a>
  <br>
  <a href="https://github.com/1Cyrvox/ShuJing/blob/main/examples/heavy_top.py"><img alt="三个旋转陀螺进动和章动，其轴线在玻璃球面上描绘出曲线" src="https://raw.githubusercontent.com/1Cyrvox/ShuJing/main/docs/content/showcase/heavy_top.gif" width="32%"></a>
  <a href="https://github.com/1Cyrvox/ShuJing/blob/main/examples/hopf_fibration.py"><img alt="霍普夫纤维化：彩色相连的圆构成嵌套的环面，珠子沿其穿行" src="https://raw.githubusercontent.com/1Cyrvox/ShuJing/main/docs/content/showcase/hopf_fibration.gif" width="32%"></a>
  <a href="https://github.com/1Cyrvox/ShuJing/blob/main/examples/catenoid_helicoid.py"><img alt="彩虹螺旋面弯折成悬链面，同时保持其内蕴曲率" src="https://raw.githubusercontent.com/1Cyrvox/ShuJing/main/docs/content/showcase/catenoid_helicoid.gif" width="32%"></a>
</p>

**36.2 秒的视频，在 3.08 秒内渲染完成。** 在 Apple M4 Pro 上以 1080p60 渲染五个场景，ManimGX 比 ManimCE 快 **90.6 倍**，比 ManimGL 快 **11.5 倍**，比 Blender Workbench 快 **18.7 倍**，从启动到生成 MP4。[测量方法](https://github.com/1Cyrvox/ShuJing/tree/main/benchmarks)：场景、设置和每次运行。

<figure class="mx-benchmark">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://www.aipaikj.top/images/benchmark-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://www.aipaikj.top/images/benchmark-light.svg">
    <img alt="总渲染时间：ManimGX 3.08 秒，ManimGL 35.28 秒，Blender Workbench 57.61 秒，ManimCE 278.83 秒，Blender EEVEE 601.40 秒" src="https://www.aipaikj.top/images/benchmark-light.svg" width="100%">
  </picture>
  <p align="center"><sub>所有引擎均使用可用的最快编码预设。数值越低越好。</sub></p>
</figure>

**对比同一场景。** 2.5 秒时的相连圆环，由每个引擎渲染。

| ManimGX | ManimCE | ManimGL | Blender Workbench | Blender EEVEE |
| :---: | :---: | :---: | :---: | :---: |
| ![ManimGX 在 2.5 秒时渲染的八个相连圆环](https://www.aipaikj.top/images/benchmark-quality/manimgx-light.png) | ![ManimCE 在 2.5 秒时渲染的八个相连圆环](https://www.aipaikj.top/images/benchmark-quality/manim_ce-light.png) | ![ManimGL 在 2.5 秒时渲染的八个相连圆环](https://www.aipaikj.top/images/benchmark-quality/manimgl-light.png) | ![Blender Workbench 在 2.5 秒时渲染的八个相连圆环](https://www.aipaikj.top/images/benchmark-quality/blender_workbench-light.png) | ![Blender EEVEE 在 2.5 秒时渲染的八个相连圆环](https://www.aipaikj.top/images/benchmark-quality/blender_eevee-light.png) |

## 快速入门

**用提示词。** 粘贴到 Claude Code、Codex 或 Cursor 中。你的智能体负责设置：

```text
Follow https://www.aipaikj.top/llms.txt.
Install ManimGX, make a 3D animation of the solar system, and open it.
```

**用 pip。** 在 macOS、Linux 或 Windows 上安装，需要 Python 3.13+：

```sh
pip install manimgx
```

字体、排版和视频编码均已包含。
如需编辑器设置和引导式首次动画，请参考
[快速入门](https://www.aipaikj.top/user-guide/quickstart/)。

## 从 Python 到 MP4

将以下内容保存为 `scene.py`：

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

你将得到 `Hello3D.mp4`，一段 1080p60 视频：

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://www.aipaikj.top/films/readme-Hello3D.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://www.aipaikj.top/films/readme-Hello3D-light.svg">
    <img alt="蓝色立方体在相机环绕时被绘制出来" src="https://www.aipaikj.top/films/readme-Hello3D-light.svg#readme" width="100%">
  </picture>
</p>

## 为什么选择 ManimGX？

**面向智能体时代的 3D 视频 API。** 你的智能体使用
[Manim CE 的 API](https://www.manim.community)
编写 Python。ManimGX 的 Rust + wgpu 引擎极速渲染 MP4。

- **完全静态类型。** 包括关键字参数和 `.animate` 链。
- **2D 与 3D 并存。** 曲面、网格和移动相机与文本、方程
  和图形并列。
- **可在浏览器中运行。** `npm install manimgx`。[Pyodide](https://pyodide.org) 在
  Web Worker 中运行
  Python；WebGPU 渲染场景。
  [嵌入场景](https://www.aipaikj.top/user-guide/rendering/#embed-in-a-web-page)无需渲染服务器。
- **智能体反馈。** [`manimgx inspect`](https://www.aipaikj.top/user-guide/rendering/#inspect)：故事板和 2D 布局检查，在播放结束处或你选择的时刻。
- **文本与数学。** 编写 LaTeX 或 Typst。无需安装 LaTeX。
- **语音同步。** [将动画与口述词语匹配](https://www.aipaikj.top/user-guide/sound-and-voice/)
  使用 `self.say()`。

## 文档

**[www.aipaikj.top](https://www.aipaikj.top)** 提供指南、带源代码的
渲染示例和 API 参考：

- [快速入门](https://www.aipaikj.top/user-guide/quickstart/)：安装、设置
  编辑器并渲染你的第一个场景。
- [用户指南](https://www.aipaikj.top/user-guide/the-basics/)：学习场景、
  动画、3D、文本和声音，每次一个概念。
- [示例](https://www.aipaikj.top/gallery/)：观看完整影片并阅读
  生成它们的 Python 代码。
- [API 参考](https://www.aipaikj.top/reference/)：查找类、方法
  及其类型化参数。
- [从 Manim CE 迁移](https://www.aipaikj.top/user-guide/coming-from-manim-ce/)：
  改编现有场景并查看行为差异之处。

对于智能体，[llms.txt](https://www.aipaikj.top/llms.txt) 以 Markdown 格式提供设置说明
和文档链接。

## 巨人肩上

[Grant Sanderson](https://www.3blue1brown.com) 创建了
[Manim](https://github.com/3b1b/manim)。ManimGX 以
[Manim Community Edition](https://www.manim.community) 的 API 为目标，这是广泛使用的
社区维护分支。

Rust 渲染器使用 [wgpu](https://wgpu.rs) 进行原生 GPU 渲染，在浏览器中使用 WebGPU。
其 3D 光照改编自 Google 的
[Filament](https://github.com/google/filament)：基于物理的材质、
基于图像的光照、环境光遮蔽、泛光和 AgX 色调映射。
[Typst](https://typst.app) 排版文本和数学，[mitex](https://github.com/mitex-rs/mitex) 将 LaTeX 输入转换为 Typst。
[x264](https://www.videolan.org/developers/x264.html) 将原生视频导出编码为
H.264；[FFmpeg](https://ffmpeg.org) 解码导入的音频，使用
[libopus](https://opus-codec.org) 处理 Opus。

[Pyodide](https://pyodide.org) 在浏览器 worker 中运行 Python 场景。Linux wheel
捆绑 [Mesa](https://mesa3d.org) 的 lavapipe，在没有合适 GPU 时用于 CPU 上的 Vulkan 渲染。

## 社区

ManimGX 是 [Academa](https://academa.ai) 的开源项目，由 [Abdullah Geduk](https://geduk.io) 和 [Sina Atalay](https://sinaatalay.com) 创建。数境（ShuJing）是其中文适配衍生发行版，由[爱派未来科技](https://www.aipaikj.top)维护。我们欢迎社区的贡献。

问题、错误报告和功能请求请从
[issue](https://github.com/1Cyrvox/ShuJing/issues/new/choose) 开始。
如需贡献代码，请阅读[贡献指南](https://github.com/1Cyrvox/ShuJing/blob/main/.github/CONTRIBUTING.md)
和[开发者指南](https://www.aipaikj.top/developer-guide/)。

[变更日志](https://www.aipaikj.top/changelog/) ·
[引用 ManimGX](https://github.com/1Cyrvox/ShuJing/blob/main/CITATION.cff)

所有参与者请遵守
[行为准则](https://github.com/1Cyrvox/ShuJing/blob/main/.github/CODE_OF_CONDUCT.md)。
请通过
[安全策略](https://github.com/1Cyrvox/ShuJing/blob/main/.github/SECURITY.md) 私下报告漏洞。

## 许可证

ManimGX 自身的代码采用 [MIT 许可证](https://github.com/1Cyrvox/ShuJing/blob/main/LICENSE)。
原生 wheel 包含 x264，整体采用 GPL-3.0-or-later。

捆绑的组件保留其许可证：参见
[第三方声明](https://github.com/1Cyrvox/ShuJing/blob/main/LICENSE-THIRD-PARTY)、
[Linux 渲染器声明](https://github.com/1Cyrvox/ShuJing/blob/main/LICENSE-LAVAPIPE)，
以及 [Noto](https://github.com/1Cyrvox/ShuJing/blob/main/fonts/manimgx-fonts/LICENSE)
和 [Noto CJK](https://github.com/1Cyrvox/ShuJing/blob/main/fonts/manimgx-fonts-cjk/LICENSE) 字体许可证。

本软件使用了 [FFmpeg](https://ffmpeg.org) 的代码，其许可为
[LGPL-2.1-or-later](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html)。
完整源代码（包括 FFmpeg）位于每个
[GitHub 发布版](https://github.com/1Cyrvox/ShuJing/releases) 的 `manimgx-X.Y.Z-source.tar.xz` 中。
