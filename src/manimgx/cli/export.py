"""离线场景导出：视频、检视与演示。"""

import json
import os
import re
import time
import webbrowser
from fractions import Fraction
from html import escape
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING, Annotated
from urllib.parse import quote

import typer
from PIL import Image

from manimgx.animation import clock
from manimgx.animation.timeline import Animation
from manimgx.cli.diagnostics import Names, names, written_frame
from manimgx.cli.scenes import (
    File,
    Format,
    Fps,
    Resolution,
    SceneName,
    fail,
    scene,
    take,
)
from manimgx.cli.storyboard import Sheets, Watch, line
from manimgx.config import config
from manimgx.rendering.film import (
    DEFAULT_ENCODER_CRF,
    DEFAULT_ENCODER_PRESET,
    Cut,
    Film,
    Frame,
    Play,
    X264Preset,
)
from manimgx.scene import Scene

if TYPE_CHECKING:
    from manimgx.animation.transform import Transform
    from manimgx.drawing.geometry import Path as MotionPath


def render(
    file: File,
    name: SceneName = None,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="视频文件（.mp4）。[默认：文件旁的 <Scene>.mp4]",
        ),
    ] = None,
    resolution: Resolution = None,
    fps: Fps = None,
    preset: Annotated[
        X264Preset,
        typer.Option(
            help="编码速度：更快的预设编码更早完成，但生成更大的文件。"
        ),
    ] = DEFAULT_ENCODER_PRESET,
    crf: Annotated[
        float,
        typer.Option(
            min=0,
            max=51,
            help="视频质量：值越低质量越高、文件越大。",
        ),
    ] = DEFAULT_ENCODER_CRF,
) -> None:
    """将场景渲染为带声音的 MP4 视频。

    同时在视频旁写入分镜图（每次播放结尾的帧，布局问题以边框标出并编号）并列出
    这些问题——参见 `manimgx inspect`——若场景包含语音或字幕，还写入字幕文件（.srt）。"""
    kind = scene(file, name)
    video = output or file.with_name(f"{kind.__name__}.mp4")
    if video.suffix.lower() != ".mp4":
        raise fail(f"error: {video}: ManimGX writes MP4 video; name the output *.mp4")
    look = Format.own(resolution, fps)
    watch = Watch(Sheets(video.with_name(f"{video.stem}.storyboard.png")))
    started = time.perf_counter()
    try:
        made, _ = take(kind, look, video=video, plays=watch, preset=preset, crf=crf)
    finally:
        sheets = watch.storyboard.close()
    took = time.perf_counter() - started
    megabytes = video.stat().st_size / 1e6
    typer.echo(
        f"{video}  {float(made.clock):.2f} s, {look}, {megabytes:.1f} MB "
        f"(rendered in {took:.1f} s)"
    )
    typer.echo(f"storyboard: {', '.join(str(s) for s in sheets)}")
    subtitles = made.film.subtitles()
    if subtitles:
        srt = video.with_suffix(".srt")
        srt.write_text(subtitles, encoding="utf-8")
        typer.echo(f"subtitles: {srt}")
    typer.echo(watch.report(timeline=False, film=made.film))


def moments(given: list[str]) -> set[Fraction | None]:
    """以秒为单位的互异时刻；None 表示 `end`。`-t 1,2` 等价于 `-t 1 -t 2`。"""
    out: set[Fraction | None] = set()
    for part in (p.strip() for text in given for p in text.split(",")):
        if not part:
            continue
        try:
            moment = None if part == "end" else Fraction(part)
            if moment is not None and moment < 0:
                raise ValueError
        except (ValueError, ZeroDivisionError):
            raise fail(
                f"error: {part!r} is not a time: non-negative seconds or 'end'"
            ) from None
        out.add(moment)
    if given and not out:
        raise fail("error: --time needs seconds from the start, or 'end'")
    return out


