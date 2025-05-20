"""
CanvasWidget bridges JournalService with the rendering Engine.

Responsible for rendering journal content to the main drawing surface.
"""

from core.events import EventBus
from core.interfaces import Renderer
from core.services import JournalService

class CanvasWidget:
    """
    CanvasWidget: Connects JournalService (data/model) to Renderer (view).

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
        self._dirty = True  # TODO: optimize for minimal redraws

        # Subscribe to stroke or page update events
        bus.subscribe('stroke_added', self._on_update)

    def _on_update(self, _) -> None:
        """
        Handles update notifications (e.g., a new stroke was added).
        Could set a dirty flag or trigger animation/redraw.
        """
        self._dirty = True

    def render(self) -> None:
        """
        Render the current journal state to the canvas.
        """
        self._journal.render(self._renderer)
        self._dirty = False
