# GitHub 工作流

## 问题

有些任务必须每次以相同方式运行：

- **每次变更**，推送到 `main` 或在 pull request 中提出：运行检查，以及 ManimGX 支持的每个系统和 Python 上的测试；与之前的代码计时；构建文档；发布测试的覆盖率和文档预览。
- **每次发布：** 测试；构建 wheel、源码分发、字体包和可执行文件；将它们发布到 GitHub 和 PyPI，浏览器包到 npm，Docker 镜像到 ghcr.io。
- **每个 issue 和 pull request：** 对新来者 issue 的首次回复、首次审查，以及维护者可以请求的助手。
- **当维护者请求更新时：** 审查和更新固定的 action 和依赖。

手动完成时，步骤会被遗忘，每次运行都耗费某人的时间。

## 什么是 GitHub Actions？

[GitHub Actions](https://docs.github.com/en/actions) 在仓库中发生某些事情时在 GitHub 的服务器上运行自动化。工作流是 `.github/workflows/` 中的文件，说明：

1. **何时运行：** 推送到 `main`、pull request、标签、评论、GitHub 界面中的点击。
2. **做什么：** 作业，每个是步骤列表（命令或已发布的 action）。
3. **在哪里运行：** 在全新的虚拟机上：Ubuntu、macOS 或 Windows。

构建或测试的作业如你在新机器上所做开始：检出仓库，安装 `just` 和 `uv`（在 Linux 上还有 Mesa 的 lavapipe 用于渲染时绘制），并运行 `just` 配方（见[搭建](index.md)）。工作流运行 justfile 的配方，因此任务在 CI 中与在你的机器上相同。

## ManimGX 的工作流

七个常规的构建、发布和协作工作流在
[`.github/workflows/`](https://github.com/1Cyrvox/ShuJing/tree/main/.github/workflows) 中。

### 1. [`test.yaml`](https://github.com/1Cyrvox/ShuJing/blob/main/.github/workflows/test.yaml)：检查和测试

**何时运行：**

- 每次推送到 `main`。
- 每个 pull request。
- 手动，从 GitHub 界面。
- 当发布工作流调用它时。

**做什么**，在六个作业定义中：

1. **运行 pre-commit 检查**，在 Ubuntu 上：安装锁定的工具而不编译项目，然后运行 `just check`，禁用自动环境同步。
2. **测试浏览器包**，在 Ubuntu 上：检查 Rust 浏览器特性，用 Chrome 运行其浏览器测试，然后针对编译的 worker、播放器和公共声明运行 `just test-typescript`。
3. **构建和链接**，在 Linux、macOS 和 Windows 上各一次：检查源码获取和链接的编解码器，构建一个稳定 ABI wheel，并运行 `just test-rust`。Linux 为渲染器测试安装 lavapipe。每个成功的作业保留其 wheel。
4. **测试**，六次：在该 OS 的同一 wheel 上安装 Python 3.13 和 3.14，检查安装的产品，获取已验证的冻结语料包，然后运行 `just test-coverage`。这些作业不重建扩展。即使套件失败，它们也保留覆盖率和渲染失败证据。
5. **合并覆盖率**，即使测试作业失败：`just combine-coverage` 将作业数据合并为一份报告，其表格进入运行的摘要。报告保留，带覆盖率徽章的数据（`badge.json`）。
6. **发布覆盖率**，为 `main` 的推送和来自仓库分支的 pull request：到 Worker `manimgx-coverage`
   （[`.github/deploy/coverage.jsonc`](https://github.com/1Cyrvox/ShuJing/blob/main/.github/deploy/coverage.jsonc)）。
   `main` 的报告在 <https://coverage.aipaikj.top> 服务。每个提交的报告也是其自己的预览部署（在预览 `main` 或 `pr-<number>` 中），提交的"coverage"状态链接到它。

### 2. [`benchmark.yaml`](https://github.com/1Cyrvox/ShuJing/blob/main/.github/workflows/benchmark.yaml)：定时基准测试

**何时运行：**

- 每次推送到 `main` 以及更改包、引擎、示例、基准测试、其工作流或依赖的每个 pull request。
- 手动，从 GitHub 界面，针对你命名的提交、分支或标签。

**做什么**，在 macOS 上的一个作业中：针对基线运行 `just bench`（见](testing.md#_20)）。Pull request 检出为合并到其基线，因此其基线是合并的第一个父提交；推送到 `main` 与其前一个提交比较。Metal 在 GPU 上绘制，而退役的 CPU 指令（当暴露时）或 CPU 时间判定主机工作。每个工作负载的摘要命名所用的度量。变慢的工作负载使作业失败，每个工作负载的变更进入运行的摘要。配对运行留在同一机器上；所有九个工作负载保持其分辨率和轮次。GPU 执行和等待仅出现在墙时间列：着色器和 GPU 调度更改需要在安静机器上审查那些时间。Linux 和 Windows 保持其功能渲染测试。

### 3. [`deploy-docs.yaml`](https://github.com/1Cyrvox/ShuJing/blob/main/.github/workflows/deploy-docs.yaml)：文档站点

**何时运行：**

- 每次推送到 `main`。
- 每个 pull request，当其打开、更新、重新打开和关闭时。
- 手动，从 GitHub 界面。

**做什么**，在四个作业中：

1. **构建**，在 macOS 上，除 pull request 关闭外的每次运行：检查文档的 JavaScript 交互和参考声明，恢复已验证的影片缓存条目，运行 `just render-docs`，保存完成的影片，然后运行 `just build-docs-pages`。Metal 绘制示例；旁白示例从 `docs/voice/` 说话，因此无需语音密钥。构建的 `docs/site/` 保留七天。部署配置从受信任的基线提交单独检出，因此构建不能为带凭据的作业提供要执行的命令。
2. **部署**，从 `main`（推送或手动运行）：用 `wrangler deploy --config .github/deploy/docs.jsonc` 将构建的内容部署到 Cloudflare Workers，提交哈希作为其消息。`docs` 环境显示站点地址，
   <https://www.aipaikj.top>。
3. **预览**，为来自仓库分支的 pull request：将构建上传为名为 `pr-<number>` 的预览，在其自己的地址，显示在 `docs-preview` 环境上。
4. **删除预览**，当 pull request 关闭时，文档和覆盖率的都删除。不存在的预览已是干净的；认证失败和其他 API 错误使作业失败。

见](documentation.md#_13)了解站点如何服务。

### 4. [`release.yaml`](https://github.com/1Cyrvox/ShuJing/blob/main/.github/workflows/release.yaml)：发布

**何时运行：**

- 推送的标签 `vX.Y.Z`（`just release`；见](project-management.md#_11)）。
- 更改发布方式的 pull request：发布的工作流和脚本、`pyproject.toml` 文件、npm 包或引擎 crate 的清单和构建脚本。它是空运行：构建一切，不发布任何内容。
- 手动，从 GitHub 界面，在分支上：也是空运行。

**做什么**，按顺序。一切在发布任何内容之前构建：

1. **检查版本。** 标签必须是 `v` 后跟 ManimGX 的版本（在 `pyproject.toml` 中），且变更日志必须有该版本的部分。以 `aN`、`bN` 或 `rcN` 结尾的版本是预发布。
2. **测试**，在标签上：运行 Test 工作流。
3. **构建：** wheel（`create-wheels.yaml`）、源码分发和 wheel 的完整源码（`just build-source`：提交的仓库，包括其构建配方、字体和浏览器源码，带引擎构建获取的每个 crate 和每个归档，加上 Linux wheel 作业保留的精确分发源码；源归档等待那些平台构建；见](engine.md#_12)）、字体包（`just build-fonts`）和可执行文件，从 wheel（`create-executables.yaml`），以及打包的 npm 构件。每个 Linux 架构从这些相同的 wheel 和字体构件构建其 Docker 镜像，外部依赖针对 `uv.lock` 认证。镜像在无网络访问下通过产品冒烟测试。BuildKit 在 OCI 归档中保留其出处和 SBOM。
4. **起草 GitHub 发布**，在标签上：为每个文件的出处签名（工作流、提交和构建它的运行的证明，`gh attestation verify FILE --repo 1Cyrvox/ShuJing` 检查），并起草发布 `manimgx X.Y.Z`，带文件（完整源码也是，PyPI 不获得），其说明是变更日志该版本的部分（`just release-notes`），然后是完整源码所在之处，x264 和 FFmpeg 的许可证要求如此。草稿然后变为公开，在注册表上传开始之前使那些源码可用。
5. **发布到 PyPI：** 先字体包，然后 ManimGX 的 wheel 和源码分发，用 `uv publish`，每个带其
   [PEP 740](https://peps.python.org/pep-0740/) 证明。`--check-url` 跳过 PyPI 已有的文件：字体在更改时发布。每个包有自己的 GitHub 环境和受信任的发布者：`manimgx` 为 `pypi`，`manimgx-fonts` 为 `pypi-fonts`，`manimgx-fonts-cjk` 为 `pypi-fonts-cjk`。字体作业作为矩阵运行，每个仅下载其包的分发。首次发布之前，在 PyPI 上注册三个待定发布者，所有者 `1Cyrvox`，仓库 `ShuJing`，工作流 `release.yaml`，以及那些环境名称；创建匹配的 GitHub 环境，允许发布标签（`v*`）。待定发布者需要不同的工作流/环境组合，即使其项目名称不同。发布使用工作流的 OIDC 令牌：不存储 PyPI 令牌。
6. **发布到 npm：** `publish-npm.yaml` 从公开 GitHub 发布获取浏览器的 tarball，并针对发布工作流、标签和提交验证其证明。它确认匹配的 Python 浏览器 wheel 在 PyPI 上公开后，才带出处发布。上传被接受后，验证等待最多五分钟的注册表可见性。重试仅在现有版本的 SHA512 完整性匹配精确 tarball 时接受它。同一工作流可以从 `main` 手动运行，带已发布的 `tag`，以用当前工具重试发布而不重建或移动该标签。首次发布，在包存在于 npm 之前，创建一个短期细粒度令牌，对所有包有读/写访问并绕过 2FA，将其作为 `NPM_TOKEN` 存储在 GitHub `npm` 环境中（允许 `v*` 标签和 `main`）。令牌仅传递给发布步骤。包存在后，配置其 npm 受信任的发布者，所有者 `1Cyrvox`，仓库 `ShuJing`，工作流 `release.yaml` 和 `publish-npm.yaml`，环境 `npm`；npm 检查调用者的工作流身份。启用直接发布（`npm publish`），因为工作流不暂存发布。然后撤销令牌并删除 GitHub 密钥：后续发布使用 OIDC。
7. **发布 Docker 镜像：** 复制测试的 OCI 归档而不更改其摘要，包括出处和 SBOM，并组装 `linux/amd64` 和 `linux/arm64` 平台索引。其出处被签名，并发布到
   `ghcr.io/1Cyrvox/ShuJing`，标记 `X.Y.Z` 和 `X.Y`（预发布仅 `X.Y.Z`），标注 `MIT AND GPL-3.0-or-later`：ManimGX 的代码，以及引擎，x264 使其整体为 GPL-3.0-or-later。它不需要新的包解析或镜像构建。首次上传后，在其 GitHub 包设置中将容器包的
   [可见性设为 Public](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility#configuring-visibility-of-packages-for-an-organization)；仓库可见性不设置包可见性。在宣布发布之前确认匿名拉取。
8. **确认完成：** 所有注册表上传已成功且 GitHub 发布公开。跨注册表的发布不是原子的；失败的目的地可以用保留的构件重试。仅发布不锁定发布的文件或标签：这需要为仓库启用 GitHub 的
   [不可变发布](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases)。此工作流在发布为草稿时附加每个文件，且不更改该设置。记录的构件摘要和出处证明验证获取的字节；它们不启用 GitHub 的不可变性策略。

### 5. [`create-wheels.yaml`](https://github.com/1Cyrvox/ShuJing/blob/main/.github/workflows/create-wheels.yaml)：wheel

**何时运行：** 当发布工作流调用它（或创建可执行文件，手动运行）时，以及手动运行以尝试分支的 wheel 时。

**做什么：** 每个平台一个作业（Linux x86_64 和 arm64、macOS arm64 和 x86_64、Windows x86_64 和 Pyodide）运行 `just build-wheel`；macOS x86_64 wheel 在 arm64 运行器上交叉编译（`CIBW_ARCHS`），并在 Rosetta 下测试，Linux 作业先为其 wheel 构建 Mesa 的 lavapipe（`scripts/release/build_lavapipe.sh`）。cibuildwheel 构建平台的 wheel 并在每个支持的 Python 上测试，如 `pyproject.toml` 中的 `[tool.cibuildwheel]` 所述（见](project-management.md#_4)）。每个 wheel 保留为 `wheel-<platform>`。

### 6. [`create-executables.yaml`](https://github.com/1Cyrvox/ShuJing/blob/main/.github/workflows/create-executables.yaml)：可执行文件

**何时运行：** 当发布工作流用其 wheel 调用它时，以及手动运行时，当它先构建 wheel 时。

**做什么：** 每个平台一个作业取平台的 wheel 并运行
`just create-executable`
（[`scripts/release/create_executable.py`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/release/create_executable.py)），后者在保留之前用可执行文件渲染一个场景。Linux 在 wheel 的 manylinux SDK 内构建启动器，因此两者都需要 glibc 2.28 或更新。然后全新的 glibc 2.28 容器在无 Python、无 GPU 驱动、无网络访问或安装缓存下运行可执行文件：它使用其嵌入的 Python 和内置的 lavapipe。macOS 使用 Metal，Windows 使用 WARP。每个可执行文件保留为 `executable-<platform>`：`manimgx-<os>-<arch>.tar.gz`，或 Windows 上的 `.zip`。

解释器是精确的 Python Build Standalone 发布和目标归档，由 SHA-256 验证。可执行文件归档包括 `build-inputs.json`、原始 `PYTHON.json` 和 `LICENSE-PYTHON`；元数据和声明也留在嵌入的 Python 内。源构件保留启动器的锁定源码和 `python-inputs.tar.xz`，后者包含解释器的构建配方、元数据和声明。相应的开源运行时输入按摘要保留一次，在 `release-sources/python/` 中；每个平台的收据标识其输入，最终源构建验证它们。选择遵循锁定的 PBS 和 CPython 构建配方，包括 Windows 单独的 libffi、Tcl 和 Tk 输入。仅用于恢复上游声明的源码在收据中单独标记。

Windows 的解释器还携带 Microsoft 的专有 `vcruntime140.dll` 和 `vcruntime140_1.dll`，记录为 `PYTHON.json` 中的 `vcruntime:140`。这些是受 [Microsoft 分发条款](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files)管辖的二进制可再分发文件，而非源归档提供的开源组件。

### 7. [`ai.yaml`](https://github.com/1Cyrvox/ShuJing/blob/main/.github/workflows/ai.yaml)：Claude 处理 issue 和 pull request

Claude 通过 [claude-code-action](https://github.com/anthropics/claude-code-action) 在 Amazon Bedrock 上运行。GitHub 的 OIDC 令牌交换为短期 AWS 会话（用于变量 `AWS_ROLE` 中的角色），因此不存储密钥。使用它的作业在 `ai` 环境中运行，每次运行有美元预算。

**何时运行：** 打开 issue、对 issue 或 pull request 发表评论，或打开 pull request 或标记为准备好审查时。

**做什么**，以三种方式：

- **首次回复** 对团队外人员（非所有者、成员或协作者，且非机器人）打开的 issue。模型 Claude Sonnet 读取 issue、打开 issue 的标题和仓库，不能做其他任何事：它只能读取检出的文件，以最多 2,000 个字符和最多三个相关 issue 的答回答。其指令是工作流自己的（`prompt`）。第二个作业，无模型无检出，发布回复：它拒绝看起来携带凭据的回复，化解其 @-提及，丢弃其图片，链接相关 issue，并说明回复是自动的，维护者会跟进。
- **审查** 来自仓库分支的 pull request（非草稿，非机器人的），当其打开或标记为准备好时：Anthropic 的代码审查插件，用 Claude Opus，评论它确定的问题。
- **@claude：** 维护者在新 issue 中提及 @claude，或在 issue 或 pull request 的评论中，并请求任何内容：回答、审查、变更。作业首先检查作者是否可以写入仓库，否则停止。Claude Opus 在 `just sync` 制作的环境中工作，其命令在 Claude Code 的沙箱中运行：它们仅能访问 GitHub、PyPI、crates.io 和 npm，从不看到 AWS 会话。它被告知遵循
  [`AGENTS.md`](https://github.com/1Cyrvox/ShuJing/blob/main/AGENTS.md)，在推送之前运行 `just check` 和其变更触及的测试，并以草稿 pull request 打开变更。对于来自 fork 的 pull request，它只读取。

## 部署凭据

构建和测试不接收部署凭据。发布作业仅使用受信任基线提交的部署文件和静态构件：

- 检查、测试和文档构建运行仓库的代码（它们构建引擎并渲染场景），带只能读取仓库的令牌。获取 Cloudflare API 令牌的作业在构建的文件上运行固定的 Wrangler（以及 `gh`，设置覆盖率状态）。清理使用受信任基线提交的 `cleanup.py`。部署配置和可执行代码都不从构建构件获取。
- Academa 的 `internal/manimgx-hosting` Terraform 单元拥有 Worker 身份、自定义域名、GitHub 环境和凭据。每个站点的
  `CLOUDFLARE_API_TOKEN` 只能编辑该 Worker；账户 ID 是仓库变量 `CLOUDFLARE_ACCOUNT_ID`。生产环境允许 `main`；预览环境还允许 pull request 合并引用。
- 来自 fork 和 Dependabot 的 pull request 不获得密钥：它们被构建和测试，不预览，其覆盖率不发布。
- 首次回复的模型只能读取，发布其回复的作业不运行模型。
- @claude 助手是例外：它运行仓库的代码（`just sync`、检查、测试），手边有 AWS 会话，其沙箱对它运行的每个命令隐藏会话。

每个工作流的默认权限为无（`permissions: {}`）；每个作业请求其所需。

## 细节

- 每个 pull request 或分支同时一次 Test 和文档工作流运行：对 pull request 的新提交取消其运行中的，而 `main` 上的运行在下一次开始之前完成。
- 每个 action 固定到提交，其版本在旁边的注释中，wrangler 的版本固定在 `WRANGLER_VERSION`。维护者审查这些固定的更新，而
  [zizmor](https://docs.zizmor.sh)，`just check` 的检查之一，发现工作流中的安全问题。
- Test、文档和 AI 工作流复用编译的 Rust 依赖。浏览器引擎有单独的缓存键。Pull request 构建不写入共享缓存；文档仅从 `main` 保存，Test 还从显式非 PR 运行保存，AI 仅恢复它们。

## 依赖更新

维护者发起依赖更新并在将它们集成到 `main` 之前验证。没有计划的 Dependabot 配置，因此版本更新不会自动创建分支。[Dependabot 警报](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-alerts)
保持启用；自动安全更新 pull request 被禁用。警报和上游发布说明指导维护，包括对按提交固定的 action 的检查。

- `just upgrade` 在清单的版本要求内刷新 Python 和 Rust 锁定文件，并重新生成第三方声明。显式审查主版本变更，包括其 API、行为和许可证；某些要求已允许它们。
- 在其自己的 `package.json` 和 `bun.lock` 中审查浏览器和语料库审查面板的依赖。用新锁定文件运行其检查和构建。
- 单独审查 action 提交、pre-commit hook 修订、Docker 基础镜像和原生源码固定。这些不被 `just upgrade` 更改；一起更新其记录的版本和源标识。

更新后运行 `just check` 和受影响的测试。对原生依赖闭包的更改还需要平台构建、包冒烟测试和源码/声明检查；对渲染路径的更改需要语料库和配对基准测试。仅新版本不是兼容性的证据。

## `.github/` 中的其他文件

[贡献指南](https://github.com/1Cyrvox/ShuJing/blob/main/.github/CONTRIBUTING.md)、安全策略、行为准则、issue 表单（bug、功能、文档、问题；无空白 issue）和 pull request 模板（摘要、测试计划、AI 的使用）。GitHub 在适用处显示每个。

## 了解更多

- [`.github/workflows/`](https://github.com/1Cyrvox/ShuJing/tree/main/.github/workflows)：工作流文件。
- [GitHub Actions 文档](https://docs.github.com/en/actions)。
- [Dependabot 警报](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-alerts)。