def inspect(
    file: File,
    name: SceneName = None,
    time: Annotated[
        list[str] | None,
        typer.Option(
            "--time",
            "-t",
            metavar="TIME",
            help=(
                "从开始的秒数，或 'end'；多个时刻：重复 -t 或用逗号"
                " 分隔。"
            ),
            show_default=False,
        ),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="分镜图（.png）。[默认：文件旁的 <Scene>.storyboard.png]",
        ),
    ] = None,
) -> None:
    """检视场景：生成标注 PNG、时间线和二维布局检查，不生成视频。

    默认采样各次播放和等待的结尾。使用 -t 时，检视视频播放器在那些时刻显示的帧；
    'end' 表示最后一帧。检查内容包括内容被裁剪、文字重叠、线条或填充覆盖文字、
    以及标签过小。三维场景生成图片和时间线；布局检查被跳过。仅检视被采样的时刻。

    图片按时间顺序排列，标注为 #play t=… file:line，问题以边框标出并编号。
    每张分镜图放六张图片（多余的放入 `<name>-2.png`、……）。默认采样省略连续相同
    的图片。使用 -t 时，仅绘制请求的帧，且除非包含 'end'，场景在最后一个请求帧
    所属的播放结束后停止。

    存在布局问题时退出码为 1；提示（如图形超出画面）不计入问题。
    """
    kind = scene(file, name)
    wanted = moments(time or [])
    target = output or file.with_name(f"{kind.__name__}.storyboard.png")
    if target.suffix.lower() != ".png":
        raise fail(
            f"error: {target}: a storyboard is a PNG image; name the output *.png"
        )
    look = Format.own()
    fps = clock.rational(look.fps)
    # The last sample no later than the requested observed instant.
    pending = sorted(
        ((clock.frame_at(t, fps, after=True) - 1, t) for t in wanted if t is not None),
        reverse=True,
    )
    known: Names | None = None
    watch = Watch(Sheets(target))

    class Sampling(Scene):
        """通过场景现有的求值方法观察选定的帧。"""

        def _emit(self, repeat: int = 1) -> None:
            while pending and pending[-1][0] < self.frame + repeat:
                when = Fraction(pending.pop()[0]) / fps
                watch.see(self, when, known=known)
            super()._emit(repeat)

        def _pure_tweens(
            self, anim: Animation, alpha: list[float]
        ) -> "tuple[list[tuple[Transform, MotionPath]], set[int]] | None":
            if pending and pending[-1][0] < self.frame + len(alpha):
                return None  # this play needs its mutable world at the selected frames
            return super()._pure_tweens(anim, alpha)

    def ended(made: Scene, play: Play, animations: tuple[Animation, ...]) -> None:
        nonlocal known
        if not made.three_d:
            known = names(made, written_frame())
        watch.lines.append(line(play, animations))
        if None not in wanted and not pending:
            raise Cut  # the play showing the last frame asked for is over

    try:
        # Only an inspection with selected frames uses the adapter. Scene and render
        # keep their ordinary evaluation path, including subclasses' overrides.
        observed = (
            type(kind.__name__, (kind, Sampling), {"__module__": kind.__module__})
            if pending
            else kind
        )
        made, film = take(observed, look, plays=ended if wanted else watch)
        if pending:
            raise fail(
                f"error: the scene ends at {float(made.clock):.2f} s; there is no frame at"
                f" {pending[-1][1]} s",
                1,
            )
        if None in wanted or (not wanted and not film.plays):
            watch.see(made, Fraction(film.frame_count - 1) / fps, known=known)
    finally:
        sheets = watch.storyboard.close()
    typer.echo(
        f"{file}: {kind.__name__}, {float(made.clock):.2f} s, {len(film.plays)} plays"
    )
    typer.echo(f"storyboard: {', '.join(str(s) for s in sheets)}")
    typer.echo(watch.report(film=film if not wanted or None in wanted else None))
    if watch.layout.numbers:
        raise typer.Exit(1)


