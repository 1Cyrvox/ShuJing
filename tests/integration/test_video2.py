"""A film's video: decoded, it shows the frames the film drew, in their colors — the engine's
conversion to NV12, x264 (built into the engine), and what the MP4 says of its colors agree.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import av
import numpy as np
import pytest
from tests.integration.corpus.frames import decode
from tests.integration.corpus.run_manimgx import mp4_frames

import manimgx as m
from manimgx._engine import Player
from manimgx.rendering.feed import Feeder
from manimgx.rendering.film import Cut, Frame, X264Preset

SIZE = (320, 180)
pytestmark = pytest.mark.config(pixel_width=SIZE[0], pixel_height=SIZE[1])


@pytest.mark.parametrize("queued_layers", [False, True])
@pytest.mark.parametrize("samples", [1, 4])
def test_captured_exports_preserve_pixels_and_video_across_pending_draws(
    tmp_path: Path, queued_layers: bool, samples: int
) -> None:
    # RGBA rows require padding; NV12 edges are partial macroblocks.
    width, height = 130, 74
    capture, plain, direct = (Player(width, height, samples) for _ in range(3))
    feeders = [Feeder(width, height, player) for player in (capture, plain, direct)]
    camera = m.Camera(three_d=True)
    # Cover the picture in see-through mesh layers: the first draw must grow its fragment
    # lists. Capturing must return the successful retry, including after older queued draws.
    layers: list[m.Mobject] = [
        m.MeshMobject(
            np.array([[-8, -5, z], [8, -5, z], [8, 5, z], [-8, 5, z]]),
            np.array([[0, 1, 2], [0, 2, 3]]),
            color=m.BLUE if i % 2 else m.RED,
            fill_opacity=0.2,
        )
        for i, z in enumerate(np.linspace(-0.2, 0.2, 12))
    ]
    captured_video, plain_video = tmp_path / "captured.mp4", tmp_path / "plain.mp4"
    expected_frames: list[np.ndarray] = []
    capture.begin_export(str(captured_video), 30)
    plain.begin_export(str(plain_video), 30)
    for index, wanted in enumerate([False, False, False, True, True, False, True]):
        objects = (
            layers
            if (index >= 3) != queued_layers
            else [m.Square(fill_opacity=1).shift((index % 3) * m.RIGHT)]
        )
        prepared = [feeder.frame(camera, objects) for feeder in feeders]
        expected = direct.render(*prepared[2])
        assert any(expected[0::4])  # geometry is visible, including the mesh layers
        expected_frames.append(
            np.frombuffer(expected, np.uint8)
            .reshape(height, width, 4)[:, :, :3]
            .astype(int)
        )
        view, records, cameras = prepared[0]
        actual = capture.push(view, records, cameras=cameras, capture=wanted)
        assert actual == (expected if wanted else None)
        view, records, cameras = prepared[1]
        assert plain.push(view, records, cameras=cameras) is None
    capture.end_export()
    plain.end_export()
    assert captured_video.read_bytes() == plain_video.read_bytes()
    shown = [frame.astype(int) for frame in decode(captured_video, (width, height))]
    assert len(shown) == len(expected_frames)
    for picture, frame in zip(shown, expected_frames, strict=True):
        assert np.abs(picture - frame).mean() < 2.0

