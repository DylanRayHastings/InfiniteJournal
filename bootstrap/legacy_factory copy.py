# bootstrap/factory.py (Updated to ensure proper tool initialization)
from pathlib import Path
import logging
from core.event_bus import EventBus
from .adapters import load_adapters
from .database import init_database
from .services import init_services
from .widgets import init_widgets
from .errors import StartupError
from icecream import ic

logger = logging.getLogger(__name__)

def compose_app(settings, bus=None):
    """Compose and return the fully wired App instance."""
    bus = bus or EventBus()
    Path(settings.DATA_PATH).mkdir(parents=True, exist_ok=True)

    engine, clock, input_adapter = load_adapters()
    database = init_database(settings.DATABASE_URL)
    repo, exporter, tool_service, journal_service, undo_service = init_services(
        settings.DATA_PATH, settings, bus, database
    )
    
    # Ensure tool service starts with correct default tool
    if tool_service.current_tool_mode not in settings.VALID_TOOLS:
        tool_service.set_mode("brush")  # Force to brush if invalid
    
    widgets = init_widgets(journal_service, engine, bus, clock, settings, tool_service)

    from services.copy.app import App
    app = App(
        settings=settings,
        engine=engine,
        clock=clock,
        input_adapter=input_adapter,
        journal_service=journal_service,
        tool_service=tool_service,
        undo_service=undo_service,
        repository=repo,
        exporter=exporter,
        widgets=widgets,
        bus=bus,
    )
    if settings.DEBUG:
        ic(app)
    logger.info("Application composed successfully with tool: %s", tool_service.current_tool_mode)
    return app