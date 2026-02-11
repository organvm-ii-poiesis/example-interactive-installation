"""JSON streaming renderer — one JSON line per frame to stdout.

Useful for piping installation output to external visualization tools,
logging systems, or web dashboards.  Each frame is emitted as a single
line of compact JSON (NDJSON / JSON Lines format).

Example output::

    {"frame": 0, "timestamp": 1707600000.123, "params": {"visual.brightness": 0.72, ...}}
    {"frame": 1, "timestamp": 1707600000.156, "params": {"visual.brightness": 0.74, ...}}
"""

from __future__ import annotations

import json
import sys
from typing import Any


class JsonStreamRenderer:
    """Emits one JSON object per frame to stdout.

    Parameters
    ----------
    output:
        File-like object to write to (defaults to ``sys.stdout``).
    compact:
        If ``True`` (default), emit one line per frame with no extra
        whitespace.  If ``False``, pretty-print each frame.
    include_routed:
        If ``True``, include the ``routed`` breakdown alongside the
        flat ``params`` dict.
    """

    def __init__(
        self,
        output: Any = None,
        compact: bool = True,
        include_routed: bool = False,
    ) -> None:
        self.output = output or sys.stdout
        self.compact = compact
        self.include_routed = include_routed
        self.lines_written: int = 0

    def render(self, frame_data: dict[str, Any]) -> None:
        """Write one frame as a JSON line."""
        record: dict[str, Any] = {
            "frame": frame_data.get("frame", 0),
            "timestamp": frame_data.get("timestamp", 0.0),
            "params": frame_data.get("params", {}),
        }

        if self.include_routed:
            record["routed"] = frame_data.get("routed", {})

        if self.compact:
            line = json.dumps(record, separators=(",", ":"))
        else:
            line = json.dumps(record, indent=2)

        self.output.write(line + "\n")
        self.output.flush()
        self.lines_written += 1

    def get_last_line(self) -> str | None:
        """Return the last written line (only works with StringIO outputs)."""
        if hasattr(self.output, "getvalue"):
            lines = self.output.getvalue().strip().split("\n")
            return lines[-1] if lines else None
        return None
