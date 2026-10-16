# 环境搭建

本指南用于开发 ManimGX 本身：其 Python 包、Rust 引擎、TypeScript 浏览器包、测试以及本文档。它说明了项目的工作方式以及如何参与开发。如何提出
变更（issue、pull request、AI 的使用）请见
[贡献指南](https://github.com/1Cyrvox/ShuJing/blob/main/.github/CONTRIBUTING.md)。

本页面将引导一台机器完成 ManimGX 的克隆，使其能够构建、检查、测试并服务
文档。

## 前置条件

ManimGX 是一个 Python 包，其引擎用 Rust 编写。你需要四个工具；构建和
测试它不需要系统提供其他任何东西：引擎从源码构建 x264（包含 NASM，即
x264 的 x86-64 代码所用的汇编器）、FFmpeg 的音频解码器和 libopus，其构建过程会在首次运行时获取这些源码（使用 `curl` 和 `tar`，macOS、Linux 和
Windows 均自带），而测试使用 PyAV 读写视频，PyAV 在其 wheel 中自带 FFmpeg 的库。

- **[`uv`](https://docs.astral.sh/uv/getting-started/installation/)**：项目
  管理器。它安装 Python（3.13 或 3.14）、所有依赖项以及 ManimGX 本身，
  并编译其引擎。
- **[`just`](https://just.systems/man/en/packages.html)**：命令运行器。开发任务是
  [`justfile`](https://github.com/1Cyrvox/ShuJing/blob/main/justfile) 中的配方。
- **[Rust](https://www.rust-lang.org/tools/install)**，稳定工具链，通过
  `rustup` 安装，连同其链接所需的 C 工具链（`rustup` 会说明具体需要哪个：macOS 上是 Xcode Command Line
  Tools，Debian 或 Ubuntu 上是 `build-essential`，Windows 上是 Visual Studio 的 C++ 构建工具）：它编译引擎以及 x264、FFmpeg 和 libopus 的 C 代码。
- **[`bun`](https://bun.sh)**：它安装浏览器包的锁定工具，打包其
  TypeScript 源码，并运行其测试。它还构建语料库评审面板的网页（见
  [测试](testing.md#_15)）。

### GPU

引擎使用 [wgpu](https://wgpu.rs) 绘图：在 macOS 上通过 Metal，在
Windows 上通过 Direct3D 12（在没有 GPU 时使用 WARP，在 CPU 上运行），在 Linux 上通过 Vulkan。它选用
高性能适配器，该适配器必须能混合 float32 渲染目标（视图在其中累加其覆盖范围）并支持带模板的 float32 深度（`depth32float-stencil8`）。反转 Z
投影需要浮点深度来区分远处的表面。缺少任一能力的适配器会被拒绝；Linux 随后会尝试使用内置的 lavapipe。如果没有合适的适配器，渲染时会报告缺少的能力。浏览器需要同样的两个
WebGPU 能力。

在没有 GPU 驱动程序的 Linux 上，Mesa 的 lavapipe 在 CPU 上绘图。Linux wheel 内置了它
（`scripts/release/build_lavapipe.sh` 负责构建，引擎会自行加载：见
[引擎](engine.md#_4)）；而从源码构建的引擎（如本文所述）则使用
系统的 lavapipe，工作流的 Linux 作业会安装它：

```sh
sudo apt-get install libvulkan1 mesa-vulkan-drivers
```

### Manim Community Edition

集成语料库保留了经过评审的 Manim Community Edition 渲染结果用于比较。常规测试在同一主机上比较最新的稳定发行版和当前的 ManimGX，不需要 CE；在首次发布之前，它们会检查渲染和导出。本地评审影片可以从备份中恢复并根据其已提交的校验和进行验证，也可以用 `just corpus render` 重新生成。像素发生变化需要重新评审。用 CE 渲染新的或已变更的场景需要其依赖组：`uv sync --group ce`（`just sync` 会再次将其排除）。它与 Cairo 和 Pango 的绑定在没有 wheel 的平台上会从源码构建（macOS 和 Linux 上的 pycairo，Linux 上的 ManimPango），因此需要这些库：macOS 上用 `brew install cairo pkg-config`，Debian 或 Ubuntu 上用 `apt-get install libcairo2-dev libpango1.0-dev pkg-config`。

## 搭建开发环境

1. 克隆仓库并进入其中：

    ```sh
    git clone https://github.com/1Cyrvox/ShuJing.git
    cd manimgx
    ```

2. 创建环境：

    ```sh
    just sync
    ```

    uv 会创建 `./.venv`：包含 Python、以可编辑模式安装的 manimgx（其引擎已编译）、
    开发工具和文档工具。首次同步会编译引擎
    及其依赖项（Typst、wgpu、x264），这需要一些时间。此后，每当其 Rust 源码、着色器或清单发生变化时，`uv run`
    都会自行重建引擎，因此没有单独的构建步骤（见
    [项目管理](project-management.md#_10)）。
    Bun 从 `browser/bun.lock` 安装浏览器包的开发工具。

3. 检查是否正常工作：

    ```sh
    just check
    just test-typescript
    just test tests/integration/test_time.py
    ```

    `just check` 运行仓库中的所有检查（见
    [项目管理](project-management.md#pre-commit-configyaml-just-check)）。
    `test_time.py` 中的测试会渲染场景，因此会使用 GPU。单独运行 `just test` 会
    运行整个测试套件，它会渲染集成语料库的每个案例，耗时
    更长（见 [测试](testing.md)）。

4. 在编辑器中选择该环境的解释器。在 Visual Studio Code 中：按
   ++ctrl+shift+p++（macOS 上为 ++cmd+shift+p++），运行 **Python: Select Interpreter**，并
   选择 `./.venv` 中的解释器。引擎的 crate 是一个工作区，
   [`rust/`](https://github.com/1Cyrvox/ShuJing/tree/main/rust)：如果编辑器找不到，请将 rust-analyzer 指向 `rust/Cargo.toml`。

## 命令

`just` 列出配方，分为四组。GitHub 工作流运行这些相同的配方，因此
任务在你的机器上和在 CI 中的执行方式相同。运行项目工具的配方会
使用 `uv run --frozen` 来运行它们：在环境中，以 `uv.lock` 锁定的版本运行，保持
lockfile 原样。其他命令也以同样方式运行（`uv run --frozen python …`）。

### 开发

- `just sync`：创建 `.venv`，包含 `uv.lock` 锁定的所有内容，将引擎构建到其中，并
  安装浏览器包锁定的开发工具。
- `just lock`：在 `pyproject.toml` 的依赖项变更后更新 `uv.lock`。
- `just upgrade`：将 `uv.lock` 和 `Cargo.lock` 移动到清单允许的
  最新版本。
- `just licenses`：在 `Cargo.lock` 变更后写入 wheel 的第三方声明
  （`LICENSE-THIRD-PARTY`），检查
  ManimGX 的 `license` 是否涵盖它。
- `just format`：应用 ruff 的修复并用 ruff 格式化 Python（包括 Markdown 中的
  Python），以及用 Prettier 格式化浏览器包。
- `just format-file <path>`：在单个文件或文件夹中应用 ruff 的修复并用 ruff 格式化。
- `just check`：对每个文件执行 `.pre-commit-config.yaml` 中的所有检查。必须通过。
- `just check-typescript`：检查浏览器包的类型和格式。

### 测试

- `just test [args]`：并行运行测试套件；`args` 传递给 pytest，例如
  `just test tests/integration/test_time.py -x`。
- `just test-rust`：Rust 工作区的核心和原生库测试，不嵌入 Python。
- `just check-rust-web`：编译检查浏览器引擎。
- `just test-rust-web`：引擎的浏览器测试，使用 wasm-bindgen-test-runner 和
  浏览器驱动。
- `just test-typescript`：构建并测试浏览器包，包括其编译后的 worker
  和公开声明。
- `just test-coverage [args]`：同上，但会测量覆盖率（见
  [测试](testing.md#_16)）。
- `just combine-coverage <folder>`：将多次运行的覆盖率合并为一份报告，如同 CI
  所做的那样。
- `just bench [REF] [args]`：计时基准测试，将当前检出版本与 REF 的 ManimGX 进行比较，未指定时默认为 main
  （见 [测试](testing.md#_17)）。
- `just corpus <command>`：渲染、比较和评审集成语料库。
- `just review`：语料库的评审面板，地址为 <http://127.0.0.1:8000>。

### 文档

- `just serve-docs`：文档站点位于 <http://localhost:8000>，随页面变更而重建。
- `just build-docs`：将文档站点构建到 `docs/site/`，即部署时的形态。
- `just render-docs [args]`：渲染缺失或已变更的示例影片。
- `just build-docs-pages`：从已完成的影片构建页面。

见 [文档](documentation.md#_10)。

### 发布

- `just build-wheel`：本机的 wheel，输出到 `dist/`，在每个受支持的 Python 上测试。
- `just build-sdist`：源码发行版，输出到 `dist/`。
- `just create-executable`：本机的可执行文件，输出到 `dist/`，由其中的 wheel 生成。
- `just build-docker-image <version>`：基于 PyPI 上发布的某个版本构建 Docker 镜像。
- `just release-notes <version>`：变更日志中某个版本的章节。
- `just release`：在 `pyproject.toml` 中为版本打标签并推送标签；Release
  工作流会将其发布。

见 [项目管理](project-management.md#_11)。

### 手动操作

在 `rust/` 中运行的 `cargo clippy` 会检查 `rust/engine/Cargo.toml` 为引擎设置的 lint。它没有配方，也没有工作流运行它。LaTeX 命令规格测试是
`just test-rust` 的一部分；在 `rust/` 中运行 `cargo test --locked -p mitex-spec-gen` 可以仅检查这些
测试（见 [引擎](engine.md#_9)）。
