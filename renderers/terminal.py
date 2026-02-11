"""Terminal-based ASCII renderer for interactive installations.

Renders frame data as colored ASCII art in the terminal using ANSI
escape codes.  Designed to produce visually interesting output even
at low resolutions — useful for rapid prototyping and demos without
a full graphics stack.

Brightness-to-character mapping (darkest to brightest)::

    ' .:-=+*#%@'
"""

from __future__ import annotations

import sys
from typing import Any


# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------

RESET = "\033[0m"
CLEAR_SCREEN = "\033[2J\033[H"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"

# Brightness ramp (10 levels, index 0 = dark)
BRIGHTNESS_CHARS = " .:-=+*#%@"


def _ansi_fg(r: int, g: int, b: int) -> str:
    """Return an ANSI 24-bit foreground colour escape sequence."""
    return f"\033[38;2;{r};{g};{b}m"


def _brightness_to_char(value: float) -> str:
    """Map a 0-1 float to a brightness character."""
    idx = int(max(0.0, min(1.0, value)) * (len(BRIGHTNESS_CHARS) - 1))
    return BRIGHTNESS_CHARS[idx]


def _brightness_to_color(value: float) -> str:
    """Map a 0-1 float to a blue-to-white colour gradient."""
    v = max(0.0, min(1.0, value))
    # Dark blue → cyan → white
    r = int(v * 255)
    g = int(v * 255)
    b = int(80 + v * 175)
    return _ansi_fg(r, g, b)


# ---------------------------------------------------------------------------
# Arrow characters for motion vectors
# ---------------------------------------------------------------------------

_ARROWS = {
    (0, -1): "^",
    (0, 1): "v",
    (-1, 0): "<",
    (1, 0): ">",
    (-1, -1): "\\",
    (1, -1): "/",
    (-1, 1): "/",
    (1, 1): "\\",
    (0, 0): "o",
}


def _motion_arrow(dx: float, dy: float) -> str:
    """Pick a directional arrow for a motion vector."""
    sx = 0 if abs(dx) < 0.2 else (1 if dx > 0 else -1)
    sy = 0 if abs(dy) < 0.2 else (1 if dy > 0 else -1)
    return _ARROWS.get((sx, sy), "o")


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

class TerminalRenderer:
    """Renders installation frames as coloured ASCII art.

    Parameters
    ----------
    width:
        Output width in characters (default 60).
    height:
        Output height in rows (default 20).
    show_stats:
        If ``True``, print frame number and FPS below the render.
    """

    def __init__(
        self,
        width: int = 60,
        height: int = 20,
        show_stats: bool = True,
    ) -> None:
        self.width = width
        self.height = height
        self.show_stats = show_stats
        self._first_frame = True

    @staticmethod
    def clear_screen() -> None:
        """Clear the terminal and move cursor to top-left."""
        sys.stdout.write(CLEAR_SCREEN)
        sys.stdout.flush()

    def render(self, frame_data: dict[str, Any]) -> None:
        """Draw one frame to stdout."""
        if self._first_frame:
            sys.stdout.write(HIDE_CURSOR)
            self._first_frame = False

        lines: list[str] = [CLEAR_SCREEN]

        params = frame_data.get("params", {})
        routed = frame_data.get("routed", {})
        frame_num = frame_data.get("frame", 0)

        # ---- Visual rendering ----
        visual = routed.get("visual", {})
        brightness = visual.get("brightness", 0.5)
        density = visual.get("particle_density", 0.5)
        trace_x = visual.get("trace_x", 0.0)
        trace_y = visual.get("trace_y", 0.0)
        trace_br = visual.get("trace_brightness", 0.5)

        # Header
        lines.append(
            _ansi_fg(100, 200, 255)
            + f"  INSTALLATION  frame {frame_num:05d}"
            + RESET
        )
        lines.append("  " + "-" * (self.width + 2))

        # Determine render mode based on available params
        has_depth = "particle_density" in visual or "brightness" in visual
        has_trace = "trace_x" in visual

        for row in range(self.height):
            row_chars: list[str] = []
            for col in range(self.width):
                nx = col / max(1, self.width - 1)
                ny = row / max(1, self.height - 1)

                if has_trace:
                    # Motion trace mode — draw a trail from the trace point
                    tx = (trace_x + 1.0) / 2.0  # normalise -1..1 → 0..1
                    ty = (trace_y + 1.0) / 2.0
                    dist = ((nx - tx) ** 2 + (ny - ty) ** 2) ** 0.5
                    val = max(0.0, 1.0 - dist * 3.0) * trace_br
                    color = _ansi_fg(
                        int(val * 255),
                        int(val * 180),
                        int(80 + val * 175),
                    )
                    ch = _brightness_to_char(val)
                    row_chars.append(color + ch + RESET)

                elif has_depth:
                    # Depth / particle mode — radial pattern modulated by density
                    cx, cy = 0.5, 0.5
                    dist = ((nx - cx) ** 2 + (ny - cy) ** 2) ** 0.5
                    wave = 0.5 + 0.5 * __import__("math").sin(
                        dist * 20.0 - frame_num * 0.3 + density * 10.0
                    )
                    val = wave * brightness * density
                    color = _brightness_to_color(val)
                    ch = _brightness_to_char(val)
                    row_chars.append(color + ch + RESET)

                else:
                    row_chars.append(" ")

            lines.append("  |" + "".join(row_chars) + "|")

        lines.append("  " + "-" * (self.width + 2))

        # Audio bar
        audio = routed.get("audio", {})
        if audio:
            vol = audio.get("volume", 0.0)
            pitch = audio.get("pitch", 440.0)
            bar_len = int(vol * 30)
            bar = _ansi_fg(80, 255, 120) + "|" * bar_len + RESET
            lines.append(f"  AUDIO  vol={vol:.2f}  pitch={pitch:.0f}Hz  {bar}")

        # Spatial info
        spatial = routed.get("spatial", {})
        if spatial:
            pan = spatial.get("pan", 0.0)
            depth = spatial.get("depth", 0.0)
            indicator_pos = int((pan + 1.0) / 2.0 * 20)
            spatial_bar = ["."] * 21
            spatial_bar[max(0, min(20, indicator_pos))] = "O"
            lines.append(
                f"  SPATIAL  pan={pan:+.2f}  depth={depth:.2f}  "
                + "".join(spatial_bar)
            )

        if self.show_stats:
            ts = frame_data.get("timestamp", 0)
            lines.append(
                _ansi_fg(120, 120, 120)
                + f"  t={ts:.2f}  params={len(params)}"
                + RESET
            )

        sys.stdout.write("\n".join(lines) + "\n")
        sys.stdout.flush()

    def cleanup(self) -> None:
        """Restore cursor visibility."""
        sys.stdout.write(SHOW_CURSOR)
        sys.stdout.flush()
