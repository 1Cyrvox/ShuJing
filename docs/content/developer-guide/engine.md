# 引擎

引擎是 [`rust/engine/`](https://github.com/1Cyrvox/ShuJing/tree/main/rust/engine) 中的 Rust crate，Rust
工作空间 [`rust/`](https://github.com/1Cyrvox/ShuJing/tree/main/rust) 的 crate 之一。
maturin 将它编译进包中作为 `manimgx._engine`，一个 Python 扩展模块。它
做三件事：在 GPU 上绘制帧、将它们编码为 MP4，以及排版文本。
Python 决定每一帧显示什么；引擎制作像素。它还将一个影片记录为
一个*take*，即写下来的相同工作，供 ManimGX 的播放器播放：一个播放器，在本
机屏幕上其自身的窗口中（`manimgx preview`）和在页面的画布上是相同的，在
页面画布上，编译为 WebAssembly 的引擎本身就是播放器。

## 为什么用编译引擎？

绘制一帧意味着计算数百万像素，而 GPU 通过 Python 无法直接访问的原生
API（Metal、Vulkan）来完成。Typst 是一个 Rust 库，x264
是一个 C 库。一个编译的扩展模块将它们全部容纳在 Python 进程中：没有
子进程，也没有在程序之间传递的文件。

该 crate 的依赖承担繁重工作：

- [wgpu](https://wgpu.rs)：一个覆盖 Metal、Vulkan 和其他的 GPU API。
- [PyO3](https://pyo3.rs)：Python 模块、其类和其函数。
- [wasm-bindgen](https://wasm-bindgen.github.io/wasm-bindgen/)：播放器到
  JavaScript 的绑定，以及 wgpu 到浏览器 WebGPU 和 Web Audio 的绑定。
- [Typst](https://github.com/typst/typst)（`typst`、`typst-kit`、`typst-layout`）：
  排版器，作为一个库。
- [mitex](https://github.com/mitex-rs/mitex)：将 LaTeX 转换为 Typst。
- [x264](https://www.videolan.org/developers/x264.html)：H.264 编码器，一个 C 库，
  从其源码与引擎一起构建（`rust/x264/`）。
- [FFmpeg](https://ffmpeg.org) 的音频解码器，以及用于
  Opus 的 [libopus](https://opus-codec.org)：C 库，从其源码与引擎一起构建（`rust/ffmpeg/`）。
- [winit](https://github.com/rust-windowing/winit)：`manimgx preview` 播放所在的窗口；
  [cpal](https://github.com/RustAudio/cpal)：其声音，在 macOS 和 Windows 上。
- [rustybuzz](https://github.com/harfbuzz/rustybuzz)，Typst 设置文本的整形器，以及
  [unicode-bidi](https://github.com/servo/unicode-bidi)：播放器界面的文本，按行。

## 文件

| 文件 | 容纳内容 |
| --- | --- |
| [`src/lib.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/lib.rs) | 该 crate：其构建（特性）和内容键 |
| [`src/render.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/render.rs) | GPU 的播放器（`Player`，也是 Python 的）：形状的存储、一帧的通道、GPU |
| [`src/lavapipe.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/lavapipe.rs) | Mesa 的 lavapipe，由 Linux wheel 捆绑，在没有 GPU 驱动的地方加载 |
| [`src/python.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/python.rs) | Python 模块：`Player` 和 `Recorder` 类以及 Python 调用的函数 |
| [`src/take.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/take.rs) | 一个 take 的消息，写入和读取 |
| [`src/pack.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/pack.rs) | 一个 take 的数组，每个针对它替换的那个编码 |
| [`src/project.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/project.rs) | 投影器：take 如其到来，按需绘制其中任意一帧，在有界内存中 |
| [`src/player.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/player.rs) | ManimGX 的播放器，在任意屏幕上：时钟上的投影器、其界面和声音、其查看器的输入 |
| [`src/chrome.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/chrome.rs) | 播放器的界面（其控件、其文本），由引擎自身绘制 |
| [`src/text.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/text.rs) | 界面的文本：按 Typst 整形的方式排列的行，使用 ManimGX 的字体 |
| [`src/speaker.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/speaker.rs) | 播放器的声音，跟随其时钟：窗口的（cpal）、页面的（Web Audio） |
| [`src/window.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/window.rs) | 本机屏幕上窗口中的播放器（winit） |
| [`src/web.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/web.rs) | 页面画布上的播放器（WebAssembly） |
| [`src/export.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/export.rs) | 影片的视频：转换并交给编码器的帧 |
| [`src/vector.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/vector.rs), [`src/vector.wgsl`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/vector.wgsl) | 路径覆盖和视图的合成 |
| [`src/blend.wgsl`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/blend.wgsl) | 光栅管线：点云和网格 |
| [`src/paint.wgsl`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/paint.wgsl) | 绘制属性，两条管线如此求值它 |
| [`src/nv12.wgsl`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/nv12.wgsl) | 一帧变化的宏块，为编码器转换 |
| [`src/encode.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/encode.rs) | 通过 x264 的 H.264 |
| [`src/mp4.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/mp4.rs) | MP4 文件 |
| [`src/audio.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/audio.rs) | 从其文件读取的声音（FFmpeg），并重采样 |
| [`src/aac.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/aac.rs) | 影片的声音，作为 AAC |
| [`src/typeset.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/src/typeset.rs) | 作为库的 Typst，以及 mitex |
| [`build.rs`](https://github.com/1Cyrvox/ShuJing/blob/main/rust/engine/build.rs) | 页面的播放器，在 Pyodide 的模块旁构建并携带于其中 |
| [`../mitex-spec-gen/`](https://github.com/1Cyrvox/ShuJing/tree/main/rust/mitex-spec-gen) | mitex 的 Typst 包（获取的），以及从中制作的 LaTeX 命令规格 |
| [`../x264/`](https://github.com/1Cyrvox/ShuJing/tree/main/rust/x264) | x264，从其源码构建（获取的），在一个 C 垫片和少数安全调用之后 |
| [`../nasm/`](https://github.com/1Cyrvox/ShuJing/tree/main/rust/nasm) | NASM，从其源码构建（获取的），用于 x264 的 x86-64 汇编 |
| [`../ffmpeg/`](https://github.com/1Cyrvox/ShuJing/tree/main/rust/ffmpeg) | FFmpeg 的音频解码器和 libopus，从其源码构建（获取的），在一个 C 垫片和一个安全调用之后 |
| [`../fetch/`](https://github.com/1Cyrvox/ShuJing/tree/main/rust/fetch) | 其他 crate 构建所用的源码，由其构建脚本获取并以其文件的哈希固定 |

每个文件以一段陈述其设计的注释开始。

## 与 Python 的边界

[`src/manimgx/_engine.pyi`](https://github.com/1Cyrvox/ShuJing/blob/main/src/manimgx/_engine.pyi)
是引擎的接口，如 Python 所见，带类型：`Player` 和 `Recorder` 类、
排版函数、`digest`（命名上传内容的键）、`note`
和 `TypstError`。它是
手写的，因此对引擎接口的更改也会更改它；ty 据此检查 Python
代码。

- **从 3.13 起每个 Python 一个模块。** 该 crate 针对 Python 的稳定
  ABI 构建（PyO3 的 `abi3-py313`）。
- **字节，而非对象。** 传递的是打包的数组：控制点为 float64、
  336 字节的记录、float32 的视图。Python 用 numpy 打包它们
  （[`rendering/feed.py`](https://github.com/1Cyrvox/ShuJing/blob/main/src/manimgx/rendering/feed.py)）；
  引擎按原样读取它们。一个形状按其对象定义的方式传递，且
  引擎导出绘制所需的内容：它扁平化路径的曲线，并将网格的面求和
  为其顶点的法线。
- **上传一次，然后逐帧。** `add_path`、`add_points`、`add_mesh`、`add_rows` 和
  `add_texture` 在一个键下存储一个形状、一组颜色行或一个图像；`grow_path`
  扩展一个路径，`evict` 遗忘不再有帧显示的内容。然后一帧是一个视图
  及其记录：`render` 绘制一帧并读回为 RGBA，`push` 将一帧发送到
  `begin_export` 启动且 `end_export` 完成的视频。
- **一个 take 是相同的调用，写下来。** `Recorder` 接受 `Player` 接受的上传，
  然后为每一帧 `frame`，并将它们写为消息：一个 take，投影器将其读回
  （参见[播放器](#_10)和[浏览器](#_11)）。一个给定 `take`
  的影片记录进一个。
- **GIL 被释放**，当引擎绘制和编码时，因此其他 Python 线程运行。
- **每个进程一个 GPU**，一旦进程知道它将
  绘制（`start_gpu`）就在其自身的线程上启动：一个绘制命令在命令行其余部分加载之前启动它，
  一个带视频或帧的影片在其开始时启动它。它同时启动，第一帧
  等待它；一个从不绘制的进程（`manimgx --version`、一个 take、一个仅
  计其帧的影片）从不启动它。一个在 GPU 启动之前结束的进程等待
  它，当 Python 退出时：退出卸载驱动程序，且不得在它启动时卸载一个。

## 绘制

wgpu 选取高性能适配器：macOS 上的 Metal、Windows 上的 Direct3D 12（在没有
GPU 时为 CPU 上的 WARP）、Linux 上的 Vulkan。引擎需要一个能混合
float32 渲染目标的适配器，因为 2D 视图在一个目标中累加其覆盖。

在 Linux 上，当没有适配器可用时（没有 GPU 驱动：服务器、容器），引擎用
Mesa 的 lavapipe（CPU 上的 Vulkan）绘制，Linux wheel 将其捆绑在旁
（`manimgx/lavapipe/libvulkan_lvp.so`，从 Mesa 的源码构建，LLVM 由
[`scripts/release/build_lavapipe.sh`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/release/build_lavapipe.sh) 链入）。
`src/lavapipe.rs` 如同 Vulkan 的加载器加载驱动那样加载它，并给 wgpu 一个它的
实例：系统的加载器和环境都不参与，有 GPU 的机器
从不加载它。从源码构建的引擎没有自己的 lavapipe；在那里，系统的 Mesa
绘制。

### 路径覆盖与合成

路径使用扁平化段的解析覆盖，而非计数多样本命中。
同一管线在 2D 和通过 3D 相机绘制路径。

1. 一个计算通道将每条路径的每条曲线扁平化为其在屏幕上的大小
   所需的段数（Wang 界以 1/32 像素为目标，每条曲线最多 256 段），
   每一帧，按其绘制的大小。
2. 一个光栅通道将每个段的精确面积加到对象在 float
   图集中的矩形中：填充按其环绕数，描边为沿曲线法线的片段，带
   其连接和端点。
3. 一个计算通道将视图的每个 16×16 图块在到达它的对象上合成，
   按深度顺序，绘制顺序打破平局。它将每个像素保持为由一条线分割
   的两个区域，以保留共享边的重叠。

段面积是解析的；完整图像是一个近似。曲线被
扁平化，覆盖以浮点累加，每个部分覆盖层的
边界被重建为半平面。两个区域无法保留多个部分层
的每个交点。合成还将近似平行的边界
近似为平行，并在图集组之间合并其区域。当
多条边或透明曲面在一个像素内相遇时，这些限制很重要。

2D 视图的点云和网格由光栅管线绘制，进入合成
按其顺序放置的层。

参见 `vector.rs` 和 `vector.wgsl`。

### 光栅管线

光栅管线绘制点云和网格，带逐采样深度。在 3D 视图中，
其光栅基与路径的解析覆盖和深度平面组合。
一个顶点由混合本身放置：
clip = C₁·S₁ + C₂·S₂，其中 Cₖ = camera · Mₖ 在 CPU 上每个对象组合一次（第
二项仅在形状变形时）。类型仅在顶点如何变为
三角形上不同：

- 一个点是面向相机的圆盘。
- 一个网格是其三角形，可选带纹理。

透明网格片段被收集在列表中并按深度顺序合成。点
精灵被排序并绘制在其他几何的深度层之间。光栅采样
覆盖和路径重建的覆盖是不同的表示；它们的
组合不保留每个子像素重叠。

一个相机的图像，如 [`ZoomedScene`][manimgx.ZoomedScene] 所示，是一个先绘制
到纹理中的视图，帧随后按键采样它。

参见 `blend.wgsl`，以及 `render.rs` 中的 `Player`。

### 绘制属性

`paint.wgsl` 被两条管线共享。颜色在 OKLab 中混合，按不透明度加权，如同
Python 的颜色混合。一个渐变是均匀间隔的停止点。一个补间的绘制属性是两个绘制属性以及
第二个混入的程度：引擎混合它们，因此一个补间不上传任何东西。

## 编码

**问题：** 逐帧编码视频在未变化处重复工作，而
动画帧的大部分不会变化：一个移动的方形仅触及图像的少数
块。

**引擎的回答：** 记录说明什么变化了，因此仅转换、读回
和分析那些。

1. 对于每一帧，引擎找到可能与前一帧不同的 16×16 宏块：每个变化记录的旧和新足迹。一个新相机、
   添加或删除的对象，或任何无法界定的东西使其成为整帧。
2. 它在 GPU 上仅将那些宏块转换为 NV12（`nv12.wgsl`），并仅读回
   那些。
3. x264 在其自身的线程上被告知哪些宏块未变化并跳过
   那里的分析（`encode.rs`）。
4. `mp4.rs` 将每幅图像写为一个 MP4 的样本；一个保持帧是一个
   持续时间更长的样本。当 B 帧改变解码顺序时，每个样本保持其持续时间。
   解码时钟累加那些持续时间；有符号合成偏移保留
   创作的显示时间。这是 MP4 时序契约：样本表时序决定
   呈现，包括最终保持，独立于编码器的解码时间戳。
   头部先写入，因此播放器可以在文件到达之前开始。

[`Film.export`][manimgx.Film.export] 报告进展如何：所花秒数、其中
在 x264 中的部分、转换的宏块比例，以及文件大小。

x264 与引擎一起从其源码构建（r3223，8 位，无其命令行），因此
无需安装任何东西，引擎静态链接它。其构建
脚本写入 x264 的 `configure` 会为目标写入的配置，然后编译其
C 和其汇编，用 `cc` crate：AArch64 上用 C 编译器的 NEON 和 SVE；在
x86-64 上，用 NASM 的 SSE 到 AVX-512，x264 的 x86 代码即为此编写。NASM 也来自其
源码（`rust/nasm/`）：编译进 x264 的构建脚本，后者将其作为自身的一个进程运行。其他地方，仅 x264 的 C；汇编使 x264 快两到五倍。Rust 通过
`x264/src/shim.c` 看到 x264，后者设置 x264 的参数并将图像移入、样本移出，因此 x264 的结构体从不进入 Rust。构建耗时几秒，并产生
与 `configure` 构建的 x264 相同的字节。

## 排版

`typeset.rs` 将 Typst 作为库运行。`typeset` 接受 Typst 源码并返回其布局，
直接从 Typst 的帧读取：每个字形及其轮廓的键、其位置、其
绘制属性和它绘制的源的字节；每个形状作为三次曲线；每个带标签的
组作为其中的项。一个字形的轮廓单独到来，按键
（`glyph_outlines`），因此它仅传递一次。

字体来自 Python 传递的文件夹，其中包括 ManimGX 自己的：字体包
（[`fonts/manimgx-fonts/`](https://github.com/1Cyrvox/ShuJing/tree/main/fonts/manimgx-fonts)
和
[`fonts/manimgx-fonts-cjk/`](https://github.com/1Cyrvox/ShuJing/tree/main/fonts/manimgx-fonts-cjk)，
独立发布并要求精确版本），然后来自 Typst 的内嵌字体。系统
的字体仅在文本命名的字体系列中被读取：其扫描在磁盘上缓存，且
它们是内存映射的，而非整体读取（一个 CJK 字体可达 60 MB）。

LaTeX 通过 mitex（`mitex_math`、`mitex_text`）到达 Typst。mitex 通过一个
*命令规格*转换：它知道哪些 LaTeX 命令，以及每个命令接受多少参数。mitex
自身的规格 crate 从一个 git 子模块读取规格，或用 PATH 上的一个 `typst` 制作它；
`rust/Cargo.toml` 用
[`mitex-spec-gen`](https://github.com/1Cyrvox/ShuJing/tree/main/rust/mitex-spec-gen)
替换该 crate，
后者获取 mitex 的 Typst 包（带其自身的 `lib.typ`，仅导入转换的 LaTeX 调用的作用域）并持有从中制作的规格（`spec.rkyv`）。引擎将该
包服务于 Typst 自身，作为 `@preview/mitex:0.2.7`，因此
转换的代码在磁盘上无文件的情况下找到其作用域，且转换器和它为之转换的 Typst
代码来自相同的文件。`cargo test -p mitex-spec-gen`，在 `rust/`
中，检查提交的规格仍是该包制作的，且引擎服务于
其每个文件；mitex 升级后，`MITEX_SPEC=write cargo test -p mitex-spec-gen`
写入新规格。Test 工作流通过 `just test-rust` 与 Rust 工作空间的其余部分一起检查规格；它从不重新生成它。

## 播放器

ManimGX 的播放器播放 take：本机屏幕上其自身窗口中的 [`manimgx preview`](../user-guide/rendering.md#_5) 和
[`Window`][manimgx.Window]，页面画布上的 npm 包。它是一个播放器，`player.rs`，两个屏幕上相同的代码：一个屏幕给
它一个表面，传递其查看器的输入，在到期时绘制它并执行它的要求。窗口的屏幕是 winit 的（`window.rs`）；页面的是编译为 WebAssembly
的引擎（`web.rs`），页面的元素传递其事件
（[`browser/src/player.ts`](https://github.com/1Cyrvox/ShuJing/blob/main/browser/src/player.ts)）。

- **任意帧，一次。** 播放器将 take 按发送时的样子保留（`project.rs`），并绘制其时钟
  所在的帧，按其显示的大小，在屏幕自身的像素中。一个更新的 take，即再次
  运行的场景，一旦它有了显示的时刻或结束时就替换显示的那个：一次编辑从不丢失
  位置。一个 take 以其自身的消息（END）结束，说明其场景是否失败：
  一个失败的 take 仅在它到达显示的时刻时才替换显示的那个。一次保存使一次运行它
  使之过时（take 抛出 `Cut`），场景立即再次运行。一个其
  透视层溢出列表的帧在其计数恢复时再次绘制：播放器从不
  等待 GPU。
- **一个时钟。** 它从一个瞬间以一个速率运行，在 take
  被记录时在制作的最后一帧等待，并在结束时停止；一帧为它被看到的时刻绘制（屏幕提前
  刷新）。声音跟随它（`speaker.rs`），在时钟
  运行时连续，在跳变或 30 ms 漂移后再次从时钟：在窗口中，为它
  被听到的瞬间写入（cpal；在 Linux 上窗口是静默的，因为系统的音频会是
  链接的 ALSA）；在页面中，一个在上下文时刻启动的 Web Audio 源，在
  时钟到达时被听到（其输出时间戳将上下文的时钟绑定到页面的）。
- **其界面是引擎自身的绘制。** 控件、时间、play（其章节，
  以播放它们的行命名）、字幕、错误和键是形状和
  文本，影片上 2D 视图的记录，精确绘制（`chrome.rs`）：无工具包，且两个
  屏幕上一个界面。其文本按行设置，用 ManimGX 的字体（`text.rs`），由
  rustybuzz（Typst 设置文本的整形器）整形：一个测试以两种方式设置界面的行并
  在相同位置找到相同的字形。Typst 自身，一个文档排版器，在页面中会是 28 MB
  的 WebAssembly；这些行占 0.7 MB。播放器合成影片，在
  其位置，以及界面在一次通道中。一个控件在布局放置它的地方，因此一次点击、一次轻触和
  一个键做相同的事。
- **以 web 的语言输入。** 一个键以其 `KeyboardEvent.key` 值到来（winit 如 web 那样
  命名键），一个指针以其像素位置，一个滚轮的转动以点，按 web 的方式。每个输入说明播放器是否接受了它，以便页面让其余的通过：在
  影片上的垂直滚动滚动页面，横向滚动移动播放头。
- **注释，双向。** 导演的注释（JSON）给它 play、节和字幕，
  take 之间还有文件的场景和场景的错误。播放器请求文件的
  另一个场景：窗口将该请求写为其标准输出上的一行 JSON，页面
  将其发布给其导演。

窗口是一个独立的进程（`python -m manimgx.rendering.window`，其主
线程运行窗口的事件循环，`_engine.window`），take 通过管道到达它，在其
标准输入上：因此场景保留其进程——其主线程、其信号——如同
`manimgx render` 给它们的，一个脚本或笔记本可以打开一个，一个崩溃的场景
让窗口保持开启。一个 `Window` 是一个 take：`Scene.render(take=window)`。关闭它切断
发送给它的影片（`Cut`）；当其导演关闭它或离开时它关闭。在页面上，播放器
在页面自身的线程上运行，如同窗口在其自身的上：其事件、其时钟、其
绘制和其声音在一个线程上，因此它立即说明是否接受了一个输入。

在 M4 Pro 上测量：一次保存 43-79 ms 后出现在屏幕上；窗口以每帧 0.5-1.7 ms（中位数）绘制最重的
示例影片（Hopf 纤维化，2560×1440），在 60 Hz 下使用一个核心的 5-17%，内存 150-320 MB。在 Chrome 中，页面的线程每帧在其上花 0.7 ms，界面
包含在内（中位数；95 百分位 1.2 ms，在 1920×1080）。

## 浏览器

在浏览器中，Python 在 [Pyodide](https://pyodide.org) 中运行，它没有 GPU，且
引擎是同一 crate 的两个 WebAssembly 构建：

- **Python 模块，无 GPU**（特性 `python` 和 `typeset`）：排版、
  内容键、声音读取和 `Recorder`，但无 `Player`。Pyodide 的工具链为
  `wasm32-unknown-emscripten` 编译它，它作为 ManimGX 的浏览器 wheel 发布
  （`pyemscripten_2026_0_wasm32`，[PEP 783](https://peps.python.org/pep-0783/)）。在那里，每个
  影片被记录为一个 take。
- **播放器**（特性 `web`，用于 `wasm32-unknown-unknown`）：页面画布上的 `player.rs`，
  用 WebGPU 绘制并用 Web Audio 发声（`web.rs`）。页面的元素将
  take 如其到来那样交给它（`feed`）、其查看器的输入（`key`、`pointer`、`press`、`release`、`cancel`、
  `wheel`）及其画布的大小，并在到期时绘制它（`wake`、`draw`）。它将
  take 按发送时的样子保留，编码，并在帧绘制时从中制作帧的形状；GPU 的
  播放器保留最近绘制的帧所绘制的，直到一个预算。其界面的字体来自
  Pyodide，即窗口界面设置的字体：`_engine.face_fonts` 给出 ManimGX 的字体
  文件和 Typst 的等宽字体。
  [`browser/`](https://github.com/1Cyrvox/ShuJing/tree/main/browser) 持有
  页面侧：元素和导演的 worker（Pyodide）。

一个 take 是 Python 和播放器之间的协议：`manimgx preview` 通过一个
管道将一个发送到其窗口，在浏览器中导演将一个从 Pyodide 交给页面。其
上传持有的内容作为数组传递（`pack.rs`），每个在其
类型和内容的键下，发送一次，并针对它替换的数组编码：同一角色在前一帧由同一记录槽绘制的内容，写者从帧的记录中读取。一个
形状每帧变化一点的影片作为其变化发送：示例影片的
take 因此小 14 倍（之前共 50 GB，之后 3.6 GB），一个 30
秒的 3D 影片是几十兆字节，而之前是几千兆字节。一个网格的点、uv 和法线以
float32 传递，即 GPU 绘制它们的精度；其他一切按 Python 给的精确传递。
浏览器和原生播放器共享 take 解码器和渲染器。回放和直接
渲染在同一适配器和运行时上检查相同像素。不同的
GPU 后端、驱动和创作运行时可能产生不同的浮点结果；
共享渲染器不保证它们之间像素相同。

每个 take 以其格式版本开始，向 Python 暴露为 `_engine.TAKE_VERSION`。
它覆盖视图、记录、上传和编码数组的布局。共享投影器
在读取资源之前检查它，因此原生窗口、浏览器和无头回放以
显式错误拒绝不支持或未版本化的录制。对这些布局
的更改若改变其含义则需要新的格式版本；包发布和参考
清单有各自的版本。

## 他人的源码

仓库仅持有 ManimGX 的代码。引擎构建所用的他人所写的内容——
x264 和 NASM、FFmpeg 的音频解码器和 libopus、mitex 的 Typst 包——其 crate 的构建
脚本从每个项目发布它的地方获取（`fetch::tree`，在 `rust/fetch/` 中），每个
以其文件的 SHA-256 固定：它们的路径和字节，而非存档的（主机
重新生成存档），因此相同文件的任何副本都通过。一棵树获取一次到 crate 的
构建文件夹中并按该哈希再次找到。首次构建需要网络，如同 cargo 对
crate 那样。`MANIMGX_SOURCES` 为存档命名一个文件夹（一个绝对路径）：构建在那里读取
一个存档，如果不在则先下载到那里。持有它们的文件夹离线构建；由你的检出共享的一个每个存档仅下载一次；而构建进一个空的
则收集它构建所用的内容。构建脚本在每个目标上获取相同的存档，
无论它编译其中的什么，因此一次构建收集每次构建读取的内容。

发布在 wheel 旁附带 `manimgx-X.Y.Z-source.tar.xz`（`just build-source` 制作它）。
它是提交的仓库，由 `SOURCE_COMMIT` 标识，带 `vendor/`、`rust/Cargo.lock` 命名的每个 crate
（`cargo vendor`）、`sources/`、存档，以及一个读取它们的
`.cargo/config.toml`，
离线。Mesa、glslang 和 LLVM 通过 `fetch-file` 使用同一存储，以其
存档哈希固定。LLVM 以其原生目标和一个在重新具体化期间保留
寄存器类约束的源码修正构建；其补丁和构建配方在
`scripts/release/` 中。Linux wheel 作业还保留 auditwheel 实际捆绑的库的精确源 RPM，由 auditwheel 的 SBOM 标识。每个
平台的清单记录其 wheel 哈希、二进制包版本和源码哈希。
`just build-source` 消耗两个 Linux 源码制品，合并进 `release-sources/`，
并在将它们加入源码存档之前检查那些哈希。

存档提供分发组件的源码；它不冻结操作系统
或编译器工具链。重新构建 lavapipe 使用其检查过的存档、源码补丁
和构建配方以及所需的 Linux 构建工具。引擎本身在安装了 Rust、一个 C 编译器和 Python 构建依赖
（包括 maturin）后，无需获取原生源码或 Cargo crate 即可构建：

```sh
tar -xf manimgx-X.Y.Z-source.tar.xz
cd manimgx-X.Y.Z && uv build --wheel --no-build-isolation --offline
```

每个由其 crate 的构建脚本用 `cc` crate 构建，仅用 C 编译器，在每个目标上相同：没有项目自身的构建系统运行。x264 和 NASM 的脚本写入
其 `configure` 会为目标写入的配置。FFmpeg 的 `configure` 一次性解析
ManimGX 解码所用的组件，`rust/ffmpeg/build.rs` 保留它解析的内容（它
开启的名称、它编译的文件；命令在脚本的注释中）：其
配置据此写入，以可移植 C（无汇编、无线程：一次一个文件解码），在每个目标上相同，包括浏览器的。Opus 交给 libopus，
参考解码器，它通过 RFC 8251 的所有测试向量（FFmpeg 自身的失败四个）。
`rust/ffmpeg/src/shim.c` 从内存解码一个文件为浮点采样，最多两个声道
（更宽的声音下混为立体声，缩放以使其不削波），在文件声明处开始和结束。

在 Windows 上，`rust/dxc/` 准备精确的上游 DirectX Shader Compiler 存档，验证
其 SHA-256，并将 `dxcompiler.dll` 放在已安装扩展旁。引擎从
该包位置加载它。其单独固定的源码树和源码依赖为
源码分发保留，其声明在 `LICENSE-DXC` 中；该 DLL 是一个官方
二进制输入，而非每次 wheel 安装重建的编译器。

## 构建

- `uv sync` 和每次 `uv run` 在其某个源码变化时重建引擎，使用
  maturin 的 release 构建：参见
  [项目管理](project-management.md#_10)。
- `just build-wheel` 如发布那样用 cibuildwheel 构建本机的 wheel，并
  在每个受支持的 Python 上测试它（参见
  [项目管理](project-management.md#_4)）；`just build-wheel pyodide`
  用 Pyodide 的工具链构建浏览器的。
- `build.rs` 用 Pyodide 的模块（其自身的 cargo，在
  `rust/target/web-player/` 中）为页面构建播放器，模块携带它：`_engine.web()` 给出其 JavaScript
  和 WebAssembly（`engine.js`、`engine_bg.wasm`），导演将其交给页面。它
  需要 Rust 的 WebAssembly 目标（`rustup target add wasm32-unknown-unknown`）；没有它
  模块构建，带一个警告。原生模块不携带：原生地，影片在
  窗口中播放。
- 在 `rust/` 中手动运行 Cargo（`cargo clippy`、`cargo test -p mitex-spec-gen`、
  `cargo test -p fetch`）使用 `dev` 配置，它也优化了（`opt-level = 2`）。
- `rust/engine/Cargo.toml` 拒绝 Clippy 的正确性 lint 并对其可疑和
  性能的发出警告。没有配方、检查或工作流运行 Clippy：在 `rust/` 中运行 `cargo clippy`。

已安装 wheel 套件和集成语料库测试 Python 边界（参见
[测试](testing.md)）。`just test-rust` 在 Linux、macOS 和 Windows 上测试 Rust 工作空间，
带 render、export、typeset 和 player 特性，不嵌入 Python。这些测试
检查一个 take 读回如其所写、其数组的编码精确解码，以及投影器如何
接收 take：一个更新的在显示的帧替换显示的、一个失败的被丢弃
或结束、流无论怎样切割都整体读取。它们还检查播放器：其键按
web 的名称、其章节、一个 take 的声音如其所写读取，以及界面的行，按
Typst 设置的方式设置。`just check-rust-web` 检查浏览器特性边界，
`just test-rust-web` 用 wasm-bindgen-test-runner 和一个浏览器
驱动运行其浏览器测试；CI 使用 Chrome。这些聚焦的法则补充了浏览器中完整场景的手动播放。fetch crate 的测试，也是 `just test-rust` 的一部分，检查 `MANIMGX_SOURCES`：一个
空文件夹收集一个存档，完整的，一个满的在其 URL 的存档消失时构建。
