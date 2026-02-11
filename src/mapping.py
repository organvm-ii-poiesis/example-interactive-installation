"""Parameter mapping engine for sensor-to-output transformations.

The mapping engine sits between sensors and outputs.  It takes raw
sensor readings, applies configurable mathematical transforms, and
produces normalized output parameters that renderers can consume.

Supported transforms:
    - **linear** — proportional scaling between input and output ranges
    - **exponential** — curved scaling for perceptually uniform brightness/volume
    - **threshold** — binary gate that flips at a configurable cutoff
    - **invert** — flips the value within its range (1 - x)
    - **smooth** — exponential moving average (low-pass filter)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable

from .sensor_sim import SensorData


# ---------------------------------------------------------------------------
# Mapping rule
# ---------------------------------------------------------------------------

@dataclass
class MappingRule:
    """Declarative description of one sensor→output parameter mapping.

    Attributes
    ----------
    source_param:
        Dot-path into the sensor data dict, e.g. ``"depth.avg_depth"``.
    target_param:
        Dot-path for the output parameter, e.g. ``"visual.brightness"``.
    transform:
        Name of the transform function (``"linear"``, ``"exponential"``,
        ``"threshold"``, ``"invert"``, ``"smooth"``).
    min_out:
        Lower bound of the output range.
    max_out:
        Upper bound of the output range.
    """

    source_param: str
    target_param: str
    transform: str = "linear"
    min_out: float = 0.0
    max_out: float = 1.0


# ---------------------------------------------------------------------------
# Built-in transforms
# ---------------------------------------------------------------------------

def linear_map(value: float, min_out: float, max_out: float) -> float:
    """Scale *value* (assumed 0-1) linearly into [min_out, max_out]."""
    clamped = max(0.0, min(1.0, value))
    return min_out + clamped * (max_out - min_out)


def exponential_map(value: float, min_out: float, max_out: float) -> float:
    """Apply an exponential curve before scaling.

    Etically useful for audio volume / brightness where human perception
    is logarithmic; this curve makes small inputs nearly silent and large
    inputs ramp sharply.
    """
    clamped = max(0.0, min(1.0, value))
    curved = clamped ** 2.5
    return min_out + curved * (max_out - min_out)


def threshold_gate(value: float, min_out: float, max_out: float) -> float:
    """Return *max_out* when value >= 0.5, otherwise *min_out*."""
    return max_out if value >= 0.5 else min_out


def invert(value: float, min_out: float, max_out: float) -> float:
    """Invert the value then scale: closer → louder, etc."""
    clamped = max(0.0, min(1.0, value))
    inverted = 1.0 - clamped
    return min_out + inverted * (max_out - min_out)


# ---------------------------------------------------------------------------
# Transform registry
# ---------------------------------------------------------------------------

TRANSFORMS: dict[str, Callable[[float, float, float], float]] = {
    "linear": linear_map,
    "exponential": exponential_map,
    "threshold": threshold_gate,
    "invert": invert,
}


# ---------------------------------------------------------------------------
# Low-pass smoother (stateful, per-parameter)
# ---------------------------------------------------------------------------

class _Smoother:
    """Exponential moving average filter."""

    def __init__(self, alpha: float = 0.15) -> None:
        self.alpha = alpha
        self._value: float | None = None

    def __call__(self, raw: float) -> float:
        if self._value is None:
            self._value = raw
        else:
            self._value += self.alpha * (raw - self._value)
        return self._value


# ---------------------------------------------------------------------------
# Mapping engine
# ---------------------------------------------------------------------------

class MappingEngine:
    """Applies a set of :class:`MappingRule` instances to sensor data.

    Parameters
    ----------
    rules:
        Ordered list of mapping rules.  All rules are evaluated on every
        call to :meth:`apply`.
    smooth_alpha:
        Smoothing factor for the ``"smooth"`` transform.  Lower values
        produce heavier smoothing.
    """

    def __init__(
        self,
        rules: list[MappingRule],
        smooth_alpha: float = 0.15,
    ) -> None:
        self.rules = list(rules)
        self._smoothers: dict[str, _Smoother] = {}
        self._smooth_alpha = smooth_alpha

    # -- internal helpers -------------------------------------------------

    @staticmethod
    def _resolve(data: dict[str, Any], dotpath: str) -> float | None:
        """Walk a dot-separated path into a nested dict.

        The first segment is the sensor type (already used for routing),
        so we skip it and look for the remainder in the data dict.
        """
        parts = dotpath.split(".")
        if len(parts) < 2:
            return None

        # Strip sensor-type prefix — the data dict is already scoped
        key = parts[-1]
        value = data.get(key)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _get_smoother(self, key: str) -> _Smoother:
        if key not in self._smoothers:
            self._smoothers[key] = _Smoother(self._smooth_alpha)
        return self._smoothers[key]

    # -- public API -------------------------------------------------------

    def apply(self, sensor_data: SensorData) -> dict[str, float]:
        """Map one sensor reading to output parameters.

        Returns a dict whose keys are target parameter paths (e.g.
        ``"visual.brightness"``) and whose values are floats.
        """
        results: dict[str, float] = {}

        for rule in self.rules:
            # Only apply rules whose source prefix matches this sensor
            source_prefix = rule.source_param.split(".")[0]
            if source_prefix != sensor_data.sensor_type:
                continue

            raw = self._resolve(sensor_data.data, rule.source_param)
            if raw is None:
                continue

            transform_name = rule.transform

            if transform_name == "smooth":
                smoother = self._get_smoother(rule.target_param)
                value = smoother(raw)
                value = linear_map(value, rule.min_out, rule.max_out)
            else:
                fn = TRANSFORMS.get(transform_name, linear_map)
                value = fn(raw, rule.min_out, rule.max_out)

            results[rule.target_param] = round(value, 6)

        return results
