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
