"""命令行场景运行：其参数、源文件、格式、影片与面向作者的报错。"""

import dataclasses
import difflib
import importlib.util
import linecache
import os
import re
import sys
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import CodeType, ModuleType
from typing import Annotated, Self

import typer
from rich.console import Console

import manimgx
from manimgx.animation.timeline import Animation
from manimgx.config import Config, config
from manimgx.rendering.film import (
    DEFAULT_ENCODER_CRF,
    DEFAULT_ENCODER_PRESET,
    Film,
    FrameSink,
    Play,
    X264Preset,
)
from manimgx.scene import Scene


@dataclass(frozen=True, slots=True)
class Size:
    """图片的像素尺寸。"""

    width: int
    height: int

    def __str__(self) -> str:
        return f"{self.width}x{self.height}"


def size(text: str) -> Size:
    """将 `WIDTHxHEIGHT` 解析为尺寸。"""
    width, _, height = text.lower().partition("x")
    try:
        parsed = Size(int(width), int(height))
    except ValueError:
        raise typer.BadParameter(
            f"{text!r} is not WIDTHxHEIGHT, e.g. 1280x720"
        ) from None
    if parsed.width <= 0 or parsed.height <= 0 or parsed.width % 2 or parsed.height % 2:
        raise typer.BadParameter(
            f"{text!r}: width and height must be even and positive"
        )
    return parsed


File = Annotated[
    Path,
    typer.Argument(
        metavar="FILE",
        help="场景文件：定义 ManimGX 场景的 Python 文件。",
        show_default=False,
    ),
]
SceneName = Annotated[
    str | None,
    typer.Argument(
        metavar="SCENE",
        help=(
            "场景（文件中的一个类）；仅当文件定义了多个场景时需要。"
        ),
        show_default=False,
    ),
]
# a scene's format is its own — what its file sets in `config`, else 1920x1080 at 60 fps — unless
# an option says otherwise
Resolution = Annotated[
    Size | None,
    typer.Option(
        "--resolution",
        "-r",
        parser=size,
        metavar="WxH",
        help=(
            "像素，如 1280x720。[默认：场景的 config，未设置则为 1920x1080]"
        ),
        show_default=False,
    ),
]
Fps = Annotated[
    int | None,
    typer.Option(
        min=1,
        help="每秒帧数。[默认：场景的 config，未设置则为 60]",
        show_default=False,
    ),
]


PACKAGE = str(Path(manimgx.__file__).parent)

# names from older Manim (CE before 0.x renames, manimgl) and what ManimGX has instead
RENAMED = {
    "ShowCreation": "Create",
    "ShowCreationThenDestruction": "ShowPassingFlash",
    "ShowCreationThenFadeOut": "ShowPassingFlash",
    "CircleIndicate": "Circumscribe",
    "WiggleOutThenIn": "Wiggle",
    "TextMobject": "Text (plain text) or Tex (text with LaTeX)",
    "TexText": "Tex",
    "OldTexText": "Tex",
    "TexMobject": "MathTex",
    "OldTex": "MathTex",
    "FadeInFrom": "FadeIn(mobject, shift=direction)",
    "FadeInFromDown": "FadeIn(mobject, shift=UP)",
    "FadeOutAndShift": "FadeOut(mobject, shift=direction)",
    "FadeInFromLarge": "FadeIn(mobject, scale=factor)",
    "GraphScene": "a Scene with Axes (axes.plot(f))",
    "ParametricSurface": "Surface",
    "ContinualAnimation": "mobject.add_updater(function)",
}


def _names() -> list[str]:
    return [name for name in dir(manimgx) if not name.startswith("_")]


def hints(error: BaseException) -> list[str]:
    """针对场景作者在命名上的错误，提示应改用什么。"""
    text = str(error)
    if isinstance(error, AttributeError) and (
        match := re.search(r"module 'manimgx' has no attribute '(\w+)'", text)
    ):
        return [_instead(match.group(1))]
    if isinstance(error, AttributeError) and error.obj is not None and error.name:
        close = difflib.get_close_matches(error.name, dir(error.obj), n=3, cutoff=0.6)
        if close:
            return [f"did you mean {' or '.join(close)}?"]
    if isinstance(error, NameError) and error.name:
        if error.name in _names():
            return [
                f"{error.name} is manimgx.{error.name}: `import manimgx as m`, then "
                f"m.{error.name}"
            ]
        if error.name in RENAMED:
            return [_instead(error.name)]
    if isinstance(error, ModuleNotFoundError) and error.name in ("manim", "manimlib"):
        return ["manimgx is the module: `import manimgx as m` (its API is Manim CE's)"]
    return []


def _instead(name: str) -> str:
    if name in RENAMED:
        return f"{name} is {RENAMED[name]} in ManimGX"
    close = difflib.get_close_matches(name, _names(), n=3, cutoff=0.6)
    if close:
        return f"ManimGX has no {name}; did you mean {' or '.join(close)}?"
    return f"ManimGX has no {name}"


def report_error(error: BaseException) -> str:
    """错误经过场景代码后的形式：场景中的最后几帧（以及 ManimGX 抛出它的位置）、
    错误信息和提示。"""
    frames = traceback.extract_tb(error.__traceback__)
    own = [
        f
        for f in frames
        if not f.filename.startswith(PACKAGE)
        and "/typer/" not in f.filename
        and not f.filename.startswith("<")
    ]
    lines: list[str] = []
    for f in own[-3:]:
        lines.append(f"{Path(f.filename).name}:{f.lineno}: in {f.name}")
        if f.line:
            lines.append(f"    {f.line}")
    inside = [f for f in frames if f.filename.startswith(PACKAGE)]
    if inside and frames[-1].filename.startswith(PACKAGE):
        last = inside[-1]
        where = Path(last.filename).relative_to(PACKAGE)
        lines.append(f"  (raised in manimgx/{where}:{last.lineno}, in {last.name})")
    lines.append(f"{type(error).__name__}: {error}")
    lines += [f"hint: {h}" for h in hints(error)]
    return "\n".join(lines)


