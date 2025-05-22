import logging
from .errors import StartupError

logger = logging.getLogger(__name__)

def init_services(
    data_path, settings, bus, database
):
    """Initialize repository, exporter, tool, journal, and undo services."""
    try:
        from adapters.fs_adapter import FileSystemJournalRepository, ScreenshotExporter
        from services.tools import ToolService
        from services.journal import JournalService
        from services.undo import UndoRedoService
    except ImportError as e:
        raise StartupError(f"Service import failed: {e}") from e

    repo = FileSystemJournalRepository(data_path)
    for method in ('save', 'close'):
        if not hasattr(repo, method):
            raise StartupError(f"Repository missing required '{method}()' method")

    exporter = ScreenshotExporter(data_path)
    tool_service = ToolService(settings=settings, bus=bus)
    journal_service = JournalService(bus=bus, tool_service=tool_service, database=database)
    undo_service = UndoRedoService(bus=bus)

    logger.debug("Services initialized successfully")
    return repo, exporter, tool_service, journal_service, undo_service
