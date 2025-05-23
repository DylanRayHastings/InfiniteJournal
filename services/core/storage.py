"""
Universal Storage System
Eliminates ALL storage duplication through unified provider architecture.

This module abstracts file system, database, memory, and configuration storage
into a single, consistent interface with comprehensive error handling.
"""

import json
import pickle
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, TypeVar, Generic, Protocol
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from contextlib import contextmanager
import threading
import tempfile
import shutil

logger = logging.getLogger(__name__)

T = TypeVar('T')
KeyType = TypeVar('KeyType')
ValueType = TypeVar('ValueType')


class StorageError(Exception):
    """Base exception for storage operations."""
    
    def __init__(self, message: str, key: str = None, storage_type: str = None):
        super().__init__(message)
        self.key = key
        self.storage_type = storage_type
        self.timestamp = datetime.now(timezone.utc)


class StorageNotFoundError(StorageError):
    """Raised when requested data is not found."""
    pass


class StoragePermissionError(StorageError):
    """Raised when storage access is denied."""
    pass


@dataclass
class StorageMetadata:
    """Metadata for stored items."""
    created_at: datetime
    modified_at: datetime
    size_bytes: int
    checksum: Optional[str] = None
    content_type: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class StorageProvider(Protocol, Generic[KeyType, ValueType]):
    """Universal storage provider interface."""
    
    def store(self, key: KeyType, value: ValueType, metadata: Optional[StorageMetadata] = None) -> bool:
        """Store value under key."""
        ...
    
    def retrieve(self, key: KeyType) -> ValueType:
        """Retrieve value by key."""
        ...
    
    def exists(self, key: KeyType) -> bool:
        """Check if key exists."""
        ...
    
    def delete(self, key: KeyType) -> bool:
        """Delete value by key."""
        ...
    
    def list_keys(self) -> List[KeyType]:
        """List all available keys."""
        ...
    
    def clear(self) -> None:
        """Clear all stored data."""
        ...
    
    def get_metadata(self, key: KeyType) -> Optional[StorageMetadata]:
        """Get metadata for key."""
        ...


class BaseStorageProvider(ABC, Generic[KeyType, ValueType]):
    """Base implementation for storage providers."""
    
    def __init__(self, storage_name: str = "storage"):
        self.storage_name = storage_name
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._lock = threading.RLock()
        
    @abstractmethod
    def _do_store(self, key: KeyType, value: ValueType, metadata: Optional[StorageMetadata]) -> bool:
        """Implementation-specific store operation."""
        pass
        
    @abstractmethod
    def _do_retrieve(self, key: KeyType) -> ValueType:
        """Implementation-specific retrieve operation."""
        pass
        
    @abstractmethod
    def _do_exists(self, key: KeyType) -> bool:
        """Implementation-specific exists check."""
        pass
        
    @abstractmethod
    def _do_delete(self, key: KeyType) -> bool:
        """Implementation-specific delete operation."""
        pass
        
    @abstractmethod
    def _do_list_keys(self) -> List[KeyType]:
        """Implementation-specific key listing."""
        pass
        
    @abstractmethod
    def _do_clear(self) -> None:
        """Implementation-specific clear operation."""
        pass
    
    def store(self, key: KeyType, value: ValueType, metadata: Optional[StorageMetadata] = None) -> bool:
        """Store value with error handling."""
        with self._lock:
            try:
                if metadata is None:
                    metadata = StorageMetadata(
                        created_at=datetime.now(timezone.utc),
                        modified_at=datetime.now(timezone.utc),
                        size_bytes=self._calculate_size(value)
                    )
                    
                result = self._do_store(key, value, metadata)
                self.logger.debug(f"Stored {key} in {self.storage_name}")
                return result
                
            except Exception as error:
                self.logger.error(f"Failed to store {key}: {error}")
                raise StorageError(f"Store operation failed: {error}", str(key), self.storage_name)
    
    def retrieve(self, key: KeyType) -> ValueType:
        """Retrieve value with error handling."""
        with self._lock:
            try:
                if not self.exists(key):
                    raise StorageNotFoundError(f"Key not found: {key}", str(key), self.storage_name)
                    
                result = self._do_retrieve(key)
                self.logger.debug(f"Retrieved {key} from {self.storage_name}")
                return result
                
            except StorageNotFoundError:
                raise
            except Exception as error:
                self.logger.error(f"Failed to retrieve {key}: {error}")
                raise StorageError(f"Retrieve operation failed: {error}", str(key), self.storage_name)
    
    def exists(self, key: KeyType) -> bool:
        """Check existence with error handling."""
        try:
            return self._do_exists(key)
        except Exception as error:
            self.logger.error(f"Failed to check existence of {key}: {error}")
            return False
    
    def delete(self, key: KeyType) -> bool:
        """Delete with error handling."""
        with self._lock:
            try:
                if not self.exists(key):
                    return False
                    
                result = self._do_delete(key)
                self.logger.debug(f"Deleted {key} from {self.storage_name}")
                return result
                
            except Exception as error:
                self.logger.error(f"Failed to delete {key}: {error}")
                raise StorageError(f"Delete operation failed: {error}", str(key), self.storage_name)
    
    def list_keys(self) -> List[KeyType]:
        """List keys with error handling."""
        try:
            return self._do_list_keys()
        except Exception as error:
            self.logger.error(f"Failed to list keys: {error}")
            raise StorageError(f"List operation failed: {error}", None, self.storage_name)
    
    def clear(self) -> None:
        """Clear with error handling."""
        with self._lock:
            try:
                self._do_clear()
                self.logger.info(f"Cleared {self.storage_name}")
            except Exception as error:
                self.logger.error(f"Failed to clear storage: {error}")
                raise StorageError(f"Clear operation failed: {error}", None, self.storage_name)
    
    def _calculate_size(self, value: Any) -> int:
        """Calculate approximate size of value."""
        try:
            if isinstance(value, str):
                return len(value.encode('utf-8'))
            elif isinstance(value, bytes):
                return len(value)
            elif hasattr(value, '__sizeof__'):
                return value.__sizeof__()
            else:
                return len(str(value))
        except Exception:
            return 0


