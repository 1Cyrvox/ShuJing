"网格上的图片：解码后的像素与实时相机视图。"

from pathlib import Path
from typing import TYPE_CHECKING, Self, Unpack
from warnings import deprecated

import numpy as np

from manimgx.config import config
from manimgx.constants import DOWN, LEFT, RIGHT, UP, Resampling
from manimgx.drawing.paint import (
    WHITE,
    YELLOW_C,
    Fill,
    Look,
    ManimColor,
    ParsableManimColor,
    Style,
    _Style,
)
from manimgx.mobject import MeshMobject

__all__ = ["ImageMobject", "ImageMobjectFromCamera"]

if TYPE_CHECKING:
    from manimgx.mobjects.annotations import FrameOptions
    from manimgx.scene import Camera


class ImageMobject(MeshMobject):
    """一幅图片：一个图像文件或一个像素数组，置于一个与其像素高度相当的矩形上。

    一幅 `scale_to_resolution` 像素高（未指定时为 1080）的图像与画框短边
    （默认为 8 个场景单位）等高，其他图像按比例缩放。当显示尺寸大于其像素时，
    图片由 `resampling_algorithm` 从像素重建：默认为穿过每个像素的平滑三次曲线；
    linear 混合相邻像素；nearest 将每个像素显示为其颜色的小方块。当显示尺寸
    小于其像素时，图片被采样而非平均。该 mobject 的不透明度与其像素自身的相乘。

    Args:
        filename_or_array: 图片内容：图像文件的路径、文件内容
            （字节串），或取值 0 到 255 的像素值数组：(h, w) 灰度、(h, w, 3)
            RGB 或 (h, w, 4) RGBA。
        scale_to_resolution: 与画框短边等高的图像有多少像素高；
            0 表示图像高 3 个单位，与其尺寸无关。
        invert: 是否反转其颜色（不反转其透明度）。
        image_mode: 文件被读入的模式，以 Pillow 库的命名方式表示：
            "RGBA"，或 "L" 表示灰度。
        resampling_algorithm: 图片如何从其像素重建，以 Pillow 库的编号表示：
            0，nearest；2，linear；3，cubic（Keys 的三次卷积，Pillow 的 bicubic）；
            [RESAMPLING_ALGORITHMS][manimgx.RESAMPLING_ALGORITHMS] 按名称给出这些值。
        stroke_width: 图片周围边框的宽度，以百分之一场景单位为单位；
            0 表示无边框。
        stroke_color: 边框的颜色。

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class ImageMobjectExample(m.Scene):
            def construct(self) -> None:
                ramp = np.linspace(0, 255, 256)
                pixels = np.zeros((256, 256, 3), dtype=np.uint8)
                pixels[..., 0] = ramp  # red grows to the right
                pixels[..., 2] = ramp[:, np.newaxis]  # blue grows downward
                image = m.ImageMobject(pixels, scale_to_resolution=400)
                self.play(m.FadeIn(image))
        ```

        ```python
        import numpy as np

        import manimgx as m


        class ImageMobjectResamplingExample(m.Scene):
            def construct(self) -> None:
                pixels = np.full((3, 3), 60, dtype=np.uint8)
                pixels[1, 1] = 255  # one white pixel, amid gray ones
                images = m.Group()
                for name in ("nearest", "linear", "cubic"):
                    image = m.ImageMobject(
                        pixels,
                        scale_to_resolution=6,
                        resampling_algorithm=m.RESAMPLING_ALGORITHMS[name],
                    )
                    images.add(m.Group(image, m.Text(name).next_to(image, m.DOWN)))
                self.add(images.arrange(buff=0.5))
        ```
    """

    # a textured quad, CE's four corners (UL, UR, DL, DR) its vertices; the opacity lives
    # in the paint, a multiplier
    def __init__(
        self,
        filename_or_array: str | Path | bytes | np.ndarray,
        scale_to_resolution: int = 1080,
        invert: bool = False,
        image_mode: str = "RGBA",
        resampling_algorithm: Resampling = 3,
        stroke_width: float = 0,  # a border's (the picture is the texture)
        stroke_color: ParsableManimColor = WHITE,
        **kwargs: Unpack[Look],
    ) -> None:
        import io

        from PIL import Image

        if isinstance(filename_or_array, (str, Path, bytes)):
            source = (
                io.BytesIO(filename_or_array)
                if isinstance(filename_or_array, bytes)
                else filename_or_array
            )
            pixels = np.array(Image.open(source).convert(image_mode))
        else:
            pixels = np.array(filename_or_array)
        pixels = _to_rgba(pixels)
        if invert:
            pixels[:, :, :3] = 255 - pixels[:, :, :3]
        pixels.flags.writeable = False
        self.scale_to_resolution = scale_to_resolution
        self.resampling_algorithm = resampling_algorithm
        super().__init__(
            np.array([UP + LEFT, UP + RIGHT, DOWN + LEFT, DOWN + RIGHT], dtype=float),
            np.array([[0, 1, 2], [1, 3, 2]]),
            uvs=np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=float),
            texture=pixels,
            **kwargs,
        )
        if (
            stroke_width > 0
        ):  # a border is just a rectangle child that follows every transform
            from manimgx.mobjects.shapes import Polygon

            self.add(
                Polygon(
                    *self.points[[0, 1, 3, 2]],
                    stroke_width=stroke_width,
                    stroke_color=stroke_color,
                )
            )

    @property
    def pixel_array(self) -> np.ndarray:
        """当前图片的 (h, w, 4) RGBA 像素，取值 0 到 255。

        由该图像解码或着色的图片是只读的。当变为另一个带纹理网格时，
        会采用其纹理，包括其是否可写。
        """
        texture = self.paint.texture
        assert isinstance(texture, np.ndarray)
        return texture

    def generate_points(self) -> Self:
        super().generate_points()
        self.center()
        texture = self._texture
        assert isinstance(texture, np.ndarray)
        h, w = texture.shape[:2]
        # an image `scale_to_resolution` pixels high spans the frame's short side
        short = min(config.frame_width, config.frame_height)
        height = h / self.scale_to_resolution * short if self.scale_to_resolution else 3
        return self.stretch_to_fit_height(height).stretch_to_fit_width(height * w / h)

    def set_color(  # pyright: ignore[reportIncompatibleMethodOverride]  # ty: ignore[invalid-method-override]  # CE's: an image's tint, then its alpha
        self,
        color: ParsableManimColor = YELLOW_C,
        alpha: float | None = None,
        family: bool = True,
    ) -> Self:
        """将每个像素着为 `color`，保留其不透明度：图片变为该颜色的剪影。

        Args:
            alpha: 同时设置每个像素的不透明度，取值 0 到 1；None 保留各自的原值。
            family: 仅为 Manim 兼容性而接受；被忽略：仅对图片本身着色。
        """
        pixels = self.pixel_array.copy()
        pixels[:, :, :3] = (ManimColor(color).to_rgb() * 255).astype(np.uint8)
        if alpha is not None:
            pixels[:, :, 3] = int(255 * alpha)
        pixels.flags.writeable = False
        self.paint = self.paint.but(texture=pixels)
        return self

    def set_opacity(
        self, opacity: float = 1.0, family: bool = True, *, alpha: float | None = None
    ) -> Self:
        """设置图片的不透明度，该值与其像素自身的相乘。

        Args:
            opacity: 不透明度，取值 0 到 1。
            family: 是否设置其整个族（包括边框），还是仅设置图片本身。
            alpha: 不透明度，使用 Manim 图像所用的名称；若给定，则优先于
                `opacity`。
        """
        return super().set_opacity(opacity if alpha is None else alpha, family)

    def set_resampling_algorithm(self, resampling_algorithm: Resampling) -> Self:
        """设置在显示尺寸大于像素时，图片如何从其像素重建。

        Args:
            resampling_algorithm: 滤波器，以 Pillow 库的编号表示：0，nearest
                （每个像素为其颜色的小方块）；2，linear；3，cubic（平滑，且
                穿过每个像素）；
                [RESAMPLING_ALGORITHMS][manimgx.RESAMPLING_ALGORITHMS] 按名称给出
                这些值。
        """
        self.resampling_algorithm = resampling_algorithm
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_style(self) -> Fill:
        """图片的样式，以填充关键字表示：其颜色和不透明度。

        Returns:
            一个包含 `fill_color` 和 `fill_opacity` 的字典。
        """
        return Fill(fill_color=self.get_color(), fill_opacity=self.get_fill_opacity())


