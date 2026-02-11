"""Tests for all three renderers (terminal, JSON stream, OSC)."""

from __future__ import annotations

import io
import json
from typing import Any

import pytest

from renderers.json_stream import JsonStreamRenderer
from renderers.osc import OscRenderer
from renderers.terminal import TerminalRenderer, _brightness_to_char, _motion_arrow


# ---------------------------------------------------------------------------
# Shared fixture data
# ---------------------------------------------------------------------------

def _sample_frame(frame: int = 0) -> dict[str, Any]:
    return {
        "frame": frame,
        "timestamp": 1707600000.0 + frame * 0.033,
        "params": {
            "visual.brightness": 0.7,
            "visual.particle_density": 0.5,
            "audio.volume": 0.4,
            "spatial.pan": -0.3,
        },
        "routed": {
            "visual": {"brightness": 0.7, "particle_density": 0.5},
            "audio": {"volume": 0.4},
            "spatial": {"pan": -0.3},
        },
    }


# ---------------------------------------------------------------------------
# Terminal renderer
# ---------------------------------------------------------------------------

class TestTerminalRenderer:
    """Tests for the TerminalRenderer class."""

    def test_render_produces_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        renderer = TerminalRenderer(width=10, height=5, show_stats=False)
        renderer.render(_sample_frame())
        captured = capsys.readouterr()
        assert len(captured.out) > 0

    def test_brightness_char_mapping(self) -> None:
        # 0.0 should map to space (darkest)
        assert _brightness_to_char(0.0) == " "
        # 1.0 should map to '@' (brightest)
        assert _brightness_to_char(1.0) == "@"

    def test_motion_arrow_directions(self) -> None:
        assert _motion_arrow(1.0, 0.0) == ">"
        assert _motion_arrow(-1.0, 0.0) == "<"
        assert _motion_arrow(0.0, -1.0) == "^"
        assert _motion_arrow(0.0, 1.0) == "v"
        assert _motion_arrow(0.0, 0.0) == "o"

    def test_cleanup_restores_cursor(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        renderer = TerminalRenderer(width=5, height=3)
        renderer.cleanup()
        captured = capsys.readouterr()
        assert "\033[?25h" in captured.out  # SHOW_CURSOR


# ---------------------------------------------------------------------------
# JSON stream renderer
# ---------------------------------------------------------------------------

class TestJsonStreamRenderer:
    """Tests for the JsonStreamRenderer class."""

    def test_produces_valid_json(self) -> None:
        buf = io.StringIO()
        renderer = JsonStreamRenderer(output=buf)
        renderer.render(_sample_frame(0))
        renderer.render(_sample_frame(1))

        lines = buf.getvalue().strip().split("\n")
        assert len(lines) == 2

        for line in lines:
            parsed = json.loads(line)
            assert "frame" in parsed
            assert "timestamp" in parsed
            assert "params" in parsed

    def test_frame_numbers_sequential(self) -> None:
        buf = io.StringIO()
        renderer = JsonStreamRenderer(output=buf)
        for i in range(5):
            renderer.render(_sample_frame(i))

        lines = buf.getvalue().strip().split("\n")
        frames = [json.loads(line)["frame"] for line in lines]
        assert frames == [0, 1, 2, 3, 4]

    def test_lines_written_counter(self) -> None:
        buf = io.StringIO()
        renderer = JsonStreamRenderer(output=buf)
        assert renderer.lines_written == 0
        renderer.render(_sample_frame())
        assert renderer.lines_written == 1

    def test_include_routed(self) -> None:
        buf = io.StringIO()
        renderer = JsonStreamRenderer(output=buf, include_routed=True)
        renderer.render(_sample_frame())
        parsed = json.loads(buf.getvalue().strip())
        assert "routed" in parsed


# ---------------------------------------------------------------------------
# OSC renderer
# ---------------------------------------------------------------------------

class TestOscRenderer:
    """Tests for the OscRenderer class."""

    def test_formats_addresses_correctly(self) -> None:
        renderer = OscRenderer(address_prefix="/installation")
        renderer.render(_sample_frame())
        buffer = renderer.get_buffer()

        addresses = [msg[0] for msg in buffer]
        assert "/installation/visual/brightness" in addresses
        assert "/installation/audio/volume" in addresses
        assert "/installation/spatial/pan" in addresses

    def test_values_are_floats(self) -> None:
        renderer = OscRenderer()
        renderer.render(_sample_frame())
        for _addr, value in renderer.get_buffer():
            assert isinstance(value, float)

    def test_buffer_size_limit(self) -> None:
        renderer = OscRenderer(buffer_size=5)
        for i in range(10):
            renderer.render(_sample_frame(i))
        assert len(renderer.get_buffer()) <= 5

    def test_clear_buffer(self) -> None:
        renderer = OscRenderer()
        renderer.render(_sample_frame())
        assert len(renderer.get_buffer()) > 0
        renderer.clear_buffer()
        assert len(renderer.get_buffer()) == 0

    def test_format_bundle_does_not_modify_buffer(self) -> None:
        renderer = OscRenderer()
        bundle = renderer.format_bundle(_sample_frame())
        assert len(bundle) > 0
        assert len(renderer.get_buffer()) == 0  # buffer untouched

    def test_custom_address_prefix(self) -> None:
        renderer = OscRenderer(address_prefix="/my/project")
        renderer.render(_sample_frame())
        addresses = [msg[0] for msg in renderer.get_buffer()]
        assert all(addr.startswith("/my/project/") for addr in addresses)

    def test_messages_total_counter(self) -> None:
        renderer = OscRenderer()
        renderer.render(_sample_frame())
        first_count = renderer.messages_total
        assert first_count > 0
        renderer.render(_sample_frame())
        assert renderer.messages_total == first_count * 2
