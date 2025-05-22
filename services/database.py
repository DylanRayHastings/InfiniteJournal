"""
File-backed JSON storage for canvas strokes, with atomic writes,
enhanced error handling, and Google-style docstrings.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, List
from urllib.parse import urlparse

# Constants
_TEMP_SUFFIX = ".tmp"

# Configure module-level logger
logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when the provided database URL is invalid or unsupported."""


class DataPersistenceError(Exception):
    """Raised when reading from or writing to the storage file fails."""


def parse_database_url(database_url: str) -> Path:
    """Parse a database URL or file path into a Path object.

    Supports sqlite:/// and file:/// schemes, as well as plain paths.

    Args:
        database_url: Database URL string or filesystem path.

    Returns:
        Path pointing to the database file.

    Raises:
        ConfigurationError: If the URL is empty or uses an unsupported scheme.
    """
    if not database_url:
        raise ConfigurationError("`database_url` must not be empty.")

    parsed = urlparse(database_url)
    scheme = parsed.scheme.lower()

    if scheme in ("sqlite", "file"):
        raw = parsed.path
        # Handle Windows drive letters: '/C:/dir' → 'C:/dir'
        if raw.startswith("/") and len(raw) > 2 and raw[2] == ":" and raw[1].isalpha():
            raw = raw.lstrip("/")
        return Path(raw)
    elif scheme == "":
        return Path(database_url)
    else:
        raise ConfigurationError(f"Unsupported URL scheme '{scheme}' in `{database_url}`.")


def serialize(obj: Any) -> Any:
    """Default JSON serializer for non-serializable objects.

    Tries, in order:
      1. `to_dict()` if available
      2. `__dict__`
      3. Fallback to `str(obj)`

    Args:
        obj: Object to serialize.

    Returns:
        A JSON-serializable representation of the object.
    """
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        return obj.to_dict()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


class CanvasDatabase:
    """File-backed storage for strokes with atomic JSON writes."""

    def __init__(self, database_url: str) -> None:
        """Initialize storage, creating directories and file if needed.

        Args:
            database_url: SQLite-style URL or direct filesystem path.

        Raises:
            ConfigurationError: If the URL is invalid.
            DataPersistenceError: If initialization write fails.
        """
        self.file_path = parse_database_url(database_url)
        self._ensure_directory_exists()

        if not self.file_path.exists():
            # First-time initialization
            self._write([], init=True)

    def add_stroke(self, stroke: Any) -> None:
        """Append a stroke object and persist to disk.

        Args:
            stroke: Object convertible by `serialize`.

        Raises:
            DataPersistenceError: On read/write errors.
        """
        strokes = self._read()
        strokes.append(stroke)
        self._write(strokes)

    def get_all_strokes(self) -> List[Any]:
        """Retrieve all stored strokes.

        Returns:
            List of stroke data (raw JSON objects).

        Raises:
            DataPersistenceError: If reading fails.
        """
        return self._read()

    def save(self, data: List[Any]) -> None:
        """Overwrite storage with the given list of strokes.

        Args:
            data: List of stroke-like objects.

        Raises:
            DataPersistenceError: On write failure.
        """
        self._write(data)

    def _ensure_directory_exists(self) -> None:
        """Create parent directory if it does not exist.

        Raises:
            DataPersistenceError: If directory creation fails.
        """
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.exception("Failed to create directory '%s'.", self.file_path.parent)
            raise DataPersistenceError(
                f"Cannot create directory '{self.file_path.parent}'."
            ) from e

    def _read(self) -> List[Any]:
        """Load JSON data from the storage file.

        Returns:
            Stored list of strokes, or [] on decode errors or missing file.

        Raises:
            DataPersistenceError: On low-level I/O errors.
        """
        try:
            with self.file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                logger.warning("Expected a JSON list in '%s'; resetting.", self.file_path)
                return []
            return data
        except json.JSONDecodeError as e:
            logger.warning("Corrupted JSON in '%s': %s", self.file_path, e)
            return []
        except FileNotFoundError:
            logger.info("File '%s' not found; returning empty list.", self.file_path)
            return []
        except OSError as e:
            logger.exception("Error reading file '%s'.", self.file_path)
            raise DataPersistenceError(
                f"Cannot read file '{self.file_path}'."
            ) from e

    def _write(self, data: List[Any], init: bool = False) -> None:
        """Atomically write the full data list to disk with JSON serialization.

        Args:
            data: List of stroke-like objects.
            init: True if this is the initial file creation (affects logging).

        Raises:
            DataPersistenceError: On write or rename failures.
        """
        temp_path = self.file_path.with_suffix(self.file_path.suffix + _TEMP_SUFFIX)

        try:
            with temp_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=serialize)
                f.flush()
                os.fsync(f.fileno())

            # Atomic rename
            os.replace(str(temp_path), str(self.file_path))
            action = "Initialized" if init else "Updated"
            logger.info("%s store file '%s'.", action, self.file_path)
        except OSError as e:
            logger.exception("Failed to write file '%s'.", self.file_path)
            raise DataPersistenceError(
                f"Cannot write file '{self.file_path}'."
            ) from e

    def close(self) -> None:
        """Close the database. No-op since writes are immediate."""
        logger.debug("CanvasDatabase.close() called; no resources to release.")