class Mistake(Exception):
    """命令输入有误；消息说明正确的用法。"""


class Source(SourceFileLoader):
    """当前创作源，不复用带时间戳的字节码，也不写入缓存。"""

    def get_code(self, fullname: str) -> CodeType:
        linecache.cache.pop(self.path, None)
        return self.source_to_code(self.get_data(self.path), self.path)


def load(path: Path) -> ModuleType:
    """以文件名（不含扩展名）为模块名运行该文件，将其目录置于路径最前（使其能导入
    同目录的邻居）——不以 `__main__` 运行，因此其自身的 `if __name__ == "__main__":`
    块保持原位不执行。"""
    defaults = Config()
    for field in dataclasses.fields(Config):
        setattr(config, field.name, getattr(defaults, field.name))
    if not path.is_file():
        raise Mistake(f"{path}: no such file")
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise Mistake(f"{path}: not a Python file")
    spec.loader = Source(path.stem, str(path.resolve()))
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module  # dataclasses and pickles resolve names through it
    sys.path.insert(0, str(path.resolve().parent))
    spec.loader.exec_module(module)
    return module


def scenes(module: ModuleType) -> list[type[Scene]]:
    """模块所定义的场景，按定义顺序排列。"""
    return [
        value
        for value in vars(module).values()
        if isinstance(value, type)
        and issubclass(value, Scene)
        and value.__module__ == module.__name__
    ]


def pick(path: Path, module: ModuleType, name: str | None) -> type[Scene]:
    """`name` 所指名的场景——未指名时，取文件中唯一的场景。"""
    found = scenes(module)
    names = [scene.__name__ for scene in found]
    if name is not None:
        for scene in found:
            if scene.__name__ == name:
                return scene
        close = difflib.get_close_matches(name, names, n=3)
        hint = f" Did you mean {' or '.join(close)}?" if close else ""
        raise Mistake(
            f"{path} has no scene {name!r}.{hint} Its scenes: {', '.join(names)}"
        )
    if len(found) == 1:
        return found[0]
    if not found:
        raise Mistake(f"{path} defines no scene (a subclass of manimgx.Scene)")
    raise Mistake(
        f"{path} defines {len(found)} scenes ({', '.join(names)}): name one after the"
        " file"
    )


@dataclass(frozen=True, slots=True)
class Format:
    """一次拍摄所生成的画面：其像素尺寸和每秒帧数。"""

    width: int
    height: int
    fps: float

    @classmethod
    def own(cls, size: Size | None = None, fps: float | None = None) -> Self:
        """场景自身的格式——即其文件对 `config` 的设置——除非 `size` 或 `fps` 另有指定。"""
        shape = size or Size(config.pixel_width, config.pixel_height)
        return cls(shape.width, shape.height, fps or config.frame_rate)

    def __str__(self) -> str:
        return f"{self.width}x{self.height} at {self.fps:g} fps"


def fail(message: str, code: int = 2) -> typer.Exit:
    """说明出错原因（输出到 stderr）并以 `code` 退出：2 表示命令有误，1 表示场景失败。"""
    typer.echo(message, err=True)
    return typer.Exit(code)


def scene(file: Path, name: str | None) -> type[Scene]:
    """命令所指名的场景：其文件在 ManimGX 自身的配置上运行（文件在此设置的任何内容
    都属于该场景，而非此前某次拍摄），并选出该场景。"""
    try:
        return pick(file, load(file), name)
    except Mistake as mistake:
        raise fail(f"error: {mistake}") from None
    except Exception as error:
        raise fail(report_error(error), 1) from None


type Watch = Callable[[Scene, Play, tuple[Animation, ...]], object]
"""一次播放结束时命令所执行的操作：接收场景（播放结束时的状态）、该次播放及其
所播放的内容。"""


def take(
    kind: type[Scene],
    look: Format,
    *,
    video: str | os.PathLike[str] | None = None,
    frames: FrameSink | None = None,
    plays: Watch | None = None,
    preset: X264Preset = DEFAULT_ENCODER_PRESET,
    crf: float = DEFAULT_ENCODER_CRF,
) -> tuple[Scene, Film]:
    """以 `look` 格式运行场景，生成其影片（以及视频、帧和播放记录，视请求而定）。
    在终端中，stderr 上的状态行会随各次播放的结束而更新。"""
    config.pixel_width, config.pixel_height = look.width, look.height
    config.frame_rate = look.fps
    shown = Console(stderr=True)
    try:
        with shown.status(f"{kind.__name__}…", spinner="dots") as status:
            # after the config: its camera frame follows the picture's shape
            made = kind()

            def hook(play: Play, did: tuple[Animation, ...]) -> None:
                if shown.is_terminal:
                    status.update(
                        f"{kind.__name__}  t = {float(play.end):.1f} s, play"
                        f" #{play.index}"
                    )
                if plays is not None:
                    plays(made, play, did)

            return made, made.render(
                video, frames=frames, plays=hook, preset=preset, crf=crf
            )
    except Exception as error:
        raise fail(report_error(error), 1) from None
