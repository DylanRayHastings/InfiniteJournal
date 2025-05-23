"""
CanvasWidget bridges JournalService with the rendering Engine with persistent display.

Responsible for rendering journal content to the main drawing surface and ensuring
all content remains visible between drawing operations.
"""

from core.event_bus import EventBus
from core.interfaces import Renderer
from services.journal import JournalService

class CanvasWidget:
    """
    CanvasWidget: Connects JournalService (data/model) to Renderer (view).
    Ensures all drawn content persists visually until explicitly cleared.

    Args:
        journal (JournalService): Provides page and stroke data.
        renderer (Renderer): Handles drawing operations.
        bus (EventBus): Event bus for subscribing to journal changes.
    """

    def __init__(
        self,
        journal: JournalService,
        renderer: Renderer,
        bus: EventBus
    ) -> None:
        self._journal = journal
        self._renderer = renderer
        self._always_render = True  # Always render content for persistence

        # Subscribe to stroke or page update events
        bus.subscribe('stroke_added', self._on_update)
        bus.subscribe('page_cleared', self._on_page_cleared)

    def _on_update(self, _) -> None:
        """
        Handles update notifications (e.g., a new stroke was added).
        Invalidates cache to ensure fresh rendering.
        """
        # Invalidate journal cache to ensure fresh rendering
        self._journal.invalidate_cache()

    def _on_page_cleared(self, _) -> None:
        """
        Handles page clear notifications.
        """
        # No special handling needed - journal will be empty

    def render(self) -> None:
        """
        Render the current journal state to the canvas.
        This method is called every frame to ensure persistent visibility.
        """
        # Always call render - the journal service handles optimization internally
        # This ensures that all existing strokes remain visible between drawing operations
        self._journal.render(self._renderer)