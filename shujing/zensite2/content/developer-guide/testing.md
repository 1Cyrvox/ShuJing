# 测试

测试是检查其他代码是否做其应做之事的代码。编写一次，每次更改后再次运行，说明更改是否破坏了什么。

ManimGX 的 Python 和集成测试在
[`tests/`](https://github.com/academa-labs/manimgx/tree/main/tests)。
其中大多数渲染场景，因此套件需要渲染所需的内容：引擎可绘制的 GPU（见[搭建](index.md#gpu)）。再次渲染语料库的 Manim 参考还需要 Manim Community Edition（见[搭建](index.md#manim-community-edition)）。

浏览器包的测试在其旁，在
[`browser/tests/`](https://github.com/academa-labs/manimgx/tree/main/browser/tests)。
用 `just test-typescript` 运行它们：它构建包，用浏览器和 Pyodide 副本测试编译的播放器和嵌入的 worker，并对生成公共声明的消费者进行类型检查。这些测试需要 Bun；不需要 GPU 或下载 Pyodide。

## [pytest](https://docs.pytest.org)：测试运行器

pytest 找到 `tests/` 下名为 `test_*.py` 的文件并运行其中名为 `test_*` 的函数。[pytest-xdist](https://pytest-xdist.readthedocs.io) 并行运行它们，每个 CPU 核一个 worker。`just test` 运行它们，并将参数传递给 pytest：

```sh
just test                                      # 整个套件
just test tests/integration/test_time.py       # 一个模块
just test -k add_subpath_example               # 名称匹配的测试：一个案例的
just test tests/integration/test_time.py -x    # 在第一个失败处停止
```

整个套件渲染集成语料库的每个案例，因此需要一些时间；工作时运行你更改触及的部分。`pyproject.toml` 将仓库根放在路径上，因此测试将其自己的工具导入为 `tests.integration.corpus`。

Test 工作流在每次推送到 `main` 和每个 pull request 时在 Linux、macOS 和 Windows 上用 Python 3.13 和 3.14 运行套件（见[GitHub 工作流](github-workflows.md#1-testyaml)）。九个基准测试影片在 Linux 和 macOS 上运行。Windows 仍运行功能语料库、原生渲染测试、打包检查和工作法则；其软件 GPU 在这些长影片上的成本不在性能门控之内。

## 测试是什么

```text
tests/
├── unit/                 ← 每个模块的属性：unit/<path>/test_<module>.py
├── conftest.py           ← 每个测试的全新世界，其 `config` 标记，Hypothesis 的配置
├── strategies.py         ← Hypothesis 绘制的内容，以及每个 mobject 类的注册表
├── oracles.py            ← 缓慢、明显正确的计算，用于比较
├── scenes.py             ← 由函数组成的场景，绘制或探测；随机故事
├── test_tests.py         ← 套件自身的规则
├── integration/
│   ├── test_*.py         ← 故事：与 Manim 的比较无法看到的内容
│   ├── test_corpus.py    ← 语料库的三项检查，针对每个案例
│   ├── test_corpus_tools.py ← 语料库的工具保持其规则
│   ├── cases/            ← 语料库：每个案例一个文件夹
│   ├── corpus/           ← 语料库的工具：渲染、比较、审查
│   ├── review/           ← 审查面板：FastAPI 服务器及其网页
│   └── settings.json     ← 比较的度量和容差
├── docs/
│   ├── test_llms.py      ← llms.txt 的引导，对照 API 检查；每个页面的 Markdown
│   ├── test_skill.py     ← 代理技能，对照其规范检查
│   ├── test_reference.py ← API 参考显示包文档化的每个名称，一次
│   ├── test_hidden.py    ← 文档中无示例使用 manimgx 隐藏的名称
│   ├── test_deprecated.py ← 已弃用的内容排除在参考之外
│   └── test_examples.py  ← 旁白示例说出 docs/voice/ 保留的内容
└── benchmarks/
    ├── test_laws.py      ← 成本法则：工作随所制作的内容增长
    ├── test_speed.py     ← 定时：此检出对照另一个提交（just bench）
    ├── scenes/           ← 三个场景，test_speed.py 计时
    ├── harness.py        ← 比较的树，测量的渲染，及其轮次
    └── work.py           ← 工作，计数
```

[`tests/docs/test_llms.py`](https://github.com/academa-labs/manimgx/blob/main/tests/docs/test_llms.py)
检查文档 `llms.txt` 的引导，为 AI 代理手工编写（见](documentation.md#markdown)）：其场景运行，它教授的每个名称都存在。它还检查每个页面在 `llms.txt` 的一个部分中，因此每个页面有其 Markdown。
[`tests/docs/test_skill.py`](https://github.com/academa-labs/manimgx/blob/main/tests/docs/test_skill.py)
检查代理技能的 front matter（见](documentation.md#_10)）。
[`tests/docs/test_examples.py`](https://github.com/academa-labs/manimgx/blob/main/tests/docs/test_examples.py)
在无语音密钥下运行旁白示例，如站点构建时（见](documentation.md#_5)）。
[`tests/docs/test_reference.py`](https://github.com/academa-labs/manimgx/blob/main/tests/docs/test_reference.py)
保持手工编写的 API 参考完整：包文档化的每个名称在某个页面上，一次，且它隐藏的名称不在（见](documentation.md#api)）。
[`tests/docs/test_hidden.py`](https://github.com/academa-labs/manimgx/blob/main/tests/docs/test_hidden.py)
对文档显示的每个示例进行类型检查，在 ManimGX 隐藏的名称（`@deprecated`）上失败。单元测试在 `tests/unit/`，基准测试在 `tests/benchmarks/`（见](#_17)），套件的其余部分在 `tests/integration/`。

### 单元测试

[`tests/unit/`](https://github.com/academa-labs/manimgx/tree/main/tests/unit) 镜像包：`tests/unit/<path>/test_<module>.py` 测试 `src/manimgx/<path>/<module>.py`，以列出其检查的属性的文档字符串开始。[`tests/test_tests.py`](https://github.com/academa-labs/manimgx/blob/main/tests/test_tests.py)
将套件约束到两者，以及其到每个公共 mobject 和动画类的注册表。

单元测试检查公共 API 的属性，而非示例，也非代码内部如何构建：没有测试读取私有存储、计数调用或排序 hook 以固定如何达到结果。用 [Hypothesis](https://hypothesis.readthedocs.io)，测试陈述对每个输入成立的内容，Hypothesis 绘制数百个输入，然后将任何失败的缩小到仍失败的最简单的。做工作的属性：

- 与
  [`tests/oracles.py`](https://github.com/academa-labs/manimgx/blob/main/tests/oracles.py) 中缓慢且明显正确的计算一致：de Casteljau 构造、numpy 的根查找器、Gauss–Legendre 求积、数字位数的 `decimal` 运算、所绘内容的紧包围盒；
- 法则：`AnimationGroup(x)` 播放如 `x`，嵌套的连续播放如一个，`Rotate` 是 `.animate.rotate`，一起播放的移动如依次应用般结束；
- 每个公共类遵循的法则，在
  [`tests/strategies.py`](https://github.com/academa-labs/manimgx/blob/main/tests/strategies.py) 的注册表上：`MOBJECTS`（副本、目标、保存的状态或再次构造是同一对象图的独立副本，不触及其原始；其输入和输出是值；其盒是所绘内容）和 `ANIMATIONS`（制作后不更改任何内容；开始后显示其所显示；是其进度的函数）；
- 对照简单模型检查的状态机，在公共调用的任何历史上：家族的编辑、变换、更新器及其时钟、场景的成员、图的编辑、馈送器的账本、绘制记住的内容；
- 记住的工作不可见：用 ManimGX 记忆温暖制作的任何内容等于冷制作（标记 `cold` 的测试以无记忆开始和结束）；
- 对于时间，在无头场景上讲述的随机故事
  （[`tests/scenes.py`](https://github.com/academa-labs/manimgx/blob/main/tests/scenes.py)）：提前计算的播放显示逐帧计算的同一播放所显示的，且某时刻的世界在每个帧率下相同。

[`tests/conftest.py`](https://github.com/academa-labs/manimgx/blob/main/tests/conftest.py)
从同一世界开始每个测试：场景时钟为 0，配置如发布时，测试后恢复。需要其他配置的测试用标记说明，模块用 `pytestmark = pytest.mark.config(pixel_width=320, pixel_height=180)`，测试用 `@pytest.mark.config(frame_rate=30)`，从不手动设置和恢复。它还持有 Hypothesis 的配置：`default`；`thorough`，每个属性 2,000 个示例（`just test-thorough`）；以及 `mutation`。在 CI 上，Hypothesis 加载自己的 `ci` 配置。

修复附带其破坏的属性，陈述为无修复则失败。在一个输入上发现的 bug 是该输入添加到其破坏的法则（`@example`，或注册表的条目），而非其自己的测试；增长过快的工作是成本法则的一行。已知 bug 破坏的法则精确标记其破坏的案例为 `xfail(strict=True)`，其原因是用一句话描述的 bug：bug 修复之日，标记必须去掉。

### 变异测试

通过的测试证明不多，除非代码错误时它会失败。
[mutmut](https://mutmut.readthedocs.io) 检查那个：它以小方式更改代码（`<` 换 `<=`，`+` 换 `-`），一次一个变异体，并对每个运行测试。没有测试失败的变异体是测试放行的更改。`just mutate` 在 `pyproject.toml` 中 `[tool.mutmut]` 列出的模块上运行它，在 `mutation` 配置下，且在测试之间遗忘 ManimGX 记住的一切（`manimgx.caches.clear`），因此缓存不能隐藏变异体。它很慢，因此手动运行，不在 CI 上。

### 故事

[`tests/integration/`](https://github.com/academa-labs/manimgx/tree/main/tests/integration) 中除 `test_corpus.py` 外的每个 `test_*.py` 模块讲述关于一个主题的故事：时间、运动、引擎绘制的内容（描边、填充、图像）、光、透视、3D 合成、影片的 hook、其视频、声音和 take、窗口和预览、横幅。故事渲染场景并在场景计算的每个时刻探测它，通常在多个帧率下。其模块的文档字符串列出其显示的内容。`tests/scenes.py` 由函数制作场景（`scene`、`scene_3d`），绘制一个并将其帧保持为数组（`frames`），或保持探测器在每个时刻所见（`instants`）。

故事检查与 Manim 的比较无法检查的内容。
[`test_time.py`](https://github.com/academa-labs/manimgx/blob/main/tests/integration/test_time.py)，
例如，检查一帧显示的内容不取决于帧率：在每秒 10、30 和 60 帧时，由更新器移动的点在每个时刻在其精确轨迹所放之处。

修复或功能附带显示它的测试：其所属模块中的故事，或新的语料库案例（见](#_13)）。

## 集成语料库

### 问题

ManimGX 实现 Manim Community Edition 的 API。为 Manim 编写的场景必须工作，并在引擎更改时继续工作。一个函数的测试看不到错误的帧，而参考图像太多无法手动检查。且"与 Manim 相同"不是"正确"：Manim 有自己的 bug，ManimGX 有意与之不同（精确时钟，例如）。

因此语料库在两个引擎中渲染真实场景，比较它们，让人决定什么是对的，并将 ManimGX 保持在每个存储的渲染上，因此更改不会不被注意地通过。

### 案例

案例是
[`tests/integration/cases/`](https://github.com/academa-labs/manimgx/tree/main/tests/integration/cases) 中的文件夹：

- `scene.py`：唯一的源码。它是 Manim 代码，仅通过 `import manimgx` 到达引擎。场景读取的文件（SVG、声音）在其旁。
- `manimgx.mkv` 和 `ce.mkv`：每个引擎的无损帧，本地生成，被 Git 忽略。其 `.sha256` 伴随文件记录精确的已审查视频文件。
- `case.json`：事实，由工具写入。两个渲染所来自的源码哈希、每帧的哈希，以及两个引擎帧的比较方式。
- `review.json`，一旦有人审查了案例：其裁决和注释，固定在所展示的渲染上。

案例是 Manim 文档和文档字符串的示例（`scene.py` 的第一行命名其来源）、为覆盖 ManimGX 的 API 编写的场景、回归，以及为回答问题而编写的场景（问题是其文档字符串）。语料库是规范：其工作案例显示的是 ManimGX 做的。

### 两个引擎，一个源码

两个引擎运行相同的字节。ManimGX 按原样运行 `scene.py`。Manim 将 `manimgx` 解析为 `manim` 运行它，如果真正的 ManimGX 被导入则运行失败
（[`run_ce.py`](https://github.com/academa-labs/manimgx/blob/main/tests/integration/corpus/run_ce.py)）。每个渲染在自己的进程中，带固定哈希种子。

帧由其像素哈希标识，本地以无损视频存储（RGB 中的 x264，用 [PyAV](https://pyav.basswood-io.com) 写读，FFmpeg 的库在 wheel 中）。视频仅在像素更改时重写，因此再次渲染未更改的场景不更改任何文件。提交的 `.sha256` 伴随文件标识每个已审查视频，而不将视频放入克隆历史。语料库以 960 × 540、每秒 10 帧渲染。

### 在同一场景时间比较

帧按场景时间配对，从不按索引。ManimGX 的帧 _k_ 显示场景在恰好 _k_/fps。Manim 将每个播放舍入到整帧，从不显示场景最后一个动画落地；那些都不应算作 ManimGX 的错。因此每个 ManimGX 帧与 Manim 在同一场景时间屏幕上的帧比较。

每对在四个度量中测量，从 0 到 255：`local_max`、`mae`、`rmse` 和 `max`。
[`settings.json`](https://github.com/academa-labs/manimgx/blob/main/tests/integration/settings.json)
选择决定的那个及其容差：`local_max` 上至 30。`local_max` 是任何 7 × 7 窗口上每个像素最大通道差的最大均值：单个错误像素衰减到自身的 1/49，而错误的描边或形状突出。

见 [`compare.py`](https://github.com/academa-labs/manimgx/blob/main/tests/integration/corpus/compare.py)。

### 裁决

案例处于以下状态之一：

| 状态 | 含义 |
| --- | --- |
| `working` | 在每个 ManimGX 帧，Manim 的帧在容差内，且场景持续同样长。 |
| `not_matching` | 否则，或 Manim 无法渲染场景。 |
| `not_working` | ManimGX 无法渲染场景。 |
| `stale`、`unrendered` | 案例无当前渲染可判断。 |

比较给出裁决；人对恰好这些渲染的裁决覆盖它。Manim 是参考，不是正确的定义，因此"Manim 这样做"是仔细查看的理由，不是更改 ManimGX 的理由。案例在工作时被信任。

见 [`case.py`](https://github.com/academa-labs/manimgx/blob/main/tests/integration/corpus/case.py)。

### 三项检查

[`test_corpus.py`](https://github.com/academa-labs/manimgx/blob/main/tests/integration/test_corpus.py)
以三种方式检查每个案例：

1. `test_same_source`：两个参考都从此精确的 `scene.py` 渲染，后者导入 ManimGX，从不导入 Manim。因此两个引擎运行了相同的程序。
2. `test_types`：场景按编写类型检查：ty 带每条规则，无法绕过检查器（抑制注释、`Any`、`cast`、…），且无 ManimGX 留为 `Any` 或 `Unknown` 的值
   （[`typecheck.py`](https://github.com/academa-labs/manimgx/blob/main/tests/integration/corpus/typecheck.py)）。
3. `test_regression`：最新稳定的 ManimGX 发布和今天的包在相同主机和适配器上的独立新进程中渲染场景，使用相同的已安装依赖和字体。每个 RGB 像素、精确持续时间、时间线和帧数必须一致，导出的 MP4 必须包含每帧。这覆盖每个案例，包括那些与 Manim 不同或等待审查的。首次稳定发布之前，每个场景仍被渲染并检查其导出帧数。

CI 在测试之前解析最新稳定的 GitHub 发布，并在测试 worker 共享的清单中记录其版本和 wheel SHA-256 标识。下载在使用前验证。无兼容 wheel 的已发布发布、无效校验和或失败下载是错误；仅无稳定发布启用首次发布引导。本地，测试夹具解析最新发布，或读取 `MANIMGX_CORPUS_RELEASE` 命名的清单。

失败将发布标识、参考影片、进程日志和第一对差异帧保留在 `tests/integration/_diffs/<case>/`。成功的比较移除其临时影片。回归接受不使用图像容差。全新克隆需要已发布包下载，而非归档的语料库影片，来运行这些测试。

### 使用语料库

`test_corpus.py` 仅检查；`just corpus` 渲染和审查。参考仅在更改意在更改它时更改，且有人查看了新帧之后。

审查面板和 `just corpus diff CASE` 使用由提交伴随文件标识的本地影片。对照那些伴随文件验证恢复的影片。要创建新的审查影片，使用 `just corpus render CASE`；更改的像素更新本地事实并需要在提交之前进行新审查。

- **新案例** 是 `cases/` 中持有其 `scene.py` 的文件夹。用 `just corpus render CASE` 渲染它，它在两个引擎中渲染并比较；查看它（`just review`）；用 `just corpus review CASE working`（或 `not_matching` 或 `not_working`；`--note` 说明原因）记录裁决。提交场景、事实、审查和视频哈希伴随文件；Git 忽略视频。
- **意在更改案例外观的更改** 用
  `just corpus render CASE…` 再次渲染其参考。案例的审查固定在为其给出的渲染上，因此不再为新渲染代言：提交之前查看新帧，并更新裁决（在审查面板中，或用 `just corpus review`）。
- `just corpus status` 说明每个案例的处境，`just corpus --help` 列出其余。

### 语料库的工具

`just corpus` 运行
[`tests/integration/corpus`](https://github.com/academa-labs/manimgx/tree/main/tests/integration/corpus)：

| 命令 | 做什么 |
| --- | --- |
| `render [CASE…] [--all \| --stale] [--engine E] [-j N]` | 渲染参考，然后比较 |
| `compare [CASE…] [--all] [-j N]` | 再次比较现有参考 |
| `status [--list STATE…]` | 每个案例的处境 |
| `review CASE VERDICT [--note TEXT]` | 记录裁决（`auto`：比较的） |
| `settings [--metric M] [--tolerance T]` | 比较的度量和容差 |
| `diff CASE [--frames N]` | 将 Manim 和 ManimGX 最不同的帧对写为图像 |
| `types` | 每个场景的类型报告 |
| `leaks` | 在一个进程中在其他之后渲染不同的场景 |

`render` 仅在像素更改时重写本地视频，更新该视频的 SHA-256 伴随文件，且仅在事实更改时更新 `case.json`。渲染 Manim 的参考（`ce` 引擎，以及场景更改时两个引擎）需要 Manim Community Edition：`uv sync --group ce`（见[搭建](index.md#manim-community-edition)）。

### 审查面板

判断案例意味着查看它。`just review` 构建面板的网页（Svelte，由 bun 用 Vite 构建到 `web/dist`）并服务它，带其 FastAPI 服务器，在 <http://127.0.0.1:8000>。面板浏览语料库，并排显示每个案例两个引擎的帧，并记录裁决；它还更改比较的设置并再次渲染案例。

对于面板本身的工作，`uv run fastapi dev` 单独服务服务器，随其更改重新加载，`bun run dev` 在 `tests/integration/review/web/` 中服务页面。

见 [`tests/integration/review/`](https://github.com/academa-labs/manimgx/tree/main/tests/integration/review)。

## 覆盖率

覆盖率说明测试运行 ManimGX 的哪些行，因此哪些行没有测试检查。`just test-coverage` 用 [pytest-cov](https://pytest-cov.readthedocs.io) 运行套件：终端中的摘要，以及 `htmlcov/index.html` 中的每行。

`pyproject.toml` 中的 `[tool.coverage.run]` 在测试进程和它们启动的进程中测量包（语料库在每个案例自己的进程中渲染），路径相对于仓库，因此不同系统上的运行合并：`just combine-coverage <folder>` 将其数据文件合并为一份报告。

Test 工作流合并其运行的覆盖率并发布报告，由 Cloudflare 服务，如
[`.github/deploy/coverage.jsonc`](https://github.com/academa-labs/manimgx/blob/main/.github/deploy/coverage.jsonc)
所述：`main` 的在 <https://coverage.manimgx.academa.ai>，pull request 的（来自本仓库分支）在预览地址，每个提交的从其"coverage"状态链接。

## 基准测试

速度是功能，使 ManimGX 变慢的更改是如任何其他一样的回归。基准测试在
[`tests/benchmarks/`](https://github.com/academa-labs/manimgx/tree/main/tests/benchmarks)，
以两种方式寻找一个：成本法则，与套件其余部分一起运行；以及定时基准测试，单独运行。

### 没有基准测试持有秒数

断言"此场景在两秒内渲染"的测试检查机器与检查代码一样多。场景在一台机器上比另一台慢两倍（GitHub 给相差 1.5 倍的机器同一运行器标签），而在一台机器上一次运行与下一次相差几个百分点。因此没有基准测试将测量与写下的数字比较：每个并排比较两次测量。

- **工作**，渲染做什么，在每台机器上相同，可以精确计数：ManimGX 运行的 Python 函数及其循环迭代（用
  [`sys.monitoring`](https://docs.python.org/3/library/sys.monitoring.html) 计数）、从几何各部分计算的点、哈希的字节、交给引擎的字节
  （[`work.py`](https://github.com/academa-labs/manimgx/blob/main/tests/benchmarks/work.py)）。
  法则比较同一事物两个大小的工作。
- **时间** 只能与同一机器同一时间测量的时间比较。定时基准测试交替运行此检出和另一个提交的 ManimGX，并逐轮比较。

### 成本法则

[`test_laws.py`](https://github.com/academa-labs/manimgx/blob/main/tests/benchmarks/test_laws.py)
陈述工作如何增长，Hypothesis 检查它：

- **增长。** 加倍制作的事物最多做两倍工作，留十分之一的余量（两倍分辨率的表面，四倍）：逐曲线构建的路径、一起播放的形状组、写入的文本、每帧重绘的图、追踪更长的路径、保持更长的影片、布局的表格。有些随增长对 Python 无更多成本，其数组做增长（`PYTHON`：一旦元素，无循环运行）。每个是一行，
  `law(build, sizes, power)`：`build(n)` 设置大小为 n 的运行并返回它，仅运行被计数。Hypothesis 绘制大小，且
  [`target`](https://hypothesis.readthedocs.io/en/latest/reference/api.html#hypothesis.target)
  向最差比率攀登；最大大小总是运行。计数 ManimGX 无内容的法则失败。
- **共享。** 任何 mobject 的副本，移动、转动和缩放，上传一个所做的：形状上传一次，其副本和移动是其放置。Hypothesis 从每个公共 mobject 类的注册表绘制类，以及副本和移动。
- **静止。** 保持 mobject 静止的场景（无更新器的）一秒做的工作与半分钟一样多：保持的帧发送一次。
- **历史。** 讲述四次的故事做两次讲述的两倍工作：场景保持的任何内容不使其后续帧更贵。

它们用 `just test` 运行，在秒内，在每个系统上。它们发现更改工作如何增长的内容：当路径读取其所有点以找到其终点时（在 `eef74e37` 中修复），两倍曲线的路径计算四倍的点，路径和追踪路径的法则在该代码上失败。今天失败的法则标记 `xfail(strict=True)` 及其原因，代码修复之日标记必须去掉。

工作看不到变慢的操作，同一调用每次花更长时间：那是定时基准测试的用途。

### 定时基准测试

工作负载是如用户渲染般渲染的场景：`manimgx render`，在自己的进程中，从启动到完成的视频。工作负载在
[`test_speed.py`](https://github.com/academa-labs/manimgx/blob/main/tests/benchmarks/test_speed.py)，
是三个场景，在 1920 × 1080 和每秒 60 帧，如 README 的
[基准测试](https://github.com/academa-labs/manimgx/tree/main/benchmarks)制作自己的
（[`scenes/`](https://github.com/academa-labs/manimgx/tree/main/tests/benchmarks/scenes)：
相机环绕的表面、每帧重建的表面和 2D 讲解），以及六个示例影片在 480 × 270 和每秒 10 帧。在套件中，每个渲染一次，微小：它仍渲染。`just bench` 将它们与另一个 ManimGX 计时：

```sh
just bench                # 此检出对照 main
just bench HEAD           # 你的未提交更改对照上次提交
just bench v0.1.0         # 对照任何提交、分支或标签
just bench ../manimgx-2   # 对照另一个检出，如磁盘上的
just bench main -k orbit  # 一些工作负载（参数传递给 pytest）
```

- REF 的 ManimGX 在 pytest 的缓存（`.pytest_cache/`）中从 git 制作：当 REF 的引擎源码（`rust/`）是此检出时用此检出的引擎，否则构建（首次需要几分钟）。不同的引擎拥有其构建目录，因此编译输出不能在两个源码树之间交叉。
- 每次运行是全新进程，带固定哈希种子和空临时目录，因此没有运行找到另一个的 Typst 布局。它从启动到退出测量：README 计时的内容，包括导入、GPU 启动、故事板和编码器。
- 判定的是主机暴露的最稳定度量。当每个样本有正指令计数时，比较使用进程退役的指令，不随运行它的核或机器其他活动而变。在一台 GPU 被其他程序保持 90% 忙碌的 Mac 上，相同的树在每轮中一致到 1.7% 以内；其 CPU 时间相差达 36%，墙时间 57%。如果任何计数器不可用，如在托管的 macOS VM 上，每个样本和重试使用 CPU 时间，每个线程的。每个工作负载的行命名其度量。墙时间包括争用和等待；它和进程的峰值内存被报告但不判定。
- 一轮运行两者，随机顺序。第一轮不保留：它将每个树的文件读入磁盘缓存（一分钟前制作的树在此之前慢 12%）。然后五轮（`--bench-rounds`）。
- 一轮的两个度量产生比率。工作负载在中位数比率超过 1 以上 5% 且轮次一致，五个全部一致时变慢：机器的噪声使比率双向，真实更改移动所有。看起来变慢的工作负载再计时五轮，在所有十个上判定：九个必须一致。然后其测试失败。REF 无法渲染的工作负载（它使用 REF 之后的内容）被跳过。
- 每个树的工作也计数，一次，表格显示更改的计数："points ×7328" 说明减速做了什么。

放入代码，减速在花费 5% 或更多之处找到；无更改时无发现。在那台忙碌的 Mac 上测量，提交 `289730bd`：

| 此检出 | 发现变慢的工作负载 | 最大变化，及其工作 |
| --- | --- | --- |
| 未更改 | 无：每轮在 1.7% 以内 | 无计数更改 |
| 整体读取路径以追加曲线（`eef74e37` 回退） | neural_untangle，尝试的 3 个中 | +60%：7,328 倍的点 |
| 每帧 0.5 毫秒的 Python | 9 个中的 5 个 | +9%（讲解）：循环 ×6.2 |
| ManimGX 导入时 150 毫秒的工作 | 9 个中的 4 个 | +13%（taylor_poles） |
| 表面精炼两次 | morph | +50% |

在一个进程中计时每个场景的帧，如基准测试之前所做，看不到 ManimGX 导入时做的工作；在那台 Mac 上判定 CPU 时间，相同的树快 12%，对影片从不运行的代码的更改使其"慢 5%"，每轮都是。指令看不到的等待（进程休眠直到 GPU 完成）或在 GPU 上做的工作显示在墙时间列：在安静机器上阅读它。

[基准测试工作流](github-workflows.md#2-benchmarkyaml) 在 macOS 上为更改包的每个 pull request 运行它们，对照其基线，以及为每次推送到 `main`，对照其前一个提交；其表格在运行的摘要中。度量是退役 CPU 指令（当可用时），否则 CPU 时间，Metal 在 GPU 上绘制。这门控主机工作，包括几何、排版和编码；不门控 GPU 执行或等待。对于着色器或 GPU 调度的更改，在安静机器上审查配对墙时间；在 Linux 上用 lavapipe 的 `just bench` 还在其 CPU 度量中包括软件绘制。九个工作负载、其分辨率和轮次在任一系统上相同。意在花费时间的更改（功能）在其 pull request 中说明，带表格。

## 了解更多

- [`test_corpus.py`](https://github.com/academa-labs/manimgx/blob/main/tests/integration/test_corpus.py)：三项检查。
- [`corpus/case.py`](https://github.com/academa-labs/manimgx/blob/main/tests/integration/corpus/case.py)：案例持有什么，及其状态。
- [`corpus/__main__.py`](https://github.com/academa-labs/manimgx/blob/main/tests/integration/corpus/__main__.py)：语料库的工具。