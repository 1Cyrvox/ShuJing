# 项目管理

## 什么是项目管理？

仓库是包 ManimGX，持有比其代码更多的内容：

```text
.
├── src/manimgx/             ← 包：场景 API 和命令行
├── rust/                    ← 引擎的 crate：引擎，编译为包中的
│                              manimgx._engine，以及从他人源码构建的 crate，
│                              它们获取这些源码
├── tests/                   ← 包的测试和集成语料库
├── fonts/                   ← 排版所用字体，各自的包：
│   ├── manimgx-fonts/         Noto 字体
│   └── manimgx-fonts-cjk/     Noto Sans CJK（浏览器中不含）
├── browser/                 ← 浏览器的 ManimGX，发布到 npm，带其测试
├── docker/                  ← Docker 镜像
├── docs/                    ← 文档站点：其页面、其设置、其构建加载的内容
├── examples/                ← 三十个示例影片，每个一个 Python 文件
├── benchmarks/              ← README 对 Manim CE、ManimGL 和 Blender 的基准测试：
│                              其场景、其运行器和其记录的结果
├── scripts/                 ← 编写和构建的内容：发布的脚本、文档生成的
│                              页面和图片，以及引擎的 DFG 表
├── skills/                  ← 代理技能
├── pyproject.toml           ← 包、其工作区（带 fonts/）、工具及其设置
├── uv.lock                  ← 每个 Python 包的精确版本
├── justfile                 ← 开发任务
├── .pre-commit-config.yaml  ← 检查
├── README.md                ← 首页：GitHub 的、PyPI 的和文档的欢迎页
├── AGENTS.md                ← 本指南的命令和规则简述，面向编码代理
├── CITATION.cff             ← 如何引用 ManimGX
├── LICENSE                  ← ManimGX 的许可证，MIT 许可证
├── LICENSE-THIRD-PARTY      ← wheel 中他人持有版权的内容
├── LICENSE-LAVAPIPE         ← Linux wheel 内置的 lavapipe 的声明
├── LICENSES/                ← 仓库文件所适用的每个许可证的文本
├── REUSE.toml               ← 每个文件是谁的，在哪个许可证下，未说明处
└── .github/                 ← 工作流、部署配置、贡献指南、issue 表单和 pull request 模板
```

项目管理是 `src/`、`rust/` 和 `browser/src/` 中的代码之外的一切：使代码可安装、在每台机器上相同、并以相同方式被每个人检查的内容。仓库根是包；除此之外发布的内容（字体包、浏览器包、Docker 镜像）有自己的文件夹。

## 为什么仅有代码不够？

仅代码留下两个问题开放：用户如何获取它，以及开发者如何在其上工作。

### 分发

用户想要 `pip install manimgx` 和可用的 `manimgx` 命令。ManimGX 比纯 Python 更难发布：其引擎是编译的，因此每个平台需要自己的构建，引擎在其中。发布以五种形式发布 ManimGX：

