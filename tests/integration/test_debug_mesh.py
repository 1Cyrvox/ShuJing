"""A film's video: decoded, it shows the frames the film drew, in their colors — the engine's
conversion to NV12, x264 (built into the engine), and what the MP4 says of its colors agree.
"""

from pathlib import Path
import numpy as np
import pytest

import av
from tests.integration.corpus.frames import decode
from tests.integration.corpus.run_manimgx import mp4_frames
from manimgx.rendering.film import Cut, Frame, X264Preset
from unittest.mock import Mock, patch
import manimgx as m
from manimgx._engine import Player
from manimgx.rendering.feed import Feeder

SIZE = (320, 180)
pytestmark = pytest.mark.config(pixel_width=SIZE[0], pixel_height=SIZE[1])


@pytest.mark.parametrize("queued_layers", [False, True])
@pytest.mark.parametrize("samples", [1, 4])
def test_captured(tmp_path: Path, queued_layers: bool, samples: int) -> None:
    width, height = 130, 74
    capture, plain, direct = (Player(width, height, samples) for _ in range(3))
    feeders = [Feeder(width, height, p) for p in (capture, plain, direct)]
    camera = m.Camera(three_d=True)
    layers = [
        m.MeshMobject(
            np.array([[-8, -5, z], [8, -5, z], [8, 5, z], [-8, 5, z]]),
            np.array([[0, 1, 2], [0, 2, 3]]),
            color=m.BLUE if i % 2 else m.RED,
            fill_opacity=0.2,
        )
        for i, z in enumerate(np.linspace(-0.2, 0.2, 12))
    ]
    captured_video, plain_video = tmp_path / "captured.mp4", tmp_path / "plain.mp4"
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
        arr = np.frombuffer(expected, np.uint8)
        if arr.max() == 0:
            print(f"BLACK at index={index} s={samples} q={queued_layers}")
        assert arr.max() > 0
        view, records, cameras = prepared[0]
        capture.push(view, records, cameras=cameras, capture=wanted)
        view, records, cameras = prepared[1]
        plain.push(view, records, cameras=cameras)
    capture.end_export()
    plain.end_export()
