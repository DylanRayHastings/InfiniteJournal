import sys
import logging
from typing import Type, Any, Callable

logger = logging.getLogger(__name__)

class StartupError(Exception):
    """Raised for startup configuration and initialization failures."""
    pass


def make_exception_hook(settings) -> Callable[[Type[BaseException], BaseException, Any], None]:
    """Return a sys.excepthook that logs uncaught exceptions and exits cleanly."""
    def _hook(exc_type: Type[BaseException], exc_value: BaseException, exc_tb: Any) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            logger.info("Interrupted by user")
            sys.exit(0)
        logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))
        if not getattr(settings, 'DEBUG', False):
            print(f"Unexpected error. See logs in '{settings.LOG_DIR}/app.log'")
        sys.exit(1)
    return _hook
