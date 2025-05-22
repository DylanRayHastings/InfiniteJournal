"""
StatusBar: displays elapsed time and optional notifications.
"""

from core.interfaces import Renderer, Clock
from config import Settings

class StatusBar:
    """
    UI component to display the elapsed time and (optionally) status messages.

    Args:
        clock (Clock): Provides timing information.
        renderer (Renderer): Handles drawing the status bar.
        settings (Settings): Accesses configuration constants.
    """
    def __init__(self, clock: Clock, renderer: Renderer, settings: Settings) -> None:
        self._clock = clock
        self._renderer = renderer
        self._settings = settings

    def render(self) -> None:
        """
        Renders the status bar at the bottom-left corner, showing the elapsed time.
        Extend this method to include more status messages or icons as needed.
        """
        # Fetch elapsed time and format
        elapsed = self._clock.get_time()
        timestamp = f"Time: {elapsed:.1f}s"

        # Position 10px from left, 20px from bottom
        x = 10
        y = self._settings.height - 20

        # Text color
        color = (255, 255, 255)

        # Draw the timestamp
        # draw_text(text, position, font_size, color)
        self._renderer.draw_text(timestamp, (x, y), 14, color)
