import atexit
import logging
from .url_validator import validate_database_url
from .errors import StartupError

logger = logging.getLogger(__name__)

def init_database(database_url: str):
    """Initialize database and register its close() at exit."""
    validate_database_url(database_url)
    try:
        from services.database import CanvasDatabase
        db = CanvasDatabase(database_url)
    except Exception as e:
        raise StartupError(f"Database init failed: {e}") from e

    if not hasattr(db, 'close'):
        raise StartupError("Database backend missing 'close' method")

    atexit.register(db.close)
    logger.debug("Database initialized successfully")
    return db


# File: bootstrap/adapters.py
import logging
from importlib import import_module
from .errors import StartupError

logger = logging.getLogger(__name__)

def load_adapters():
    """Dynamically load engine, clock, and input adapters."""
    try:
        mod = import_module('adapters.pygame_adapter')
        engine = mod.PygameEngineAdapter()
        clock = mod.PygameClockAdapter()
        input_adapter = mod.PygameInputAdapter()
    except (ImportError, AttributeError) as e:
        raise StartupError(f"Adapter import failed: {e}") from e

    for method in ('open_window', 'draw_line'):
        if not hasattr(engine, method):
            raise StartupError(f"Engine adapter missing '{method}'")

    logger.debug("Adapters loaded successfully")
    return engine, clock, input_adapter