def _to_rgba(pixels: np.ndarray) -> np.ndarray:
    if pixels.ndim == 2:
        pixels = np.stack([pixels] * 3, axis=-1)
    if pixels.shape[2] == 3:
        pixels = np.concatenate(
            [pixels, np.full((*pixels.shape[:2], 1), 255, dtype=pixels.dtype)], axis=2
        )
    return pixels.astype(np.uint8)


class ImageCameraOptions(_Style, total=False):
    """相机图片的关键字，供将其传递下去的场景使用：例如
    [ZoomedScene][manimgx.ZoomedScene] 的显示。

    除此之外，它们还接受[样式关键字][manimgx.drawing.paint.Style]。
    """

    default_display_frame_config: "FrameOptions | None"
    """图片轮廓的[环绕矩形
    关键字][manimgx.mobjects.annotations.FrameOptions]，覆盖默认的宽 3 白色
    无边距轮廓（默认为 None）。"""


@deprecated("Manim CE's machinery for ZoomedScene: use ZoomedScene", category=None)
class ImageMobjectFromCamera(MeshMobject):
    """相机所见的内容，作为一幅图片：一个显示相机视图的矩形，每帧重新绘制。

    图片高 3 个单位，宽高比与画框一致。移动相机的
    [frame][manimgx.Camera.frame] 可看向别处，缩放它即可缩放：图片随之变化。
    相机能看到除该图片之外的所有内容；[ZoomedScene][manimgx.ZoomedScene] 用
    它来显示其缩放相机的视图。

    Args:
        camera: 其视图由该图片显示的相机。
        default_display_frame_config: [add_display_frame][manimgx.ImageMobjectFromCamera.add_display_frame]
            所绘轮廓的[环绕矩形
            关键字][manimgx.mobjects.annotations.FrameOptions]，覆盖默认的宽 3 白色
            无边距轮廓。

    Examples:
        ```python
        import manimgx as m


        class ImageMobjectFromCameraExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=4, color=m.BLUE, fill_opacity=0.5)
                self.add(square.shift(2 * m.LEFT + 0.5 * m.DOWN))
                camera = m.Camera()
                frame = camera.frame.scale(0.25).move_to(square.get_corner(m.UL))
                frame.set_stroke(m.YELLOW, 3)
                picture = m.ImageMobjectFromCamera(camera).add_display_frame()
                self.add(frame, picture.to_corner(m.UR))
                self.play(frame.animate.move_to(square.get_corner(m.DR)), run_time=3)
        ```
    """

    # a quad textured with the camera's view (a camera's view is a texture)

    def __init__(
        self,
        camera: "Camera",
        default_display_frame_config: "FrameOptions | None" = None,
        **kwargs: Unpack[Style],
    ) -> None:
        self.camera = camera
        """其视图由该图片显示的相机。"""
        frame: FrameOptions = {"stroke_width": 3, "stroke_color": WHITE, "buff": 0}
        self.default_display_frame_config = frame | (default_display_frame_config or {})
        w = (
            1.5 * config.frame_width / config.frame_height
        )  # CE: 3 units high, the frame's aspect
        super().__init__(
            np.array(
                [[-w, 1.5, 0], [w, 1.5, 0], [-w, -1.5, 0], [w, -1.5, 0]], dtype=float
            ),
            np.array([[0, 1, 2], [1, 3, 2]]),
            uvs=np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=float),
            texture=camera,
            **kwargs,
        )

    def add_display_frame(self, **kwargs: "Unpack[FrameOptions]") -> Self:
        """为图片绘制轮廓：一个环绕矩形，作为子 mobject 添加。

        Args:
            **kwargs: [环绕矩形
                关键字][manimgx.mobjects.annotations.FrameOptions]，覆盖
                `default_display_frame_config`。
        """
        from manimgx.mobjects.annotations import SurroundingRectangle

        self.display_frame = SurroundingRectangle(
            self, **(self.default_display_frame_config | kwargs)
        )
        return self.add(self.display_frame)
