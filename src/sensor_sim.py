"""Simulated sensor classes for interactive installation prototyping.

Provides software-only sensor emulation so installations can be developed
and tested without physical hardware.  Each sensor generates plausible
data streams that mimic real-world devices (depth cameras, LIDAR units,
motion trackers).

All sensors share a common base class and return a uniform SensorData
envelope so downstream mapping and rendering code never needs to know
which physical device (or simulation) produced the reading.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data envelope
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SensorData:
    """Immutable envelope for one sensor reading."""

    timestamp: float
    sensor_type: str
    data: dict[str, Any]


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class Sensor:
    """Abstract base for all simulated sensors.

    Parameters
    ----------
    sensor_type:
        Short identifier such as ``"depth"`` or ``"lidar"``.
    noise:
        Standard deviation of Gaussian noise added to readings.
        ``0.0`` means perfectly clean data.
    update_rate:
        Target readings per second (used only for informational
        purposes; the caller controls actual polling frequency).
    """

    def __init__(
        self,
        sensor_type: str = "generic",
        noise: float = 0.0,
        update_rate: int = 30,
    ) -> None:
        self.sensor_type = sensor_type
        self.noise = max(0.0, noise)
        self.update_rate = update_rate
        self._tick: int = 0

    # -- helpers ----------------------------------------------------------

    def _add_noise(self, value: float) -> float:
        """Add Gaussian noise to *value*, clamped to [0, 1]."""
        if self.noise <= 0.0:
            return value
        return max(0.0, min(1.0, value + random.gauss(0.0, self.noise)))

    def _add_noise_unbounded(self, value: float) -> float:
        """Add Gaussian noise without clamping."""
        if self.noise <= 0.0:
            return value
        return value + random.gauss(0.0, self.noise)

    # -- public API -------------------------------------------------------

    def read(self) -> SensorData:
        """Return one reading wrapped in a :class:`SensorData` envelope."""
        self._tick += 1
        data = self._generate()
        return SensorData(
            timestamp=time.time(),
            sensor_type=self.sensor_type,
            data=data,
        )

    def _generate(self) -> dict[str, Any]:
        """Override in subclasses to produce sensor-specific data."""
        return {}


# ---------------------------------------------------------------------------
# Depth sensor
# ---------------------------------------------------------------------------

class DepthSensor(Sensor):
    """Simulates a depth camera (e.g. Intel RealSense, Kinect).

    Produces a 2-D depth field (list of lists of floats in [0, 1]) where
    ``0`` is closest and ``1`` is farthest.  A person-shaped blob wanders
    across the field over time.

    Parameters
    ----------
    width, height:
        Resolution of the depth field in cells.
    noise:
        Standard deviation of Gaussian noise.
    update_rate:
        Target FPS (informational).
    """

    def __init__(
        self,
        width: int = 40,
        height: int = 20,
        noise: float = 0.05,
        update_rate: int = 30,
    ) -> None:
        super().__init__(sensor_type="depth", noise=noise, update_rate=update_rate)
        self.width = max(1, width)
        self.height = max(1, height)

        # Blob state — smooth random walk
        self._blob_x: float = self.width / 2.0
        self._blob_y: float = self.height / 2.0
        self._blob_vx: float = 0.0
        self._blob_vy: float = 0.0

    # -- internals --------------------------------------------------------

    def _step_blob(self) -> None:
        """Advance the person-blob by one tick with momentum."""
        # Random acceleration
        self._blob_vx += random.gauss(0, 0.3)
        self._blob_vy += random.gauss(0, 0.3)

        # Damping
        self._blob_vx *= 0.9
        self._blob_vy *= 0.9

        self._blob_x += self._blob_vx
        self._blob_y += self._blob_vy

        # Bounce off edges
        if self._blob_x < 2 or self._blob_x > self.width - 3:
            self._blob_vx *= -1
            self._blob_x = max(2, min(self.width - 3, self._blob_x))
        if self._blob_y < 2 or self._blob_y > self.height - 3:
            self._blob_vy *= -1
            self._blob_y = max(2, min(self.height - 3, self._blob_y))

    def _generate(self) -> dict[str, Any]:
        self._step_blob()

        # Build depth field — background at ~0.9, blob creates a dip
        blob_radius_x = 3.0
        blob_radius_y = 5.0  # taller than wide — person shape
        field: list[list[float]] = []
        presence = 0.0
        total_depth = 0.0
        motion_energy = abs(self._blob_vx) + abs(self._blob_vy)

        for row in range(self.height):
            row_data: list[float] = []
            for col in range(self.width):
                dx = (col - self._blob_x) / blob_radius_x
                dy = (row - self._blob_y) / blob_radius_y
                dist_sq = dx * dx + dy * dy
                if dist_sq < 1.0:
                    # Inside blob — closer to camera
                    depth = 0.2 + 0.3 * dist_sq
                    presence = max(presence, 1.0 - dist_sq)
                else:
                    depth = 0.85 + 0.1 * math.sin(row * 0.3 + col * 0.2)
                depth = self._add_noise(depth)
                row_data.append(round(depth, 4))
                total_depth += depth
            field.append(row_data)

        cell_count = self.width * self.height
        avg_depth = total_depth / cell_count if cell_count else 0.0

        return {
            "field": field,
            "width": self.width,
            "height": self.height,
            "avg_depth": round(avg_depth, 4),
            "presence": round(min(1.0, presence), 4),
            "motion_energy": round(min(1.0, motion_energy / 4.0), 4),
        }


# ---------------------------------------------------------------------------
# LIDAR sensor
# ---------------------------------------------------------------------------

class LidarSensor(Sensor):
    """Simulates a 2-D/3-D LIDAR scanner.

    Produces a point cloud (list of ``(x, y, z)`` tuples) representing
    objects detected at various distances.  A cluster of points orbits
    slowly to simulate a moving object.

    Parameters
    ----------
    num_points:
        Number of points per scan.
    noise:
        Standard deviation of positional noise.
    update_rate:
        Target scans per second (informational).
    """

    def __init__(
        self,
        num_points: int = 100,
        noise: float = 0.02,
        update_rate: int = 15,
    ) -> None:
        super().__init__(sensor_type="lidar", noise=noise, update_rate=update_rate)
        self.num_points = max(1, num_points)
        self._angle: float = 0.0

    def _generate(self) -> dict[str, Any]:
        self._angle += 0.05  # slow orbit

        points: list[tuple[float, float, float]] = []
        cluster_cx = 3.0 * math.cos(self._angle)
        cluster_cz = 3.0 * math.sin(self._angle) + 5.0  # offset so always in front

        cluster_size = self.num_points // 3

        for i in range(self.num_points):
            if i < cluster_size:
                # Cluster points (simulated object)
                x = cluster_cx + random.gauss(0, 0.3)
                y = random.gauss(0, 0.5)
                z = cluster_cz + random.gauss(0, 0.3)
            else:
                # Background scatter
                angle = random.uniform(0, 2 * math.pi)
                dist = random.uniform(2, 10)
                x = dist * math.cos(angle)
                y = random.uniform(-1, 1)
                z = dist * math.sin(angle)

            x = self._add_noise_unbounded(x)
            y = self._add_noise_unbounded(y)
            z = self._add_noise_unbounded(z)
            points.append((round(x, 4), round(y, 4), round(z, 4)))

        # Derived metrics
        xs = [p[0] for p in points]
        zs = [p[2] for p in points]
        distances = [math.sqrt(p[0] ** 2 + p[1] ** 2 + p[2] ** 2) for p in points]

        centroid_x = sum(xs) / len(xs)
        centroid_z = sum(zs) / len(zs)
        nearest = min(distances)

        # Point density — how clustered the points are
        mean_dist = sum(distances) / len(distances)
        variance = sum((d - mean_dist) ** 2 for d in distances) / len(distances)
        density = max(0.0, min(1.0, 1.0 - math.sqrt(variance) / 5.0))

        return {
            "points": points,
            "num_points": len(points),
            "nearest_distance": round(nearest, 4),
            "centroid_x": round(centroid_x, 4),
            "centroid_z": round(centroid_z, 4),
            "point_density": round(density, 4),
        }


# ---------------------------------------------------------------------------
# Motion sensor
# ---------------------------------------------------------------------------

class MotionSensor(Sensor):
    """Simulates a motion tracker (e.g. optical flow, accelerometer).

    Produces smooth motion vectors ``(dx, dy)`` and a scalar magnitude
    using Perlin-like sinusoidal paths with random phase offsets.

    Parameters
    ----------
    noise:
        Standard deviation of noise on each axis.
    update_rate:
        Target readings per second (informational).
    """

    def __init__(
        self,
        noise: float = 0.1,
        update_rate: int = 30,
    ) -> None:
        super().__init__(sensor_type="motion", noise=noise, update_rate=update_rate)
        self._phase_x: float = random.uniform(0, 2 * math.pi)
        self._phase_y: float = random.uniform(0, 2 * math.pi)
        self._freq_x: float = random.uniform(0.3, 0.7)
        self._freq_y: float = random.uniform(0.2, 0.5)

    def _generate(self) -> dict[str, Any]:
        t = self._tick * 0.05

        dx = math.sin(t * self._freq_x + self._phase_x) * 0.8
        dy = math.cos(t * self._freq_y + self._phase_y) * 0.8

        # Occasionally change direction
        if random.random() < 0.02:
            self._phase_x += random.uniform(-0.5, 0.5)
            self._phase_y += random.uniform(-0.5, 0.5)

        dx = self._add_noise_unbounded(dx)
        dy = self._add_noise_unbounded(dy)
        magnitude = math.sqrt(dx * dx + dy * dy)

        return {
            "dx": round(dx, 4),
            "dy": round(dy, 4),
            "magnitude": round(magnitude, 4),
        }


# ---------------------------------------------------------------------------
# Factory helper
# ---------------------------------------------------------------------------

SENSOR_REGISTRY: dict[str, type[Sensor]] = {
    "depth": DepthSensor,
    "lidar": LidarSensor,
    "motion": MotionSensor,
}


def create_sensor(sensor_type: str, **kwargs: Any) -> Sensor:
    """Instantiate a sensor by type name.

    Raises ``ValueError`` if *sensor_type* is not registered.
    """
    cls = SENSOR_REGISTRY.get(sensor_type)
    if cls is None:
        raise ValueError(
            f"Unknown sensor type {sensor_type!r}. "
            f"Available: {sorted(SENSOR_REGISTRY)}"
        )
    return cls(**kwargs)
