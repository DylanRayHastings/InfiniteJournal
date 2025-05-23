# bootstrap/widgets.py (Updated)
import logging
from typing import Any, List

logger = logging.getLogger(__name__)

def init_widgets(
    journal_service: Any,
    engine: Any,
    bus: Any,
    clock: Any,
    settings: Any,
    tool_service: Any,
) -> List[Any]:
    """Instantiate UI widgets in order."""
    from ui.canvas_widget import CanvasWidget
    from ui.hotbar import HotbarWidget
    from ui.status_bar import StatusBar
    from ui.popup_manager import PopupManager

    widgets = [
        CanvasWidget(journal_service, engine, bus),
        HotbarWidget(tool_service, engine, bus),
        StatusBar(clock, engine, settings),
        PopupManager(bus, engine, clock),
    ]
    logger.debug("Widgets initialized: %s", [type(w).__name__ for w in widgets])
    return widgets