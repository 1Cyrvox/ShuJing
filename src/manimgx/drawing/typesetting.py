"""Typst 源码 → 其排版布局，在本进程中排版（`_engine.typeset`）并缓存于磁盘。
布局为文档顺序中每个项目（字形或形状）对应一行，包含每个形状的曲线，以及每个
带标签分组的成员；布局拥有每个字形的不可变轮廓和插入符记录。"""

import functools
import os
import pickle
import tempfile
from dataclasses import dataclass
from importlib.resources import files
from importlib.util import find_spec
from pathlib import Path

import numpy as np

from manimgx import _engine
from manimgx.caches import Memo, forgets
from manimgx.drawing.geometry import Shape

# The fonts ManimGX ships, its font packages' (Noto): with Typst's own, every face a document is
# set in or falls back to, so text is the same on every machine; a system font only by name. The
# CJK one is not installed in the browser
FONTS = tuple(
    str(files(package))
    for package in ("manimgx_fonts", "manimgx_fonts_cjk")
    if find_spec(package) is not None
)
TYPST_COMPILATION_FONT_SIZE = 10
TYPST_TEMPLATE = (
    "#set page(width: auto, height: auto, margin: 0pt, fill: none)\n#set text(size:"
    " {text_size}pt)\n{preamble}\n"
)
TypstError = _engine.TypstError
"""当 Typst 无法排版文档，或 LaTeX 无法转换为 Typst 时抛出的错误：
其消息为 Typst（或 mitex）的消息，每个错误附带其所在源码的字节位置，
从整个被排版文档的起始处计数——页面设置和前导部分位于代码之前。"""

# a row's columns (see rust/engine/src/typeset.rs): an item's origin is its source node (start,
# end; its own, else the innermost element around it from the source) and the bytes of the
# node's text a glyph's cluster draws (start, end)
KIND, KEY, PLACEMENT, FILL, STROKE, WIDTH, ADVANCE, NODE, DRAWN = (
    0,
    1,
    slice(2, 8),
    slice(8, 12),
    slice(12, 16),
    16,
    17,
    slice(18, 20),
    slice(20, 22),
)
ROW = 23
GLYPH, SHAPE = 0.0, 1.0


type Glyph = tuple[int, Shape | None, bytes]


@dataclass(frozen=True, slots=True)
class Layout:
    """一个排版后的绘图：`rows`（n × ROW，带轮廓和形状的字形），`shapes`
    （三次曲线控制点，y 轴向上），`labels`（一个标签及其对应的行，包括空分组），
    `body`（正文在源码中的起始位置，以字节计），以及 `glyphs`（其各行所引用的
    不可变轮廓和插入符记录）。"""

    rows: np.ndarray
    shapes: list[np.ndarray]
    labels: list[tuple[str, list[int]]]
    body: int
    glyphs: dict[int, Glyph]


# Reuse under disjoint native (<2^48) or content (>=2^52) keys. The bound counts
# aliases; either can be forgotten independently. Live layouts own their records.
_GLYPHS: Memo[int, Glyph] = Memo(1 << 12)
_CACHE = (
    Path(directory) / "layouts"
    if (directory := _engine.cache_directory()) is not None
    else None
)
# what made a layout, part of its key: the entry's format, and the engine's own file (a rebuilt
# engine never reads a layout an older one made)
_ENGINE = Path(_engine.__file__).stat()
_VERSION = f"layout 4, engine {_ENGINE.st_size} {_ENGINE.st_mtime_ns}".encode()
_CONTENT = 1 << 52  # glyph keys by content: exact in float64, apart from the engine's
type Stored = tuple[
    np.ndarray,
    list[np.ndarray],
    list[tuple[str, list[int]]],
    int,
    dict[int, tuple[bytes, bytes]],
]


def typst_string(text: str) -> str:
    """将 `text` 写作 Typst 字符串字面量，Typst 会将其原样读回为恰好 `text`。

    Args:
        text: 任意文本。

    Returns:
        该字面量，包含其引号。
    """
    escaped = (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )
    return f'"{escaped}"'


