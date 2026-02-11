#!/usr/bin/env python3
"""Run a sensor-driven interactive installation simulation.

Loads the depth_field preset, creates an InstallationEngine with the
terminal renderer, runs for 5 seconds, and prints summary statistics.

Usage::

    python -m examples.run_simulation
    # or
    python examples/run_simulation.py
"""

from __future__ import annotations

import os
import sys

# Ensure the project root is on the import path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.config import load_config
from src.engine import InstallationEngine
from renderers.terminal import TerminalRenderer


def main() -> None:
    """Entry point for the depth-field simulation demo."""
    preset_path = os.path.join(PROJECT_ROOT, "presets", "depth_field.yaml")

    print("Loading preset:", preset_path)
    config = load_config(preset_path)
    print(f"  Name: {config.name}")
    print(f"  Sensors: {len(config.sensors)}")
    print(f"  Mappings: {len(config.mappings)}")
    print(f"  Outputs: {len(config.outputs)}")
    print(f"  Renderer: {config.renderer}")
    print(f"  Tick rate: {config.tick_rate} FPS")
    print()

    renderer = TerminalRenderer(width=50, height=18, show_stats=True)
    engine = InstallationEngine(config, renderer=renderer)

    duration = 5.0
    print(f"Running simulation for {duration:.0f} seconds...")
    print()

    try:
        engine.run(duration_seconds=duration)
    except KeyboardInterrupt:
        pass
    finally:
        renderer.cleanup()

    print()
    print("=" * 50)
    print("  SIMULATION COMPLETE")
    print("=" * 50)
    print(f"  Frames rendered:  {engine.frame_count}")
    print(f"  Elapsed time:     {engine.elapsed_time:.2f}s")
    print(f"  Average FPS:      {engine.average_fps:.1f}")
    print(f"  Target FPS:       {config.tick_rate}")
    print("=" * 50)


if __name__ == "__main__":
    main()
