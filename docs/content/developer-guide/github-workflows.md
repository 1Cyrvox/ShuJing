# GitHub 工作流

## 问题

有些任务必须每次以相同的方式运行：

- **每次变更**，推送到 `main` 或以 pull request 提出时：运行检查，
  并在 ManimGX 支持的每个系统和 Python 上运行测试；与之前的代码进行计时比较；构建文档；发布测试覆盖率和文档预览。
- **每次发布：**测试；构建 wheel、源码发行版、字体
  包和可执行文件；将它们发布到 GitHub 和 PyPI，将浏览器
  包发布到 npm，将 Docker 镜像发布到 ghcr.io。
- **每个 issue 和 pull request：**对新来者 issue 的首次回复、首次
  评审，以及维护者可以调用的助手。
- **当维护者请求更新时：**评审并更新锁定的 action 和依赖项。

手动完成时，步骤会被遗忘，而且每次运行都要耗费某人的时间。

## 什么是 GitHub Actions？

[GitHub Actions](https://docs.github.com/en/actions) 在仓库中发生某些事件时，于 GitHub 的服务器上运行自动化。工作流是 `.github/workflows/` 中的一个文件，它指定：

1. **何时运行：**推送到 `main`、pull request、标签、评论、在
   GitHub 界面中的点击。
2. **做什么：**作业，每个作业是一个步骤列表（命令或已发布的 action）。
3. **在哪里运行：**在一台全新的虚拟机上：Ubuntu、macOS 或 Windows。

构建或测试的作业如同你在新机器上所做的那样开始：它检出
仓库，安装 `just` 和 `uv`（在 Linux 上还安装 Mesa 的 lavapipe 以供渲染时绘图），并运行 `just` 配方（见 [环境搭建](index.md)）。工作流运行 justfile 的配方，因此任务在 CI 中和在你的机器上执行方式相同。

## ManimGX 的工作流

七个常规的构建、发布和协作工作流位于
[`.github/workflows/`](https://github.com/1Cyrvox/ShuJing/tree/main/.github/workflows)。

### 1. [`test.yaml`](https://github.com/1Cyrvox/ShuJing/blob/main/.github/workflows/test.yaml)：检查与测试

**何时运行：**

- 每次推送到 `main`。
- 每个 pull request。
- 手动触发，从 GitHub 界面。
- 当 Release 工作流调用它时。

**做什么**，包含六个作业定义：

1. **运行 pre-commit 检查**，在 Ubuntu 上：安装锁定的工具但不编译
   项目，然后禁用自动环境同步运行 `just check`。
2. **测试浏览器包**，在 Ubuntu 上：检查 Rust 浏览器特性，用 Chrome 运行其
   浏览器测试，然后针对编译后的 worker、
   player 和公开声明运行 `just test-typescript`。
3. **构建与链接**，在 Linux、macOS 和 Windows 上各一次：检查源码获取和
   链接的编解码器，构建一个稳定 ABI 的 wheel，并运行 `just test-rust`。Linux 为
   渲染器测试安装 lavapipe。每个成功的作业会保留其 wheel。
4. **测试**，共六次：在该操作系统上安装相同的 wheel（Python 3.13 和 3.14），检查
   已安装的产品，获取经过验证的冻结语料包，然后运行
   `just test-coverage`。这些作业不重建扩展。即使测试套件失败，它们也会保留覆盖率和
   渲染失败证据。
5. **合并覆盖率**，即使某个测试作业失败：`just combine-coverage` 将各作业的数据合并为一份
   报告，其表格会放入运行的摘要中。报告会被保留，
   同时保留覆盖率徽章的数据（`badge.json`）。
6. **发布覆盖率**，针对 `main` 的推送以及来自仓库分支的 pull request：发布到 Worker `manimgx-coverage`
   （[`.github/deploy/coverage.jsonc`](https://github.com/1Cyrvox/ShuJing/blob/main/.github/deploy/coverage.jsonc)）。
   `main` 的报告通过 <https://coverage.www.aipaikj.top> 提供。每个提交的报告
   也是其自身的预览部署（在预览 `main` 或 `pr-<number>` 中），提交的
   "coverage" 状态会链接到它。

### 2. [`benchmark.yaml`](https://github.com/1Cyrvox/ShuJing/blob/main/.github/workflows/benchmark.yaml)：计时基准测试

**何时运行：**

- 每次推送到 `main`，以及每个变更了包、引擎、
  示例、基准测试、其工作流或依赖项的 pull request。
- 手动触发，从 GitHub 界面，针对你指定的提交、分支或标签。

**做什么**，在 macOS 上的一个作业中：针对基准运行 `just bench`（见
[测试](testing.md#_20)）。pull request 会以
合并到其基准后的状态检出，因此其基准是合并的第一个父提交；推送到 `main`
则与其前一个提交比较。Metal 在 GPU 上绘图，而
已退役的 CPU 指令（当暴露时）或 CPU 时间则用于评判宿主机工作。每个工作负载的摘要
会注明所使用的度量方式。变慢的工作负载会导致作业失败，
每个工作负载的变化都会放入运行的摘要中。配对运行保持在同一台机器上；
所有九个工作负载保留其分辨率和轮次。GPU 执行和等待仅出现在
wall-time 列中：着色器和 GPU 调度的变更需要在
安静的机器上审查那些时间。Linux 和 Windows 保留其功能性渲染测试。

### 3. [`deploy-docs.yaml`](https://github.com/1Cyrvox/ShuJing/blob/main/.github/workflows/deploy-docs.yaml)：文档站点

**何时运行：**

- 每次推送到 `main`。
- 每个 pull request，在其打开、更新、重新打开和关闭时。
- 手动触发，从 GitHub 界面。

**做什么**，包含四个作业：

1. **构建**，在 macOS 上运行（pull request 关闭时除外）：检查文档的
   JavaScript 交互和引用声明，恢复经过验证的影片缓存条目，
   运行 `just render-docs`，保存已完成的影片，然后运行 `just build-docs-pages`。
   Metal 绘制示例；旁白示例从 `docs/voice/` 发声，因此不需要语音密钥。构建好的 `docs/site/` 保留七天。部署配置从
   受信任的基准提交中单独检出，因此构建无法为带有凭据的作业
   提供要执行的命令。
2. **部署**，来自 `main`（推送或手动运行）：使用 `wrangler deploy --config .github/deploy/docs.jsonc` 将构建产物部署到
   Cloudflare Workers，以提交的哈希作为其消息。`docs` 环境显示站点地址，
   <https://www.aipaikj.top>。
3. **预览**，针对来自仓库分支的 pull request：将构建产物作为
   名为 `pr-<number>` 的预览上传，拥有自己的地址，显示在 `docs-preview`
   环境中。
4. **删除预览**，当 pull request 关闭时，同时针对文档和覆盖率。不存在的
   预览视为已清理；认证失败和其他 API 错误会导致
   作业失败。

关于站点如何提供服务，见 [文档](documentation.md#_11)。

### 4. [`release.yaml`](https://github.com/1Cyrvox/ShuJing/blob/main/.github/workflows/release.yaml)：发布

**何时运行：**

- 推送的标签，`vX.Y.Z`（`just release`；见
  [项目管理](project-management.md#_11)）。
- 变更发布方式的 pull request：发布的 workflows 和脚本、
  `pyproject.toml` 文件、npm 包，或引擎 crate 的清单和构建
  脚本。这是试运行：构建一切，但不发布任何内容。
- 手动触发，从 GitHub 界面，在分支上：同样是试运行。

**做什么**，按顺序执行。所有内容在发布任何东西之前都会先构建：

1. **检查版本。**标签必须是 `v` 后跟 ManimGX 的版本（在
   `pyproject.toml` 中），且变更日志必须有该
   版本的章节。以 `aN`、
   `bN` 或 `rcN` 结尾的版本是预发布版本。
2. **测试**，在标签上：运行 Test 工作流。
3. **构建：**wheel（`create-wheels.yaml`）、源码发行版和 wheel 的
   完整源码（`just build-source`：已提交的仓库，包括其构建
   配方、字体和浏览器源码，以及每个 crate 和引擎构建所获取的每个
   归档，加上 Linux wheel 作业保留的精确发行版源码；
   源码归档等待这些平台构建完成；见
    [他人的源码](engine.md#_12)）、字体包（`just build-fonts`），以及
   由 wheel 生成的可执行文件（`create-executables.yaml`）和打包的 npm 制品。
   每个 Linux 架构从这些相同的 wheel 和字体制品构建其 Docker 镜像，
   外部依赖根据 `uv.lock` 进行认证。镜像在无网络访问的情况下通过产品
   冒烟测试。BuildKit 将其来源证明和 SBOM 保留在 OCI 归档中。
4. **起草 GitHub release**，在标签上：为每个文件的来源证明签名（即对
   工作流、提交和构建它的运行的证明，可由
   `gh attestation verify FILE --repo 1Cyrvox/ShuJing` 验证），并起草 release
   `manimgx X.Y.Z`，包含这些文件（也包括完整源码，PyPI 不会收到），其说明为
   变更日志中该版本的章节（`just release-notes`），然后说明完整
   源码的位置，这是 x264 和 FFmpeg 的许可证所要求的。草稿随后变为公开，
   在注册表上传开始之前使这些源码可用。
5. **发布到 PyPI：**先发布字体包，然后是 ManimGX 的 wheel 和源码
   发行版，使用 `uv publish`，每个都附带其
   [PEP 740](https://peps.python.org/pep-0740/) 证明。`--check-url` 会跳过 PyPI 已有的文件：字体在变更时发布。每个包有自己的 GitHub
   环境和受信任的发布者：`manimgx` 对应 `pypi`，`manimgx-fonts` 对应
   `pypi-fonts`，`manimgx-fonts-cjk` 对应 `pypi-fonts-cjk`。字体作业以
   矩阵方式运行，每个作业仅下载其包的发行版。在首次发布之前，
   在 PyPI 上注册三个待定发布者，owner 为 `1Cyrvox`，repository 为
   `manimgx`，workflow 为 `release.yaml`，以及那些环境名称；创建匹配的
   GitHub 环境并允许 release 标签（`v*`）。待定发布者需要不同的
   workflow/environment 组合，即使其项目名称不同。发布
   使用工作流的 OIDC 令牌：不存储 PyPI 令牌。
6. **发布到 npm：**`publish-npm.yaml` 从公开的
   GitHub release 获取浏览器的 tarball，并根据 release 工作流、标签和提交验证其证明。
   它确认匹配的 Python 浏览器 wheel 已在 PyPI 上公开，然后才带
   来源证明进行发布。上传被接受后，验证最多等待五分钟以等待注册表
   可见。重试仅在现有版本的 SHA512 完整性匹配
   确切的 tarball 时才接受该版本。同一工作流可以从 `main` 手动运行，使用已发布的 `tag`，
   以当前工具重试发布而无需重建或移动该标签。
   对于首次发布，在包存在于 npm 之前，创建一个
   短期的细粒度令牌，具有对所有包的读/写访问权限并绕过 2FA，
   将其作为 `NPM_TOKEN` 存储在 GitHub `npm` 环境中（允许 `v*` 标签和 `main`）。
   该令牌仅传递给发布步骤。包存在后，配置
   其 npm 受信任发布者，owner 为 `1Cyrvox`，repository 为 `manimgx`，workflows 为
   `release.yaml` 和 `publish-npm.yaml`，environment 为 `npm`；npm 检查调用者的
   工作流身份。启用直接发布（`npm publish`），
   因为工作流不暂存 release。然后撤销令牌并删除
   GitHub 密钥：后续发布使用 OIDC。
7. **发布 Docker 镜像：**复制经过测试的 OCI 归档而不改变其摘要，
   包括来源证明和 SBOM，并组装 `linux/amd64` 和 `linux/arm64`
   平台索引。其来源证明已签名，并发布到
   `ghcr.io/1Cyrvox/ShuJing`，标记为 `X.Y.Z` 和 `X.Y`（预发布版本
   仅 `X.Y.Z`），标签为 `MIT AND GPL-3.0-or-later`：ManimGX 的代码，以及引擎，由于
   x264 使整体成为 GPL-3.0-or-later。它不需要新的包解析或镜像构建。
   首次上传后，在其 GitHub 包设置中将容器包的
   [可见性设为 Public](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility#configuring-visibility-of-packages-for-an-organization)；
   仓库可见性不会设置包可见性。
   在宣布发布之前确认匿名拉取成功。
8. **确认完成：**所有注册表上传均已成功，且 GitHub release 已
   公开。跨注册表的发布不是原子的；失败的目标可以使用
   保留的制品重试。仅发布不会锁定 release 的文件或标签：这需要
   为仓库启用 GitHub 的
   [不可变 release](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases)。
   此工作流在 release 为草稿时附加每个文件，并且
   不更改该设置。记录的制品摘要和来源
   证明验证所获取的字节；它们不启用 GitHub 的不可变性策略。

### 5. [`create-wheels.yaml`](https://github.com/1Cyrvox/ShuJing/blob/main/.github/workflows/create-wheels.yaml)：wheel

**何时运行：**当 Release 工作流调用它时（或 Create executables 手动运行时），以及手动运行以尝试某个分支的 wheel 时。

**做什么：**每个平台一个作业（Linux x86_64 和 arm64、macOS arm64 和 x86_64、
Windows x86_64 和 Pyodide）运行 `just build-wheel`；macOS x86_64 wheel 在
arm64 runner 上交叉编译（`CIBW_ARCHS`），并在其上通过 Rosetta 测试，Linux 作业首先为其 wheel 构建 Mesa 的
lavapipe（`scripts/release/build_lavapipe.sh`）。cibuildwheel 构建该
平台的 wheel 并在每个
受支持的 Python 上测试，如 `pyproject.toml` 中的 `[tool.cibuildwheel]` 所述（见
[项目管理](project-management.md#_4)）。每个 wheel 保留为
`wheel-<platform>`。

### 6. [`create-executables.yaml`](https://github.com/1Cyrvox/ShuJing/blob/main/.github/workflows/create-executables.yaml)：可执行文件

**何时运行：**当 Release 工作流调用它时（带有其 wheel），以及手动运行时（此时它会
先构建 wheel）。

**做什么：**每个平台一个作业，获取该平台的 wheel 并运行
`just create-executable`
（[`scripts/release/create_executable.py`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/release/create_executable.py)），
它在保留可执行文件之前先用它渲染一个场景。Linux 在
wheel 的 manylinux SDK 内构建启动器，因此两者都需要 glibc 2.28 或更新版本。一个全新的 glibc 2.28
容器随后在没有 Python、GPU 驱动程序、网络访问或
安装缓存的情况下运行该可执行文件：它使用其内嵌的 Python 和内置的 lavapipe。macOS 使用 Metal，
Windows 使用 WARP。每个可执行文件保留为
`executable-<platform>`：`manimgx-<os>-<arch>.tar.gz`，Windows 上则为 `.zip`。

解释器是一个精确的 Python Build Standalone 发行版和目标归档，通过
SHA-256 验证。可执行文件归档包括 `build-inputs.json`、原始的 `PYTHON.json`
和 `LICENSE-PYTHON`；元数据和声明也保留在内嵌的 Python 中。
源码制品保留启动器的锁定源码和 `python-inputs.tar.xz`，
其中包含解释器的构建配方、元数据和声明。对应的
开源运行时输入按摘要唯一保留在 `release-sources/python/` 中；
每个平台的回执标识其输入，最终的源码构建会验证它们。
选择遵循锁定的 PBS 和 CPython 构建配方，包括 Windows 单独的
libffi、Tcl 和 Tk 输入。仅用于恢复上游声明的源码在
回执中单独标记。

Windows 的解释器还携带 Microsoft 专有的 `vcruntime140.dll` 和
`vcruntime140_1.dll`，在 `PYTHON.json` 中记录为 `vcruntime:140`。这些是受
[Microsoft 分发条款](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files) 管辖的二进制
可再分发组件，而非源码归档提供的开源组件。

### 7. [`ai.yaml`](https://github.com/1Cyrvox/ShuJing/blob/main/.github/workflows/ai.yaml)：issue 和 pull request 上的 Claude

Claude 通过 [claude-code-action](https://github.com/anthropics/claude-code-action) 运行，
基于 Amazon Bedrock。GitHub 的 OIDC 令牌被交换为一个短期的 AWS 会话（对应
变量 `AWS_ROLE` 中的角色），因此不存储任何密钥。使用它的作业在 `ai`
环境中运行，每次运行都有以美元计的预算。

**何时运行：**打开 issue、在 issue 或 pull request 上发表评论，或
pull request 被打开或标记为准备好评审时。

**做什么**，有三种方式：

- **首次回复**，针对团队外部人员（不是 owner、member
  或 collaborator，也不是 bot）打开的 issue。一个模型 Claude Sonnet 读取 issue、
  打开的 issue 的标题和仓库，除此之外不能做任何事：它只能读取
  检出的文件，并以最多 2,000 个字符的回复和最多
  三个相关 issue 来回答。其指令是工作流自身的（`prompt`）。
  第二个作业没有模型也没有检出，负责发布回复：它会拒绝看起来
  携带凭据的回复，消除其中的 @-mention，删除其中的图片，链接相关
  issue，并说明该回复是自动生成的，维护者会跟进。
- **评审**，针对来自仓库分支的 pull request（不是草稿，也不是
  bot 的），在其打开或标记为准备好时：Anthropic 的 code-review 插件，使用 Claude
  Opus，对它确信的问题发表评论。
- **@claude：**维护者在新 issue 中，或在 issue 或
  pull request 的评论中提及 @claude，并要求任何东西：回答、评审、变更。作业首先
  检查作者是否可以写入仓库，否则停止。Claude Opus
  在 `just sync` 创建的环境中工作，其命令在 Claude Code 的
  沙箱中运行：它们只能访问 GitHub、PyPI、crates.io 和 npm，永远看不到 AWS 会话。它
  被告知遵循 [`AGENTS.md`](https://github.com/1Cyrvox/ShuJing/blob/main/AGENTS.md)，
  在推送之前运行 `just check` 及其变更涉及的测试，并以
  草稿 pull request 的形式打开变更。对于来自 fork 的 pull request，它只读取。

## 部署凭据

构建和测试不接收部署凭据。发布作业仅使用受信任
基准提交的部署文件和静态制品：

- 检查、测试和文档构建运行仓库的代码（它们构建
  引擎并渲染场景），使用的令牌只能读取仓库。获取
  Cloudflare API 令牌的作业在构建的文件上运行锁定的 Wrangler（以及 `gh`，用于设置
  覆盖率状态）。清理使用受信任基准提交的 `cleanup.py`。部署配置和可执行代码均不从构建制品中获取。
- Academa 的 `internal/manimgx-hosting` Terraform 单元拥有 Worker 身份、
  自定义域名、GitHub 环境和凭据。每个站点的
  `CLOUDFLARE_API_TOKEN` 只能编辑该 Worker；账户 ID 是仓库
  变量 `CLOUDFLARE_ACCOUNT_ID`。生产环境允许 `main`；预览
  环境还允许 pull request 合并引用。
- 来自 fork 和 Dependabot 的 pull request 不获取任何密钥：它们被构建和测试，
  但不预览，其覆盖率也不发布。
- 首次回复的模型只能读取，发布其回复的作业不运行模型。
- @claude 助手是例外：它在 AWS 会话可用的情况下运行仓库的代码（`just sync`、
  检查、测试），其沙箱对它运行的每个命令隐藏该会话。

每个工作流的默认权限均为无（`permissions: {}`）；每个作业按需申请权限。

## 细节

- Test 和文档工作流每个 pull request 或分支同时只运行一次：向
  pull request 的新提交会取消其正在运行的作业，而 `main` 上的运行会在
  下一次开始之前完成。
- 每个 action 都锁定到一个提交，其版本在旁边的注释中，wrangler 的
  版本锁定在 `WRANGLER_VERSION` 中。维护者评审这些锁定的更新，
  [zizmor](https://docs.zizmor.sh) 作为 `just check` 的一项检查，用于发现工作流中的安全
  问题。
- Test、文档和 AI 工作流复用已编译的 Rust 依赖。浏览器引擎
  有单独的缓存键。Pull request 构建不写入共享缓存；文档仅从
  `main` 保存，Test 还从显式的非 PR 运行中保存，AI 仅恢复它们。

## 依赖更新

维护者发起依赖更新，并在将其集成到
`main` 之前进行验证。没有计划性的 Dependabot 配置，因此版本更新不会
自动创建分支。[Dependabot 告警](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-alerts)
保持启用；自动安全更新 pull request 已禁用。告警和上游
发行说明指导维护工作，包括对按提交锁定的 action 的检查。

- `just upgrade` 在清单的版本要求范围内刷新 Python 和 Rust 的 lockfile，
  并重新生成第三方声明。显式评审
  主版本变更，包括其 API、行为和许可证；某些要求已经允许它们。
- 在各自的 `package.json`
  和 `bun.lock` 中评审浏览器和语料库评审面板的依赖。使用新的 lockfile 运行其检查和构建。
- 分别评审 action 提交、pre-commit hook 版本、Docker 基础镜像和原生
  源码锁定。这些不会被 `just upgrade` 更改；一起更新其记录的
  版本和源码标识。

更新后运行 `just check` 和受影响的测试。原生依赖
闭包的变更还需要平台构建、包冒烟测试和源码/声明检查；渲染
路径的变更需要语料库和配对基准测试。仅新版本本身不能证明
兼容性。

## `.github/` 中的其他文件

[贡献指南](https://github.com/1Cyrvox/ShuJing/blob/main/.github/CONTRIBUTING.md)、
安全策略、行为准则、issue 表单（bug、功能、文档、
问题；没有空白 issue）和 pull request 模板（摘要、测试计划以及
AI 的使用）。GitHub 会在适用的地方分别显示它们。

## 了解更多

- [`.github/workflows/`](https://github.com/1Cyrvox/ShuJing/tree/main/.github/workflows)：
  工作流文件。
- [GitHub Actions 文档](https://docs.github.com/en/actions)。
- [Dependabot 告警](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-alerts)。
