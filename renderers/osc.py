"""OSC (Open Sound Control) renderer for Max/MSP, TouchDesigner, SuperCollider.

Formats output parameters as OSC messages following the address pattern
``/installation/{param_name}``.  This renderer does NOT send messages
over the network (that would require the ``python-osc`` dependency);
instead it formats and buffers them for testing, logging, or manual
forwarding.

OSC message format::

    ("/installation/visual/brightness", 0.72)
    ("/installation/audio/volume", 0.45)

The buffer can be read by external code that does the actual UDP send.
"""

from __future__ import annotations

from typing import Any


class OscRenderer:
    """Formats installation parameters as OSC address/value pairs.

    Parameters
    ----------
    address_prefix:
        Root OSC address prefix (default ``"/installation"``).
    buffer_size:
        Maximum number of messages to keep in the ring buffer.
        Oldest messages are discarded when the buffer overflows.
    log:
        If ``True``, print every message to stdout (useful for
        debugging).
    """

    def __init__(
        self,
        address_prefix: str = "/installation",
        buffer_size: int = 1000,
        log: bool = False,
    ) -> None:
        self.address_prefix = address_prefix.rstrip("/")
        self.buffer_size = buffer_size
        self.log = log

        # Ring buffer of (address, value) tuples
        self._buffer: list[tuple[str, float]] = []
        self.messages_total: int = 0

    # -- public API -------------------------------------------------------

    def render(self, frame_data: dict[str, Any]) -> None:
        """Convert frame parameters to OSC messages and buffer them."""
        params = frame_data.get("params", {})

        for key, value in params.items():
            # Convert dotted param name to OSC path
            # e.g. "visual.brightness" → "/installation/visual/brightness"
            osc_path = key.replace(".", "/")
            address = f"{self.address_prefix}/{osc_path}"

            message = (address, float(value))
            self._push(message)

            if self.log:
                print(f"OSC  {address}  {value:.6f}")

    def get_buffer(self) -> list[tuple[str, float]]:
        """Return a copy of the current message buffer."""
        return list(self._buffer)

    def get_last_messages(self, n: int = 10) -> list[tuple[str, float]]:
        """Return the last *n* messages from the buffer."""
        return list(self._buffer[-n:])

    def clear_buffer(self) -> None:
        """Empty the message buffer."""
        self._buffer.clear()

    def format_bundle(self, frame_data: dict[str, Any]) -> list[tuple[str, float]]:
        """Format one frame as an OSC bundle (list of messages).

        Unlike :meth:`render`, this does not modify the internal buffer.
        """
        params = frame_data.get("params", {})
        bundle: list[tuple[str, float]] = []
        for key, value in params.items():
            osc_path = key.replace(".", "/")
            address = f"{self.address_prefix}/{osc_path}"
            bundle.append((address, float(value)))
        return bundle

    # -- internals --------------------------------------------------------

    def _push(self, message: tuple[str, float]) -> None:
        """Add a message to the ring buffer, evicting old entries if full."""
        self._buffer.append(message)
        self.messages_total += 1
        if len(self._buffer) > self.buffer_size:
            self._buffer = self._buffer[-self.buffer_size:]
