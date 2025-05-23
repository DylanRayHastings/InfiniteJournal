"""
Unified Canvas Storage System.

File-backed JSON storage for canvas strokes with atomic writes,
centralized validation, enhanced error handling, and dependency injection.
Consolidates all storage, validation, and serialization functionality
into a production-ready, testable implementation.

Quick start:
    storage = CanvasStorageService("sqlite:///canvas.db")
    storage.add_stroke(stroke_data)
    all_strokes = storage.get_all_strokes()

Extension points:
    - Add custom serializers: Implement SerializationProvider interface
    - Add validation rules: Extend ValidationService
    - Add storage backends: Implement StorageProvider interface
    - Add monitoring: Inject LoggingProvider implementation
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List, Dict, Optional, Protocol
from urllib.parse import urlparse


class ConfigurationError(Exception):
    """Raised when provided configuration is invalid or unsupported."""


class DataPersistenceError(Exception):
    """Raised when reading from or writing to storage fails."""


class ValidationError(Exception):
    """Raised when data validation fails."""


class LoggingProvider(Protocol):
    """Interface for logging operations."""
    
    def info(self, message: str, *args: Any) -> None:
        """Log info level message."""
        ...
    
    def warning(self, message: str, *args: Any) -> None:
        """Log warning level message."""
        ...
    
    def error(self, message: str, *args: Any) -> None:
        """Log error level message."""
        ...
    
    def exception(self, message: str, *args: Any) -> None:
        """Log exception with traceback."""
        ...
    
    def debug(self, message: str, *args: Any) -> None:
        """Log debug level message."""
        ...


class SerializationProvider(Protocol):
    """Interface for object serialization operations."""
    
    def serialize_object(self, obj: Any) -> Any:
        """Convert object to JSON-serializable format."""
        ...
    
    def serialize_to_json(self, data: List[Any], file_path: Path) -> None:
        """Write data as JSON to file with proper formatting."""
        ...
    
    def deserialize_from_json(self, file_path: Path) -> List[Any]:
        """Read and parse JSON data from file."""
        ...


class StorageProvider(Protocol):
    """Interface for file system operations."""
    
    def ensure_directory_exists(self, directory_path: Path) -> None:
        """Create directory if it does not exist."""
        ...
    
    def file_exists(self, file_path: Path) -> bool:
        """Check if file exists."""
        ...
    
    def create_temporary_file_path(self, original_path: Path) -> Path:
        """Generate temporary file path for atomic operations."""
        ...
    
    def atomic_file_replace(self, temp_path: Path, target_path: Path) -> None:
        """Atomically replace target file with temporary file."""
        ...


class ValidationService:
    """Centralized validation logic for all canvas storage operations."""
    
    def __init__(self, logger: LoggingProvider):
        self.logger = logger
    
    def validate_database_url_not_empty(self, database_url: str) -> None:
        """Validate database URL is provided and not empty."""
        if not database_url:
            raise ConfigurationError("database_url must not be empty")
    
    def validate_url_scheme_supported(self, parsed_url: Any, original_url: str) -> None:
        """Validate URL scheme is supported by the system."""
        scheme = parsed_url.scheme.lower()
        supported_schemes = ("sqlite", "file", "")
        
        if scheme not in supported_schemes:
            raise ConfigurationError(f"Unsupported URL scheme '{scheme}' in '{original_url}'")
    
    def validate_stroke_data_provided(self, stroke: Any) -> None:
        """Validate stroke data is provided for storage."""
        if stroke is None:
            raise ValidationError("stroke data cannot be None")
    
    def validate_stroke_list_provided(self, data: List[Any]) -> None:
        """Validate stroke list is provided for bulk operations."""
        if data is None:
            raise ValidationError("stroke data list cannot be None")
    
    def validate_json_data_is_list(self, data: Any, file_path: Path) -> bool:
        """Validate JSON data represents a list of strokes."""
        if not isinstance(data, list):
            self.logger.warning("Expected JSON list in '%s' but found %s, resetting to empty list", file_path, type(data).__name__)
            return False
        return True


class DefaultLoggingProvider:
    """Default implementation of logging provider using Python logging."""
    
    def __init__(self, logger_name: str = __name__):
        self.logger = logging.getLogger(logger_name)
    
    def info(self, message: str, *args: Any) -> None:
        """Log info level message."""
        self.logger.info(message, *args)
    
    def warning(self, message: str, *args: Any) -> None:
        """Log warning level message."""
        self.logger.warning(message, *args)
    
    def error(self, message: str, *args: Any) -> None:
        """Log error level message."""
        self.logger.error(message, *args)
    
    def exception(self, message: str, *args: Any) -> None:
        """Log exception with traceback."""
        self.logger.exception(message, *args)
    
    def debug(self, message: str, *args: Any) -> None:
        """Log debug level message."""
        self.logger.debug(message, *args)


class DefaultSerializationProvider:
    """Default implementation of serialization provider using JSON."""
    
    def __init__(self, logger: LoggingProvider):
        self.logger = logger
    
    def serialize_object(self, obj: Any) -> Any:
        """
        Convert object to JSON-serializable format using multiple strategies.
        
        Attempts serialization in order:
        1. Call to_dict() method if available
        2. Use __dict__ attribute if available  
        3. Convert to string as fallback
        """
        if hasattr(obj, "to_dict") and callable(obj.to_dict):
            return obj.to_dict()
        
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        
        return str(obj)
    
    def serialize_to_json(self, data: List[Any], file_path: Path) -> None:
        """Write data as formatted JSON to file with flush and sync."""
        try:
            with file_path.open("w", encoding="utf-8") as file_handle:
                json.dump(data, file_handle, indent=2, default=self.serialize_object)
                file_handle.flush()
                os.fsync(file_handle.fileno())
        except OSError as error:
            self.logger.exception("Failed to write JSON to file '%s'", file_path)
            raise DataPersistenceError(f"Cannot write file '{file_path}'") from error
    
    def deserialize_from_json(self, file_path: Path) -> List[Any]:
        """Read and parse JSON data from file with comprehensive error handling."""
        try:
            with file_path.open("r", encoding="utf-8") as file_handle:
                return json.load(file_handle)
        except json.JSONDecodeError as error:
            self.logger.warning("Corrupted JSON in '%s': %s", file_path, error)
            return []
        except FileNotFoundError:
            self.logger.info("File '%s' not found, returning empty list", file_path)
            return []
        except OSError as error:
            self.logger.exception("Error reading file '%s'", file_path)
            raise DataPersistenceError(f"Cannot read file '{file_path}'") from error


class DefaultStorageProvider:
    """Default implementation of storage provider using file system operations."""
    
    def __init__(self, logger: LoggingProvider):
        self.logger = logger
    
    def ensure_directory_exists(self, directory_path: Path) -> None:
        """Create directory and all parent directories if they do not exist."""
        try:
            directory_path.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            self.logger.exception("Failed to create directory '%s'", directory_path)
            raise DataPersistenceError(f"Cannot create directory '{directory_path}'") from error
    
    def file_exists(self, file_path: Path) -> bool:
        """Check if file exists at the specified path."""
        return file_path.exists()
    
    def create_temporary_file_path(self, original_path: Path) -> Path:
        """Generate temporary file path by appending .tmp suffix."""
        return original_path.with_suffix(original_path.suffix + ".tmp")
    
    def atomic_file_replace(self, temp_path: Path, target_path: Path) -> None:
        """Atomically replace target file with temporary file using os.replace."""
        try:
            os.replace(str(temp_path), str(target_path))
        except OSError as error:
            self.logger.exception("Failed to replace file '%s' with '%s'", target_path, temp_path)
            raise DataPersistenceError(f"Cannot replace file '{target_path}'") from error


class DatabaseUrlParser:
    """Handles parsing and validation of database URLs and file paths."""
    
    def __init__(self, validator: ValidationService):
        self.validator = validator
    
    def parse_database_url_to_path(self, database_url: str) -> Path:
        """
        Parse database URL or file path into Path object.
        
        Supports multiple URL formats:
        - sqlite:///path/to/file.db
        - file:///path/to/file.db  
        - /direct/path/to/file.db
        
        Handles Windows drive letters correctly by removing leading slash
        from paths like '/C:/directory/file.db'.
        """
        self.validator.validate_database_url_not_empty(database_url)
        
        parsed_url = urlparse(database_url)
        self.validator.validate_url_scheme_supported(parsed_url, database_url)
        
        if parsed_url.scheme.lower() in ("sqlite", "file"):
            return self._extract_path_from_url(parsed_url.path)
        
        return Path(database_url)
    
    def _extract_path_from_url(self, url_path: str) -> Path:
        """Extract file system path from URL path, handling Windows drive letters."""
        if self._is_windows_drive_path(url_path):
            return Path(url_path.lstrip("/"))
        
        return Path(url_path)
    
    def _is_windows_drive_path(self, path: str) -> bool:
        """Check if path represents Windows drive letter format."""
        return (path.startswith("/") and 
                len(path) > 2 and 
                path[2] == ":" and 
                path[1].isalpha())


class CanvasStorageService:
    """
    Unified canvas storage service with dependency injection and centralized validation.
    
    Provides atomic file operations, comprehensive error handling, and extensible
    architecture through dependency injection of logging, serialization, and storage providers.
    
    Features:
    - Atomic writes using temporary files
    - Centralized validation logic
    - Comprehensive error handling with detailed logging
    - Dependency injection for testing and customization
    - Support for multiple URL schemes and file paths
    - Automatic directory creation
    - JSON serialization with custom object support
    """
    
    def __init__(
        self, 
        database_url: str,
        logger: Optional[LoggingProvider] = None,
        serializer: Optional[SerializationProvider] = None,
        storage: Optional[StorageProvider] = None
    ):
        """
        Initialize canvas storage service with dependency injection.
        
        Args:
            database_url: SQLite-style URL or direct filesystem path
            logger: Optional custom logging provider
            serializer: Optional custom serialization provider  
            storage: Optional custom storage provider
        """
        self.logger = logger or DefaultLoggingProvider()
        self.validator = ValidationService(self.logger)
        self.storage = storage or DefaultStorageProvider(self.logger)
        self.serializer = serializer or DefaultSerializationProvider(self.logger)
        self.url_parser = DatabaseUrlParser(self.validator)
        
        self.file_path = self.url_parser.parse_database_url_to_path(database_url)
        self._initialize_storage_system()
    
    def add_stroke(self, stroke: Any) -> None:
        """
        Add single stroke to storage and persist immediately.
        
        Validates stroke data, loads existing strokes, appends new stroke,
        and writes updated data atomically to prevent data corruption.
        """
        self.validator.validate_stroke_data_provided(stroke)
        
        existing_strokes = self._load_all_strokes_from_file()
        updated_strokes = existing_strokes + [stroke]
        self._save_strokes_to_file(updated_strokes)
        
        self.logger.info("Stroke added successfully to storage")
    
    def get_all_strokes(self) -> List[Any]:
        """
        Retrieve all stored strokes from persistent storage.
        
        Returns empty list if file does not exist or contains invalid data.
        Logs warnings for data corruption issues but does not raise exceptions.
        """
        return self._load_all_strokes_from_file()
    
    def save(self, data: List[Any]) -> None:
        """
        Replace all stored strokes with provided data list.
        
        Validates input data and atomically overwrites existing storage
        with new stroke collection.
        """
        self.validator.validate_stroke_list_provided(data)
        self._save_strokes_to_file(data)
        self.logger.info("All strokes replaced successfully in storage")
    
    def close(self) -> None:
        """
        Close storage service and release resources.
        
        No-op implementation since all writes are immediate and atomic.
        Provided for interface compatibility with database-like systems.
        """
        self.logger.debug("Canvas storage service closed, no resources to release")
    
    def _initialize_storage_system(self) -> None:
        """Initialize storage system by creating directories and initial file."""
        self.storage.ensure_directory_exists(self.file_path.parent)
        
        if not self.storage.file_exists(self.file_path):
            self._save_strokes_to_file([], is_initialization=True)
    
    def _load_all_strokes_from_file(self) -> List[Any]:
        """Load and validate stroke data from persistent storage file."""
        raw_data = self.serializer.deserialize_from_json(self.file_path)
        
        if not self.validator.validate_json_data_is_list(raw_data, self.file_path):
            return []
        
        return raw_data
    
    def _save_strokes_to_file(self, data: List[Any], is_initialization: bool = False) -> None:
        """
        Atomically save stroke data to persistent storage using temporary file.
        
        Creates temporary file, writes data, flushes to disk, then atomically
        replaces target file to prevent corruption during write operations.
        """
        temp_file_path = self.storage.create_temporary_file_path(self.file_path)
        
        self.serializer.serialize_to_json(data, temp_file_path)
        self.storage.atomic_file_replace(temp_file_path, self.file_path)
        
        operation_type = "Initialized" if is_initialization else "Updated"
        self.logger.info("%s canvas storage file '%s'", operation_type, self.file_path)


def create_canvas_storage_service(database_url: str) -> CanvasStorageService:
    """
    Factory function to create canvas storage service with default configuration.
    
    Provides convenient way to create storage service without manually
    configuring dependency injection for common use cases.
    """
    return CanvasStorageService(database_url)