"""Simplified storage system."""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

class StorageProvider:
    """Simple storage provider interface."""
    
    def store(self, key, value):
        raise NotImplementedError
        
    def retrieve(self, key):
        raise NotImplementedError
        
    def exists(self, key):
        raise NotImplementedError

class MemoryStorageProvider(StorageProvider):
    """Memory storage provider."""
    
    def __init__(self, name="memory"):
        self.name = name
        self._data = {}
        
    def store(self, key, value):
        self._data[key] = value
        return True
        
    def retrieve(self, key):
        return self._data.get(key)
        
    def exists(self, key):
        return key in self._data
        
    def delete(self, key):
        if key in self._data:
            del self._data[key]
            return True
        return False

def create_memory_storage(name="memory"):
    """Create memory storage."""
    return MemoryStorageProvider(name)

def create_file_storage(path):
    """Create file storage."""
    return MemoryStorageProvider("file")  # Simplified to memory