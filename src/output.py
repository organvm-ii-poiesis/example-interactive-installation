"""Output target abstraction and parameter routing.

Provides a thin layer between the mapping engine and actual renderers.
Each :class:`OutputTarget` subclass represents a category of output
(visual, audio, spatial) and collects the parameters relevant to it.

The :class:`OutputRouter` inspects parameter prefixes (``visual.*``,
``audio.*``, ``spatial.*``) and dispatches them to the appropriate
target, so renderers receive only the parameters they care about.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Base target
# ---------------------------------------------------------------------------

class OutputTarget:
    """Base class for output destinations.

    Subclasses override :meth:`send` to do something useful with the
    incoming parameters (store them, log them, forward them, etc.).
    """

    target_type: str = "generic"

    def __init__(self) -> None:
        self.last_params: dict[str, float] = {}

    def send(self, params: dict[str, float]) -> None:
        """Receive a batch of parameters for this output category."""
        self.last_params = dict(params)


# ---------------------------------------------------------------------------
# Concrete targets
# ---------------------------------------------------------------------------

class VisualOutput(OutputTarget):
    """Stores parameters destined for visual rendering.

    Typical keys: ``particle_density``, ``brightness``, ``trace_x``,
    ``trace_y``, ``trace_brightness``.
    """

    target_type: str = "visual"


class AudioOutput(OutputTarget):
    """Stores parameters destined for audio rendering.

    Typical keys: ``volume``, ``pitch``, ``complexity``.
    """

    target_type: str = "audio"


class SpatialOutput(OutputTarget):
    """Stores parameters destined for spatial positioning.

    Typical keys: ``pan``, ``depth``, ``elevation``.
    """

    target_type: str = "spatial"


# ---------------------------------------------------------------------------
# Target registry
# ---------------------------------------------------------------------------

OUTPUT_REGISTRY: dict[str, type[OutputTarget]] = {
    "visual": VisualOutput,
    "audio": AudioOutput,
    "spatial": SpatialOutput,
}


def create_output(output_type: str) -> OutputTarget:
    """Instantiate an output target by type name."""
    cls = OUTPUT_REGISTRY.get(output_type)
    if cls is None:
        raise ValueError(
            f"Unknown output type {output_type!r}. "
            f"Available: {sorted(OUTPUT_REGISTRY)}"
        )
    return cls()


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

class OutputRouter:
    """Dispatches mapped parameters to the correct output targets.

    Parameters are expected to have dotted prefixes matching target types
    (e.g. ``visual.brightness``).  The router strips the prefix before
    forwarding.

    Parameters
    ----------
    targets:
        List of :class:`OutputTarget` instances to route to.
    """

    def __init__(self, targets: list[OutputTarget]) -> None:
        self._targets: dict[str, OutputTarget] = {}
        for t in targets:
            self._targets[t.target_type] = t

    @property
    def targets(self) -> dict[str, OutputTarget]:
        """Read-only view of registered targets keyed by type."""
        return dict(self._targets)

    def route(self, params: dict[str, float]) -> dict[str, dict[str, float]]:
        """Route *params* to targets based on prefix.

        Returns a dict of ``{target_type: {param_name: value}}`` for
        every target that received at least one parameter.
        """
        buckets: dict[str, dict[str, float]] = {}

        for key, value in params.items():
            parts = key.split(".", 1)
            if len(parts) != 2:
                continue
            prefix, name = parts
            if prefix not in self._targets:
                continue
            buckets.setdefault(prefix, {})[name] = value

        for prefix, bucket in buckets.items():
            self._targets[prefix].send(bucket)

        return buckets