def present(
    file: File,
    name: SceneName = None,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="视频文件（.mp4）；页面写在其旁（.html）。[默认:"
            " 文件旁的 <Scene>.mp4]",
        ),
    ] = None,
    resolution: Resolution = None,
    fps: Fps = None,
    pdf: Annotated[
        bool,
        typer.Option(
            help="同时写入 PDF：每张幻灯片结束时的画面，每张一页。"
        ),
    ] = False,
    show: Annotated[
        bool, typer.Option("--open/--no-open", help="在浏览器中打开页面。")
    ] = True,
) -> None:
    """演示场景：其各节即为幻灯片。

    渲染视频，写入一个播放该视频的页面（在每个节末暂停，直到你继续），并打开它。
    按键：→ 或空格 下一张，← 上一张，F 全屏，B 黑屏，Shift+P 演讲者视图
    （备注、下一张幻灯片、计时器），C 字幕，? 帮助。翻页器可用：它发送相同的按键。
    在场景中用 `self.next_section(...)` 开始一个节。
    """
    kind = scene(file, name)
    video = output or file.with_name(f"{kind.__name__}.mp4")
    if video.suffix.lower() != ".mp4":
        raise fail(f"error: {video}: ManimGX writes MP4 video; name the output *.mp4")
    look = Format.own(resolution, fps)
    pictures: list[bytes] = []  # the pictures slides end on, for the PDF
    last: list[Frame] = []

    def keep(frame: Frame) -> None:
        if frame.key and frame.index > 0:
            pictures.append(frame.pixels())
        last[:] = [frame]

    started = time.perf_counter()
    made, film = take(kind, look, video=video, frames=keep if pdf else None)
    if pdf and last:
        pictures.append(last[0].pixels())  # the film's last picture ends the last slide
    html = video.with_suffix(".html")
    html.write_text(page(film, Path(video.name), kind.__name__), encoding="utf-8")
    slides = len(film.sections)
    typer.echo(
        f"{video}  {float(made.clock):.2f} s, {look}, {slides} slides (rendered in"
        f" {time.perf_counter() - started:.1f} s)"
    )
    typer.echo(f"{html}")
    if pdf:
        size = (config.pixel_width, config.pixel_height)
        images = [Image.frombytes("RGBA", size, p).convert("RGB") for p in pictures]
        handout = video.with_suffix(".pdf")
        images[0].save(handout, save_all=True, append_images=images[1:])
        typer.echo(f"{handout}")
    if show:
        webbrowser.open(html.resolve().as_uri())


def page(film: Film, video: str | os.PathLike[str], title: str = "ManimGX") -> str:
    """演示 `film` 的页面，其视频为 `video`（路径或 URL，页面据此查找：
    通常相对于页面）。

    Args:
        film: 已渲染的影片。
        video: 页面查找视频的位置：URL 字符串或文件系统路径
            （相对于页面，除非为绝对路径）。
        title: 页面的标题。

    Returns:
        页面的 HTML。
    """
    deck = {
        "fps": float(film.fps),
        "frames": film.frame_count,
        "sections": [
            {"name": s.name, "frame": s.frame, "type": s.type, "notes": s.notes}
            for s in film.sections
        ],
        "captions": [[c.start, c.end, c.text] for c in film.captions()],
    }
    html = (files("manimgx") / "cli" / "present.html").read_text(encoding="utf-8")
    if not isinstance(video, str):
        path = Path(video)
        video = path.as_uri() if path.is_absolute() else quote(path.as_posix())
    values = {
        "DECK_TITLE": escape(title),
        "DECK_VIDEO": escape(video),
        "DECK_JSON": json.dumps(deck).replace("</", "<\\/"),
    }
    return re.sub(r"DECK_(?:TITLE|VIDEO|JSON)", lambda match: values[match[0]], html)
