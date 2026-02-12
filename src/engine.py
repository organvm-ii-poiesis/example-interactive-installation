"""Main installation engine — the real-time loop that ties everything together.

The :class:`InstallationEngine` reads from sensors, applies mappings,
routes parameters to output targets, and invokes the renderer on every
frame.  It is the single entry-point for running an installation.

Usage::

    from src.config import load_config
    from src.engine import InstallationEngine

    config = load_config("presets/depth_field.yaml")
    engine = InstallationEngine(config)
    engine.run(duration_seconds=10)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from .config import (
    InstallationConfig,
    materialize_outputs,
    materialize_sensors,
    validate_config,
)
from .mapping import MappingEngine, MappingRule
from .output import OutputRouter, OutputTarget
from .sensor_sim import Sensor


# ---------------------------------------------------------------------------
# Renderer protocol
# ---------------------------------------------------------------------------

class Renderer(Protocol):
    """Structural protocol that any renderer must satisfy."""

    def render(self, frame_data: dict[str, Any]) -> None: ...


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class InstallationEngine:
    """Drives an interactive installation at a fixed tick rate.

    Parameters
    ----------
    config:
        Fully loaded :class:`InstallationConfig`.
    renderer:
        Optional renderer instance.  If ``None``, the engine runs
        headless (useful for testing and benchmarking).
    """

    def __init__(
        self,
        config: InstallationConfig,
        renderer: Renderer | None = None,
    ) -> None:
        # Validate
        errors = validate_config(config)
        if errors:
            raise ValueError(
                "Invalid configuration:\n  " + "\n  ".join(errors)
            )

        self.config = config
        self.renderer = renderer

        # Materialize components
        self.sensors: list[Sensor] = materialize_sensors(config)
        self.outputs: list[OutputTarget] = materialize_outputs(config)
        self.router = OutputRouter(self.outputs)
        self.mapper = MappingEngine(config.mappings)

        # Tick rate
        self.tick_rate: int = config.tick_rate
        self._tick_interval: float = 1.0 / self.tick_rate

        # Stats
        self.frame_count: int = 0
        self.elapsed_time: float = 0.0
        self._frame_times: list[float] = []

        # Callbacks
        self._frame_callbacks: list[Callable[[dict[str, Any]], None]] = []

    # -- public API -------------------------------------------------------

    def on_frame(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Register a callback invoked after every rendered frame.

        The callback receives the full ``frame_data`` dict.
        """
        self._frame_callbacks.append(callback)

    @property
    def average_fps(self) -> float:
        """Compute the average frames-per-second over the run."""
        if self.elapsed_time <= 0:
            return 0.0
        return self.frame_count / self.elapsed_time

    def run(self, duration_seconds: float, tick_rate: int | None = None) -> None:
        """Execute the main loop for *duration_seconds*.

        Parameters
        ----------
        duration_seconds:
            How long to run before stopping.
        tick_rate:
            Override the config's tick rate (frames per second).
        """
        if tick_rate is not None:
            self.tick_rate = tick_rate
            self._tick_interval = 1.0 / tick_rate

        start = time.monotonic()
        next_tick = start

        while True:
            now = time.monotonic()
            if now - start >= duration_seconds:
                break

            # Sleep until next tick
            sleep_time = next_tick - now
            if sleep_time > 0:
                time.sleep(sleep_time)

            frame_start = time.monotonic()

            # -- tick --
            frame_data = self._tick()
            self.frame_count += 1

            # Render
            if self.renderer is not None:
                self.renderer.render(frame_data)

            # Callbacks
            for cb in self._frame_callbacks:
                cb(frame_data)

            frame_end = time.monotonic()
            self._frame_times.append(frame_end - frame_start)

            next_tick += self._tick_interval

            # If we're behind schedule, catch up without busy-looping
            if next_tick < time.monotonic():
                next_tick = time.monotonic()

        self.elapsed_time = time.monotonic() - start

    def step(self) -> dict[str, Any]:
        """Execute a single tick and return the frame data.

        Useful for testing or manual stepping.
        """
        frame_data = self._tick()
        self.frame_count += 1
        if self.renderer is not None:
            self.renderer.render(frame_data)
        for cb in self._frame_callbacks:
            cb(frame_data)
        return frame_data

    # -- internals --------------------------------------------------------

    def _tick(self) -> dict[str, Any]:
        """One iteration of the sense-map-route cycle."""
        all_params: dict[str, float] = {}

        # Read all sensors and map
        for sensor in self.sensors:
            reading = sensor.read()
            mapped = self.mapper.apply(reading)
            all_params.update(mapped)

        # Route to outputs
        routed = self.router.route(all_params)

        return {
            "frame": self.frame_count,
            "timestamp": time.time(),
            "params": all_params,
            "routed": routed,
        }