def typeset(
    body: str,
    preamble: str = "",
    text_size: float = TYPST_COMPILATION_FONT_SIZE,
    font_paths: list[str | Path] | None = None,
    package_path: str | Path | None = None,
) -> Layout:
    """排版一个 Typst 文档，并从 Typst 的帧中读取其布局。

    文档使用 ManimGX 附带的字体（Typst 自带字体和 Noto 字面）排版，
    排在 `font_paths` 中字体之后；系统字体仅在文档指定了上述字体均不包含
    的字族时才会被读取。布局保存在当前用户的缓存目录中
    （在页面中为浏览器的私有文件系统）：同一文档，在相同字体和包的条件下，
    会在任意进程中被读回，而不会重新排版。

    Args:
        body: 文档的正文：Typst 标记。
        preamble: 排在正文之前的 Typst 代码。
        text_size: 文本的字号，以磅为单位。
        font_paths: 字体文件所在目录，连同其子目录一起搜索，
            排在 ManimGX 附带字体之前。
        package_path: Typst 包的导入目录，除 mitex（引擎自带的）之外；
            None 表示仅有 mitex。
    """
    prefix = TYPST_TEMPLATE.format(text_size=text_size, preamble=preamble)
    source = prefix + body + "\n"
    fonts = (*(str(p) for p in font_paths or ()), *FONTS)
    packages = None if package_path is None else str(package_path)
    depends = _files(fonts if packages is None else (*fonts, packages))
    key = _engine.digest(_VERSION, b"\0", source.encode(), b"\0", depends)
    path = None if _CACHE is None else _CACHE / f"{key:016x}.layout"
    stored = None if path is None else _read(path)
    if stored is None:
        stored = _typeset(source, fonts, packages, int.from_bytes(depends, "little"))
        if path is not None:
            _write(path, stored)
    rows, shapes, labels, _, glyphs = stored
    records = {
        key: _glyph(key, points, carets) for key, (points, carets) in glyphs.items()
    }
    return Layout(rows, shapes, labels, len(prefix.encode()), records)


def _glyph(key: int, points: bytes, carets: bytes) -> Glyph:
    """解码一条不可变记录，在其被记住期间复用之。"""
    record = _GLYPHS.get(key)
    if record is None:
        array = np.frombuffer(points).reshape(-1, 3)
        record = _GLYPHS.keep(
            key, (key, Shape(array.copy()) if len(array) else None, carets)
        )
    return record


@forgets
@functools.cache
def _files(paths: tuple[str, ...]) -> bytes:
    """布局除其源码外所依赖的文件（字体、包），以路径、大小和
    时间表示，每进程一次。"""
    found = []
    for root in map(Path, paths):
        found.append(f"{root}\0".encode())
        within = sorted(root.rglob("*")) if root.is_dir() else [root]
        for file in within:
            if file.is_file():
                stat = file.stat()
                found.append(f"{file}\0{stat.st_size}\0{stat.st_mtime_ns}\0".encode())
    return _engine.digest(*found).to_bytes(8, "little")


def _read(path: Path) -> Stored | None:
    """一个已存储的布局，前提是存在且其排版所用字体未发生更改。"""
    try:
        stored: Stored = pickle.loads(path.read_bytes())
    except (OSError, pickle.UnpicklingError, EOFError, ValueError):
        return None
    system = stored[3]
    if system and system != _engine.system_fonts_fingerprint():
        return None
    return stored


def _write(path: Path, stored: Stored) -> None:
    """存储一个布局：整体写入后再重命名，使读取者永远不会看到只写了一半的布局。"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=path.parent) as own:
            partial = Path(own) / "layout"
            partial.write_bytes(pickle.dumps(stored, protocol=5))
            os.replace(partial, path)
    except OSError:
        pass


def _typeset(
    source: str, fonts: tuple[str, ...], packages: str | None, revision: int
) -> Stored:
    """用 Typst 排版；每个字形按键内容索引，附带其轮廓和插入符。"""
    raw, shapes, labels, system = _engine.typeset(
        source, fonts, packages, revision=revision
    )
    rows = np.frombuffer(raw).reshape(-1, ROW).copy()
    glyphs = rows[:, KIND] == GLYPH
    keys = rows[glyphs, KEY].astype(np.int64).tolist()
    held = {k: record for k in set(keys) if (record := _GLYPHS.get(k)) is not None}
    new = sorted(set(keys) - held.keys())
    for k, data in zip(new, _engine.glyph_outlines(new)):
        carets = np.array(_engine.ligature_carets(k), dtype="<f8").tobytes()
        content = _CONTENT | (
            _engine.digest(
                len(data).to_bytes(8, "little"),
                data,
                carets,
            )
            & (_CONTENT - 1)
        )
        held[k] = _GLYPHS.keep(k, _glyph(content, data, carets))
    records = {record[0]: record for record in held.values()}
    rows[glyphs, KEY] = [held[k][0] for k in keys]
    drawn = [
        i
        for i, row in enumerate(rows)
        if row[KIND] != GLYPH or records[int(row[KEY])][1] is not None
    ]
    if len(drawn) != len(rows):
        row_of = {old: new for new, old in enumerate(drawn)}
        rows = rows[drawn]
        labels = [
            (label, [row_of[i] for i in members if i in row_of])
            for label, members in labels
        ]
    glyphs = {
        key: (b"" if shape is None else shape.array.tobytes(), carets)
        for key, shape, carets in records.values()
    }
    return (
        rows,
        [np.frombuffer(s).reshape(-1, 3) for s in shapes],
        labels,
        _engine.system_fonts_fingerprint() if system else 0,
        glyphs,
    )
