<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="showcase/logo-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="showcase/logo-light.svg">
    <img alt="数境" src="showcase/logo-light.svg" width="640">
  </picture>
</p>

<p align="center">
  <b>极速 3D 数学动画引擎，兼容 <a href="https://www.manim.community">Manim Community（ManimCE）</a> API语法。</b><br>
  由 Rust 和 wgpu 驱动，GPU 加速渲染，在Apple M4 Pro基准场景测试下，比 ManimCE 快90.6倍。
</p>

<p align="center">
  <b><a href="/">文档</a></b> ·
  <a href="/user-guide/quickstart/">快速开始</a> ·
  <a href="https://github.com/academa-labs/manimgx/tree/main/examples">示例</a> ·
  <a href="/reference/">API 参考</a>
</p>

<p align="center">
  <a href="https://pypi.org/project/manimgx/"><img alt="PyPI version" src="https://img.shields.io/pypi/v/manimgx?color=58c4dd&label=PyPI"></a>
  <a href="https://www.npmjs.com/package/manimgx"><img alt="npm version" src="https://img.shields.io/npm/v/manimgx?color=58c4dd"></a>
  <a href="https://pepy.tech/projects/manimgx"><img alt="PyPI total downloads" src="https://img.shields.io/pepy/dt/manimgx?color=58c4dd&label=PyPI%20downloads"></a>

</p>

<p align="center">
  <a href="https://github.com/academa-labs/manimgx/blob/main/examples/quadratic_formula.py"><img alt="二次公式：移动彩色矩形和方程项完成配方" src="showcase/quadratic_formula.gif" width="32%"></a>
  <a href="https://github.com/academa-labs/manimgx/blob/main/examples/fourier_pi.py"><img alt="傅里叶级数：旋转箭头链画出 π 的轮廓" src="showcase/fourier_pi.gif" width="32%"></a>
  <a href="https://github.com/academa-labs/manimgx/blob/main/examples/linear_maps.py"><img alt="矩阵变换平面：网格、基向量和单位正方形一起变换" src="showcase/linear_maps.gif" width="32%"></a>
  <br>
  <a href="https://github.com/academa-labs/manimgx/blob/main/examples/derivative.py"><img alt="切线沿曲线滑动，斜率描绘出导数" src="showcase/derivative.gif" width="32%"></a>
  <a href="https://github.com/academa-labs/manimgx/blob/main/examples/complex_maps.py"><img alt="复函数将网格弯折成抛物线、圆和射线" src="showcase/complex_maps.gif" width="32%"></a>
  <a href="https://github.com/academa-labs/manimgx/blob/main/examples/lorenz_attractor.py"><img alt="洛伦兹吸引子：邻近轨迹在三维空间中分离成蝴蝶形" src="showcase/lorenz_attractor.gif" width="32%"></a>
  <br>
  <a href="https://github.com/academa-labs/manimgx/blob/main/examples/heavy_top.py"><img alt="三个陀螺进动和章动，轴在球面上描绘曲线" src="showcase/heavy_top.gif" width="32%"></a>
  <a href="https://github.com/academa-labs/manimgx/blob/main/examples/hopf_fibration.py"><img alt="霍普夫纤维化：彩色相连圆环形成嵌套环面" src="showcase/hopf_fibration.gif" width="32%"></a>
  <a href="https://github.com/academa-labs/manimgx/blob/main/examples/catenoid_helicoid.py"><img alt="彩虹螺旋面弯曲成悬链面，保持内蕴曲率" src="showcase/catenoid_helicoid.gif" width="32%"></a>
</p>

