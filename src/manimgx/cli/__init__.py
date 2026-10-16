"""ManimGX 命令行：将场景渲染为视频、检视、演示，以及实时预览。

    manimgx render scene.py [Scene] [-o video.mp4]      视频、分镜图、布局问题
    manimgx inspect scene.py [Scene] [-t 0,2.5,end]    时间线、分镜图、布局问题
    manimgx present scene.py [Scene]                    其各节作为幻灯片，在浏览器中展示
    manimgx preview scene.py [Scene]                    播放窗口，每次保存时重新生成

命令所写入的内容输出到 stdout，每个文件一行，随后是报告；错误输出到 stderr。
成功时退出码为 0，场景失败（或 `inspect` 发现问题）时为 1，命令有误时为 2。
当输出被管道重定向时（如智能体的 shell），帮助信息为纯文本；在终端中则为富文本。
"""

import sys

from manimgx import _engine

# A command that draws starts the GPU before the rest of the command line loads (its modules,
# then the scene's file), so that the GPU comes up meanwhile; `--version`, `--help` and
# `preview` (its window draws its takes) never bring it up.
DRAWING = ("render", "inspect", "present")
if sys.argv[1:2] and sys.argv[1] in DRAWING and not {"-h", "--help"} & set(sys.argv):
    _engine.start_gpu()

from importlib.metadata import version
from typing import Annotated

import typer

from manimgx.cli.export import inspect, present, render
from manimgx.cli.preview import preview

app = typer.Typer(
    name="manimgx",
    no_args_is_help=True,
    add_completion=False,
    rich_markup_mode="rich" if sys.stdout.isatty() else None,
    pretty_exceptions_enable=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


def _version(shown: bool) -> None:
    if shown:
        typer.echo(f"manimgx {version('manimgx')}")
        raise typer.Exit


@app.callback()
def manimgx(
    _: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version,
            is_eager=True,
            help="显示版本号并退出。",
        ),
    ] = False,
) -> None:
    """面向智能体的动画引擎：以 Manim 的 Python API 极速生成数学和 3D 视频，底层基于 Rust GPU 核心。

    场景文件是 Manim CE 代码：`import manimgx as m`，一个继承 m.Scene 的类及其
    `construct`。在循环中工作：

    \b
        manimgx inspect scene.py            时间线、分镜图、布局问题
        manimgx inspect scene.py -t 1.5,end  检视特定时刻
        manimgx render scene.py             视频（MP4），附带相同报告

    文件写在场景文件旁边；每个命令会打印其写入的文件。"""


app.command()(render)
app.command()(inspect)
app.command()(preview)
app.command()(present)


def main() -> None:
    app(prog_name="manimgx")
