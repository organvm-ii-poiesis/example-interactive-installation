"""Configuration loader and validator for installation presets.

Loads YAML preset files (via PyYAML) into typed dataclass instances
that the :class:`~src.engine.InstallationEngine` can consume directly.
Validation catches common mistakes (missing fields, unknown sensor types)
before the engine starts.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .mapping import MappingRule
from .output import OUTPUT_REGISTRY, create_output, OutputTarget
from .sensor_sim import SENSOR_REGISTRY, Sensor, create_sensor


# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------

@dataclass
class SensorConfig:
    """Raw configuration for one sensor."""

    type: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class OutputConfig:
    """Raw configuration for one output target."""

    type: str


@dataclass
class InstallationConfig:
    """Complete configuration for an interactive installation.

    Attributes
    ----------
    name:
        Human-readable name for the installation preset.
    sensors:
        List of sensor configurations.
    mappings:
        List of mapping rules linking sensor parameters to outputs.
    outputs:
        List of output target configurations.
    renderer:
        Name of the renderer to use (``"terminal"``, ``"json_stream"``,
        ``"osc"``).
    tick_rate:
        Target frames per second for the main loop.
    """

    name: str = "Untitled Installation"
    sensors: list[SensorConfig] = field(default_factory=list)
    mappings: list[MappingRule] = field(default_factory=list)
    outputs: list[OutputConfig] = field(default_factory=list)
    renderer: str = "terminal"
    tick_rate: int = 30


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_config(yaml_path: str | Path) -> InstallationConfig:
    """Parse a YAML preset file into an :class:`InstallationConfig`.

    Parameters
    ----------
    yaml_path:
        Filesystem path to a ``.yaml`` file.

    Returns
    -------
    InstallationConfig
        Fully populated configuration object.

    Raises
    ------
    FileNotFoundError
        If *yaml_path* does not exist.
    ValueError
        If the YAML content is not a mapping (dict).
    """
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as fh:
        raw: Any = yaml.safe_load(fh)

    if not isinstance(raw, dict):
        raise ValueError(f"Expected a YAML mapping, got {type(raw).__name__}")

    return _parse_config(raw)


def load_config_from_dict(raw: dict[str, Any]) -> InstallationConfig:
    """Build an :class:`InstallationConfig` directly from a dict.

    Useful in tests and when YAML has already been parsed.
    """
    return _parse_config(raw)


def _parse_config(raw: dict[str, Any]) -> InstallationConfig:
    """Internal helper that converts a raw dict to a config object."""
    sensors: list[SensorConfig] = []
    for s in raw.get("sensors", []):
        stype = s.get("type", "generic")
        params = {k: v for k, v in s.items() if k != "type"}
        sensors.append(SensorConfig(type=stype, params=params))

    mappings: list[MappingRule] = []
    for m in raw.get("mappings", []):
        mappings.append(
            MappingRule(
                source_param=m["source"],
                target_param=m["target"],
                transform=m.get("transform", "linear"),
                min_out=float(m.get("min_out", 0.0)),
                max_out=float(m.get("max_out", 1.0)),
            )
        )

    outputs: list[OutputConfig] = []
    for o in raw.get("outputs", []):
        outputs.append(OutputConfig(type=o.get("type", "visual")))

    return InstallationConfig(
        name=raw.get("name", "Untitled Installation"),
        sensors=sensors,
        mappings=mappings,
        outputs=outputs,
        renderer=raw.get("renderer", "terminal"),
        tick_rate=int(raw.get("tick_rate", 30)),
    )


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

def validate_config(config: InstallationConfig) -> list[str]:
    """Check *config* for common errors.

    Returns a list of human-readable error strings.  An empty list means
    the configuration is valid.
    """
    errors: list[str] = []

    if not config.name or not config.name.strip():
        errors.append("Installation name is empty.")

    if not config.sensors:
        errors.append("At least one sensor is required.")

    for i, s in enumerate(config.sensors):
        if s.type not in SENSOR_REGISTRY:
            errors.append(
                f"Sensor #{i}: unknown type {s.type!r}. "
                f"Available: {sorted(SENSOR_REGISTRY)}"
            )

    if not config.mappings:
        errors.append("At least one mapping rule is required.")

    for i, m in enumerate(config.mappings):
        if not m.source_param:
            errors.append(f"Mapping #{i}: source_param is empty.")
        if not m.target_param:
            errors.append(f"Mapping #{i}: target_param is empty.")
        if m.min_out > m.max_out:
            errors.append(
                f"Mapping #{i}: min_out ({m.min_out}) > max_out ({m.max_out})."
            )

    if not config.outputs:
        errors.append("At least one output target is required.")

    for i, o in enumerate(config.outputs):
        if o.type not in OUTPUT_REGISTRY:
            errors.append(
                f"Output #{i}: unknown type {o.type!r}. "
                f"Available: {sorted(OUTPUT_REGISTRY)}"
            )

    if config.tick_rate < 1:
        errors.append(f"tick_rate must be >= 1, got {config.tick_rate}.")

    valid_renderers = {"terminal", "json_stream", "osc"}
    if config.renderer not in valid_renderers:
        errors.append(
            f"Unknown renderer {config.renderer!r}. "
            f"Available: {sorted(valid_renderers)}"
        )

    return errors


# ---------------------------------------------------------------------------
# Materialization helpers
# ---------------------------------------------------------------------------

def materialize_sensors(config: InstallationConfig) -> list[Sensor]:
    """Create live :class:`Sensor` instances from config."""
    sensors: list[Sensor] = []
    for sc in config.sensors:
        sensors.append(create_sensor(sc.type, **sc.params))
    return sensors


def materialize_outputs(config: InstallationConfig) -> list[OutputTarget]:
    """Create live :class:`OutputTarget` instances from config."""
    return [create_output(oc.type) for oc in config.outputs]
