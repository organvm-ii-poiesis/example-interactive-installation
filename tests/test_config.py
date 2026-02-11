"""Tests for configuration loading and validation."""

from __future__ import annotations

import os
import tempfile
from typing import Any

import pytest

from src.config import (
    InstallationConfig,
    MappingRule,
    OutputConfig,
    SensorConfig,
    load_config,
    load_config_from_dict,
    validate_config,
)


# ---------------------------------------------------------------------------
# Sample raw dicts
# ---------------------------------------------------------------------------

VALID_RAW: dict[str, Any] = {
    "name": "Test Preset",
    "sensors": [{"type": "motion", "noise": 0.1, "update_rate": 30}],
    "mappings": [
        {
            "source": "motion.magnitude",
            "target": "visual.brightness",
            "transform": "linear",
            "min_out": 0.0,
            "max_out": 1.0,
        }
    ],
    "outputs": [{"type": "visual"}],
    "renderer": "terminal",
    "tick_rate": 15,
}


class TestLoadConfigFromDict:
    """Tests for load_config_from_dict."""

    def test_parses_valid_dict(self) -> None:
        config = load_config_from_dict(VALID_RAW)
        assert config.name == "Test Preset"
        assert len(config.sensors) == 1
        assert config.sensors[0].type == "motion"
        assert len(config.mappings) == 1
        assert config.mappings[0].source_param == "motion.magnitude"
        assert config.tick_rate == 15

    def test_defaults_for_missing_fields(self) -> None:
        config = load_config_from_dict({"name": "Minimal"})
        assert config.name == "Minimal"
        assert config.sensors == []
        assert config.mappings == []
        assert config.renderer == "terminal"
        assert config.tick_rate == 30

    def test_sensor_params_extracted(self) -> None:
        raw = {
            "sensors": [{"type": "depth", "width": 20, "height": 10, "noise": 0.01}],
        }
        config = load_config_from_dict(raw)
        assert config.sensors[0].params["width"] == 20
        assert config.sensors[0].params["height"] == 10
        assert config.sensors[0].params["noise"] == 0.01


class TestLoadConfigFromFile:
    """Tests for load_config with YAML files."""

    def test_loads_yaml_file(self) -> None:
        yaml_content = (
            "name: File Test\n"
            "sensors:\n"
            "  - type: motion\n"
            "    noise: 0.05\n"
            "mappings:\n"
            "  - source: motion.dx\n"
            "    target: visual.x\n"
            "    transform: linear\n"
            "    min_out: 0.0\n"
            "    max_out: 1.0\n"
            "outputs:\n"
            "  - type: visual\n"
            "renderer: terminal\n"
            "tick_rate: 20\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as fh:
            fh.write(yaml_content)
            fh.flush()
            path = fh.name

        try:
            config = load_config(path)
            assert config.name == "File Test"
            assert config.sensors[0].type == "motion"
            assert config.tick_rate == 20
        finally:
            os.unlink(path)

    def test_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path/config.yaml")


class TestValidateConfig:
    """Tests for config validation."""

    def _valid_config(self) -> InstallationConfig:
        return InstallationConfig(
            name="Valid",
            sensors=[SensorConfig(type="motion", params={})],
            mappings=[
                MappingRule("motion.dx", "visual.x", "linear", 0.0, 1.0)
            ],
            outputs=[OutputConfig(type="visual")],
            renderer="terminal",
            tick_rate=30,
        )

    def test_valid_config_has_no_errors(self) -> None:
        errors = validate_config(self._valid_config())
        assert errors == []

    def test_empty_name(self) -> None:
        config = self._valid_config()
        config.name = ""
        errors = validate_config(config)
        assert any("name" in e.lower() for e in errors)

    def test_no_sensors(self) -> None:
        config = self._valid_config()
        config.sensors = []
        errors = validate_config(config)
        assert any("sensor" in e.lower() for e in errors)

    def test_unknown_sensor_type(self) -> None:
        config = self._valid_config()
        config.sensors = [SensorConfig(type="teleportation", params={})]
        errors = validate_config(config)
        assert any("unknown" in e.lower() for e in errors)

    def test_no_mappings(self) -> None:
        config = self._valid_config()
        config.mappings = []
        errors = validate_config(config)
        assert any("mapping" in e.lower() for e in errors)

    def test_no_outputs(self) -> None:
        config = self._valid_config()
        config.outputs = []
        errors = validate_config(config)
        assert any("output" in e.lower() for e in errors)

    def test_unknown_output_type(self) -> None:
        config = self._valid_config()
        config.outputs = [OutputConfig(type="hologram")]
        errors = validate_config(config)
        assert any("unknown" in e.lower() for e in errors)

    def test_invalid_tick_rate(self) -> None:
        config = self._valid_config()
        config.tick_rate = 0
        errors = validate_config(config)
        assert any("tick_rate" in e for e in errors)

    def test_unknown_renderer(self) -> None:
        config = self._valid_config()
        config.renderer = "opengl"
        errors = validate_config(config)
        assert any("renderer" in e.lower() for e in errors)

    def test_min_out_greater_than_max_out(self) -> None:
        config = self._valid_config()
        config.mappings = [
            MappingRule("motion.dx", "visual.x", "linear", 10.0, 5.0)
        ]
        errors = validate_config(config)
        assert any("min_out" in e for e in errors)