**36.2 秒的视频，仅需 3.08 秒渲染。** 在 Apple M4 Pro 上以 1080p60 渲染五个场景，数境（ManimGX）比 **ManimCE 快 90.6 倍**，比 **ManimGL 快 11.5 倍**，比 **Blender Workbench 快 18.7 倍**。[如何测量](https://github.com/academa-labs/manimgx/tree/main/benchmarks)。

<figure class="mx-benchmark">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="images/benchmark-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="images/benchmark-light.svg">
    <img alt="渲染时间对比" src="images/benchmark-light.svg" width="100%">
  </picture>
  <p align="center"><sub>所有引擎使用最快编码预设。越低越好。</sub></p>
</figure>

**同一场景对比。** 2.5 秒处的八个相连圆环，由各引擎渲染：

| 数境 / ManimGX | ManimCE | ManimGL | Blender Workbench | Blender EEVEE |
| :---: | :---: | :---: | :---: | :---: |
| ![ManimGX](images/benchmark-quality/manimgx-light.png) | ![ManimCE](images/benchmark-quality/manim_ce-light.png) | ![ManimGL](images/benchmark-quality/manimgl-light.png) | ![Blender Workbench](images/benchmark-quality/blender_workbench-light.png) | ![Blender EEVEE](images/benchmark-quality/blender_eevee-light.png) |

## 快速开始

**用 pip 安装。** 在 macOS、Linux 或 Windows 上安装（需要 Python 3.13+）：

```sh
pip install manimgx
```

字体、排版和视频编码已全部内置。编辑器配置和引导式首次动画请见[快速开始](/user-guide/quickstart/)。

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

即可得到 `Hello3D.mp4`，一段 1080p60 的视频。

## 为什么选择数境？

**面向AI助手的3D视频API。** AI助手可使用 [Manim Community（ManimCE）](https://www.manim.community) 风格Python代码，由数境的Rust + wgpu引擎渲染输出MP4，极速完成。

- **完全静态类型。** 关键字参数和 `.animate` 链全部有类型标注。
- **2D 与 3D 统一。** 曲面、网格和移动相机，与文本、方程和图表并存。
- **浏览器中运行。** `npm install manimgx`，Pyodide 运行 Python，WebGPU 渲染场景。
- **AI 助手反馈。** [`manimgx inspect`](/user-guide/rendering/#inspect)：故事板和 2D 布局检查。
- **文本与数学。** 支持 LaTeX 和 Typst，无需安装 LaTeX。
- **语音同步。** 用 `self.say()` 将动画与语音对齐。
- **中文优先。** 中文数学公式排版、中文教学模板、中文文档。

## 文档

- [快速开始](/user-guide/quickstart/)：安装、配置编辑器、渲染你的第一个动画。
- [用户指南](/user-guide/the-basics/)：逐步学习场景、动画、3D、文本和声音。
- [API 参考](/reference/)：查询类、方法及其类型化参数。
- [从 Manim CE 迁移](/user-guide/coming-from-manim-ce/)：适配现有场景，检查行为差异。

## 站在巨人的肩膀上

[Grant Sanderson](https://www.3blue1brown.com) 创建了 [Manim](https://github.com/3b1b/manim)。数境基于 [ManimGX](https://github.com/academa-labs/manimgx)，它兼容 [Manim Community Edition](https://www.manim.community) 的 API。

Rust 渲染器使用 [wgpu](https://wgpu.rs) 进行原生 GPU 渲染和浏览器中的 WebGPU 渲染。3D 光照改编自 Google 的 [Filament](https://github.com/google/filament)：基于物理的材质、基于图像的光照、环境光遮蔽、泛光和 AgX 色调映射。[Typst](https://typst.app) 排版文本和数学公式，[mitex](https://github.com/mitex-rs/mitex) 将 LaTeX 输入转换为 Typst。[x264](https://www.videolan.org/developers/x264.html) 将原生视频导出编码为 H.264。

## 社区

数境是由 [爱派未来科技](https://aipaikj.top) 维护的开源项目，是基于 [ManimGX](https://github.com/academa-labs/manimgx) 开发的中文适配衍生发行版。

上游ManimGX引擎原生Bug、基础引擎相关功能请求，请提交至 [academa-labs/manimgx Issues](https://github.com/academa-labs/manimgx/issues/new/choose)；数境本地化适配、中文文档、新增功能以及自研修复Bug，请在数境仓库提交反馈。

## 许可证

数境代码继承上游 [academa-labs/manimgx](https://github.com/academa-labs/manimgx/blob/main/LICENSE) 的开源许可证；文档采用 [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) 许可证。