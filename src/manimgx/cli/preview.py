"""`manimgx preview`：在 ManimGX 播放器中展示场景，独立窗口运行，每次保存代码时重新生成。

场景在此运行，如同 `manimgx render` 运行它一样，但其影片被录制为一个片段（参见
[`Film`][manimgx.Film]）并发送至 [`Window`][manimgx.Window]，由后者在生成的同时播放。
保存时场景会重新运行——立即运行：被保存操作标记为过期的运行会被中断——新片段在到达
同一时刻时替换旧片段：编辑不会丢失播放位置。错误会显示在最后一个正常片段之上。
"""

import importlib
import sys
import time
import traceback
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from importlib.abc import MetaPathFinder
from importlib.machinery import ModuleSpec, PathFinder, SourceFileLoader
from pathlib import Path
from types import ModuleType
from typing import Annotated

import typer

from manimgx.cli.scenes import (
    File,
    Format,
    Fps,
    Mistake,
    Resolution,
    SceneName,
    Size,
    Source,
    fail,
    load,
    pick,
    report_error,
    scenes,
)
from manimgx.config import config
from manimgx.rendering.film import Cut
from manimgx.rendering.window import Window

POLL = 0.02  # seconds between looks at the files


def preview(
    file: File,
    name: SceneName = None,
    time_: Annotated[
        float,
        typer.Option(
            "--time", "-t", min=0, help="播放头起始位置，以秒为单位。"
        ),
    ] = 0.0,
    resolution: Resolution = None,
    fps: Fps = None,
) -> None:
    """实时预览场景：在窗口中展示，每次保存代码时重新生成。

    窗口在场景生成的同时播放。保存文件或其旁边导入的模块会重新运行场景，窗口保持
    播放位置；错误显示在最后一帧正常画面之上。包含多个场景的文件播放指定的场景，
    或第一个场景；按 N 和 P 切换其他场景。按键：空格 播放/暂停，← → 5 秒，, . 一帧，
    Option（或 Ctrl）加 ← → 一次播放，? 显示全部按键。关闭窗口或 Ctrl+C 停止。"""
    if not file.is_file():
        raise fail(f"error: {file}: no such file")
    with Window(f"{file.name} — ManimGX", time=time_) as window:
        try:
            files = [file]
            while window.open:
                news = News(files, window)  # the files as this run reads them
                files = run(file, name, resolution, fps, window, news)
                news.watch(files)
                while window.open and not news():
                    time.sleep(POLL)
                if news.asked is not None:
                    name = news.asked
                else:
                    time.sleep(POLL)  # an editor saving in steps: let it finish
        except KeyboardInterrupt:
            pass
    if window.failure is not None:
        raise fail(f"error: the window: {window.failure}", 1)


class News:
    """使一次运行过期的因素：其读取的文件被再次保存，或在窗口中请求了另一个场景。
    调用时检查是否存在过期因素（每 `POLL` 秒检查一次）。"""

    def __init__(self, files: list[Path], window: Window) -> None:
        self.seen = dict(zip(files, stamps(files), strict=True))
        self.window = window
        self.asked: str | None = None
        self.any = False  # there was some
        self.looked = time.monotonic()

    def watch(self, files: list[Path]) -> None:
        """同时监视 `files`：尚未监视的文件以其当前状态加入监视。"""
        new = [f for f in files if f not in self.seen]
        self.seen.update(zip(new, stamps(new), strict=True))

    def __call__(self) -> bool:
        now = time.monotonic()
        if now - self.looked < POLL:
            return False
        self.looked = now
        self.asked = self.window.asked() or self.asked
        files = list(self.seen)
        self.any = self.asked is not None or stamps(files) != list(self.seen.values())
        return self.any


def run(
    file: Path,
    name: str | None,
    resolution: Size | None,
    fps: int | None,
    window: Window,
    news: News,
) -> list[Path]:
    """运行场景一次，将其片段（或错误）送入 `window`，并在 `news` 标记过期时中断。
    返回需要监视的文件：场景文件及其旁边导入的模块。"""
    root = file.resolve().parent
    started = time.perf_counter()

    def take(data: bytes) -> None:
        if news():
            raise Cut  # out of date: run again
        window(data)

    with imports(file, news.watch) as source:
        try:
            module = load(file)
            found = [s.__name__ for s in scenes(module)]
            # unnamed, the file's first scene: its viewer goes to the others in the window (N, P)
            kind = pick(
                file, module, found[0] if name is None and len(found) > 1 else name
            )
            window.scenes(found, kind.__name__)
            look = Format.own(resolution, fps)
            config.pixel_width, config.pixel_height = look.width, look.height
            config.frame_rate = look.fps
            film = kind().render(take=take)
            cut = "cut: " if news.any or not window.open else ""
            typer.echo(
                f"{kind.__name__}: {cut}{film.frame_count} frames in"
                f" {time.perf_counter() - started:.2f} s",
                err=True,
            )
        except Exception as error:
            text = str(error) if isinstance(error, Mistake) else report_error(error)
            typer.echo(text, err=True)
            own = [
                f
                for f in traceback.extract_tb(error.__traceback__)
                if Path(f.filename).resolve().is_relative_to(root)
            ]
            window.failed(
                error, text, own[-1].lineno if own else getattr(error, "lineno", None)
            )
    return list(source.files)


class Sources(MetaPathFinder):
    """一次创作世代所拥有的场景目录导入。"""

    def __init__(
        self, file: Path, host: set[str], watch: Callable[[list[Path]], None] | None
    ) -> None:
        self.root = file.resolve().parent
        self.host = host
        self.watch = watch
        self.modules = {file.stem}
        self.files = {file.resolve()}

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None = None,
        target: ModuleType | None = None,
    ) -> ModuleSpec | None:
        top = fullname.partition(".")[0]
        if top in self.host and top not in self.modules:
            return None
        spec = PathFinder.find_spec(fullname, path, target)
        if spec is None:
            return None
        if "." not in fullname:
            local = PathFinder.find_spec(fullname, [str(self.root)])
            if local is None or local.origin != spec.origin:
                return None
            if spec.origin is None and not set(
                local.submodule_search_locations or ()
            ) & set(spec.submodule_search_locations or ()):
                return None
        elif fullname.rpartition(".")[0] not in self.modules:
            return None
        self.modules.add(fullname)
        if isinstance(spec.loader, SourceFileLoader):
            file = Path(spec.loader.path).absolute()
            # Ownership follows the import entry, including symlinks and namespace portions.
            self.files.add(file)
            if self.watch is not None:
                self.watch([file])
            spec.loader = Source(fullname, str(file))
        return spec


@contextmanager
def imports(
    file: Path, watch: Callable[[list[Path]], None] | None = None
) -> Iterator[Sources]:
    """为一次运行加载场景的模块；保留承载该运行的进程状态。"""
    before, path = dict(sys.modules), sys.path.copy()
    source = Sources(file, {name.partition(".")[0] for name in before}, watch)
    sys.meta_path.insert(sys.meta_path.index(PathFinder), source)
    importlib.invalidate_caches()
    try:
        yield source
    finally:
        sys.meta_path.remove(source)
        sys.path[:] = path
        for name in source.modules:
            if name in before:
                sys.modules[name] = before[name]
            else:
                sys.modules.pop(name, None)


def stamps(paths: list[Path]) -> list[float]:
    """文件的修改时间（已不存在的文件暂记为 0）。"""
    return [p.stat().st_mtime if p.exists() else 0.0 for p in paths]
