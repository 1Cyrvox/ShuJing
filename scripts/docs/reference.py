"""The command line's reference, from its Typer app: the one page of the API reference that is
generated.

`python -m scripts.docs.reference` writes `docs/content/reference/rendering/command-line.md`
(not committed), so the page always says what the app does. The rest of the reference is
written by hand, in `docs/content/reference/`: its story in prose, and the API in it as
mkdocstrings' `:::` blocks, which render each object from its docstring.
`tests/docs/test_reference.py` keeps the two together: every name the package documents is
on a page, once, and every name a page shows is still in the package.
"""

import subprocess
import sys
from pathlib import Path

REPOSITORY = Path(__file__).parents[2]
PAGE = REPOSITORY / "docs" / "content" / "reference" / "rendering" / "command-line.md"

TRANSLATIONS = [
    ("# Command line", "# 命令行"),
    ("The animation engine for agents: blazingly fast math and 3D videos with Manim's Python API, on a Rust GPU core.",
     "面向智能体的动画引擎：以 Manim 的 Python API，在 Rust GPU 内核上极速生成数学和 3D 视频。"),
    ("A scene file is Manim CE code: `import manimgx as m`, a class deriving m.Scene, its\n`construct`. Work in a loop:",
     "场景文件是 Manim CE 代码：`import manimgx as m`，一个继承 m.Scene 的类，其\n`construct`。在循环中工作："),
    ("    manimgx inspect scene.py            timeline, storyboard, layout problems\n    manimgx inspect scene.py -t 1.5,end  inspect specific moments\n    manimgx render scene.py             the video (MP4), with the same report",
     "    manimgx inspect scene.py            时间线、分镜图、布局问题\n    manimgx inspect scene.py -t 1.5,end 检查特定时刻\n    manimgx render scene.py             视频（MP4），附带相同报告"),
    ("Files are written beside the scene file; each command prints what it wrote.",
     "文件写在场景文件旁边；每条命令都会打印它写了什么。"),
    ("**Usage**:", "**用法**："),
    ("**Options**:", "**选项**："),
    ("**Commands**:", "**命令**："),
    ("**Arguments**:", "**参数**："),
    ("Show the version and exit.", "显示版本并退出。"),
    ("Show this message and exit.", "显示此帮助信息并退出。"),
    ("Render a scene to an MP4 video, with its...", "将场景渲染为 MP4 视频，附带其…"),
    ("Inspect a scene: annotated PNGs, timeline...", "检查场景：带标注的 PNG、时间线…"),
    ("Preview a scene live: in a window, made...", "实时预览场景：在一个窗口中，每次保存…"),
    ("Present a scene: its sections are the slides.", "展示场景：其各节即为幻灯片。"),
    ("Render a scene to an MP4 video, with its sound.",
     "将场景渲染为 MP4 视频，附带其声音。"),
    ("Also writes a storyboard beside the video (the frame at each play's end, layout problems\noutlined and numbered) and lists those problems — see `manimgx inspect` — and, if the\nscene speaks or has subcaptions, its subtitles (.srt).",
     "同时在视频旁边写入分镜图（每次 play 结束时的帧，布局问题以轮廓和编号标出）并列出这些问题——参见 `manimgx inspect`——以及，如果场景有语音或字幕，则写入其字幕（.srt）。"),
    ("Inspect a scene: annotated PNGs, timeline and 2D layout checks, without video.",
     "检查场景：带标注的 PNG、时间线和 2D 布局检查，不生成视频。"),
    ("Samples play and wait endings by default. With -t, inspects the frames a video player\nshows at those times; 'end' is the last frame. Checks for clipped content, overlapping\ntext, lines or fills over text, and small labels. 3D scenes get pictures and a timeline;\nlayout checks are skipped. Only sampled moments are checked.",
     "默认采样各 play 和 wait 的结束时刻。使用 -t 时，检查视频播放器在这些时刻显示的帧；'end' 是最后一帧。检查内容是否被裁剪、文字是否重叠、线条或填充是否覆盖文字，以及标签是否过小。3D 场景得到图片和时间线；布局检查被跳过。仅检查被采样的时刻。"),
    ("Pictures are chronological, captioned #play t=… file:line, with problems outlined and\nnumbered. Six fit on each sheet (more go on `<name>-2.png`, …). Default sampling omits\nconsecutive identical pictures. With -t, only the requested frames are drawn, and the\nscene stops after the last requested frame's play unless 'end' is included.",
     "图片按时间顺序排列，标注 #play t=… file:line，问题以轮廓和编号标出。每张图放六张（多出的放到 `<name>-2.png`，…）。默认采样会省略连续相同的图片。使用 -t 时，仅绘制所请求的帧，且除非包含 'end'，场景在最后一个请求帧的 play 之后停止。"),
    ("Exits 1 for layout problems; notes, such as a graph leaving the frame, do not count.",
     "存在布局问题时以退出码 1 退出；提示（如图形超出画面）不计为问题。"),
    ("Preview a scene live: in a window, made again each time its code is saved.",
     "实时预览场景：在一个窗口中，每次保存其代码时重新生成。"),
    ("The window plays the scene as it is made. Saving the file, or a module it imports from\nbeside it, runs the scene again, and the window keeps its place; an error shows over the\nlast good picture. A file of several scenes plays the one named, or its first; N and P go\nto the others. Keys: Space play/pause, ← → 5 s, , . a frame, Option (or Ctrl) with ← → a\nplay, ? all of them. Closing the window, or Ctrl+C, stops.",
     "窗口播放场景的当前版本。保存文件或其旁边导入的模块时，重新运行场景，窗口保持其位置；错误显示在最后一帧好的画面之上。含多个场景的文件播放指定的那个，或第一个；N 和 P 切换到其他场景。按键：Space 播放/暂停，← → 5 秒，, . 一帧，Option（或 Ctrl）加 ← → 一个 play，? 全部。关闭窗口或 Ctrl+C 停止。"),
    ("Present a scene: its sections are the slides.",
     "展示场景：其各节即为幻灯片。"),
    ("Renders the video, writes a page that plays it (it stops at the end of each section,\nuntil you go on), and opens it. Keys: → or Space next, ← back, F full screen, B black,\nShift+P presenter view (notes, the next slide, a timer), C captions, ? help. A clicker\nworks: it sends the same keys. Begin a section with `self.next_section(...)` in the scene.",
     "渲染视频，写入一个播放它的页面（在每个节末停止，直到你继续），并打开它。按键：→ 或 Space 下一张，← 上一张，F 全屏，B 黑屏，Shift+P 演讲者视图（备注、下一张幻灯片、计时器），C 字幕，? 帮助。翻页器可用：它发送相同的按键。在场景中用 `self.next_section(...)` 开始一个节。"),
    ("The scene file: a Python file defining ManimGX scenes.", "场景文件：一个定义 ManimGX 场景的 Python 文件。"),
    ("The scene (a class in the file); needed only if the file defines several.",
     "场景（文件中的一个类）；仅当文件定义了多个场景时才需要。"),
    ("The video (.mp4).", "视频（.mp4）。"),
    ("The video (.mp4); the page is written beside it (.html).", "视频（.mp4）；页面写在它旁边（.html）。"),
    ("Pixels, e.g. 1280x720.", "像素，例如 1280x720。"),
    ("Frames per second.", "每秒帧数。"),
    ("Encoding speed: faster presets encode sooner but produce larger files.",
     "编码速度：更快的预设编码更早但生成更大的文件。"),
    ("Video quality: lower values give higher quality and larger files.",
     "视频质量：值越低质量越高、文件越大。"),
    ("Seconds from the start, or 'end'; several: repeat -t or separate with commas.",
     "从开始起的秒数，或 'end'；多个：重复 -t 或以逗号分隔。"),
    ("The storyboard (.png).", "分镜图（.png）。"),
    ("Where the playhead starts, in seconds.", "播放头起始位置，以秒为单位。"),
    ("Also write a PDF: the picture each slide ends on, a page each.",
     "同时写入 PDF：每张幻灯片结束时的画面，每张一页。"),
    ("Open the page in the browser.", "在浏览器中打开页面。"),
]


def main() -> None:
    PAGE.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            *(sys.executable, "-m", "typer", "manimgx.cli", "utils", "docs"),
            *("--name", "manimgx", "--title", "Command line"),
            *("--output", str(PAGE)),
        ],
        check=True,
        capture_output=True,
    )
    text = PAGE.read_text(encoding="utf-8")
    for old, new in TRANSLATIONS:
        text = text.replace(old, new)
    PAGE.write_text(text, encoding="utf-8")
    print(f"wrote {PAGE.relative_to(REPOSITORY)}")


if __name__ == "__main__":
    main()
