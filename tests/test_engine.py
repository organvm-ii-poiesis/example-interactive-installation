"""Tests for the main installation engine."""

from __future__ import annotations

from typing import Any

import pytest

from src.config import InstallationConfig, MappingRule, OutputConfig, SensorConfig
from src.engine import InstallationEngine


def _minimal_config() -> InstallationConfig:
    """Return the smallest valid configuration for testing."""
    return InstallationConfig(
        name="Test Installation",
        sensors=[SensorConfig(type="motion", params={"noise": 0.0})],
        mappings=[
            MappingRule(
                source_param="motion.magnitude",
                target_param="visual.brightness",
                transform="linear",
                min_out=0.0,
                max_out=1.0,
            ),
        ],
        outputs=[OutputConfig(type="visual")],
        renderer="terminal",
        tick_rate=30,
    )


class _DummyRenderer:
    """A renderer that records frames for testing."""

    def __init__(self) -> None:
        self.frames: list[dict[str, Any]] = []

    def render(self, frame_data: dict[str, Any]) -> None:
        self.frames.append(frame_data)


class TestInstallationEngine:
    """Tests for the InstallationEngine class."""

    def test_initializes_from_config(self) -> None:
        config = _minimal_config()
        engine = InstallationEngine(config)
        assert len(engine.sensors) == 1
        assert len(engine.outputs) == 1

    def test_rejects_invalid_config(self) -> None:
        config = InstallationConfig(
            name="Bad",
            sensors=[],
            mappings=[],
            outputs=[],
            renderer="terminal",
            tick_rate=30,
        )
        with pytest.raises(ValueError, match="Invalid configuration"):
            InstallationEngine(config)

    def test_step_returns_frame_data(self) -> None:
        config = _minimal_config()
        engine = InstallationEngine(config)
        frame = engine.step()
        assert "frame" in frame
        assert "timestamp" in frame
        assert "params" in frame
        assert "routed" in frame

    def test_frame_count_increments(self) -> None:
        config = _minimal_config()
        engine = InstallationEngine(config)
        assert engine.frame_count == 0
        engine.step()
        assert engine.frame_count == 1
        engine.step()
        assert engine.frame_count == 2

    def test_run_produces_frames(self) -> None:
        config = _minimal_config()
        renderer = _DummyRenderer()
        engine = InstallationEngine(config, renderer=renderer)
        engine.run(duration_seconds=0.2, tick_rate=10)
        # Should have produced at least 1 frame
        assert engine.frame_count >= 1
        assert len(renderer.frames) >= 1

    def test_frame_callback(self) -> None:
        config = _minimal_config()
        engine = InstallationEngine(config)
        received: list[dict[str, Any]] = []
        engine.on_frame(lambda fd: received.append(fd))
        engine.step()
        assert len(received) == 1

    def test_average_fps_after_run(self) -> None:
        config = _minimal_config()
        engine = InstallationEngine(config)
        engine.run(duration_seconds=0.3, tick_rate=10)
        # FPS should be roughly close to 10, but allow wide tolerance
        assert engine.average_fps > 0

    def test_headless_run_no_renderer(self) -> None:
        config = _minimal_config()
        engine = InstallationEngine(config, renderer=None)
        engine.run(duration_seconds=0.1, tick_rate=10)
        assert engine.frame_count >= 1

    def test_params_contain_mapped_values(self) -> None:
        config = _minimal_config()
        engine = InstallationEngine(config)
        frame = engine.step()
        assert "visual.brightness" in frame["params"]
