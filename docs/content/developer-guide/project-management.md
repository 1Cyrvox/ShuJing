# 项目管理

## 什么是项目管理？

仓库即包 ManimGX，且持有的不止其代码：

```text
.
├── src/manimgx/             ← 包：场景 API 和命令行
├── rust/                    ← 引擎的 crate：引擎，编译进包作为
│                              manimgx._engine，以及用它从他人源码构建的 crate，
│                              由它们获取
├── tests/                   ← 包的测试和集成语料库
├── fonts/                   ← 文本所用字体的独立包：
│   ├── manimgx-fonts/         Noto 字体
│   └── manimgx-fonts-cjk/     Noto Sans CJK（不在浏览器中）
├── browser/                 ← 浏览器版 ManimGX，发布在 npm 上，附其测试
├── docker/                  ← Docker 镜像
├── docs/                    ← 文档站点：其页面、设置、构建加载的内容
├── examples/                ← 三十个示例影片，每个一个 Python 文件
├── benchmarks/              ← README 中针对 Manim CE、ManimGL 和 Blender 的基准测试：
│                              其场景、运行器和记录的结果
├── scripts/                 ← 编写和构建的内容：发布脚本、文档生成的
│                              页面和图片，以及引擎的 DFG 表
├── skills/                  ← 智能体技能
├── pyproject.toml           ← 包、其工作区（含 fonts/）、工具及其设置
├── uv.lock                  ← 每个 Python 包的确切版本
├── justfile                 ← 开发任务
├── .pre-commit-config.yaml  ← 检查
├── README.md                ← 首页：GitHub 的、PyPI 的和文档的 Welcome
├── AGENTS.md                ← 本指南的命令和规则简述，供编码智能体使用
├── CITATION.cff             ← 如何引用 ManimGX
├── LICENSE                  ← ManimGX 的许可证，MIT 许可证
├── LICENSE-THIRD-PARTY      ← wheel 中他人持有版权的内容
├── LICENSE-LAVAPIPE         ← Linux wheel 捆绑的 lavapipe 的声明
├── LICENSES/                ← 仓库中每个文件所适用的每个许可证的文本
├── REUSE.toml               ← 每个文件的归属及其许可证，在未声明处
└── .github/                 ← 工作流、部署配置、
                               贡献指南、issue 表单和拉取请求模板
```

项目管理是代码之外的一切，即 `src/`、`rust/` 和 `browser/src/` 之外的内容：使代码可安装、在每台机器上相同、且每个人以相同方式检查的内容。仓库的根目录是包；除此之外发布的内容（字体包、浏览器包、Docker 镜像）各有其文件夹。

## 为什么仅有代码不够？

仅代码留下两个问题：用户如何获取它，以及开发者如何在其上工作。

### 分发

用户想要 `pip install manimgx` 和可用的 `manimgx` 命令。ManimGX 比纯 Python 更难发布：其引擎是编译的，因此每个平台需要自己的构建，内含引擎。发布以五种形式发布 ManimGX：

