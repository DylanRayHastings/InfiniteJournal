from core.interfaces import Renderer, Clock
from core.events import EventBus
from typing import Optional, Tuple

class PopupManager:
    """
    Manages and renders temporary pop-up messages.

    Args:
        bus (EventBus): Event bus for receiving pop-up show events.
        renderer (Renderer): Used for measuring and drawing text.
        clock (Clock): Provides current time for popup duration.
    """

    def __init__(self, bus: EventBus, renderer: Renderer, clock: Clock) -> None:
        self._renderer = renderer
        self._clock = clock
        self._active_message: Optional[str] = None
        self._expires_at: Optional[float] = None

        # Subscribe to show_popup events
        bus.subscribe('show_popup', self._on_show)

    def _on_show(self, payload: Tuple[str, float]) -> None:
        """
        Handles popup display requests.
        Args:
            payload: Tuple containing (message: str, duration_in_seconds: float)
        """
        message, duration = payload
        current_time = self._clock.get_time()
        self._active_message = message
        self._expires_at = current_time + duration

    def render(self) -> None:
        """
        If a popup is active and not expired, renders it centered at the top.
        """
        current_time = self._clock.get_time()
        if self._active_message and self._expires_at and current_time < self._expires_at:
            width, _ = self._renderer.measure_text(self._active_message, font_size=18)
            x = (self._renderer.engine_width - width) // 2
            self._renderer.draw_text(self._active_message, (x, 10), 18)
        else:
            self._active_message = None
            self._expires_at = None
