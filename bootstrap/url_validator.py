from urllib.parse import urlparse
import logging
from .errors import StartupError

logger = logging.getLogger(__name__)

def validate_database_url(url: str) -> None:
    """Ensure the DATABASE_URL is well-formed and supported."""
    logger.debug("Validating DATABASE_URL: %r", url)
    if not url:
        raise StartupError("DATABASE_URL must be set and not empty")

    parsed = urlparse(url)
    scheme = parsed.scheme.lower() or 'file'

    if scheme == 'sqlite':
        if parsed.path in ('', ':memory:'):
            raise StartupError(f"Invalid sqlite URL '{url}'")
    elif scheme == 'file':
        if not parsed.path:
            raise StartupError(f"Invalid file URL '{url}'")
    elif scheme in ('postgres', 'postgresql', 'mysql', 'mssql'):
        if not parsed.netloc:
            raise StartupError(f"Invalid URL '{url}' — missing network location")
    else:
        raise StartupError(f"Unsupported database scheme '{parsed.scheme}'")
