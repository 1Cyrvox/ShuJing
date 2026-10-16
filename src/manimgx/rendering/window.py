"""Window：ManimGX 的播放器，运行在自身独立的窗口中，位于本机屏幕上，由本机 GPU 绘制。

窗口播放发送给它的片段（见 [`Film`][manimgx.Film]）：每一帧在录制时即刻播放，任意一帧可立即重播。
更新的片段——即场景重新运行——会在到达的同一时刻替换当前显示的内容：编辑不会丢失位置。

    with m.Window() as window:
        MyScene().render(take=window)
        window.wait()  # until it is closed

窗口是一个独立进程，片段通过管道到达该进程：它在场景运行时持续播放，
而场景的进程则保持空闲以服务场景。窗口在自身被关闭、打开它的进程关闭它或结束时关闭。
"""

import contextlib
import json
import queue
import subprocess
import sys
import threading
from collections.abc import Sequence
from types import TracebackType
from typing import Self
from warnings import deprecated

from manimgx import _engine
from manimgx.rendering.film import Cut


class Window:
    """ManimGX 的播放器，运行在本机屏幕的窗口中，播放发送给它的片段。

    窗口是一个 [`Take`][manimgx.rendering.film.Take]：将其传给
    [`Scene.render`][manimgx.Scene.render] 作为 `take`，它会在录制时播放影片。
    一旦窗口关闭，发送给它的影片即被剪切（见 [`Cut`][manimgx.rendering.film.Cut]）。

    其查看者可请求该文件的其它场景（N 和 P）。

    Args:
        title: 窗口的标题。
        time: 播放头起始位置，以秒为单位。
    """

    def __init__(self, title: str = "ManimGX", *, time: float = 0.0) -> None:
        self._process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                "from manimgx.rendering.window import _main; _main()",
            ]
            + [title, repr(float(time))],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        self._asked: queue.Queue[str] = queue.Queue()
        self.failure: str | None = None
        """窗口失败的原因（若失败）：无可打开的屏幕、无 GPU 等：此时窗口已关闭。"""
        self._listening = threading.Thread(target=self._listen, daemon=True)
        self._listening.start()

    def __call__(self, data: bytes) -> None:
        """向窗口发送片段的下一批字节。

        Raises:
            Cut: 窗口已关闭：影片在此处被剪切。
        """
        pipe = self._process.stdin
        if pipe is None or pipe.closed:
            raise Cut
        try:
            pipe.write(data)  # whole: a buffered pipe writes it all
            pipe.flush()
        except (BrokenPipeError, ValueError):
            with contextlib.suppress(OSError):
                pipe.close()
            raise Cut from None

    @deprecated("ManimGX's machinery: ManimGX preview calls it", category=None)
    def scenes(self, names: Sequence[str], playing: str) -> None:
        """告知窗口该文件的场景列表及当前播放的场景：其查看者可请求
        其它场景（N、P；见 [`asked`][manimgx.Window.asked]）。

        Args:
            names: 该文件的场景，按顺序排列。
            playing: 当前片段所对应的场景。
        """
        self._say({"scenes": list(names), "scene": playing})

    @deprecated("ManimGX's machinery: ManimGX preview calls it", category=None)
    def failed(self, error: BaseException, trace: str, line: int | None = None) -> None:
        """在最后生成的画面上显示场景错误，直至下一片段。

        Args:
            trace: 要显示的内容：场景代码所经过的行及错误信息。
            line: 场景文件中失败的行号（若有）。
        """
        fault = {"message": str(error), "type": type(error).__name__}
        self._say({"error": {**fault, "trace": trace, "line": line}})

    def _say(self, note: dict[str, object]) -> None:
        """片段之间的通知（导演的 JSON，见 `Film`）：对已关闭的窗口而言为无操作。"""
        with contextlib.suppress(Cut):
            self(_engine.note(json.dumps(note)))

    @property
    def open(self) -> bool:
        """窗口是否处于打开状态：直至其查看者关闭它，或其自身被关闭。"""
        return self._process.poll() is None

    @deprecated("ManimGX's machinery: ManimGX preview calls it", category=None)
    def asked(self) -> str | None:
        """查看者最近请求的场景（若自上次以来有请求）：N、P 分别表示该文件场景的
        下一个或上一个。"""
        name = None
        while not self._asked.empty():
            name = self._asked.get_nowait()
        return name

    def wait(self, timeout: float | None = None) -> bool:
        """等待直至窗口关闭，最多等待 `timeout` 秒；返回是否已关闭。"""
        try:
            self._process.wait(timeout)
        except subprocess.TimeoutExpired:
            return False
        self._listening.join()  # what it said before it closed, `failure` among it
        return True

    def close(self) -> None:
        """关闭窗口。"""
        pipe = self._process.stdin
        if pipe is not None and not pipe.closed:
            with contextlib.suppress(OSError):
                pipe.close()  # its end of the take: it closes
        if not self.wait(10):
            self._process.kill()
            self.wait()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        self.close()

    def _listen(self) -> None:
        """窗口所发出的内容，每行一个 JSON，按到达顺序处理：查看者请求的场景，
        或失败原因；当全部发出后，其管道端即关闭。"""
        assert self._process.stdout is not None
        with self._process.stdout as lines:
            for line in lines:
                try:
                    said = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(said, dict):
                    continue
                if isinstance(scene := said.get("scene"), str):
                    self._asked.put(scene)
                if isinstance(failure := said.get("failure"), str):
                    self.failure = failure


def _main() -> None:
    """窗口自身的进程（由 `Window` 启动）：即窗口本身，直至其被关闭。"""
    import signal

    from manimgx.drawing.typesetting import FONTS

    # Ctrl+C reaches every process of the terminal: the window's director closes it
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    title, time = sys.argv[1], float(sys.argv[2])
    try:
        _engine.window(title, time, list(FONTS))
    except BaseException as failed:  # a panic of the engine's too
        print(json.dumps({"failure": str(failed) or type(failed).__name__}), flush=True)
        sys.exit(1)
