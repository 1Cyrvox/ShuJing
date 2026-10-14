# 引擎

引擎是 [`rust/engine/`](https://github.com/1Cyrvox/ShuJing/tree/main/rust/engine) 中的 Rust crate，Rust 工作区 [`rust/`](https://github.com/1Cyrvox/ShuJing/tree/main/rust) 的 crate 之一。maturin 将其编译为包中的 `manimgx._engine`，一个 Python 扩展模块。它做三件事：在 GPU 上绘制帧，将其编码为 MP4，以及排版文本。Python 决定每帧显示什么；引擎生成像素。它还将影片记录为 *take*，即同样的工作写下来，供 ManimGX 的播放器播放：一个播放器，在本机屏幕上自己的窗口中（`manimgx preview`）和在页面的画布上相同，在页面处引擎本身编译为 WebAssembly 即为播放器。

## 为什么用编译的引擎？

绘制一帧意味着计算数百万像素，而 GPU 通过 Python 无法直接访问的原生 API（Metal、Vulkan）完成。Typst 是 Rust 库，x264 是 C 库。编译的扩展模块将它们全部保持在 Python 进程中：没有子进程，也没有在程序之间传递文件。

crate 的依赖承担繁重工作：

- [wgpu](https://wgpu.rs)：一个 GPU API 覆盖 Metal、Vulkan 等。
- [PyO3](https://pyo3.rs)：Python 模块、其类和其函数。
- [wasm-bindgen](https://wasm-bindgen.github.io/wasm-bindgen/)：播放器到 JavaScript 的绑定，以及 wgpu 到浏览器 WebGPU 和 Web Audio 的绑定。
- [Typst](https://github.com/typst/typst)（`typst`、`typst-kit`、`typst-layout`）：排版器，作为库。
- [mitex](https://github.com/mitex-rs/mitex)：将 LaTeX 转换为 Typst。
- [x264](https://www.videolan.org/developers/x264.html)：H.264 编码器，C 库，从其源码与引擎一起构建（`rust/x264/`）。
- [FFmpeg](https://ffmpeg.org) 的音频解码器，带 [libopus](https://opus-codec.org) 用于 Opus：C 库，从其源码与引擎一起构建（`rust/ffmpeg/`）。
- [winit](https://github.com/rust-windowing/winit)：`manimgx preview` 播放的窗口；
  [cpal](https://github.com/RustAudio/cpal)：其声音，在 macOS 和 Windows 上。
- [rustybuzz](https://github.com/harfbuzz/rustybuzz)，Typst 用于排版文本的整形器，以及
  [unicode-bidi](https://github.com/servo/unicode-bidi)：播放器界面的文本，分行。

## 文件

| 文件 | 包含的内容 |
| --- | --- |
| [`src/lib.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/lib.rs) | crate：其构建（特性），以及内容键 |
| [`src/render.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/render.rs) | GPU 的播放器（`Player`，Python 的也是）：形状存储、一帧的通道、GPU |
| [`src/lavapipe.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/lavapipe.rs) | Mesa 的 lavapipe，Linux wheel 内置的，在没有 GPU 驱动处加载 |
| [`src/python.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/python.rs) | Python 模块：`Player` 和 `Recorder` 类以及 Python 调用的函数 |
| [`src/take.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/take.rs) | take 的消息，写入和读取 |
| [`src/pack.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/pack.rs) | take 的数组，每个对照其替换的编码 |
| [`src/project.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/project.rs) | 投影器：take 按需到达，任意帧按需绘制，在有限内存中 |
| [`src/player.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/player.rs) | ManimGX 的播放器，在任何屏幕上：时钟上的投影器、其界面和声音、其查看器的输入 |
| [`src/chrome.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/chrome.rs) | 播放器的界面（其控件、其文字），由引擎自身绘制 |
| [`src/text.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/text.rs) | 界面的文字：按 Typst 整形的行，在 ManimGX 的字体中 |
| [`src/speaker.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/speaker.rs) | 播放器的声音，跟随其时钟：窗口的（cpal）、页面的（Web Audio） |
| [`src/window.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/window.rs) | 本机屏幕上窗口中的播放器（winit） |
| [`src/web.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/web.rs) | 页面画布上的播放器（WebAssembly） |
| [`src/export.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/export.rs) | 影片的视频：帧转换并交给编码器 |
| [`src/vector.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/vector.rs)、[`src/vector.wgsl`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/vector.wgsl) | 路径覆盖和视图合成 |
| [`src/blend.wgsl`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/blend.wgsl) | 光栅管线：点云和网格 |
| [`src/paint.wgsl`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/paint.wgsl) | 绘制，两个管线评估它的方式 |
| [`src/nv12.wgsl`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/nv12.wgsl) | 帧的已更改宏块，为编码器转换 |
| [`src/encode.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/encode.rs) | 通过 x264 的 H.264 |
| [`src/mp4.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/mp4.rs) | MP4 文件 |
| [`src/audio.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/audio.rs) | 从文件读取的声音（FFmpeg），以及重采样 |
| [`src/aac.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/aac.rs) | 影片的声音，作为 AAC |
| [`src/typeset.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/typeset.rs) | 作为库的 Typst，以及 mitex |
| [`build.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/build.rs) | 页面的播放器，在 Pyodide 模块旁构建并携带在其中 |
| [`../mitex-spec-gen/`](https://github.com/1Cyrvox/ShuJing/tree/main/rust/mitex-spec-gen) | mitex 的 Typst 包（获取的），以及从中制作的 LaTeX 命令规格 |
| [`../x264/`](https://github.com/1Cyrvox/ShuJing/tree/main/rust/x264) | x264，从其源码构建（获取的），在 C 垫片和几个安全调用之后 |
| [`../nasm/`](https://github.com/1Cyrvox/ShuJing/tree/main/rust/nasm) | NASM，从其源码构建（获取的），用于 x264 的 x86-64 汇编 |
| [`../ffmpeg/`](https://github.com/1Cyrvox/ShuJing/tree/main/rust/ffmpeg) | FFmpeg 的音频解码器和 libopus，从其源码构建（获取的），在 C 垫片和一个安全调用之后 |
| [`../fetch/`](https://github.com/1Cyrvox/ShuJing/tree/main/rust/fetch) | 其他 crate 构建所用的源码，由其构建脚本获取并按其文件哈希固定 |

每个文件以声明其设计的注释开始。

## 与 Python 的边界

[`src/manimgx/_engine.pyi`](https://github.com/1Cyrvox/ShuJing/blob/main/src/manimgx/_engine.pyi)
是引擎的接口，如 Python 所见，带类型：`Player` 和 `Recorder` 类、排版函数、`digest`（命名上传内容的键）、`note` 和 `TypstError`。它手工编写，因此引擎接口的更改也更改它；ty 据此检查 Python 代码。

- **一个模块适用于 3.13 起的每个 Python。** crate 针对 Python 的稳定 ABI 构建（PyO3 的 `abi3-py313`）。
- **字节，而非对象。** 跨越的是打包数组：控制点为 float64，336 字节的记录，float32 的视图。Python 用 numpy 打包它们
  （[`rendering/feed.py`](https://github.com/1Cyrvox/ShuJing/blob/main/src/manimgx/rendering/feed.py)）；
  引擎按原样读取。形状按其对象定义的方式跨越，引擎推导绘制所需：展平路径的曲线，并将网格面的法线求和到其顶点。
- **上传一次，然后每帧。** `add_path`、`add_points`、`add_mesh`、`add_rows` 和
  `add_texture` 在键下存储形状、一组颜色行或图像；`grow_path` 扩展路径，`evict` 遗忘不再显示的帧。然后帧是视图及其记录：`render` 绘制一帧并读回为 RGBA，`push` 将一帧发送到 `begin_export` 开始且 `end_export` 完成的视频。
- **take 是同样的调用，写下来。** `Recorder` 接受 `Player` 接受的上传，然后每帧的 `frame`，并将它们写为消息：一个 take，投影器读回（见[播放器](#the-player)和[浏览器](#the-browser)）。给定 `take` 的影片记录到一个中。
- **释放 GIL** 在引擎绘制和编码时，因此其他 Python 线程运行。
- **每进程一个 GPU**，在进程知道将绘制时在其自己的线程上启动（`start_gpu`）：绘制命令在命令行其余部分加载之前启动它，带视频或帧的影片在开始时启动。它同时启动，第一帧等待它；从不绘制的进程（`manimgx --version`、take、只计帧数的影片）从不启动它。在 GPU 启动之前结束的进程等待它，在 Python 退出时：退出卸载驱动程序，且不能在启动时卸载。

## 绘制

wgpu 采用高性能适配器：macOS 上 Metal，Windows 上 Direct3D 12（无 GPU 时 WARP，在 CPU 上），Linux 上 Vulkan。引擎需要一个能混合 float32 渲染目标的适配器，因为 2D 视图将其覆盖率加到其中。

在 Linux 上，没有适配器可用时（无 GPU 驱动：服务器、容器），引擎用 Mesa 的 lavapipe 绘制，即 CPU 上的 Vulkan，Linux wheel 在其旁边内置它
（`manimgx/lavapipe/libvulkan_lvp.so`，从 Mesa 源码构建，LLVM 由
[`scripts/release/build_lavapipe.sh`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/release/build_lavapipe.sh) 链接）。
`src/lavapipe.rs` 如 Vulkan 加载器加载驱动一样加载它，并给 wgpu 一个它的实例：系统的加载器和环境都不参与，有 GPU 的机器从不加载它。从源码构建的引擎没有自己的 lavapipe；在那里，系统的 Mesa 绘制。

### 路径覆盖和合成

路径使用展平段的解析覆盖，而非计数多样本命中。同一管线在 2D 和通过 3D 相机绘制路径。

1. 计算通道每帧将每条路径的每条曲线展平为其屏幕上尺寸所需的段数（Wang 界限目标 1/32 像素，每条曲线最多 256 段），以绘制时的尺寸。
2. 光栅通道将每段的精确面积加到对象的 float 图集矩形中：填充按其环绕数，描边为沿曲线法线的片段，带其连接和端点。
3. 计算通道按深度顺序合成视图每个 16×16 块上到达的每个对象，以绘制顺序打破平局。它将每个像素保持为两个区域，由一条线分割，以保留共享边的重叠。

段面积是解析的；完整图像是近似。曲线被展平，覆盖以浮点累积，每个部分覆盖层的边界重建为半平面。两个区域不能保留多个部分层的每个交点。合成还将近平行边界近似为平行，并在图集组之间合并其区域。当多条边或透明表面在一个像素内相遇时，这些限制有影响。

2D 视图的点云和网格由光栅管线绘制，到合成按其顺序放置的层中。

见 `vector.rs` 和 `vector.wgsl`。

### 光栅管线

光栅管线绘制点云和网格，带每样本深度。在 3D 视图中，其光栅基与路径的解析覆盖和深度平面组合。顶点由混合本身放置：
clip = C₁·S₁ + C₂·S₂，其中 Cₖ = camera · Mₖ 在 CPU 上每对象组合一次（第二项仅在形状变形时）。类型仅在顶点如何变为三角形上不同：

- 点是面向相机的圆盘。
- 网格是其三角形，可选纹理化。

透明网格片段收集在列表中并按深度顺序合成。点精灵在其他几何体的深度层之间排序和绘制。光栅样本覆盖和路径的重建覆盖是不同的表示；它们的组合不保留每个子像素重叠。

相机的图像，如 [`ZoomedScene`][manimgx.ZoomedScene] 所示，是先绘制到纹理中的视图，帧随后按其键采样。

见 `blend.wgsl`，以及 `render.rs` 中的 `Player`。

### 绘制

`paint.wgsl` 为两个管线共享。颜色在 OKLab 中混合，按不透明度加权，如 Python 的颜色混合。渐变是均匀间隔的停止点。补间的绘制是两个绘制及第二个混入的程度：引擎混合它们，因此补间不上传任何内容。

## 编码

**问题：** 逐帧编码视频在未更改处重复工作，而动画的大部分帧不变：移动的正方形只触及图像的几个块。

**引擎的答案：** 记录说明什么更改了，因此只转换、读回和分析那些。

1. 对每帧，引擎找到可能与前一帧不同的 16×16 宏块：每个更改记录的旧和新足迹。新相机、添加或移除的对象，或任何无法界定的内容使之为整帧。
2. 它在 GPU 上仅将这些宏块转换为 NV12（`nv12.wgsl`），并仅读回那些。
3. x264 在其自己的线程上被告知哪些宏块未更改，跳过其分析（`encode.rs`）。
4. `mp4.rs` 将每幅图像写为 MP4 的一个样本；保持的帧是一个持续更久的样本。每个样本在 B 帧更改解码顺序时保持其持续时间。解码时钟累积这些持续时间；有符号合成偏移保留编写的显示时间。这是 MP4 定时契约：样本表定时决定呈现，包括最终保持，独立于编码器的解码时间戳。头部先写，因此播放器可在文件到达之前开始。

[`Film.export`][manimgx.Film.export] 报告进展如何：所用秒数、其中 x264 部分、转换的宏块份额，以及文件大小。

x264 与引擎一起从其源码构建（r3229，8 位，无命令行），因此无需安装，引擎静态链接它。其构建脚本写入 x264 的 `configure` 会为目标生成的配置，然后用 `cc` crate 编译其 C 和汇编：AArch64 上用 C 编译器的 NEON 和 SVE；x86-64 上用 NASM 的 SSE 到 AVX-512，x264 的 x86 代码即为此编写。NASM 也来自其源码（`rust/nasm/`）：编译到 x264 的构建脚本中，后者将其作为自身进程运行。其他地方仅 x264 的 C；汇编使 x264 快两到五倍。Rust 通过 `x264/src/shim.c` 看到 x264，后者设置 x264 的参数并移入图像和移出样本，因此 x264 的结构从不跨入 Rust。构建需要几秒，并产生与 `configure` 构建的 x264 相同的字节。

## 排版

`typeset.rs` 将 Typst 作为库运行。`typeset` 接受 Typst 源码并返回其布局，直接从 Typst 的帧读取：每个字形及其轮廓键、其位置、其绘制和其绘制的源码字节；每个形状为三次曲线；每个标记组为其内部项。字形的轮廓单独获取，按键（`glyph_outlines`），因此只跨越一次。

字体来自 Python 传递的文件夹，其中包括 ManimGX 自己的：字体包
（[`fonts/manimgx-fonts/`](https://github.com/1Cyrvox/ShuJing/tree/main/fonts/manimgx-fonts)
和
[`fonts/manimgx-fonts-cjk/`](https://github.com/1Cyrvox/ShuJing/tree/main/fonts/manimgx-fonts-cjk)，
单独发布并要求精确版本），然后是 Typst 的嵌入字体。系统的字体仅在文本命名的族中读取：其扫描在磁盘上缓存，它们是内存映射的，而非整体读取（CJK 字体可达 60 MB）。

LaTeX 通过 mitex（`mitex_math`、`mitex_text`）到达 Typst。mitex 按 *命令规格* 转换：它知道哪些 LaTeX 命令，以及每个接受多少参数。mitex 自己的规格 crate 从 git 子模块读取规格或用 PATH 上的 `typst` 制作；
`rust/Cargo.toml` 将该 crate 替换为
[`mitex-spec-gen`](https://github.com/1Cyrvox/ShuJing/tree/main/rust/mitex-spec-gen)，
后者获取 mitex 的 Typst 包（带其自己的 `lib.typ`，仅导入转换的 LaTeX 调用的作用域）并持有从中制作的规格（`spec.rkyv`）。引擎将包作为 `@preview/mitex:0.2.7` 服务给 Typst，因此转换的代码在磁盘上无文件即找到其作用域，转换器和它为之转换的 Typst 代码来自相同文件。`cargo test -p mitex-spec-gen`，在 `rust/` 中，检查提交的规格仍是包制作的，且引擎服务其每个文件；mitex 升级后，`MITEX_SPEC=write cargo test -p mitex-spec-gen` 写入新规格。Test 工作流通过 `just test-rust` 与 Rust 工作区其余部分一起检查规格；它从不重新生成它。

## 播放器

ManimGX 的播放器播放 take：[`manimgx preview`](../user-guide/rendering.md#preview) 和本机屏幕上自己窗口中的 [`Window`][manimgx.Window]，以及页面画布上的 npm 包。它是一个播放器，`player.rs`，两个屏幕上相同的代码：屏幕给它一个表面，传递其查看器的输入，在到期时绘制它并执行其请求。窗口的屏幕是 winit 的（`window.rs`）；页面的是编译为 WebAssembly 的引擎（`web.rs`），页面的元素传递其事件
（[`browser/src/player.ts`](https://github.com/1Cyrvox/ShuJing/blob/main/browser/src/player.ts)）。

- **任意帧，一次。** 播放器按发送方式保持 take（`project.rs`），并在其时钟所处时刻、以显示的尺寸、在屏幕自己的像素中绘制该帧。更新的 take，即场景再次运行，在到达所示时刻后替换所示的一个，或结束：编辑不会丢失位置。take 以自己的消息（END）结束，说明其场景是否失败：失败的 take 仅在到达所示时刻时替换所示的一个。保存使一个运行过时（take 引发 `Cut`），场景立即再次运行。其透明层溢出列表的帧在其计数恢复后再次绘制：播放器从不等待 GPU。
- **一个时钟。** 它从某时刻以某速率运行，在 take 录制时在制作的最后一帧等待，并在结束时停止；帧为所见时刻绘制（屏幕提前刷新）。声音跟随它（`speaker.rs`），在时钟运行时连续，在跳跃或 30 毫秒漂移后再次从时钟：在窗口中，为所听时刻写入（cpal；Linux 上窗口无声，因为系统的音频是链接的 ALSA）；在页面中，在上下文时刻启动的 Web Audio 源在时钟到达时听到（其输出时间戳将上下文时钟与页面的绑定）。
- **其界面是引擎自己的绘制。** 控件、时间、播放（其章节，由播放它们的行命名）、字幕、错误和键是形状和文字，影片上 2D 视图的记录，精确绘制（`chrome.rs`）：无工具包，两个屏幕上一个界面。其文字按行排版，在 ManimGX 的字体中（`text.rs`），由 rustybuzz 整形，即 Typst 用于排版的整形器：一个测试以两种方式设置界面的行，并在相同位置找到相同的字形。Typst 本身，文档排版器，在页面中将是 28 MB 的 WebAssembly；行只需 0.7 MB。播放器在一次通道中将影片和界面合成。控件在布局放置之处，因此点击、轻触和按键做同样的事。
- **以 Web 的语言输入。** 键以其 `KeyboardEvent.key` 值到达（winit 以 Web 的方式命名键），指针以其像素位置，滚轮的转动以点，Web 的方式。每个输入说明播放器是否接受它，因此页面让其余的通过：影片上的垂直滚动滚动页面，水平滚动移动播放头。
- **注释，双向。** 导演的注释（JSON）给它播放、章节和字幕，take 之间还有文件的场景和场景的错误。播放器请求文件的另一个场景：窗口将请求写为标准输出上的一行 JSON，页面将其发布给其导演。

窗口是自己的进程（`python -m manimgx.rendering.window`，其主线程运行窗口的事件循环，`_engine.window`），take 通过管道在其标准输入上到达它：因此场景保持其进程——其主线程、其信号——如 `manimgx render` 给的，脚本或笔记本可以打开一个，崩溃的场景留下窗口。`Window` 是一个 take：`Scene.render(take=window)`。关闭它切断发送给它的影片（`Cut`）；它在导演关闭它或离开时关闭。在页面上，播放器在页面自己的线程上运行，如窗口的在它自己的上：其事件、其时钟、其绘制和其声音在一个线程上，因此它立即说明是否接受了输入。

在 M4 Pro 上测量：保存后 43-79 毫秒在屏幕上；窗口以每帧 0.5-1.7 毫秒（中位数）绘制最重的示例影片（Hopf 纤维化，2560×1440），在 60 Hz 时使用 5-17% 的一个核心，150-320 MB。在 Chrome 中，页面的线程每帧花 0.7 毫秒，包括界面（中位数；95 百分位 1.2 毫秒，1920×1080）。

## 浏览器

在浏览器中，Python 在 [Pyodide](https://pyodide.org) 中运行，它没有 GPU，引擎是同一 crate 的两个 WebAssembly 构建：

- **Python 模块，无 GPU**（特性 `python` 和 `typeset`）：排版、内容键、声音读取和 `Recorder`，但无 `Player`。Pyodide 的工具链为 `wasm32-unknown-emscripten` 编译它，它作为 ManimGX 的浏览器 wheel 发布
  （`pyemscripten_2026_0_wasm32`，[PEP 783](https://peps.python.org/pep-0783/)）。在那里，每个影片记录为 take。
- **播放器**（特性 `web`，用于 `wasm32-unknown-unknown`）：页面画布上的 `player.rs`，用 WebGPU 绘制和 Web Audio 发声（`web.rs`）。页面的元素在其到达时交给它 take（`feed`）、其查看器的输入（`key`、`pointer`、`press`、`release`、`cancel`、`wheel`）及其画布的尺寸，并在到期时绘制它（`wake`、`draw`）。它按发送方式保持 take，编码，并在帧绘制时从中制作帧的形状；GPU 的播放器保持最近绘制帧所绘制的，在预算内。其界面的字体来自 Pyodide，即窗口界面排版的字体：`_engine.face_fonts` 给出 ManimGX 的字体文件和 Typst 的等宽字体。
  [`browser/`](https://github.com/1Cyrvox/ShuJing/tree/main/browser) 持有页面侧：元素和导演的 worker（Pyodide）。

take 是 Python 和播放器之间的协议：`manimgx preview` 通过管道将一个发送到其窗口，在浏览器中导演从 Pyodide 将一个交给页面。其上传持有的内容作为数组（`pack.rs`），每个在其种类和内容键下，发送一次，并对照其替换的数组编码：同一角色在前一帧同一记录槽绘制的内容，写入者从帧的记录中读取。形状每帧稍变的影片作为其更改发送：示例影片的 take 因此小 14 倍（之前共 50 GB，之后 3.6 GB），30 秒的 3D 影片是几十兆字节，而之前是千兆字节。网格的点、uv 和法线以 float32 发送，即 GPU 绘制它们的精度；其他一切按 Python 给的精确发送。浏览器和原生播放器共享 take 解码器和渲染器。回放和直接渲染在同一适配器和运行时上检查相同像素。不同的 GPU 后端、驱动程序和编写运行时可能产生不同的浮点结果；共享渲染器不保证跨它们的相同像素。

每个 take 以其格式版本开始，暴露给 Python 为 `_engine.TAKE_VERSION`。它覆盖视图、记录、上传和编码数组的布局。共享投影器在读取资源之前检查它，因此原生窗口、浏览器和无头回放以显式错误拒绝不支持或未版本化的录制。对这些布局的更改若改变其含义需要新的格式版本；包发布和参考清单有各自的版本。

## 他人的源码

仓库仅持有 ManimGX 的代码。引擎从他人编写的构建——x264 和 NASM、FFmpeg 的音频解码器和 libopus、mitex 的 Typst 包——其 crate 的构建脚本从每个项目发布处获取（`fetch::tree`，在 `rust/fetch/` 中），每个按其文件的 SHA-256 固定：其路径和字节，而非归档的，主机重新生成后者，因此相同文件的任何副本都通过。树获取一次到 crate 的构建文件夹并按该哈希再次找到。首次构建需要网络，如 cargo 对 crate 所做。`MANIMGX_SOURCES` 为归档命名一个文件夹（绝对路径）：构建从那里读取归档，如果不在则先下载到那里。持有它们的文件夹离线构建；你的检出共享的一个每个归档只下载一次；构建到空的一个收集它构建自的内容。构建脚本在每个目标上获取相同的归档，无论编译其中的什么，因此一次构建收集每次构建读取的内容。

发布在 wheel 旁发布 `manimgx-X.Y.Z-source.tar.xz`（`just build-source` 制作它）。它是提交的仓库，由 `SOURCE_COMMIT` 标识，带 `vendor/`，`rust/Cargo.lock` 命名的每个 crate（`cargo vendor`），`sources/`，归档，以及读取它们的 `.cargo/config.toml`，离线。Mesa、glslang 和 LLVM 通过 `fetch-file` 使用同一存储，按其归档哈希固定。LLVM 以其原生目标和在重物化期间保留寄存器类约束的源码修正构建；其补丁和构建配方在 `scripts/release/` 中。Linux wheel 作业还保留 auditwheel 实际内置的库的精确源 RPM，由 auditwheel 的 SBOM 标识。每个平台的清单记录其 wheel 哈希、二进制包版本和源哈希。
`just build-source` 消耗两个 Linux 源构件，合并到 `release-sources/`，并在添加到源归档之前检查这些哈希。

归档提供分发组件的源码；它不冻结操作系统或编译器工具链。重建 lavapipe 使用其检查的归档、源码补丁和构建配方以及所需的 Linux 构建工具。引擎本身在安装 Rust、C 编译器和 Python 构建依赖（包括 maturin）后无需获取原生源码或 Cargo crate 即可构建：

```sh
tar -xf manimgx-X.Y.Z-source.tar.xz
cd manimgx-X.Y.Z && uv build --wheel --no-build-isolation --offline
```

每个由其 crate 的构建脚本用 `cc` crate、单独的 C 编译器构建，在每个目标上相同：没有项目自己的构建系统运行。x264 和 NASM 的脚本写入其 `configure` 会为目标生成的配置。FFmpeg 的 `configure` 一次解析了 ManimGX 解码用的组件，`rust/ffmpeg/build.rs` 保持其解析的内容（它开启的名称、编译的文件；命令在脚本的注释中）：其配置从那里以可移植 C 写入（无汇编、无线程：一次解码一个文件），在每个目标上相同，包括浏览器的。Opus 到 libopus，即参考解码器，通过 RFC 8251 的所有测试向量（FFmpeg 自己的失败四个）。`rust/ffmpeg/src/shim.c` 从内存解码文件到 float 样本，最多两通道（更宽的声音下混为立体声，缩放使其不削波），在文件声明处开始和结束。

在 Windows 上，`rust/dxc/` 准备精确的上游 DirectX 着色器编译器归档，验证其 SHA-256，并将 `dxcompiler.dll` 放在安装的扩展旁。引擎从该包位置加载它。其单独固定的源码树和源依赖为源码分发保留，其声明在 `LICENSE-DXC` 中；DLL 是官方二进制输入，而非每个 wheel 安装重建的编译器。

## 构建

- `uv sync` 和每次 `uv run` 在其某个源码更改时用 maturin 的发布构建重建引擎：见
  [项目管理](project-management.md#rebuilding-the-engine)。
- `just build-wheel` 如发布一样用 cibuildwheel 构建本机的 wheel，并在每个支持的 Python 上测试它（见
  [项目管理](project-management.md#distribution)）；`just build-wheel pyodide` 用 Pyodide 的工具链构建浏览器的。
- `build.rs` 用 Pyodide 的模块构建页面的播放器（自己的 cargo，在 `rust/target/web-player/` 中），模块携带它：`_engine.web()` 给出其 JavaScript 和 WebAssembly（`engine.js`、`engine_bg.wasm`），导演将其交给页面。它需要 Rust 的 WebAssembly 目标（`rustup target add wasm32-unknown-unknown`）；没有它模块构建，带警告。原生模块不携带任何：原生地，影片在窗口中播放。
- 在 `rust/` 中手动运行 Cargo（`cargo clippy`、`cargo test -p mitex-spec-gen`、
  `cargo test -p fetch`）使用 `dev` 配置，它也优化（`opt-level = 2`）。
- `rust/engine/Cargo.toml` 拒绝 Clippy 的正确性 lint 并对其可疑和性能 lint 发出警告。没有配方、检查或工作流运行 Clippy：在 `rust/` 中运行 `cargo clippy`。

安装的 wheel 套件和集成语料库测试 Python 边界（见[测试](testing.md)）。`just test-rust` 在 Linux、macOS 和 Windows 上测试 Rust 工作区，带渲染、导出、排版和播放器特性，不嵌入 Python。这些测试检查 take 读回如写入、其数组编码精确解码，以及投影器如何接收 take：更新的一个在所示帧替换所示的一个，失败的一个被丢弃或结束，流无论怎么切断都完整读取。它们还检查播放器：其键按 Web 的名称、其章节、take 的声音读回如写入，以及界面的行，按 Typst 排版。`just check-rust-web` 检查浏览器特性边界，`just test-rust-web` 用 wasm-bindgen-test-runner 和浏览器驱动运行其浏览器测试；CI 使用 Chrome。这些聚焦的法则补充了浏览器中完整场景的手动播放。fetch crate 的测试，也是 `just test-rust` 的一部分，检查 `MANIMGX_SOURCES`：空文件夹收集归档，完整的，满的在归档从其 URL 消失时构建。