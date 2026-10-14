# 项目管理

## 什么是项目管理？

仓库是包 ManimGX，持有比其代码更多的内容：

```text
.
├── src/manimgx/             ← the package: the scene API and the command line
├── rust/                    ← the engine's crates: the engine, compiled into the package as
│                              manimgx._engine, and the crates it is built with from others'
│                              sources, which they fetch
├── tests/                   ← the package's tests and the integration corpus
├── fonts/                   ← the fonts text is set in, packages of their own:
│   ├── manimgx-fonts/         the Noto fonts
│   └── manimgx-fonts-cjk/     Noto Sans CJK (not in the browser)
├── browser/                 ← ManimGX for the browser, published on npm, with its tests
├── docker/                  ← the Docker image
├── docs/                    ← the docs site: its pages, its settings, what its build loads
├── examples/                ← thirty example films, a Python file each
├── benchmarks/              ← the README's benchmark against Manim CE, ManimGL and Blender:
│                              its scenes, its runner and its recorded results
├── scripts/                 ← what writes and builds: the release's scripts, the docs' generated
│                              pages and pictures, and the engine's DFG table
├── skills/                  ← the agent skill
├── pyproject.toml           ← the package, its workspace (with fonts/), the tools and their settings
├── uv.lock                  ← the exact version of every Python package
├── justfile                 ← the development tasks
├── .pre-commit-config.yaml  ← the checks
├── README.md                ← the front page: GitHub's, PyPI's, and the docs' Welcome
├── AGENTS.md                ← this guide's commands and rules in brief, for coding agents
├── CITATION.cff             ← how to cite ManimGX
├── LICENSE                  ← ManimGX's license, the MIT License
├── LICENSE-THIRD-PARTY      ← what the wheels hold that others hold the copyright in
├── LICENSE-LAVAPIPE         ← the notices of the lavapipe the Linux wheels bundle
├── LICENSES/                ← the text of each license a file of the repository is under
├── REUSE.toml               ← whose each file is, and under which license, where it doesn't say
└── .github/                 ← the workflows, deployment configs, the
                               contributing guide, issue forms and pull request template
```

项目管理是代码之外的一切，在 `src/`、`rust/` 和 `browser/src/` 中：使
代码可安装、在每台机器上相同、且被每个人以相同方式检查的
东西。仓库根是包；除此之外发布的（字体包、
浏览器包、Docker 镜像）各有自己的文件夹。

## 为什么代码不够？

仅代码留下两个问题未解：用户如何获取它，以及开发者如何在其上工作。

### 分发

用户想要 `pip install manimgx` 和一个工作的 `manimgx` 命令。ManimGX 比
纯 Python 更难发布：其引擎是编译的，因此每个平台需要自己的构建，
引擎在其中。发布以五种形式发布 ManimGX：