class MemoryStorageProvider(BaseStorageProvider[str, Any]):
    """In-memory storage provider for fast access."""
    
    def __init__(self, storage_name: str = "memory"):
        super().__init__(storage_name)
        self._data: Dict[str, Any] = {}
        self._metadata: Dict[str, StorageMetadata] = {}
    
    def _do_store(self, key: str, value: Any, metadata: Optional[StorageMetadata]) -> bool:
        self._data[key] = value
        if metadata:
            self._metadata[key] = metadata
        return True
    
    def _do_retrieve(self, key: str) -> Any:
        return self._data[key]
    
    def _do_exists(self, key: str) -> bool:
        return key in self._data
    
    def _do_delete(self, key: str) -> bool:
        if key in self._data:
            del self._data[key]
            self._metadata.pop(key, None)
            return True
        return False
    
    def _do_list_keys(self) -> List[str]:
        return list(self._data.keys())
    
    def _do_clear(self) -> None:
        self._data.clear()
        self._metadata.clear()
    
    def get_metadata(self, key: str) -> Optional[StorageMetadata]:
        return self._metadata.get(key)


class FileStorageProvider(BaseStorageProvider[str, Any]):
    """File-based storage provider with JSON serialization."""
    
    def __init__(self, base_path: Path, storage_name: str = "file"):
        super().__init__(storage_name)
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
    def _get_file_path(self, key: str) -> Path:
        """Get file path for key."""
        safe_key = key.replace('/', '_').replace('\\', '_')
        return self.base_path / f"{safe_key}.json"
    
    def _get_metadata_path(self, key: str) -> Path:
        """Get metadata file path for key."""
        safe_key = key.replace('/', '_').replace('\\', '_')
        return self.base_path / f"{safe_key}.meta"
    
    def _do_store(self, key: str, value: Any, metadata: Optional[StorageMetadata]) -> bool:
        file_path = self._get_file_path(key)
        
        try:
            # Store data
            with file_path.open('w', encoding='utf-8') as f:
                json.dump(value, f, indent=2, default=str)
            
            # Store metadata
            if metadata:
                meta_path = self._get_metadata_path(key)
                with meta_path.open('w', encoding='utf-8') as f:
                    json.dump(metadata.to_dict(), f, indent=2, default=str)
            
            return True
            
        except Exception as error:
            if file_path.exists():
                file_path.unlink()
            raise StorageError(f"Failed to write file {file_path}: {error}")
    
    def _do_retrieve(self, key: str) -> Any:
        file_path = self._get_file_path(key)
        
        try:
            with file_path.open('r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as error:
            raise StorageError(f"Failed to read file {file_path}: {error}")
    
    def _do_exists(self, key: str) -> bool:
        return self._get_file_path(key).exists()
    
    def _do_delete(self, key: str) -> bool:
        file_path = self._get_file_path(key)
        meta_path = self._get_metadata_path(key)
        
        deleted = False
        if file_path.exists():
            file_path.unlink()
            deleted = True
        
        if meta_path.exists():
            meta_path.unlink()
        
        return deleted
    
    def _do_list_keys(self) -> List[str]:
        keys = []
        for file_path in self.base_path.glob("*.json"):
            key = file_path.stem
            keys.append(key)
        return keys
    
    def _do_clear(self) -> None:
        for file_path in self.base_path.glob("*"):
            if file_path.is_file():
                file_path.unlink()
    
    def get_metadata(self, key: str) -> Optional[StorageMetadata]:
        meta_path = self._get_metadata_path(key)
        
        if not meta_path.exists():
            return None
        
        try:
            with meta_path.open('r', encoding='utf-8') as f:
                data = json.load(f)
                return StorageMetadata(
                    created_at=datetime.fromisoformat(data['created_at']),
                    modified_at=datetime.fromisoformat(data['modified_at']),
                    size_bytes=data['size_bytes'],
                    checksum=data.get('checksum'),
                    content_type=data.get('content_type')
                )
        except Exception as error:
            self.logger.error(f"Failed to read metadata for {key}: {error}")
            return None


class ConfigurationProvider:
    """Specialized provider for configuration management."""
    
    def __init__(self, storage: StorageProvider[str, Any]):
        self.storage = storage
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def get_config(self, section: str, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        try:
            config_key = f"{section}.{key}"
            return self.storage.retrieve(config_key)
        except StorageNotFoundError:
            return default
    
    def set_config(self, section: str, key: str, value: Any) -> bool:
        """Set configuration value."""
        config_key = f"{section}.{key}"
        return self.storage.store(config_key, value)
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section."""
        section_data = {}
        prefix = f"{section}."
        
        for key in self.storage.list_keys():
            if key.startswith(prefix):
                config_key = key[len(prefix):]
                section_data[config_key] = self.storage.retrieve(key)
        
        return section_data


class StateProvider:
    """Specialized provider for application state management."""
    
    def __init__(self, storage: StorageProvider[str, Any]):
        self.storage = storage
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def save_state(self, component: str, state: Dict[str, Any]) -> bool:
        """Save component state."""
        state_key = f"state.{component}"
        return self.storage.store(state_key, state)
    
    def load_state(self, component: str, default: Dict[str, Any] = None) -> Dict[str, Any]:
        """Load component state."""
        state_key = f"state.{component}"
        try:
            return self.storage.retrieve(state_key)
        except StorageNotFoundError:
            return default or {}
    
    def clear_state(self, component: str = None) -> bool:
        """Clear component state or all states."""
        if component:
            state_key = f"state.{component}"
            return self.storage.delete(state_key)
        else:
            # Clear all state keys
            state_keys = [key for key in self.storage.list_keys() if key.startswith("state.")]
            for key in state_keys:
                self.storage.delete(key)
            return True


# Factory functions for creating storage providers
def create_memory_storage(name: str = "memory") -> MemoryStorageProvider:
    """Create memory storage provider."""
    return MemoryStorageProvider(name)


def create_file_storage(base_path: Path, name: str = "file") -> FileStorageProvider:
    """Create file storage provider."""
    return FileStorageProvider(base_path, name)


def create_json_storage(file_path: Path) -> FileStorageProvider:
    """Create JSON file storage provider."""
    return FileStorageProvider(file_path.parent, f"json_{file_path.stem}")


def create_configuration_provider(storage: StorageProvider = None) -> ConfigurationProvider:
    """Create configuration provider."""
    if storage is None:
        storage = create_memory_storage("config")
    return ConfigurationProvider(storage)


def create_state_provider(storage: StorageProvider = None) -> StateProvider:
    """Create state provider."""
    if storage is None:
        storage = create_memory_storage("state")
    return StateProvider(storage)