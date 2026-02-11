"""Tests for simulated sensor classes."""

from __future__ import annotations

import pytest

from src.sensor_sim import (
    DepthSensor,
    LidarSensor,
    MotionSensor,
    SensorData,
    create_sensor,
)


class TestSensorData:
    """Tests for the SensorData envelope."""

    def test_immutable(self) -> None:
        sd = SensorData(timestamp=1.0, sensor_type="test", data={"a": 1})
        with pytest.raises(AttributeError):
            sd.timestamp = 2.0  # type: ignore[misc]

    def test_fields(self) -> None:
        sd = SensorData(timestamp=1.0, sensor_type="depth", data={"x": 42})
        assert sd.sensor_type == "depth"
        assert sd.data["x"] == 42


class TestDepthSensor:
    """Tests for the DepthSensor class."""

    def test_produces_valid_data(self) -> None:
        sensor = DepthSensor(width=10, height=5, noise=0.0)
        reading = sensor.read()
        assert reading.sensor_type == "depth"
        assert "field" in reading.data
        assert "avg_depth" in reading.data
        assert "presence" in reading.data
        assert "motion_energy" in reading.data

    def test_field_shape(self) -> None:
        sensor = DepthSensor(width=8, height=4, noise=0.0)
        reading = sensor.read()
        field = reading.data["field"]
        assert len(field) == 4
        assert all(len(row) == 8 for row in field)

    def test_values_in_range(self) -> None:
        sensor = DepthSensor(width=10, height=5, noise=0.0)
        reading = sensor.read()
        for row in reading.data["field"]:
            for val in row:
                assert 0.0 <= val <= 1.0

    def test_noise_within_bounds(self) -> None:
        sensor = DepthSensor(width=10, height=5, noise=0.05)
        reading = sensor.read()
        for row in reading.data["field"]:
            for val in row:
                assert 0.0 <= val <= 1.0  # clamped by _add_noise

    def test_multiple_reads_advance_state(self) -> None:
        sensor = DepthSensor(width=5, height=3, noise=0.0)
        r1 = sensor.read()
        r2 = sensor.read()
        # Timestamps should differ
        assert r2.timestamp >= r1.timestamp

    def test_avg_depth_is_float(self) -> None:
        sensor = DepthSensor(width=5, height=3, noise=0.0)
        reading = sensor.read()
        assert isinstance(reading.data["avg_depth"], float)


class TestLidarSensor:
    """Tests for the LidarSensor class."""

    def test_produces_valid_data(self) -> None:
        sensor = LidarSensor(num_points=50, noise=0.0)
        reading = sensor.read()
        assert reading.sensor_type == "lidar"
        assert "points" in reading.data
        assert "nearest_distance" in reading.data
        assert "centroid_x" in reading.data

    def test_point_count(self) -> None:
        sensor = LidarSensor(num_points=30, noise=0.0)
        reading = sensor.read()
        assert len(reading.data["points"]) == 30

    def test_point_format(self) -> None:
        sensor = LidarSensor(num_points=10, noise=0.0)
        reading = sensor.read()
        for point in reading.data["points"]:
            assert len(point) == 3  # (x, y, z)
            assert all(isinstance(c, float) for c in point)

    def test_nearest_distance_positive(self) -> None:
        sensor = LidarSensor(num_points=50, noise=0.0)
        reading = sensor.read()
        assert reading.data["nearest_distance"] >= 0.0


class TestMotionSensor:
    """Tests for the MotionSensor class."""

    def test_produces_valid_data(self) -> None:
        sensor = MotionSensor(noise=0.0)
        reading = sensor.read()
        assert reading.sensor_type == "motion"
        assert "dx" in reading.data
        assert "dy" in reading.data
        assert "magnitude" in reading.data

    def test_magnitude_consistent(self) -> None:
        sensor = MotionSensor(noise=0.0)
        reading = sensor.read()
        dx = reading.data["dx"]
        dy = reading.data["dy"]
        mag = reading.data["magnitude"]
        expected = (dx**2 + dy**2) ** 0.5
        assert abs(mag - expected) < 0.01

    def test_smooth_output(self) -> None:
        """Multiple reads should produce smoothly varying values."""
        sensor = MotionSensor(noise=0.0)
        values = [sensor.read().data["dx"] for _ in range(10)]
        # Check that consecutive differences are small (smooth)
        diffs = [abs(values[i + 1] - values[i]) for i in range(len(values) - 1)]
        assert all(d < 0.5 for d in diffs)


class TestCreateSensor:
    """Tests for the factory function."""

    def test_create_depth(self) -> None:
        s = create_sensor("depth", width=5, height=3)
        assert isinstance(s, DepthSensor)

    def test_create_lidar(self) -> None:
        s = create_sensor("lidar", num_points=20)
        assert isinstance(s, LidarSensor)

    def test_create_motion(self) -> None:
        s = create_sensor("motion")
        assert isinstance(s, MotionSensor)

    def test_unknown_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown sensor type"):
            create_sensor("imaginary")