- **Wheel**，每个平台一个：Linux（x86_64 和 arm64）、macOS（arm64，以及
  在 arm64 上交叉编译的 x86_64）和 Windows（x86_64）。引擎针对 Python 的
  稳定 ABI 构建，因此一个平台的 wheel 服务每个支持的 Python，且 x264 构建到
  其中，因此 wheel 不需要系统的东西。Linux wheel 还捆绑 Mesa 的 lavapipe，
  以在没有 GPU 驱动时在 CPU 上绘图
  （[`scripts/release/build_lavapipe.sh`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/release/build_lavapipe.sh)
  先在 manylinux 镜像中构建它：约 24 MB 的 wheel）。
  [cibuildwheel](https://cibuildwheel.pypa.io) 构建每个 wheel 并在每个
  支持的 Python 上安装它，其中它必须渲染场景
  （[`scripts/release/smoke_test.py`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/release/smoke_test.py)）
  然后才保留：在 Linux 上，镜像中没有驱动，因此用捆绑的 lavapipe。其
  设置是 `pyproject.toml` 中的 `[tool.cibuildwheel]`。
- **源分发包**，在安装它的机器上构建引擎：那
  需要 Rust 和 C 编译器，无其他（引擎的构建从
  其他获取源：见[其他人的源](engine.md#others-sources)）。
- **可执行文件**，每个平台一个：一个文件持有安装了 ManimGX 的 Python，
  用于没有 Python 的机器（见[`scripts/`](#scripts)）。
- **Docker 镜像**，`ghcr.io/1Cyrvox/ShuJing`（见[`docker/`](#docker)）。
- **浏览器包**，npm 上的 `manimgx`：一个文件中的播放器，用
  浏览器 wheel 运行场景（见[`browser/`](#browser)）。

文本排版的字体是独立的包，`manimgx-fonts` 和 `manimgx-fonts-cjk`：
每个平台一个 wheel，在字体更改时发布，而非随每个 ManimGX（见
[`fonts/`](#fonts)）。

PyPI 获取 wheel、源分发包和字体包；GitHub 发布获取
wheel、源分发包、wheel 的完整源（`manimgx-X.Y.Z-source.tar.xz`：
见[许可证](#licenses)）和可执行文件；npm 获取浏览器包；ghcr.io
获取镜像。[发布](#releases)说明发布如何制作。

### 开发环境

开发者 A 今天安装依赖且测试通过。开发者 B 一个月后
安装，获得更新的 Typst 或 numpy，测试失败。对于 ManimGX 风险比
通常更尖锐：集成语料库逐像素比较当前和冻结包的帧，
因此字形如何布局或颜色如何舍入的任何更改都会显示。

因此每个人需要相同的 Python、每个包和 crate 的相同版本，以及
具有相同设置的相同工具，在一个命令中：

```sh
just sync
```

六个月前的 bug？检出那个提交并运行 `just sync`：其 Python 包
和 Rust crate 回到原样。系统的库和 Rust 工具链不
锁定。

本页的其余部分描述使这工作的文件。

## 根目录中的文件

### [`pyproject.toml`](https://github.com/1Cyrvox/ShuJing/blob/main/pyproject.toml)

包（见[包](#the-package)）、开发它的工作区，以及开发
它所需的。[uv](https://docs.astral.sh/uv/concepts/projects/workspaces/) 将
工作区作为一个管理：

- `[tool.uv.workspace]`：其其他成员，`fonts/` 中的字体包，每个有自己的
  `pyproject.toml`（见[`fonts/`](#fonts)）。一个锁文件持有全部，一个
  环境 `.venv` 全部安装。
- `[tool.uv.sources]`：成员如这里。ManimGX 要求其字体包
  精确版本；在工作区中那些是 `fonts/` 中的，可编辑安装，
  如 ManimGX，其引擎由 uv 构建。
- `[dependency-groups]`：开发所需的。`dev` 持有工具（ruff、ty、pytest 及其
  插件、prek）、审查面板的 FastAPI 和 PyAV，语料库用其
  读写视频。`docs` 持有 Zensical 和 mkdocstrings。`ce` 持有
  Manim Community Edition，它渲染语料库的 Manim 引用（见
  [设置](index.md#manim-community-edition)）。每个与 ManimGX 一起安装。
- `[tool.uv]`：`dev` 和 `docs` 默认安装。
- 工具的设置：`[tool.pytest]`、`[tool.coverage.run]`（见
  [测试](testing.md#coverage)）、`[tool.mutmut]`、`[tool.fastapi]`，以及保持
  代码形式和检查其类型的工具的设置，`[tool.ruff]` 和 `[tool.ty]`（如下）。

### [`uv.lock`](https://github.com/1Cyrvox/ShuJing/blob/main/uv.lock)

项目使用的每个 Python 包的精确版本，直到依赖的
依赖。`just sync` 安装恰好这些，而非最新的。

永不手编：在 `pyproject.toml` 中更改依赖后，运行 `just lock`，
并提交两个文件。`just upgrade` 将每个包移至
`pyproject.toml` 文件允许的最新版本。配方用 `uv run --frozen` 运行其工具，它按原样使用
锁文件，而不针对 `pyproject.toml` 文件检查它。

### [`justfile`](https://github.com/1Cyrvox/ShuJing/blob/main/justfile)

[just](https://just.systems) 运行在文件中定义一次的命令。没有它，每个人
用不同选项键入相同的长命令。有了它：

```sh
just test        # pytest, in parallel, in the locked environment
just test-rust   # the Rust core and native libraries, without embedding Python
just check       # every check of .pre-commit-config.yaml
just serve-docs  # render the docs' examples, write the reference, serve the site
```

配方分组（开发、测试、文档、发布），配方上方的注释
是 `just --list` 中的描述。GitHub 工作流运行这些相同的配方，因此
任务在开发者机器上和在 CI 中执行方式相同。[设置](index.md#commands) 列出
每个配方。

### ruff

[ruff](https://docs.astral.sh/ruff/) 保持代码形式到处相同：

- 它格式化，以其稳定风格和 88 列：Python、文档字符串中的
  示例，以及 Markdown 中的 Python。它不拆分长字符串。
- 它 lint：它发现可能的 bug、未排序的导入和过时的惯用法。`pyproject.toml` 中的 `[tool.ruff]` 选择其规则并给出它忽略的每个的原因；包的 `__init__.py` 中的重新导出可以用 `*` 导入并导入它们不
  使用的名称。

`just format` 运行 ruff 的自动修复，然后其格式化器。`just check` 也运行两者
（如下）。文档字符串有自己的形式，Google 风格，因为 API 参考从
它们生成：见[文档](documentation.md#docstrings)。

### ty

[ty](https://docs.astral.sh/ty/) 检查类型。ManimGX 全面类型化，且 ty 在其上报告
无内容：`just check` 必须无错误通过，且更改保持那样。两条
规则遵循：

- **公共签名中无 `Any`。** 关键字选项是 `TypedDict`，作为
  `**kwargs: Unpack[…]` 接受，而非 `**kwargs: Any`，因此拼错的关键字使检查失败，
  在 ManimGX 和用户场景中 alike。[`Style`][manimgx.drawing.paint.Style]，在
  [`drawing/paint.py`](https://github.com/1Cyrvox/ShuJing/blob/main/src/manimgx/drawing/paint.py) 中，
  是样式关键字；[`Polygon`][manimgx.Polygon] 接受 `**kwargs: Unpack[Style]`。
- **仅实时抑制，以 ty 的形式。** ty 遵循 `# ty: ignore[rule]` 和裸
  `# type: ignore`，而非 `# type: ignore[code]`。抑制无内容的抑制是
  错误（`[tool.ty]` 使其为错误），因此修复使其无用的抑制使检查失败。
  ruff 的格式化器不将行尾抑制注释计入行的宽度，但它
  拆分没有它的过长行并将注释移到最后一行，因此在
  `just format` 之后运行 `just check`。

`[tool.ty]` 是 ty 检查内容的唯一列表：包、文档脚本、语料库的
工具和审查服务器，以及它命名的测试。运行 ty 的钩子不传递文件给它，
因此 `just check` 检查该列表。它还将
`svgelements` 读取为无类型（ty 无法读取其
源的编码）。

用户场景被要求更多：每个语料库案例用每条规则类型检查，且
ManimGX 给它的值不能为 `Any`（见[测试](testing.md#the-three-checks)）。

### [`.pre-commit-config.yaml`](https://github.com/1Cyrvox/ShuJing/blob/main/.pre-commit-config.yaml) 和 `just check`

仓库的每个检查，作为钩子：

- 文件检查：无合并冲突标记、有效 TOML 和 YAML、最终换行、无尾随
  空白；
- [check-jsonschema](https://check-jsonschema.readthedocs.io)，它针对
  [Citation File Format](https://citation-file-format.github.io) 的模式检查 `CITATION.cff`；
- [zizmor](https://docs.zizmor.sh)，它发现 GitHub 工作流中的安全问题；
- ruff 和 ty，从环境运行（`uv run --frozen`），因此它们是
  `uv.lock` 锁定的版本；
- 浏览器包的 TypeScript 7 和 Prettier，用其 `bun.lock` 锁定的版本运行；
- [reuse](https://reuse.software)，也从环境，它检查每个文件的许可证
  和版权是否已知（见[许可证](#licenses)）。

[prek](https://prek.j178.dev)，pre-commit 的快速实现，运行它们：`just check`
是 `prek run --all-files --show-diff-on-failure`。更改文件的钩子（ruff 修复
或格式化它、添加最终换行）使检查失败，显示更改，
并保持文件更改；如果无其他问题，下次 `just check` 通过。

仓库不安装 git 钩子：检查在你运行它们时运行，以及在每次推送
到 `main` 和每个拉取请求时，在测试工作流中（见
[GitHub 工作流](github-workflows.md#1-testyaml-the-checks-and-the-tests)）。

### 许可证

ManimGX 在 MIT 许可证下，在
[`LICENSE`](https://github.com/1Cyrvox/ShuJing/blob/main/LICENSE) 中：GitHub、PyPI 和
npm 显示它。某些文件是他人的：从 Manim CE 移植的模块、引擎的 3D 光照
改编自 [Filament](https://github.com/google/filament) 的、Noto 字体、语料库的
来自 CE 文档的场景、从 mitex 的 Typst 包制作的命令规范、一些
文档和图像。仓库说明每个文件是谁的，以及在哪个许可证下，如
[REUSE](https://reuse.software) 指定：

- 带有来自其他地方代码的文件在其前几行说明：每个版权持有者的 `SPDX-FileCopyrightText`
  行（ManimGX 的 `2026 Academa, Inc.` 在其中）和
  `SPDX-License-Identifier` 行，如从 Manim CE 移植的模块所做；
- [`REUSE.toml`](https://github.com/1Cyrvox/ShuJing/blob/main/REUSE.toml) 为
  其余说明：ManimGX 自己的文件，在一个注释中；字体、语料库、数据和图像；
- [`LICENSES/`](https://github.com/1Cyrvox/ShuJing/tree/main/LICENSES) 持有每个
  许可证的文本，一次，以其 SPDX 标识符命名。

引擎 crate 为其获取的源保留的许可证文本（`COPYING`、`LICENSE`；
见[其他人的源](engine.md#others-sources)）是其项目的，如发布：REUSE
让那些名称的文件。`reuse lint`，`just check` 的钩子，在文件的
许可证或版权未知，或许可证无文本时失败。ManimGX 的新文件
不需要什么；从其他地方带来的代码需要其行；数据或图像需要注释。
wheel 持有的他人持有版权的随其声明而来（见
[包](#the-package)）。

wheel 持有 FFmpeg 的音频解码器，在 LGPL-2.1-or-later 下，且除
浏览器的每个 wheel 持有 x264，在 GPL-2.0-or-later 下，crate 在 Apache-2.0 下单独
（Typst、mitex），仅 GPL 的第三版本纳入：这样的 wheel 整体在
GPL-3.0-or-later 下。其第 6 节（和 LGPL 的，它引用它）要求
获取 wheel 的人可以获取其完整源，从 wheel 所在或
wheel 指向的地方，只要 wheel 被提供：全部，包括 crate，
而非其他发布它们的链接，可能消失。每个 GitHub 发布携带它，
`manimgx-X.Y.Z-source.tar.xz`，带源和构建配方（见
[其他人的源](engine.md#others-sources)）；wheel 的声明、README（PyPI 页面）和
发布的注释指向它，README 和注释说明 FFmpeg 要求每个提供
它的页面说的。发布在 PyPI 提供其 wheel 时永不删除。

### [`scripts/`](https://github.com/1Cyrvox/ShuJing/tree/main/scripts)

写入和构建的，每件它制作的东西一个文件夹：

- [`release/`](https://github.com/1Cyrvox/ShuJing/tree/main/scripts/release)：发布的脚本，配方和
  cibuildwheel 运行。
  - [`create_executable.py`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/release/create_executable.py)
    （`just create-executable`）从 `dist/` 中的 wheel 制作本机的可执行文件：
    一个精确的、SHA-256 验证的 Python Build Standalone 归档，带 wheel、字体
    包和 `uv.lock` 锁定的依赖安装，由
    [PyApp](https://ofek.dev/pyapp) 打包成一个文件。文件的
    首次运行解包它持有的 Python；每次运行然后在
    那里运行 `manimgx`，无网络和机器上的 Python，且 `manimgx self` 管理它（`self pip install`
    添加场景导入的包）。脚本写入
    `dist/manimgx-<os>-<arch>.tar.gz`（Windows 上为 `.zip`），在运行它制作的一次之后。
  - [`smoke_test.py`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/release/smoke_test.py)
    用已安装的 ManimGX 渲染场景：wheel 或可执行文件在保留之前通过的
    检查。它解码生成的 PCM 和参考 Opus 固件，导出
    其音轨并重新打开 MP4 的 AAC 声音。Pyodide 记录相同场景并
    检查 take 的版本、帧数、声音和成功结束，及其嵌入的播放器。
  - [`build_lavapipe.sh`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/release/build_lavapipe.sh)
    为 Linux wheel 在 manylinux 镜像中构建 Mesa 的 lavapipe（cibuildwheel 的
    `before-all`）：从其源码构建 Mesa、glslang 和 LLVM，针对锁定的哈希检查。
    LLVM 携带 `scripts/release/llvm/` 中的寄存器类修正。驱动
    仅导出 Vulkan 加载器调用的。脚本写入
    `src/manimgx/lavapipe/libvulkan_lvp.so`，wheel 随后纳入它。其检查的
    归档通过引擎的源存储。修复后，`linux_sources.py` 使用
    auditwheel 的 SBOM 和 RPM 元数据保留捆绑库的精确分发包源。这些是源和来源；系统构建
    工具不是冻结的、密封环境。
  - [`licenses.py`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/release/licenses.py)
    （`just licenses`）写入 wheel 的第三方声明（见
    [包](#the-package)）。
- [`docs/`](https://github.com/1Cyrvox/ShuJing/tree/main/scripts/docs)：文档的生成页面，`just build-docs` 在
  站点构建之前写入：画廊和命令行参考（见
  [文档](documentation.md)）。
- [`showcase/`](https://github.com/1Cyrvox/ShuJing/tree/main/scripts/showcase)：README 的图片，手动制作并提交：
  logo（横幅、页眉的、favicon）和示例影片墙。
- [`engine/`](https://github.com/1Cyrvox/ShuJing/tree/main/scripts/engine)：引擎编译所用的，手动制作：
  [`dfg_table.py`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/engine/dfg_table.py) 写入 `rust/engine/src/dfg.bin`，
  lit 表面的镜面反射从中读取的拆分求和表，仅在光照
  更改时再次运行。

### [`benchmarks/`](https://github.com/1Cyrvox/ShuJing/tree/main/benchmarks)

README 的基准测试：ManimGX 在五个场景上对比 Manim CE、ManimGL 和 Blender，每个
用每个引擎自己的 API 编写（`scenes/`）。其
[README](https://github.com/1Cyrvox/ShuJing/blob/main/benchmarks/README.md) 是
方法和结果，README 数字的来源。`run.py` 将引擎计时到
`results.json`；`chart.py` 从中绘制 README 的图表，`quality.py` 制作
README 的比较图像。`tests/benchmarks/test_comparison.py` 检查两个
README 给出的数字是记录的。

### 文档和覆盖率的托管

[`docs/zensical.toml`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/zensical.toml) 持有
文档站点的设置（见[文档](documentation.md)）；站点构建到
`docs/site/`。托管在工作流旁边配置，在
[`.github/deploy/`](https://github.com/1Cyrvox/ShuJing/tree/main/.github/deploy) 中：
`docs.jsonc` 服务文档站点，`coverage.jsonc` 服务测试的覆盖率报告
（见[测试](testing.md#coverage)）。

### [`AGENTS.md`](https://github.com/1Cyrvox/ShuJing/blob/main/AGENTS.md) 和贡献指南

`AGENTS.md` 是本指南的命令、规则和布局的简述，给编码代理；
[AI 工作流](github-workflows.md#7-aiyaml-claude-on-issues-and-pull-requests)的助手
被告知遵循它。
[贡献指南](https://github.com/1Cyrvox/ShuJing/blob/main/.github/CONTRIBUTING.md)
说明如何提议更改（先 issue，然后拉取请求）并在此链接项目如何
运作。当命令或规则更改时，`AGENTS.md` 随本指南更改。

### [`.gitignore`](https://github.com/1Cyrvox/ShuJing/blob/main/.gitignore)

制作的、非写入的，不进入 git：环境、编译的引擎、`rust/target/`、`dist/`、构建的站点、文档渲染的影片和生成的引用、覆盖率数据和报告，以及渲染输出（`media/`、`*.mp4`）。语料库的参考视频是 `.mkv` 文件且被 Git 忽略；其 SHA-256 伴随文件被提交。

## 包

仓库根是包，定义在
[`pyproject.toml`](https://github.com/1Cyrvox/ShuJing/blob/main/pyproject.toml) 中，以
[标准格式](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)：

- `[project]`：名称、版本、支持的 Python（3.13 和 3.14）、许可证，以及
  ManimGX 运行时需要的包。
  [理解 ManimGX](understanding-manimgx.md#dependencies) 说明每个的用途。
  `license` 将分发持有的每个许可证命名为一个 SPDX 表达式：
  ManimGX 自己的 MIT、编译到引擎的 crate 的（其中包括 x264 的 GPL-2.0-or-later
  ）、Typst 的字体和数据的，以及 Linux wheel 捆绑的 lavapipe 的。
  `license-files` 将 `LICENSE` 和旁边的三个声明放入 wheel 的元数据。
  其 README 是仓库的，`README.md`。
- `[project.scripts]`：使 `manimgx` 成为命令，运行 `manimgx.cli:main`。
- `[build-system]` 和 `[tool.maturin]`：[maturin](https://www.maturin.rs) 构建
  包。它将 `rust/engine/` 中的 crate 编译为模块 `manimgx._engine` 并
  放在 `src/` 的 Python 源旁边。
- `[tool.uv]`：`cache-keys` 说明引擎何时重建（如下）。
- `[tool.cibuildwheel]`：wheel 如何构建和测试（[分发](#distribution)）。
  wheel 用它发布时的字体测试，此仓库的，PyPI 可能
  还没有：在它之前安装。

在旁边，根目录，`license-files` 在 `LICENSE` 之外命名的声明：

- [`LICENSE-THIRD-PARTY`](https://github.com/1Cyrvox/ShuJing/blob/main/LICENSE-THIRD-PARTY)：
  wheel 持有的他人持有版权的内容，附带许可证和声明
  ：包和引擎命名他人的文件（从
  Manim CE 移植的模块、引擎的 3D 光照），带其版权行和来自 `LICENSES/` 的许可证文本；以及编译到引擎的每个 crate，在 wheel 持有的每个构建中
  （每个平台的扩展、Pyodide 的、页面的播放器），带其许可证和声明
  文件，工作区的 crate 那些它们获取的（x264 的、FFmpeg 的、
  libopus 的、mitex 的）。`just licenses` 在 `Cargo.lock` 更改后再次写入它（`just upgrade` 也是），或在携带第三方声明的代码在文件间移动后。测试在
  声明陈旧，或其中的许可证不在 ManimGX 的中时失败。
- [`LICENSE-LAVAPIPE`](https://github.com/1Cyrvox/ShuJing/blob/main/LICENSE-LAVAPIPE)：
  Linux wheel 持有的 lavapipe 的声明：Mesa 的，带其构建
  源的版权行，以及它持有的、链接的库和
  LLVM 的。手写，来自 Mesa 的源：测试在
  `scripts/release/build_lavapipe.sh` 构建另一个 Mesa 而非它描述的时失败。
- [`LICENSE-DXC`](https://github.com/1Cyrvox/ShuJing/blob/main/LICENSE-DXC)：
  Windows wheel 携带的锁定的 DirectX Shader Compiler 的声明，包括
  其源依赖。源归档保留匹配的源闭包。

在 `src/manimgx/` 中，Python 之外：

- `py.typed`：标记包为类型化，因此类型检查器读取其注解。
- [`_engine.pyi`](https://github.com/1Cyrvox/ShuJing/blob/main/src/manimgx/_engine.pyi)：
  引擎的接口，带类型（见[引擎](engine.md#the-boundary-with-python)）。
- [`cli/present.html`](https://github.com/1Cyrvox/ShuJing/blob/main/src/manimgx/cli/present.html)：
  在浏览器中呈现影片幻灯片的页面（`manimgx present`）。

#### 重建引擎

uv 以可编辑模式安装 manimgx：Python 文件的更改在
Python 下次运行时应用。引擎不同：它是编译的文件（macOS 和 Linux 上 `src/manimgx/` 中的 `_engine.abi3.so`，被 git 忽略），仅在 maturin 构建它后存在。

uv 在其 *缓存键* 之一更改时重建包。`cache-keys` 列出引擎的
源：crate 的 Rust 文件和着色器（`*.wgsl`，编译到其中）、其清单
和构建脚本、C 垫片、锁文件，以及 mitex 的 `lib.typ` 和命令规范。crate 获取的
仅在构建脚本更改时更改，它锁定它。
`uv run` 在运行任何东西之前将环境带到最新，因此在
编辑 `rust/engine/src/vector.wgsl` 后，下次 `just test` 重建引擎，然后测试它。

构建是 maturin 的发布构建，按 `rust/Cargo.toml` 中的 `[profile.release]`
优化（完全优化、薄链接时优化）：编译慢，运行快。引擎构建自的文件如果 `cache-keys` 中无模式匹配需要自己的
条目，否则其更改不被看到。`uv sync --reinstall-package manimgx`
无论更改什么都重建引擎。

## [`fonts/`](https://github.com/1Cyrvox/ShuJing/tree/main/fonts)

字体包，工作区的其他成员：
[`manimgx-fonts/`](https://github.com/1Cyrvox/ShuJing/tree/main/fonts/manimgx-fonts) 和
[`manimgx-fonts-cjk/`](https://github.com/1Cyrvox/ShuJing/tree/main/fonts/manimgx-fonts-cjk)，
每个有自己的清单、README 和许可证；每个持有的是其用户获取的。

文本排版的 Noto 字体，在 Typst 自己的之外，以便文本在每台
机器上相同：`manimgx-fonts` 中的 Noto Sans 和 Latin 字体缺少的脚本字体，`manimgx-fonts-cjk` 中的
Noto Sans CJK，每个在 SIL Open Font License（`LICENSE`）下。它们是
数据，40 MB，且很少更改：独立的包，由 uv 的后端构建为每个平台一个
wheel，在它们更改时发布，而非随每个 ManimGX，后者
以精确版本要求它们。版本是字体从 Noto 取出的日期。
`manimgx-fonts-cjk` 在浏览器中不要求，33 MB 对页面
下载太多。ManimGX 在安装的其中找到字体（`importlib.resources`）。

## [`rust/`](https://github.com/1Cyrvox/ShuJing/tree/main/rust)

引擎的 crate，作为一个工作区：[`rust/Cargo.toml`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/Cargo.toml)
列出它们（这里的每个文件夹）、编译它们的构建配置，以及给
mitex ManimGX 自己的规范 crate 的补丁；`Cargo.lock` 对 Rust 如 `uv.lock` 对 Python，每个
crate 的精确版本，提交（`just upgrade` 也移动它）。Cargo 在这里运行，构建到
`rust/target/`。[引擎](engine.md)说明 crate 做什么：

- `engine/`：引擎，`manimgx._engine`——带播放器，在窗口中原生，在
  Pyodide 中为页面携带播放器；其清单持有其依赖（wgpu、PyO3、
  Typst、mitex、winit、rustybuzz）和它遵循的 Clippy lint。
- `x264/`、`nasm/`：x264 和 NASM，从其源码构建。
- `ffmpeg/`：FFmpeg 的音频解码器和 libopus，从其源码构建，在一次调用之后。
- `dxc/`：Windows 的已验证 DirectX Shader Compiler 二进制和匹配的源闭包。
- `mitex-spec-gen/`：mitex 的 Typst 包，引擎服务给 Typst（带其自己的
  `lib.typ`，仅导入转换的 LaTeX 调用的作用域），以及从中制作的
  命令规范。
- `fetch/`：其他构建脚本获取的：一个源树，按其
  文件的 SHA-256 锁定（见[引擎](engine.md#others-sources)）。

仓库不持有他人写的任何东西，除了其许可证文本，crate 为
声明保留（`COPYING`、`LICENSE`），如其作者发布的；检查让它们
独立。

## [`browser/`](https://github.com/1Cyrvox/ShuJing/tree/main/browser)

ManimGX 的浏览器版，发布到 npm 为 `manimgx`：播放器的元素（`src/player.ts`）
和导演的 worker（`src/director.ts`）。`just build-npm` 在
将 worker 嵌入一个浏览器模块（`dist/manimgx.js`）之前编译它，TypeScript 7 从实现生成公共
声明。包从 PyPI 以其自己的版本安装 ManimGX 的浏览器
wheel，在 Pyodide 中，用该 wheel 的引擎携带的播放器播放。

开发工具锁定在 `bun.lock` 中。`just check` 检查 TypeScript 及其
格式化；`just test-typescript` 运行包的测试，在 `browser/tests/` 中。

## [`docker/`](https://github.com/1Cyrvox/ShuJing/tree/main/docker)

从 PyPI 安装 ManimGX（构建它的版本，
或最新的）到 `python:3.14-slim` 的镜像的 `Dockerfile`，带 Vulkan 的加载器和 Mesa 的驱动：lavapipe
在 CPU 上绘图，给容器的 GPU（AMD 和 Intel 的 `--device /dev/dri`，
NVIDIA 的 `--gpus all`）被使用。其入口点是 `manimgx` 命令，在
`/work` 中运行：

```sh
docker run --rm -v "$PWD:/work" ghcr.io/1Cyrvox/ShuJing:0.1 render scene.py
```

`just build-docker-image <version>` 为本地使用构建该 `published` 目标。发布
从其已测试的 wheel 和字体制品构建单独的 `release` 目标，运行时依赖针对 `uv.lock` 认证。它在任何注册表发布之前冒烟测试并保留 OCI
归档；发布复制那些相同的镜像摘要。

## 发布

版本在 `pyproject.toml` 中（`0.1.1`；引擎的 crate 携带相同编号）。ManimGX 遵循[语义版本控制](https://semver.org)，其[变更日志](../changelog.md)遵循 [Keep a Changelog](https://keepachangelog.com)：用户会注意到的更改在"Unreleased"下添加一行（见[文档](documentation.md#the-changelog)）。

发布需要三步：

1. `main` 上的提交在 `pyproject.toml` 中设置新版本，并将
   变更日志的"Unreleased"行移入自己的段落，`## X.Y.Z`。
2. `just release`，在该提交，请求确认，标记它 `vX.Y.Z`，并推送
   标签。
3. 标签启动[发布工作流](github-workflows.md#4-releaseyaml-a-release)。它
   除非标签是 ManimGX 的版本且变更日志有它的段落才停止；然后
   运行测试，构建一切，并发布：GitHub 发布，其注释是
   变更日志的段落（`just release-notes X.Y.Z` 打印它们），PyPI、npm 和 ghcr.io。
   PyPI 获取它没有的字体包版本：对字体的更改在
   其 `pyproject.toml` 和 ManimGX 的要求中设置新版本，并随
   下一个 ManimGX 发布。

以 `aN`、`bN` 或 `rcN` 结尾的版本（如 `0.2.0rc1`）是预发布。

## 了解更多

- [uv 文档](https://docs.astral.sh/uv/)：项目、锁文件、依赖组。
- [maturin 用户指南](https://www.maturin.rs)：混合 Rust 和 Python 项目。
- [cibuildwheel 文档](https://cibuildwheel.pypa.io)：构建和测试 wheel。
- [just 手册](https://just.systems/man/en/)。