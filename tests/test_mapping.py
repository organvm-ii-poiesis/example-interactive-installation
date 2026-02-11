"""Tests for the parameter mapping engine."""

from __future__ import annotations

import pytest

from src.mapping import (
    MappingEngine,
    MappingRule,
    exponential_map,
    invert,
    linear_map,
    threshold_gate,
)
from src.sensor_sim import SensorData


class TestLinearMap:
    """Tests for the linear_map transform."""

    def test_zero_maps_to_min(self) -> None:
        assert linear_map(0.0, 10.0, 20.0) == 10.0

    def test_one_maps_to_max(self) -> None:
        assert linear_map(1.0, 10.0, 20.0) == 20.0

    def test_midpoint(self) -> None:
        assert linear_map(0.5, 0.0, 100.0) == 50.0

    def test_clamps_above_one(self) -> None:
        assert linear_map(1.5, 0.0, 1.0) == 1.0

    def test_clamps_below_zero(self) -> None:
        assert linear_map(-0.5, 0.0, 1.0) == 0.0

    def test_negative_output_range(self) -> None:
        result = linear_map(0.5, -1.0, 1.0)
        assert abs(result - 0.0) < 1e-9


class TestExponentialMap:
    """Tests for the exponential_map transform."""

    def test_zero_maps_to_min(self) -> None:
        assert exponential_map(0.0, 0.0, 1.0) == 0.0

    def test_one_maps_to_max(self) -> None:
        assert exponential_map(1.0, 0.0, 1.0) == 1.0

    def test_midpoint_is_lower_than_linear(self) -> None:
        # Exponential curve means 0.5 input produces less than 0.5 output
        result = exponential_map(0.5, 0.0, 1.0)
        assert result < 0.5

    def test_low_value_near_zero(self) -> None:
        result = exponential_map(0.1, 0.0, 1.0)
        assert result < 0.01  # 0.1^2.5 ≈ 0.003


class TestThresholdGate:
    """Tests for the threshold_gate transform."""

    def test_below_threshold(self) -> None:
        assert threshold_gate(0.3, 0.0, 1.0) == 0.0

    def test_above_threshold(self) -> None:
        assert threshold_gate(0.7, 0.0, 1.0) == 1.0

    def test_at_threshold(self) -> None:
        assert threshold_gate(0.5, 0.0, 1.0) == 1.0

    def test_custom_output_range(self) -> None:
        assert threshold_gate(0.8, 10.0, 20.0) == 20.0
        assert threshold_gate(0.2, 10.0, 20.0) == 10.0


class TestInvert:
    """Tests for the invert transform."""

    def test_zero_maps_to_max(self) -> None:
        assert invert(0.0, 0.0, 1.0) == 1.0

    def test_one_maps_to_min(self) -> None:
        assert invert(1.0, 0.0, 1.0) == 0.0

    def test_midpoint(self) -> None:
        result = invert(0.5, 0.0, 1.0)
        assert abs(result - 0.5) < 1e-9

    def test_custom_range(self) -> None:
        result = invert(0.0, 100.0, 200.0)
        assert result == 200.0


class TestMappingEngine:
    """Tests for the MappingEngine class."""

    def _make_depth_data(self, avg_depth: float = 0.5) -> SensorData:
        return SensorData(
            timestamp=1.0,
            sensor_type="depth",
            data={"avg_depth": avg_depth, "presence": 0.8, "motion_energy": 0.3},
        )

    def test_single_rule(self) -> None:
        rules = [
            MappingRule(
                source_param="depth.avg_depth",
                target_param="visual.brightness",
                transform="linear",
                min_out=0.0,
                max_out=1.0,
            )
        ]
        engine = MappingEngine(rules)
        result = engine.apply(self._make_depth_data(0.5))
        assert "visual.brightness" in result
        assert abs(result["visual.brightness"] - 0.5) < 0.01

    def test_multiple_rules(self) -> None:
        rules = [
            MappingRule("depth.avg_depth", "visual.brightness", "linear", 0.0, 1.0),
            MappingRule("depth.presence", "visual.glow", "threshold", 0.0, 1.0),
        ]
        engine = MappingEngine(rules)
        result = engine.apply(self._make_depth_data())
        assert "visual.brightness" in result
        assert "visual.glow" in result
        assert result["visual.glow"] == 1.0  # presence=0.8 > 0.5 threshold

    def test_ignores_unmatched_sensor_type(self) -> None:
        rules = [
            MappingRule("motion.dx", "visual.x", "linear", 0.0, 1.0),
        ]
        engine = MappingEngine(rules)
        result = engine.apply(self._make_depth_data())
        assert "visual.x" not in result  # depth data, not motion

    def test_smooth_transform(self) -> None:
        rules = [
            MappingRule("depth.avg_depth", "visual.smooth_val", "smooth", 0.0, 1.0),
        ]
        engine = MappingEngine(rules, smooth_alpha=0.5)
        r1 = engine.apply(self._make_depth_data(1.0))
        r2 = engine.apply(self._make_depth_data(0.0))
        # After smoothing, the second result should not jump to 0
        assert r2["visual.smooth_val"] > 0.1

    def test_missing_source_param_skipped(self) -> None:
        rules = [
            MappingRule("depth.nonexistent", "visual.x", "linear", 0.0, 1.0),
        ]
        engine = MappingEngine(rules)
        result = engine.apply(self._make_depth_data())
        assert "visual.x" not in result