- **Wheel**，每个平台一个：Linux（x86_64 和 arm64）、macOS（arm64，以及 arm64 上交叉编译的 x86_64）和 Windows（x86_64）。引擎针对 Python 的稳定 ABI 构建，因此平台的一个 wheel 服务每个支持的 Python，x264 内置其中，因此 wheel 不需要系统上的任何东西。Linux wheel 还内置 Mesa 的 lavapipe，在没有 GPU 驱动时在 CPU 上绘制
  （[`scripts/release/build_lavapipe.sh`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/release/build_lavapipe.sh)
  先在 manylinux 镜像中构建它：约 24 MB 的 wheel）。
  [cibuildwheel](https://cibuildwheel.pypa.io) 构建每个 wheel 并在每个支持的 Python 上安装它，在其中必须渲染一个场景
  （[`scripts/release/smoke_test.py`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/release/smoke_test.py)）
  然后才保留：在 Linux 上，镜像中无驱动，因此用内置的 lavapipe。其设置是 `pyproject.toml` 中的 `[tool.cibuildwheel]`。
- **源码分发**，在安装它的机器上构建引擎：需要 Rust 和 C 编译器，无需其他（引擎的构建获取它从他人取的源码：见[他人的源码](engine.md#others-sources)）。
- **可执行文件**，每个平台一个：一个持有已安装 ManimGX 的 Python 的文件，用于没有 Python 的机器（见[`scripts/`](#scripts)）。
- **Docker 镜像**，`ghcr.io/1Cyrvox/ShuJing`（见[`docker/`](#docker)）。
- **浏览器包**，npm 上的 `manimgx`：一个文件中的播放器，用浏览器的 wheel 运行场景（见[`browser/`](#browser)）。

排版所用的字体是各自的包，`manimgx-fonts` 和 `manimgx-fonts-cjk`：每个平台一个 wheel，在字体更改时发布，而非随每次 ManimGX（见[`fonts/`](#fonts)）。

PyPI 获得 wheel、源码分发和字体包；GitHub 发布获得 wheel、源码分发、wheel 的完整源码（`manimgx-X.Y.Z-source.tar.xz`：见[许可证](#licenses)）和可执行文件；npm 获得浏览器包；ghcr.io 获得镜像。[发布](#releases)说明发布如何进行。

### 开发环境

开发者 A 今天安装依赖，测试通过。开发者 B 一个月后安装，获得更新的 Typst 或 numpy，测试失败。对 ManimGX，风险比通常更尖锐：集成语料库逐像素比较当前和冻结包的帧，因此字形布局或颜色取整方式的任何更改都会显现。

因此每个人需要相同的 Python、每个包和 crate 的相同版本，以及带相同设置的相同工具，在一个命令中：

```sh
just sync
```

六个月前的 bug？检出那个提交并运行 `just sync`：其 Python 包和 Rust crate 回到原样。系统的库和 Rust 工具链不固定。

本页其余部分描述使这生效的文件。

## 根目录中的文件

### [`pyproject.toml`](https://github.com/1Cyrvox/ShuJing/blob/main/pyproject.toml)

包（见[包](#the-package)）、开发它的工作区以及开发它所需的内容。[uv](https://docs.astral.sh/uv/concepts/projects/workspaces/) 将工作区作为一个管理：

- `[tool.uv.workspace]`：其其他成员，`fonts/` 中的字体包，每个有自己的 `pyproject.toml`（见[`fonts/`](#fonts)）。一个锁定文件持有所有，一个环境 `.venv` 安装所有。
- `[tool.uv.sources]`：成员在此处的样子。ManimGX 要求其字体包在精确版本；在工作区中那些是 `fonts/` 中的，可编辑安装，如 ManimGX，其引擎由 uv 构建。
- `[dependency-groups]`：开发所需的内容。`dev` 持有工具（ruff、ty、pytest 及其插件、prek）、审查面板的 FastAPI 和 PyAV，语料库用后者读写其视频。`docs` 持有 Zensical 和 mkdocstrings。`ce` 持有 Manim Community Edition，它渲染语料库的 Manim 参考（见[搭建](index.md#manim-community-edition)）。每个与 ManimGX 一起安装。
- `[tool.uv]`：`dev` 和 `docs` 默认安装。
- 工具的设置：`[tool.pytest]`、`[tool.coverage.run]`（见[测试](testing.md#coverage)）、`[tool.mutmut]`、`[tool.fastapi]`，以及保持代码形式和检查其类型的工具的设置，`[tool.ruff]` 和 `[tool.ty]`（下文）。

### [`uv.lock`](https://github.com/1Cyrvox/ShuJing/blob/main/uv.lock)

项目使用的每个 Python 包的精确版本，下至依赖的依赖。`just sync` 安装恰好这些，而非最新的。

从不手动编辑：在 `pyproject.toml` 中更改依赖后运行 `just lock`，并提交两个文件。`just upgrade` 将每个包移至 `pyproject.toml` 文件允许的最新版本。配方用 `uv run --frozen` 运行其工具，后者按原样使用锁定文件，不对照 `pyproject.toml` 文件检查它。

### [`justfile`](https://github.com/1Cyrvox/ShuJing/blob/main/justfile)

[just](https://just.systems) 运行在文件中一次定义的命令。没有它，每个人用不同选项输入相同的长命令。有了它：

```sh
just test        # pytest，并行，在锁定环境中
just test-rust   # Rust 核心和原生库，不嵌入 Python
just check       # .pre-commit-config.yaml 的每个检查
just serve-docs  # 渲染文档示例，写参考，服务站点
```

配方分组（开发、测试、文档、发布），配方上方的注释是其在 `just --list` 中的描述。GitHub 工作流运行这些相同的配方，因此任务在开发者的机器上与在 CI 中相同。[搭建](index.md#commands) 列出每个配方。

### ruff

[ruff](https://docs.astral.sh/ruff/) 保持代码形式在各处相同：

- 它格式化，以其稳定风格和 88 列：Python、文档字符串中的示例，以及 Markdown 中的 Python。它不拆分长字符串。
- 它 lint：发现可能的 bug、未排序的导入和过时的惯用法。`pyproject.toml` 中的 `[tool.ruff]` 选择其规则并给出其忽略每个的理由；`__init__.py` 中包的重新导出可以用 `*` 导入并导入其不使用的名称。

`just format` 运行 ruff 的自动修复，然后其格式化器。`just check` 也运行两者（下文）。文档字符串有自己的形式，Google 风格，因为 API 参考从中生成：见[文档](documentation.md#docstrings)。

### ty

[ty](https://docs.astral.sh/ty/) 检查类型。ManimGX 全程有类型，ty 在其上不报告任何内容：`just check` 必须无错误通过，变更保持如此。两条规则：

- **公共签名中无 `Any`。** 关键字选项是 `TypedDict`，作为 `**kwargs: Unpack[…]` 接受，从不作为 `**kwargs: Any`，因此拼错的关键字使检查失败，在 ManimGX 和用户场景中 alike。[`Style`][manimgx.drawing.paint.Style]，在
  [`drawing/paint.py`](https://github.com/1Cyrvox/ShuJing/blob/main/src/manimgx/drawing/paint.py) 中，是样式关键字；[`Polygon`][manimgx.Polygon] 接受 `**kwargs: Unpack[Style]`。
- **仅活跃的抑制，以 ty 的形式。** ty 接受 `# ty: ignore[rule]` 和裸 `# type: ignore`，不接受 `# type: ignore[code]`。抑制无内容的抑制是错误（`[tool.ty]` 使其为错误），因此修复使其无用的抑制使检查失败。ruff 的格式化器不将尾部抑制注释计入行宽，但它拆分无注释的过长行并将注释移到最后一行，因此在 `just format` 之后运行 `just check`。

`[tool.ty]` 是 ty 检查内容的唯一列表：包、文档脚本、语料库工具和审查服务器，以及它命名的测试。运行 ty 的 hook 不传递文件给它，因此 `just check` 检查该列表。它还将 `svgelements` 读为无类型（ty 无法读其源码的编码）。

用户场景被要求更多：每个语料库案例用每条规则类型检查，ManimGX 给它的值不能为 `Any`（见[测试](testing.md#the-three-checks)）。

### [`.pre-commit-config.yaml`](https://github.com/1Cyrvox/ShuJing/blob/main/.pre-commit-config.yaml) 和 `just check`

仓库拥有的每个检查，作为 hook：

- 文件检查：无合并冲突标记、有效的 TOML 和 YAML、最终换行、无尾随空格；
- [check-jsonschema](https://check-jsonschema.readthedocs.io)，检查 `CITATION.cff` 对照 [Citation File Format](https://citation-file-format.github.io) 的模式；
- [zizmor](https://docs.zizmor.sh)，发现 GitHub 工作流中的安全问题；
- ruff 和 ty，从环境运行（`uv run --frozen`），因此是 `uv.lock` 锁定的版本；
- 浏览器包的 TypeScript 7 和 Prettier，用其 `bun.lock` 锁定的版本运行；
- [reuse](https://reuse.software)，也从环境运行，检查每个文件的许可证和版权已知（见[许可证](#licenses)）。

[prek](https://prek.j178.dev)，pre-commit 的快速实现，运行它们：`just check` 是 `prek run --all-files --show-diff-on-failure`。更改文件的 hook（ruff 修复或格式化它、添加最终换行）使检查失败，显示更改，并保留文件更改；如果无其他问题，下一次 `just check` 通过。

仓库不安装 git hook：检查在你运行它们时运行，以及在每次推送到 `main` 和每个 pull request 时，在 Test 工作流中（见[GitHub 工作流](github-workflows.md#1-testyaml-the-checks-and-the-tests)）。

### 许可证

ManimGX 在 MIT 许可证下，在
[`LICENSE`](https://github.com/1Cyrvox/ShuJing/blob/main/LICENSE) 中：GitHub、PyPI 和 npm 显示它。某些文件是他人的：从 Manim CE 移植的模块、从 [Filament](https://github.com/google/filament) 改编的引擎 3D 光照、Noto 字体、来自 CE 文档的语料库场景、从 mitex 的 Typst 包制作的命令规格、一些文档和图片。仓库说明每个文件是谁的，在哪个许可证下，如 [REUSE](https://reuse.software) 所指定：

- 含他人代码的文件在其前几行说明：每个版权持有者一个 `SPDX-FileCopyrightText` 行（ManimGX 的 `2026 Academa, Inc.` 也在其中）和一个 `SPDX-License-Identifier` 行，如从 Manim CE 移植的模块所做；
- [`REUSE.toml`](https://github.com/1Cyrvox/ShuJing/blob/main/REUSE.toml) 为其余说明：ManimGX 自己的文件，在一个注释中；字体、语料库、数据和图片；
- [`LICENSES/`](https://github.com/1Cyrvox/ShuJing/tree/main/LICENSES) 持有每个许可证的文本，一次，以 SPDX 标识符命名。

引擎 crate 为其获取的源码保留的许可证文本（`COPYING`、`LICENSE`；见[他人的源码](engine.md#others-sources)）是其项目的，如发布：REUSE 让那些名称的文件如此。`reuse lint`，`just check` 的 hook，在文件许可证或版权未知或许可证无文本时失败。ManimGX 的新文件无需任何内容；从他处带来的代码需要其行；数据或图片需要注释。wheel 中他人持有版权的内容附带其声明（见[包](#the-package)）。

wheel 持有 FFmpeg 的音频解码器，在 LGPL-2.1-or-later 下，除浏览器的每个 wheel 持有 x264，在 GPL-2.0-or-later 下，crate 单独在 Apache-2.0 下（Typst、mitex），仅 GPL 的第三版本纳入：这样的 wheel，整体上，在 GPL-3.0-or-later 下。其第 6 节（以及 LGPL 的，引用它）要求获得 wheel 的人能获取其完整源码，从 wheel 所在处或 wheel 指向处，只要 wheel 被提供：全部，包括 crate，而非他人发布处的链接，那些可能失效。每个 GitHub 发布携带它，`manimgx-X.Y.Z-source.tar.xz`，带源码和构建配方（见[他人的源码](engine.md#others-sources)）；wheel 的声明、README（PyPI 页面）和发布的说明指向它，README 和说明说出 FFmpeg 要求每个提供它的页面说的话。发布在 PyPI 提供其 wheel 期间从不删除。

### [`scripts/`](https://github.com/1Cyrvox/ShuJing/tree/main/scripts)

编写和构建的内容，每个制作的东西一个文件夹：

- [`release/`](https://github.com/1Cyrvox/ShuJing/tree/main/scripts/release)：发布的脚本，由配方和 cibuildwheel 运行。
  - [`create_executable.py`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/release/create_executable.py)
    （`just create-executable`）从 `dist/` 中的 wheel 制作本机的可执行文件：一个精确的、SHA-256 验证的 Python Build Standalone 归档，带 wheel、字体包和 `uv.lock` 锁定的依赖安装，由
    [PyApp](https://ofek.dev/pyapp) 打包到一个文件。文件首次运行解包其持有的 Python；之后每次运行在那里运行 `manimgx`，无需网络和机器上的 Python，`manimgx self` 管理它（`self pip install` 添加场景导入的包）。脚本在运行一次所制作的内容后写入
    `dist/manimgx-<os>-<arch>.tar.gz`（Windows 上为 `.zip`）。
  - [`smoke_test.py`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/release/smoke_test.py)
    用已安装的 ManimGX 渲染一个场景：wheel 或可执行文件在保留之前通过的检查。它解码生成的 PCM 和参考 Opus 固件，导出其音轨并重新打开 MP4 的 AAC 声音。Pyodide 录制同一场景并检查 take 的版本、帧数、声音和成功结束，及其嵌入的播放器。
  - [`build_lavapipe.sh`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/release/build_lavapipe.sh)
    为 Linux wheel 在 manylinux 镜像中构建 Mesa 的 lavapipe（cibuildwheel 的 `before-all`）：从源码构建 Mesa、glslang 和 LLVM，对照固定哈希检查。LLVM 携带 `scripts/release/llvm/` 中的寄存器类修正。驱动程序仅导出 Vulkan 加载器调用的内容。脚本写入
    `src/manimgx/lavapipe/libvulkan_lvp.so`，wheel 然后纳入它。其检查的归档通过引擎的源码存储。修复后，`linux_sources.py` 使用 auditwheel 的 SBOM 和 RPM 元数据保留内置库的精确分发源码包。这些是源码和出处；系统构建工具不是冻结的密封环境。
  - [`licenses.py`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/release/licenses.py)
    （`just licenses`）写入 wheel 的第三方声明（见[包](#the-package)）。
- [`docs/`](https://github.com/1Cyrvox/ShuJing/tree/main/scripts/docs)：文档生成的页面，`just build-docs` 在站点构建之前写入：画廊和命令行参考（见[文档](documentation.md)）。
- [`showcase/`](https://github.com/1Cyrvox/ShuJing/tree/main/scripts/showcase)：README 的图片，手工制作并提交：logo（横幅、页头的、网站图标）和示例影片的墙。
- [`engine/`](https://github.com/1Cyrvox/ShuJing/tree/main/scripts/engine)：引擎编译所用的内容，手工制作：
  [`dfg_table.py`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/engine/dfg_table.py) 写入 `rust/engine/src/dfg.bin`，即读取光照表面镜面反射的拆分求和表，仅在光照更改时再次运行。

### [`benchmarks/`](https://github.com/1Cyrvox/ShuJing/tree/main/benchmarks)

README 的基准测试：ManimGX 对 Manim CE、ManimGL 和 Blender 在五个场景上，每个用各引擎自己的 API 编写（`scenes/`）。其
[README](https://github.com/1Cyrvox/ShuJing/blob/main/benchmarks/README.md) 是方法和结果，README 数字的来源。`run.py` 将引擎计时到 `results.json`；`chart.py` 从中绘制 README 的图表，`quality.py` 制作 README 的比较图片。`tests/benchmarks/test_comparison.py` 检查两个 README 给出的数字是记录的。

### 文档和覆盖率的托管

[`docs/zensical.toml`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/zensical.toml) 持有文档站点的设置（见[文档](documentation.md)）；站点构建到 `docs/site/`。托管与工作流并列配置，在
[`.github/deploy/`](https://github.com/1Cyrvox/ShuJing/tree/main/.github/deploy) 中：`docs.jsonc` 服务文档站点，`coverage.jsonc` 服务测试的覆盖率报告（见[测试](testing.md#coverage)）。

### [`AGENTS.md`](https://github.com/1Cyrvox/ShuJing/blob/main/AGENTS.md) 和贡献指南

`AGENTS.md` 是本指南的命令、规则和布局的简述，面向编码代理；
[AI 工作流](github-workflows.md#7-aiyaml-claude-on-issues-and-pull-requests) 的助手被告知遵循它。
[贡献指南](https://github.com/1Cyrvox/ShuJing/blob/main/.github/CONTRIBUTING.md)
说明如何提出变更（先 issue，然后 pull request）并链接到这里了解项目如何运作。当命令或规则更改时，`AGENTS.md` 随本指南更改。

### [`.gitignore`](https://github.com/1Cyrvox/ShuJing/blob/main/.gitignore)

生成的、非编写的内容不进 git：环境、编译的引擎、`rust/target/`、`dist/`、构建的站点、文档渲染的影片和生成的参考、覆盖率数据和报告，以及渲染输出（`media/`、`*.mp4`）。语料库的参考视频是 `.mkv` 文件，被 Git 忽略；其 SHA-256 伴随文件已提交。

## 包

仓库根是包，在
[`pyproject.toml`](https://github.com/1Cyrvox/ShuJing/blob/main/pyproject.toml) 中以
[标准格式](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) 定义：

- `[project]`：名称、版本、支持的 Python（3.13 和 3.14）、许可证，以及 ManimGX 运行时需要的包。
  [理解 ManimGX](understanding-manimgx.md#dependencies) 说明每个的用途。
  `license` 作为 SPDX 表达式命名分发持有的所有内容的许可证：ManimGX 自己的 MIT、编译到引擎中的 crate 的（包括 x264 的 GPL-2.0-or-later）、Typst 的字体和数据的，以及 Linux wheel 内置的 lavapipe 的。
  `license-files` 将 `LICENSE` 和三个声明放在其旁，到 wheel 的元数据中。其 README 是仓库的 `README.md`。
- `[project.scripts]`：使 `manimgx` 成为命令，运行 `manimgx.cli:main`。
- `[build-system]` 和 `[tool.maturin]`：[maturin](https://www.maturin.rs) 构建包。它将 `rust/engine/` 中的 crate 编译为模块 `manimgx._engine` 并放在 `src/` 的 Python 源码旁。
- `[tool.uv]`：`cache-keys` 说明何时重建引擎（下文）。
- `[tool.cibuildwheel]`：wheel 如何构建和测试（[分发](#distribution)）。wheel 用其发布的字体测试，即本仓库的，PyPI 可能还没有：在之前安装它们。

在其旁，根目录，`license-files` 命名除 `LICENSE` 之外的声明：

- [`LICENSE-THIRD-PARTY`](https://github.com/1Cyrvox/ShuJing/blob/main/LICENSE-THIRD-PARTY)：wheel 中他人持有版权的内容，带其许可证和声明：包和引擎中命名他人的文件（从 Manim CE 移植的模块、引擎的 3D 光照），带其版权行和 `LICENSES/` 中的许可证文本；以及编译到引擎中的每个 crate，在 wheel 持有的每个构建中（每个平台的扩展、Pyodide 的、页面的播放器），带其许可证和声明文件，工作区的 crate 那些它们获取的（x264 的、FFmpeg 的、libopus 的、mitex 的）。`just licenses` 在 `Cargo.lock` 更改后（`just upgrade` 也是）或在携带第三方声明的代码在文件间移动后重新写入它。测试在声明过时或其中的许可证不在 ManimGX 的之中时失败。
- [`LICENSE-LAVAPIPE`](https://github.com/1Cyrvox/ShuJing/blob/main/LICENSE-LAVAPIPE)：Linux wheel 持有的 lavapipe 的声明：Mesa 的，带其构建源码的版权行，以及其持有的、其链接的库和 LLVM 的。手工编写，从 Mesa 的源码：当
  `scripts/release/build_lavapipe.sh` 构建与其描述不同的 Mesa 时测试失败。
- [`LICENSE-DXC`](https://github.com/1Cyrvox/ShuJing/blob/main/LICENSE-DXC)：Windows wheel 携带的固定 DirectX 着色器编译器的声明，包括其源依赖。源归档保留匹配的源闭包。

在 `src/manimgx/` 中，除 Python 外：

- `py.typed`：标记包为有类型，因此类型检查器读其注解。
- [`_engine.pyi`](https://github.com/1Cyrvox/ShuJing/blob/main/src/manimgx/_engine.pyi)：引擎的接口，带类型（见[引擎](engine.md#the-boundary-with-python)）。
- [`cli/present.html`](https://github.com/1Cyrvox/ShuJing/blob/main/src/manimgx/cli/present.html)：在浏览器中呈现影片幻灯片的页面（`manimgx present`）。

#### 重建引擎

uv 以可编辑模式安装 manimgx：对 Python 文件的更改在下次 Python 运行时生效。引擎不同：它是编译的文件（macOS 和 Linux 上 `src/manimgx/` 中的 `_engine.abi3.so`，被 git 忽略），仅在 maturin 构建它后存在。

uv 在其某个 *缓存键* 更改时重建包。`cache-keys` 列出引擎的源码：crate 的 Rust 文件和着色器（`*.wgsl`，编译到其中）、其清单和构建脚本、C 垫片、锁定文件，以及 mitex 的 `lib.typ` 和命令规格。crate 获取的内容仅随其构建脚本更改，后者固定它。
`uv run` 在运行任何内容之前使环境保持最新，因此在编辑 `rust/engine/src/vector.wgsl` 后，下次 `just test` 重建引擎，然后测试它。

构建是 maturin 的发布构建，按 `rust/Cargo.toml` 中的 `[profile.release]` 优化（完全优化、薄链接时优化）：编译较慢，运行较快。引擎构建自的文件中不匹配 `cache-keys` 中任何模式的文件需要自己的条目，否则其更改不被看到。`uv sync --reinstall-package manimgx` 无论更改什么都重建引擎。

## [`fonts/`](https://github.com/1Cyrvox/ShuJing/tree/main/fonts)

字体包，工作区的其他成员：
[`manimgx-fonts/`](https://github.com/1Cyrvox/ShuJing/tree/main/fonts/manimgx-fonts) 和
[`manimgx-fonts-cjk/`](https://github.com/1Cyrvox/ShuJing/tree/main/fonts/manimgx-fonts-cjk)，
每个带其清单、其 README 和其许可证；每个持有的即其用户获得的。

排版所用的 Noto 字体，除 Typst 自己的外，使文本在每台机器上相同：`manimgx-fonts` 中的 Noto Sans 和拉丁字体缺少的脚本字体，`manimgx-fonts-cjk` 中的 Noto Sans CJK，每个在 SIL 开放字体许可证下（`LICENSE`）。它们是数据，40 MB，很少更改：各自的包，由 uv 的后端构建为每个平台一个 wheel，在更改时发布，而非随每次 ManimGX，后者要求其在精确版本。版本是字体从 Noto 取出的日期。`manimgx-fonts-cjk` 在浏览器中不要求，33 MB 对页面下载太多。ManimGX 在安装的任何字体包中找到字体（`importlib.resources`）。

## [`rust/`](https://github.com/1Cyrvox/ShuJing/tree/main/rust)

引擎的 crate，作为一个工作区：[`rust/Cargo.toml`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/Cargo.toml)
列出它们（此处的每个文件夹）、编译它们的构建配置，以及给 mitex ManimGX 自己规格 crate 的补丁；`Cargo.lock` 对 Rust 如 `uv.lock` 对 Python，每个 crate 的精确版本，已提交（`just upgrade` 也移动它）。Cargo 在此处运行，构建到 `rust/target/`。[引擎](engine.md) 说明 crate 做什么：

- `engine/`：引擎，`manimgx._engine`——带播放器，原生在窗口中，以及在 Pyodide 中携带页面播放器；其清单持有其依赖（wgpu、PyO3、Typst、mitex、winit、rustybuzz）和它遵循的 Clippy lint。
- `x264/`、`nasm/`：x264 和 NASM，从其源码构建。
- `ffmpeg/`：FFmpeg 的音频解码器和 libopus，从其源码构建，在一个调用之后。
- `dxc/`：Windows 的已验证 DirectX 着色器编译器二进制和匹配的源闭包。
- `mitex-spec-gen/`：mitex 的 Typst 包，引擎服务给 Typst（带其自己的 `lib.typ`，仅导入转换的 LaTeX 调用的作用域），以及从中制作的命令规格。
- `fetch/`：其他构建脚本获取所用的：源码树，按其文件的 SHA-256 固定（见[引擎](engine.md#others-sources)）。

仓库不持有他人编写的任何内容，除了其许可证文本，crate 为声明保留（`COPYING`、`LICENSE`），如作者发布；检查让它们如此。

## [`browser/`](https://github.com/1Cyrvox/ShuJing/tree/main/browser)

浏览器的 ManimGX，发布到 npm 为 `manimgx`：播放器的元素（`src/player.ts`）和导演的 worker（`src/director.ts`）。`just build-npm` 在将 worker 嵌入一个浏览器模块（`dist/manimgx.js`）之前编译它，TypeScript 7 从实现生成公共声明。包从 PyPI 安装 ManimGX 的浏览器 wheel，在其自己的版本，在 Pyodide 中，用该 wheel 引擎携带的播放器播放。

开发工具固定在 `bun.lock` 中。`just check` 检查 TypeScript 及其格式；`just test-typescript` 运行包的测试，在 `browser/tests/` 中。

## [`docker/`](https://github.com/1Cyrvox/ShuJing/tree/main/docker)

从 PyPI 安装 ManimGX（构建所用版本或最新）到 `python:3.14-slim` 的镜像，带 Vulkan 加载器和 Mesa 驱动：lavapipe 在 CPU 上绘制，给容器的 GPU（AMD 和 Intel 用 `--device /dev/dri`，NVIDIA 用 `--gpus all`）优先使用。其入口点是 `manimgx` 命令，在 `/work` 中运行：

```sh
docker run --rm -v "$PWD:/work" ghcr.io/1Cyrvox/ShuJing:0.1 render scene.py
```

`just build-docker-image <version>` 为本地使用构建该 `published` 目标。发布从其已测试的 wheel 和字体构件构建单独的 `release` 目标，运行时依赖针对 `uv.lock` 认证。它在任何注册表发布之前冒烟测试并保留 OCI 归档；发布复制那些相同的镜像摘要。

## 发布

版本在 `pyproject.toml` 中（`0.1.1`；引擎的 crate 携带相同编号）。ManimGX 遵循 [语义版本控制](https://semver.org)，其 [变更日志](../changelog.md) 遵循 [Keep a Changelog](https://keepachangelog.com)：用户会注意到的变更在"Unreleased"下添加一行（见[文档](documentation.md#the-changelog)）。

发布需要三步：

1. `main` 上的提交在 `pyproject.toml` 中设置新版本，并将变更日志的"Unreleased"行移入其自己的部分 `## X.Y.Z`。
2. `just release`，在该提交，请求确认，标记为 `vX.Y.Z`，并推送标签。
3. 标签启动[发布工作流](github-workflows.md#4-releaseyaml-a-release)。除非标签是 ManimGX 的版本且变更日志有其部分，否则停止；然后运行测试，构建一切，并发布：GitHub 发布，其说明是变更日志的部分（`just release-notes X.Y.Z` 打印），PyPI、npm 和 ghcr.io。PyPI 获得其没有的字体包版本：对字体的更改在其 `pyproject.toml` 和 ManimGX 的要求中设置新版本，随下次 ManimGX 发布。

以 `aN`、`bN` 或 `rcN` 结尾的版本（如 `0.2.0rc1`）是预发布。

## 了解更多

- [uv 文档](https://docs.astral.sh/uv/)：项目、锁定文件、依赖组。
- [maturin 用户指南](https://www.maturin.rs)：混合 Rust 和 Python 项目。
- [cibuildwheel 文档](https://cibuildwheel.pypa.io)：构建和测试 wheel。
- [just 手册](https://just.systems/man/en/)。