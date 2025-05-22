import logging
import logging.config
from pathlib import Path
from typing import Optional
from .errors import StartupError
from config import Settings

logger = logging.getLogger(__name__)

def setup_logging(settings: Settings, console_level: Optional[int]) -> None:
    """Configure rotating file and optional console logging."""
    log_dir = Path(settings.LOG_DIR)
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise StartupError(f"Failed to create log directory {log_dir}: {e}") from e

    cfg = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s %(levelname)-8s [%(name)s] %(message)s'
            }
        },
        'handlers': {
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': str(log_dir / 'app.log'),
                'maxBytes': Settings.Config.LOG_MAX_BYTES,
                'backupCount': Settings.Config.LOG_BACKUP_COUNT,
                'formatter': 'standard',
                'encoding': 'utf-8',
            }
        },
        'root': {
            'handlers': ['file'],
            'level': 'DEBUG' if settings.DEBUG else 'WARNING',
        }
    }

    if console_level is not None:
        cfg['handlers']['console'] = {
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
            'formatter': 'standard',
            'level': console_level,
        }
        cfg['root']['handlers'].append('console')

    try:
        logging.config.dictConfig(cfg)
    except Exception as e:
        raise StartupError(f"Logging configuration failed: {e}") from e

    logger.debug("Logging initialized: DEBUG=%s, console=%s", settings.DEBUG, console_level)
