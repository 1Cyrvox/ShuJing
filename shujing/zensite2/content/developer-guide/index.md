# 设置

本指南用于开发 ManimGX 本身：它的 Python 包、它的 Rust 引擎、它的
TypeScript 浏览器包、它的测试和这些文档。它解释了项目如何运作以及
如何参与开发。如何提议
变更（issue、拉取请求、AI 的使用）在
[贡献指南](https://github.com/1Cyrvox/ShuJing/blob/main/.github/CONTRIBUTING.md)中。

本页面将一台机器带到一个能够构建、检查、测试并服务
文档的 ManimGX 克隆。

## 前置条件

ManimGX 是一个 Python 包，带有用 Rust 编写的引擎。你需要四个工具；构建和
测试它不需要你系统上的其他任何东西：引擎从源码构建 x264（附带 NASM，即
x264 的 x86-64 代码所用的汇编器）、FFmpeg 的音频解码器和 libopus，其构建
在首次时获取这些源码（使用 `curl` 和 `tar`，macOS、Linux 和
Windows 都自带），测试使用 PyAV 读写视频，PyAV 在其
wheel 中包含 FFmpeg 的库。

- **[`uv`](https://docs.astral.sh/uv/getting-started/installation/)**：项目
  管理器。它安装 Python（3.13 或 3.14）、所有依赖以及 ManimGX 本身，
  并编译其引擎。
- **[`just`](https://just.systems/man/en/packages.html)**：命令运行器。开发
  任务是
  [`justfile`](https://github.com/1Cyrvox/ShuJing/blob/main/justfile) 中的配方。
- **[Rust](https://www.rust-lang.org/tools/install)**，稳定工具链，通过
  `rustup` 安装，附带它链接所需的 C 工具链（`rustup` 会说明是哪个：macOS 上的 Xcode Command Line
  Tools，Debian 或 Ubuntu 上的 `build-essential`，Windows 上的 Visual Studio C++ 构建工具）：它编译
  引擎，以及 x264、FFmpeg 和 libopus 的 C 代码。
- **[`bun`](https://bun.sh)**：它安装浏览器包的锁定工具，打包其
  TypeScript 源码，并运行其测试。它还构建语料库审查面板的
  网页（见[测试](testing.md#the-review-panel)）。

### GPU

引擎使用 [wgpu](https://wgpu.rs) 绘图：在 macOS 上通过 Metal，在
Windows 上通过 Direct3D 12（在没有 GPU 时使用 WARP，在 CPU 上绘图），在 Linux 上通过 Vulkan。它采用
高性能适配器，该适配器必须能混合 float32 渲染目标（视图在一个目标中累加其覆盖）并支持带模板的 float32 深度（`depth32float-stencil8`）。反转 Z
投影需要浮点深度来区分远处的表面。缺少
任一能力的适配器会被拒绝；随后 Linux 会尝试内置的 lavapipe。如果没有合适的适配器，渲染会报告缺少的能力。浏览器需要同样的两个
WebGPU 能力。

在没有 GPU 驱动的 Linux 上，Mesa 的 lavapipe 在 CPU 上绘图。Linux wheel 捆绑了它
（`scripts/release/build_lavapipe.sh` 构建它，引擎自行加载它：见
[引擎](engine.md#drawing)）；从源码构建的引擎，如这里所述，使用
系统的 lavapipe，工作流的 Linux 作业会安装它：

```sh
sudo apt-get install libvulkan1 mesa-vulkan-drivers
```

### Manim Community Edition

集成语料库保留了已审查的 Manim Community Edition 渲染结果用于比较。常规测试在同一主机上比较最新的稳定版本和当前的 ManimGX，不需要 CE；在首次发布之前，它们检查渲染和导出。本地审查影片可以从备份恢复并根据其提交的校验和验证，或用 `just corpus render` 重新生成。更改的像素需要新的审查。用 CE 渲染新增或更改的场景需要其依赖组：`uv sync --group ce`（`just sync` 会再次将其排除）。它对 Cairo 和 Pango 的绑定在没有 wheel 的地方从源码构建（macOS 和 Linux 上的 pycairo，Linux 上的 ManimPango），因此需要这些库：macOS 上 `brew install cairo pkg-config`，Debian 或 Ubuntu 上 `apt-get install libcairo2-dev libpango1.0-dev pkg-config`。

## 设置开发环境

1. 克隆仓库并进入它：

    ```sh
    git clone https://github.com/1Cyrvox/ShuJing.git
    cd manimgx
    ```

2. 创建环境：

    ```sh
    just sync
    ```

    uv 创建 `./.venv`：Python、以可编辑模式安装的 manimgx（附带已编译的引擎）、
    开发工具和文档工具。首次同步会编译引擎
    及其依赖（Typst、wgpu、x264），这需要一些时间。之后，`uv run`
    会在其 Rust 源码、着色器或清单变更时自行重建引擎，
    因此没有单独的构建步骤（见
    [项目管理](project-management.md#rebuilding-the-engine)）。
    Bun 从 `browser/bun.lock` 安装浏览器包的开发工具。

3. 检查它是否工作：

    ```sh
    just check
    just test-typescript
    just test tests/integration/test_time.py
    ```

    `just check` 运行仓库的所有检查（见
    [项目管理](project-management.md#pre-commit-configyaml-and-just-check)）。
    `test_time.py` 中的测试会渲染场景，因此它们使用 GPU。单独运行 `just test` 会运行
    整个测试套件，它会渲染集成语料库的每个案例，耗时
    更长（见[测试](testing.md)）。

4. 在编辑器中选择该环境的解释器。在 Visual Studio Code 中：按
   ++ctrl+shift+p++（macOS 上为 ++cmd+shift+p++），运行 **Python: Select Interpreter**，并
   选择 `./.venv` 中的那个。引擎的 crate 是一个工作空间，
   [`rust/`](https://github.com/1Cyrvox/ShuJing/tree/main/rust)：如果编辑器
   找不到它，将 rust-analyzer 指向 `rust/Cargo.toml`。

## 命令

`just` 列出配方，分为四组。GitHub 工作流运行这些相同的配方，因此
任务在你的机器上和在 CI 中执行方式相同。运行项目工具的配方使用
`uv run --frozen` 运行它们：在环境中，以 `uv.lock` 锁定的版本运行，按原样使用
锁文件。其他任何命令也以同样的方式运行（`uv run --frozen python …`）。

### 开发

- `just sync`：用 `uv.lock` 锁定的所有内容创建 `.venv`，将引擎构建到其中，并
  安装浏览器包的锁定开发工具。
- `just lock`：在 `pyproject.toml` 的依赖变更后更新 `uv.lock`。
- `just upgrade`：将 `uv.lock` 和 `Cargo.lock` 移至清单
  允许的最新版本。
- `just licenses`：在 `Cargo.lock` 变更后写入 wheel 的第三方声明
  （`LICENSE-THIRD-PARTY`），检查
  ManimGX 的 `license` 是否涵盖它。
- `just format`：应用 ruff 的修复并用 ruff 格式化 Python（包括
  Markdown 中的 Python），以及用 Prettier 格式化浏览器包。
- `just format-file <path>`：在一个文件或文件夹中应用 ruff 的修复并用 ruff 格式化。
- `just check`：`.pre-commit-config.yaml` 的所有检查，作用于所有文件。必须通过。
- `just check-typescript`：检查浏览器包的类型和格式。

### 测试

- `just test [args]`：测试套件，并行运行；`args` 传递给 pytest，如
  `just test tests/integration/test_time.py -x`。
- `just test-rust`：Rust 工作空间的核心和本机库测试，不嵌入 Python。
- `just check-rust-web`：编译检查浏览器引擎。
- `just test-rust-web`：引擎的浏览器测试，使用 wasm-bindgen-test-runner 和
  浏览器驱动。
- `just test-typescript`：构建并测试浏览器包，包括其编译的 worker
  和公共声明。
- `just test-coverage [args]`：同上，但测量覆盖率（见
  [测试](testing.md#coverage)）。
- `just combine-coverage <folder>`：将多次运行的覆盖率合并为一份报告，如 CI
  所做。
- `just bench [REF] [args]`：计时基准测试，此检出与 REF 的 ManimGX 对比，未指定时为 main
  （见[测试](testing.md#benchmarks)）。
- `just corpus <command>`：渲染、比较和审查集成语料库。
- `just review`：语料库的审查面板，位于 <http://127.0.0.1:8000>。

### 文档

- `just serve-docs`：文档站点位于 <http://localhost:8000>，随页面变更重新构建。
- `just build-docs`：文档站点，输出到 `docs/site/`，按部署时的形式。
- `just render-docs [args]`：渲染缺失或变更的示例影片。
- `just build-docs-pages`：从已完成的影片构建页面。

见[文档](documentation.md#local-preview)。

### 发布

- `just build-wheel`：本机的 wheel，输出到 `dist/`，在每个支持的 Python 上测试。
- `just build-sdist`：源分发包，输出到 `dist/`。
- `just create-executable`：本机的可执行文件，输出到 `dist/`，从那里的 wheel 构建。
- `just build-docker-image <version>`：已发布到 PyPI 的某个版本的 Docker 镜像。
- `just release-notes <version>`：变更日志中某个版本的段落。
- `just release`：在 `pyproject.toml` 中标记版本并推送标签；发布
  工作流会发布它。

见[项目管理](project-management.md#releases)。

### 手动运行

`cargo clippy`，在 `rust/` 中运行，检查 `rust/engine/Cargo.toml` 为引擎
设置的 lint。它没有配方，也没有工作流运行它。LaTeX 命令规范测试是
`just test-rust` 的一部分；在 `rust/` 中运行 `cargo test --locked -p mitex-spec-gen` 可仅检查
那些测试（见[引擎](engine.md#typesetting)）。