- **Wheel**，每个平台一个：Linux（x86_64 和 arm64）、macOS（arm64，以及 x86_64 在 arm64 上交叉编译）和 Windows（x86_64）。引擎针对 Python 的稳定 ABI 构建，因此一个平台的 wheel 服务于每个支持的 Python，且 x264 内置于其中，因此 wheel 不需要系统提供任何东西。Linux wheel 还捆绑 Mesa 的 lavapipe，以在没有 GPU 驱动时在 CPU 上绘制
  ([`scripts/release/build_lavapipe.sh`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/release/build_lavapipe.sh)
  先在 manylinux 镜像中构建它：约占 wheel 的 24 MB)。
  [cibuildwheel](https://cibuildwheel.pypa.io) 构建每个 wheel 并在每个支持的 Python 上安装它，在那里它必须渲染一个场景
  ([`scripts/release/smoke_test.py`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/release/smoke_test.py))
  才能保留：在 Linux 上，镜像中没有驱动，因此使用捆绑的 lavapipe。其设置是 `pyproject.toml` 中的 `[tool.cibuildwheel]`。
- **源码分发包**，在安装它的机器上构建引擎：这需要 Rust 和 C 编译器，无需其他（引擎的构建获取其从他人取用的源码：参见[他人的源码](engine.md#_12)）。
- **可执行文件**，每个平台一个：一个文件，内含安装了 ManimGX 的 Python，供没有 Python 的机器使用（参见 [`scripts/`](#scripts)）。
- **Docker 镜像**，`ghcr.io/1Cyrvox/ShuJing`（参见 [`docker/`](#docker)）。
- **浏览器包**，npm 上的 `manimgx`：一个文件中的播放器，用浏览器的 wheel 运行场景（参见 [`browser/`](#browser)）。

文本所用的字体是独立的包，`manimgx-fonts` 和 `manimgx-fonts-cjk`：每个平台一个 wheel，在字体更改时发布，而非随每个 ManimGX 发布（参见 [`fonts/`](#fonts)）。

PyPI 获得 wheel、源码分发包和字体包；GitHub 发布获得 wheel、源码分发包、wheel 的完整源码（`manimgx-X.Y.Z-source.tar.xz`：参见[许可证](#_7)）和可执行文件；npm 获得浏览器包；ghcr.io 获得镜像。[发布](#_11) 说明如何制作发布。

### 开发环境

开发者 A 今天安装依赖，测试通过。开发者 B 一个月后安装，获得更新的 Typst 或 numpy，测试失败。对 ManimGX 而言，风险比通常更尖锐：集成语料库逐像素比较当前包和冻结包的帧，因此字形布局或颜色舍入方式的任何更改都会显现。

因此每个人需要相同的 Python、每个包和 crate 的相同版本，以及相同设置下的相同工具，通过一个命令：

```sh
just sync
```

六个月前的错误？检出那个提交并运行 `just sync`：其 Python 包和 Rust crate 恢复原样。系统的库和 Rust 工具链未固定。

本页其余部分描述使此工作生效的文件。

## 根目录中的文件

### [`pyproject.toml`](https://github.com/1Cyrvox/ShuJing/blob/main/pyproject.toml)

包（参见[包](#_9)）、其开发所在的工作区，以及开发它所需的内容。[uv](https://docs.astral.sh/uv/concepts/projects/workspaces/) 将工作区作为一个整体管理：

- `[tool.uv.workspace]`：其其他成员，`fonts/` 中的字体包，每个有自己的 `pyproject.toml`（参见 [`fonts/`](#fonts)）。一个锁文件持有它们全部，一个环境 `.venv` 安装了它们全部。
- `[tool.uv.sources]`：成员在此处的状态。ManimGX 要求其字体包为确切版本；在工作区中，这些是 `fonts/` 中的包，以可编辑方式安装，如同 ManimGX，其引擎由 uv 构建。
- `[dependency-groups]`：开发所需的内容。`dev` 持有工具（ruff、ty、pytest 及其插件、prek）、审查面板的 FastAPI，以及 PyAV，语料库用它写入和读取视频。`docs` 持有 Zensical 和 mkdocstrings。`ce` 持有 Manim Community Edition，它渲染语料库的 Manim 参考（参见[设置](index.md#manim-community-edition)）。每个都与 ManimGX 一起安装。
- `[tool.uv]`：默认安装 `dev` 和 `docs`。
- 工具的设置：`[tool.pytest]`、`[tool.coverage.run]`（参见[测试](testing.md#_16)）、`[tool.mutmut]`、`[tool.fastapi]`，以及保持代码格式和检查其类型的工具的设置，`[tool.ruff]` 和 `[tool.ty]`（见下文）。

### [`uv.lock`](https://github.com/1Cyrvox/ShuJing/blob/main/uv.lock)

项目使用的每个 Python 包的确切版本，直至依赖的依赖。`just sync` 安装恰好这些，而非最新的。

切勿手动编辑：在 `pyproject.toml` 中更改依赖后，运行 `just lock`，并提交两个文件。`just upgrade` 将每个包移动到 `pyproject.toml` 文件允许的最新版本。配方用 `uv run --frozen` 运行其工具，它原样使用锁文件，不检查其与 `pyproject.toml` 文件的一致性。

### [`justfile`](https://github.com/1Cyrvox/ShuJing/blob/main/justfile)

[just](https://just.systems) 运行在文件中定义一次的命令。没有它，每个人输入相同的长命令但选项不同。有了它：

```sh
just test        # pytest，并行，在锁定的环境中
just test-rust   # Rust 核心和原生库，不嵌入 Python
just check       # .pre-commit-config.yaml 的每项检查
just serve-docs  # 渲染文档的示例，编写参考，提供站点服务
```

配方按组分类（开发、测试、文档、发布），配方上方的注释是其在 `just --list` 中的描述。GitHub 工作流运行这些相同的配方，因此任务在开发者的机器上与在 CI 中相同。[设置](index.md#_2) 列出每个配方。

### ruff

[ruff](https://docs.astral.sh/ruff/) 使代码格式在各处保持一致：

- 它以稳定的风格和 88 列格式化：Python、docstring 中的示例，以及 Markdown 中的 Python。它不拆分长字符串。
- 它进行 lint：查找可能的错误、未排序的导入和过时的惯用法。`pyproject.toml` 中的 `[tool.ruff]` 选择其规则并给出每个忽略规则的原因；包在 `__init__.py` 中的重新导出可以用 `*` 导入并导入它不使用的名称。

`just format` 运行 ruff 的自动修复，然后是其格式化器。`just check` 也运行两者（见下文）。Docstring 有自己的格式，即 Google 风格，因为 API 参考从它们生成：参见[文档](documentation.md#docstring)。

### ty

[ty](https://docs.astral.sh/ty/) 检查类型。ManimGX 全面类型化，ty 对其不报告任何内容：`just check` 必须无错误通过，更改保持如此。遵循两条规则：

- **公共签名中无 `Any`。** 关键字选项是 `TypedDict`，以 `**kwargs: Unpack[…]` 接收，而非 `**kwargs: Any`，因此拼写错误的关键字使检查失败，在 ManimGX 和用户场景中皆然。[`Style`][manimgx.drawing.paint.Style]，位于
  [`drawing/paint.py`](https://github.com/1Cyrvox/ShuJing/blob/main/src/manimgx/drawing/paint.py)，
  是样式关键字；[`Polygon`][manimgx.Polygon] 接收 `**kwargs: Unpack[Style]`。
- **仅有效的抑制，采用 ty 的形式。** ty 遵循 `# ty: ignore[rule]` 和裸 `# type: ignore`，而非 `# type: ignore[code]`。不抑制任何内容的抑制是错误（`[tool.ty]` 使其成为错误），因此被修复变为无用的抑制使检查失败。ruff 的格式化器不将行尾抑制注释计入行宽，但它会拆分没有抑制的过长行并将注释移至最后一行，因此在 `just format` 后运行 `just check`。

`[tool.ty]` 是 ty 检查内容的唯一列表：包、文档的脚本、语料库的工具和审查服务器，以及它命名的测试。运行 ty 的钩子不传递文件给它，因此 `just check` 检查该列表。它还将 `svgelements` 读取为无类型（ty 无法读取其源码的编码）。

用户场景被更严格约束：每个语料库用例用每条规则进行类型检查，且 ManimGX 给它的值不得为 `Any`（参见[测试](testing.md#_12)）。

### [`.pre-commit-config.yaml`](https://github.com/1Cyrvox/ShuJing/blob/main/.pre-commit-config.yaml) 和 `just check`

仓库拥有的每项检查，作为钩子：

- 文件检查：无合并冲突标记、有效的 TOML 和 YAML、最终换行、无尾部空白；
- [check-jsonschema](https://check-jsonschema.readthedocs.io)，它根据 [Citation File Format](https://citation-file-format.github.io) 的模式检查 `CITATION.cff`；
- [zizmor](https://docs.zizmor.sh)，它在 GitHub 工作流中查找安全问题；
- ruff 和 ty，从环境运行（`uv run --frozen`），因此它们是 `uv.lock` 固定的版本；
- 浏览器包的 TypeScript 7 和 Prettier，用其 `bun.lock` 固定的版本运行；
- [reuse](https://reuse.software)，同样来自环境，它检查每个文件的许可证和版权是否已知（参见[许可证](#_7)）。

[prek](https://prek.j178.dev)，pre-commit 的快速实现，运行它们：`just check` 即 `prek run --all-files --show-diff-on-failure`。更改文件的钩子（ruff 修复或格式化它、添加最终换行）使检查失败，显示更改，并保留更改的文件；如果没有其他问题，下一次 `just check` 通过。

仓库不安装 git 钩子：检查在你运行时运行，并在每次推送到 `main` 和每个拉取请求时，在 Test 工作流中运行（参见 [GitHub 工作流](github-workflows.md#1-testyaml)）。

### 许可证

ManimGX 采用 MIT 许可证，位于
[`LICENSE`](https://github.com/1Cyrvox/ShuJing/blob/main/LICENSE)：GitHub、PyPI 和 npm 显示它。某些文件是他人的：从 Manim CE 移植的模块、改编自 [Filament](https://github.com/google/filament) 的引擎 3D 光照、Noto 字体、来自 CE 文档的语料库场景、由 mitex 的 Typst 包制作的命令规范、少数文档和图像。仓库按照 [REUSE](https://reuse.software) 规范说明每个文件的归属及其许可证：

- 含他人代码的文件在其首行说明：每个版权持有者一个 `SPDX-FileCopyrightText` 行（ManimGX 的 `2026 Academa, Inc.` 也在其中）和一个 `SPDX-License-Identifier` 行，如同从 Manim CE 移植的模块所做；
- [`REUSE.toml`](https://github.com/1Cyrvox/ShuJing/blob/main/REUSE.toml) 为其余文件说明：ManimGX 自有的文件，在一条注释中；字体、语料库、数据和图像；
- [`LICENSES/`](https://github.com/1Cyrvox/ShuJing/tree/main/LICENSES) 持有每个许可证的文本，一次，以其 SPDX 标识符命名。

引擎的 crate 为其获取的源码保留的许可证文本（`COPYING`、`LICENSE`；参见[他人的源码](engine.md#_12)）是其项目的，按发布原样：REUSE 保留这些名称的文件。`reuse lint`，`just check` 的一个钩子，在文件许可证或版权未知，或许可证无文本时失败。ManimGX 的新文件无需任何内容；从他人带来的代码需要其行；数据或图像需要注释。wheel 中他人持有版权的内容附带其声明（参见[包](#_9)）。

wheel 持有 FFmpeg 的音频解码器，采用 LGPL-2.1-or-later，除浏览器的每个 wheel 持有 x264，采用 GPL-2.0-or-later，而 crate 单独采用 Apache-2.0（Typst、mitex），只有 GPL 的第三版本纳入它们：这样的 wheel 整体采用 GPL-3.0-or-later。其第 6 节（以及 LGPL 的，它引用该节）要求获得 wheel 的人能够获取其完整源码，从 wheel 所在处或 wheel 指向的地方，只要 wheel 被提供：全部内容，包括 crate，而非他人发布它们的链接，链接可能失效。每个 GitHub 发布携带它，`manimgx-X.Y.Z-source.tar.xz`，附带源码和构建配方（参见[他人的源码](engine.md#_12)）；wheel 的声明、README（PyPI 的页面）和发布的说明指向它，README 和说明陈述 FFmpeg 要求每个提供它的页面所陈述的内容。只要 PyPI 提供 wheel，发布就不会被删除。

### [`scripts/`](https://github.com/1Cyrvox/ShuJing/tree/main/scripts)

编写和构建的内容，每个制作的东西一个文件夹：

- [`release/`](https://github.com/1Cyrvox/ShuJing/tree/main/scripts/release)：发布的脚本，由配方和 cibuildwheel 运行。
  - [`create_executable.py`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/release/create_executable.py)
    （`just create-executable`）从 `dist/` 中的 wheel 制作本机的可执行文件：一个精确的、SHA-256 验证的 Python Build Standalone 归档，内含 wheel、字体包和 `uv.lock` 固定的依赖，由 [PyApp](https://ofek.dev/pyapp) 打包成一个文件。该文件首次运行解包其持有的 Python；之后每次运行在那里运行 `manimgx`，无需网络和机器上的 Python，`manimgx self` 管理它（`self pip install` 添加场景导入的包）。脚本在运行其制作的内容一次后写入 `dist/manimgx-<os>-<arch>.tar.gz`（Windows 上为 `.zip`）。
  - [`smoke_test.py`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/release/smoke_test.py)
    用安装的 ManimGX 渲染一个场景：wheel 或可执行文件在保留前通过的检查。它解码生成的 PCM 和参考 Opus 夹具，导出其音轨并重新打开 MP4 的 AAC 声音。Pyodide 记录同一场景并检查片段的版本、帧数、声音和成功结束，及其内嵌播放器。
  - [`build_lavapipe.sh`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/release/build_lavapipe.sh)
    在 manylinux 镜像中（cibuildwheel 的 `before-all`）为 Linux wheel 构建 Mesa 的 lavapipe：从源码构建 Mesa、glslang 和 LLVM，对照固定的哈希检查。LLVM 携带 `scripts/release/llvm/` 中的寄存器类修正。驱动仅导出 Vulkan 加载器调用的内容。脚本写入 `src/manimgx/lavapipe/libvulkan_lvp.so`，wheel 随后将其纳入。其检查过的归档通过引擎的源码存储。修复后，`linux_sources.py` 使用 auditwheel 的 SBOM 和 RPM 元数据保留捆绑库的确切发行版源码包。这些是源码和出处；系统构建工具不是固定的密封环境。
  - [`licenses.py`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/release/licenses.py)
    （`just licenses`）编写 wheel 的第三方声明（参见[包](#_9)）。
- [`docs/`](https://github.com/1Cyrvox/ShuJing/tree/main/scripts/docs)：文档生成的页面，由 `just build-docs` 在站点构建前写入：Gallery 和命令行参考（参见[文档](documentation.md)）。
- [`showcase/`](https://github.com/1Cyrvox/ShuJing/tree/main/scripts/showcase)：README 的图片，手工制作并提交：徽标（横幅、页眉的、网站图标）和示例影片墙。
- [`engine/`](https://github.com/1Cyrvox/ShuJing/tree/main/scripts/engine)：引擎编译所用的内容，手工制作：[`dfg_table.py`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/engine/dfg_table.py) 写入 `rust/engine/src/dfg.bin`，即光照表面的镜面反射所读取的分割求和表，仅在光照更改时再次运行。

### [`benchmarks/`](https://github.com/1Cyrvox/ShuJing/tree/main/benchmarks)

README 的基准测试：ManimGX 在五个场景上针对 Manim CE、ManimGL 和 Blender，每个用每个引擎自己的 API 编写（`scenes/`）。其 [README](https://github.com/1Cyrvox/ShuJing/blob/main/benchmarks/README.md) 是方法和结果，README 数字的来源。`run.py` 将引擎计时到 `results.json`；`chart.py` 从中绘制 README 的图表，`quality.py` 制作 README 的比较图像。`tests/benchmarks/test_comparison.py` 检查两个 README 给出的数字是记录的数字。

### 文档和覆盖率的托管

[`docs/zensical.toml`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/zensical.toml) 持有文档站点的设置（参见[文档](documentation.md)）；站点构建到 `docs/site/`。托管与工作流一起配置，在 [`.github/deploy/`](https://github.com/1Cyrvox/ShuJing/tree/main/.github/deploy) 中：`docs.jsonc` 提供文档站点服务，`coverage.jsonc` 提供测试覆盖率报告服务（参见[测试](testing.md#_16)）。

### [`AGENTS.md`](https://github.com/1Cyrvox/ShuJing/blob/main/AGENTS.md) 和贡献指南

`AGENTS.md` 是本指南的命令、规则和布局的简述，供编码智能体使用；[AI 工作流](github-workflows.md#7-aiyamlissue-pull-request-claude) 的助手被指示遵循它。[贡献指南](https://github.com/1Cyrvox/ShuJing/blob/main/.github/CONTRIBUTING.md) 说明如何提议更改（先 issue，再拉取请求）并链接到此处了解项目如何运作。当命令或规则更改时，`AGENTS.md` 随本指南更改。

### [`.gitignore`](https://github.com/1Cyrvox/ShuJing/blob/main/.gitignore)

制作而非编写的内容不进入 git：环境、编译的引擎、`rust/target/`、`dist/`、构建的站点、文档渲染的影片和生成的参考、覆盖率数据和报告，以及渲染输出（`media/`、`*.mp4`）。语料库的参考视频是 `.mkv` 文件，被 Git 忽略；其 SHA-256 附属文件被提交。

## 包

仓库的根目录是包，定义在
[`pyproject.toml`](https://github.com/1Cyrvox/ShuJing/blob/main/pyproject.toml) 中，采用[标准格式](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)：

- `[project]`：名称、版本、支持的 Python（3.13 和 3.14）、许可证，以及 ManimGX 运行时所需的包。
  [理解 ManimGX](understanding-manimgx.md#_8) 说明每个的用途。
  `license` 将分发包持有的每个许可证命名为一个 SPDX 表达式：
  ManimGX 自有的 MIT、编译进引擎的 crate 的许可证（其中包括 x264 的 GPL-2.0-or-later）、Typst 的字体和数据的许可证，以及 Linux wheel 捆绑的 lavapipe 的许可证。
  `license-files` 将 `LICENSE` 和旁边的三个声明放入 wheel 的元数据。
  其 README 是仓库的 `README.md`。
- `[project.scripts]`：使 `manimgx` 成为命令，运行 `manimgx.cli:main`。
- `[build-system]` 和 `[tool.maturin]`：[maturin](https://www.maturin.rs) 构建包。它将 `rust/engine/` 中的 crate 编译为模块 `manimgx._engine` 并将其放在 `src/` 的 Python 源码旁边。
- `[tool.uv]`：`cache-keys` 说明引擎何时重建（见下文）。
- `[tool.cibuildwheel]`：wheel 如何构建和测试（[分发](#_4)）。wheel 用其发布时的字体测试，即此仓库的字体，PyPI 可能还没有：它们在 wheel 之前安装。

在其旁边，根目录中，`license-files` 除 `LICENSE` 外命名的声明：

- [`LICENSE-THIRD-PARTY`](https://github.com/1Cyrvox/ShuJing/blob/main/LICENSE-THIRD-PARTY)：
  wheel 中他人持有版权的内容，附带其许可证和声明：包和引擎中命名他人的文件（从 Manim CE 移植的模块、引擎的 3D 光照），附其版权行和来自 `LICENSES/` 的许可证文本；以及编译进引擎的每个 crate，在 wheel 持有的每个构建中（每个平台的扩展、Pyodide 的、页面的播放器），附其附带的许可证和声明文件，工作区的 crate 附其获取内容的声明（x264 的、FFmpeg 的、libopus 的、mitex 的）。`just licenses` 在 `Cargo.lock` 更改后（`just upgrade` 亦然）或携带第三方声明的代码在文件间移动后重新写入它。声明过期或其中的许可证不在 ManimGX 的之中时测试失败。
- [`LICENSE-LAVAPIPE`](https://github.com/1Cyrvox/ShuJing/blob/main/LICENSE-LAVAPIPE)：
  Linux wheel 持有的 lavapipe 的声明：Mesa 的，附其构建源码的版权行，以及其持有内容、链接库和 LLVM 的声明。它从 Mesa 的源码手工编写：当 `scripts/release/build_lavapipe.sh` 构建的 Mesa 与其描述的不同时测试失败。
- [`LICENSE-DXC`](https://github.com/1Cyrvox/ShuJing/blob/main/LICENSE-DXC)：
  Windows wheel 携带的固定 DirectX Shader Compiler 的声明，包括其源码依赖。源码归档保留匹配的源码闭包。

在 `src/manimgx/` 中，除 Python 外：

- `py.typed`：将包标记为已类型化，以便类型检查器读取其注解。
- [`_engine.pyi`](https://github.com/1Cyrvox/ShuJing/blob/main/src/manimgx/_engine.pyi)：
  引擎的接口，已类型化（参见[引擎](engine.md#python)）。
- [`cli/present.html`](https://github.com/1Cyrvox/ShuJing/blob/main/src/manimgx/cli/present.html)：
  在浏览器中展示影片幻灯片的页面（`manimgx present`）。

#### 重建引擎

uv 以可编辑模式安装 manimgx：对 Python 文件的更改在下次 Python 运行时生效。引擎不同：它是一个编译文件（macOS 和 Linux 上 `src/manimgx/` 中的 `_engine.abi3.so`，被 git 忽略），只有 maturin 构建后才存在。

uv 在某个*缓存键*更改时重建包。`cache-keys` 列出引擎的源码：crate 的 Rust 文件和着色器（`*.wgsl`，编译进其中）、其清单和构建脚本、C 垫片、锁文件，以及 mitex 的 `lib.typ` 和命令规范。crate 获取的内容仅随其构建脚本更改，构建脚本固定它。
`uv run` 在运行任何内容前将环境更新到最新，因此在编辑 `rust/engine/src/vector.wgsl` 后，下次 `just test` 重建引擎，然后测试它。

构建是 maturin 的发布构建，按 `rust/Cargo.toml` 中 `[profile.release]` 的说明优化（完全优化、薄链接时优化）：编译较慢，运行较快。引擎构建来源中 `cache-keys` 无模式匹配的文件需要自己的条目，否则其更改不被察觉。`uv sync --reinstall-package manimgx` 无论更改什么都重建引擎。

## [`fonts/`](https://github.com/1Cyrvox/ShuJing/tree/main/fonts)

字体包，工作区的其他成员：
[`manimgx-fonts/`](https://github.com/1Cyrvox/ShuJing/tree/main/fonts/manimgx-fonts) 和
[`manimgx-fonts-cjk/`](https://github.com/1Cyrvox/ShuJing/tree/main/fonts/manimgx-fonts-cjk)，
每个有自己的清单、README 和许可证；每个持有的内容即其用户获得的。

文本所用的 Noto 字体，除 Typst 自有的外，使文本在每台机器上相同：`manimgx-fonts` 中的 Noto Sans 和拉丁字体缺失的脚本字体，`manimgx-fonts-cjk` 中的 Noto Sans CJK，每个采用 SIL Open Font License（`LICENSE`）。它们是数据，40 MB，很少更改：独立的包，由 uv 的后端构建为每个平台一个 wheel，在更改时发布，而非随每个 ManimGX 发布，ManimGX 要求其确切版本。版本是字体从 Noto 取出的日期。`manimgx-fonts-cjk` 在浏览器中不是必需的，33 MB 对页面下载来说太多。ManimGX 在已安装的字体包中查找字体（`importlib.resources`）。

## [`rust/`](https://github.com/1Cyrvox/ShuJing/tree/main/rust)

引擎的 crate，作为一个工作区：[`rust/Cargo.toml`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/Cargo.toml) 列出它们（此处的每个文件夹）、其编译的构建配置，以及给 mitex ManimGX 自己的规范 crate 的补丁；`Cargo.lock` 对 Rust 如同 `uv.lock` 对 Python，每个 crate 的确切版本，已提交（`just upgrade` 也移动它）。Cargo 在此处运行，构建到 `rust/target/`。[引擎](engine.md) 说明 crate 的作用：

- `engine/`：引擎，`manimgx._engine`——附播放器，原生在窗口中，在 Pyodide 中携带页面播放器；其清单持有其依赖（wgpu、PyO3、Typst、mitex、winit、rustybuzz）及其遵循的 Clippy lint。
- `x264/`、`nasm/`：x264 和 NASM，从其源码构建。
- `ffmpeg/`：FFmpeg 的音频解码器和 libopus，从其源码构建，在一次调用之后。
- `dxc/`：验证的 DirectX Shader Compiler 二进制和 Windows 的匹配源码闭包。
- `mitex-spec-gen/`：mitex 的 Typst 包，引擎将其提供给 Typst（附其自己的 `lib.typ`，仅导入转换的 LaTeX 调用的作用域），以及从中制作的命令规范。
- `fetch/`：他人构建脚本获取所用的内容：源码树，由其文件的 SHA-256 固定（参见[引擎](engine.md#_12)）。

仓库不持有他人编写的内容，但其许可证文本，crate 为声明保留它们（`COPYING`、`LICENSE`），按其作者发布原样；检查保留它们不动。

## [`browser/`](https://github.com/1Cyrvox/ShuJing/tree/main/browser)

浏览器版 ManimGX，以 `manimgx` 发布到 npm：播放器元素（`src/player.ts`）和导演 worker（`src/director.ts`）。`just build-npm` 在将其嵌入一个浏览器模块（`dist/manimgx.js`）前编译 worker，TypeScript 7 从实现生成公共声明。包从 PyPI 安装 ManimGX 的浏览器 wheel，以其自己的版本，在 Pyodide 中，用该 wheel 引擎携带的播放器播放。

开发工具固定在 `bun.lock` 中。`just check` 检查 TypeScript 及其格式；`just test-typescript` 运行包的测试，在 `browser/tests/` 中。

## [`docker/`](https://github.com/1Cyrvox/ShuJing/tree/main/docker)

镜像的 `Dockerfile`，将 ManimGX 从 PyPI 安装（构建时使用的版本或最新版本）到 `python:3.14-slim` 中，附 Vulkan 加载器和 Mesa 驱动：lavapipe 在 CPU 上绘制，而给予容器的 GPU（AMD 和 Intel 用 `--device /dev/dri`，NVIDIA 用 `--gpus all`）被替代使用。其入口点是 `manimgx` 命令，在 `/work` 中运行：

```sh
docker run --rm -v "$PWD:/work" ghcr.io/1Cyrvox/ShuJing:0.1 render scene.py
```

`just build-docker-image <version>` 为本地使用构建该 `published` 目标。发布从其已测试的 wheel 和字体构件构建独立的 `release` 目标，运行时依赖根据 `uv.lock` 认证。它在任何注册发布前进行冒烟测试并保留 OCI 归档；发布复制相同的镜像摘要。

## 发布

版本在 `pyproject.toml` 中（`0.1.1`；引擎的 crate 携带相同编号）。ManimGX 遵循 [语义化版本](https://semver.org)，其[更新日志](../changelog.md) 遵循 [Keep a Changelog](https://keepachangelog.com)：用户会注意到的更改在"Unreleased"下添加一行（参见[文档](documentation.md#_9)）。

发布需要三步：

1. `main` 上的提交在 `pyproject.toml` 中设置新版本，并将更新日志的"Unreleased"行移入其自己的章节 `## X.Y.Z`。
2. `just release`，在该提交处，请求确认，将其标记为 `vX.Y.Z`，并推送标签。
3. 标签启动 [Release 工作流](github-workflows.md#4-releaseyaml)。除非标签是 ManimGX 的版本且更新日志有对应章节，否则它停止；然后运行测试、构建一切并发布：GitHub 发布，其说明是更新日志的章节（`just release-notes X.Y.Z` 打印它们），PyPI、npm 和 ghcr.io。PyPI 获得其尚无的字体包版本：对字体的更改在其 `pyproject.toml` 和 ManimGX 的要求中设置新版本，并随下一个 ManimGX 发布。

以 `aN`、`bN` 或 `rcN` 结尾的版本（如 `0.2.0rc1`）是预发布。

## 了解更多

- [uv 的文档](https://docs.astral.sh/uv/)：项目、锁文件、依赖组。
- [maturin 的用户指南](https://www.maturin.rs)：混合 Rust 和 Python 项目。
- [cibuildwheel 的文档](https://cibuildwheel.pypa.io)：构建和测试 wheel。
- [just 的手册](https://just.systems/man/en/)。
