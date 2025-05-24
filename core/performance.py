"""
Performance optimization system - PERFORMANCE OPTIMIZED

Optimizations: __slots__, faster data structures, reduced overhead, cached calculations.
"""

import time
import logging
import threading
import weakref
from typing import Any, Dict, List, Optional, Callable, Tuple, TypeVar, Generic
from dataclasses import dataclass, field
from collections import deque, OrderedDict
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

T = TypeVar('T')

@dataclass(slots=True)
class PerformanceMetrics:
    """Performance metrics tracking - optimized."""
    operation_times: Dict[str, deque] = field(default_factory=dict)
    cache_hits: Dict[str, int] = field(default_factory=dict)
    cache_misses: Dict[str, int] = field(default_factory=dict)
    frame_times: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def record_operation(self, operation: str, duration: float) -> None:
        """Record operation timing - optimized."""
        if operation not in self.operation_times:
            self.operation_times[operation] = deque(maxlen=100)
        self.operation_times[operation].append(duration)
    
    def record_cache_hit(self, cache_name: str) -> None:
        """Record cache hit - optimized."""
        self.cache_hits[cache_name] = self.cache_hits.get(cache_name, 0) + 1
    
    def record_cache_miss(self, cache_name: str) -> None:
        """Record cache miss - optimized."""
        self.cache_misses[cache_name] = self.cache_misses.get(cache_name, 0) + 1
    
    def get_average_operation_time(self, operation: str) -> Optional[float]:
        """Get average time - optimized."""
        times = self.operation_times.get(operation)
        return sum(times) / len(times) if times else None
    
    def get_cache_hit_rate(self, cache_name: str) -> float:
        """Get cache hit rate - optimized."""
        hits = self.cache_hits.get(cache_name, 0)
        misses = self.cache_misses.get(cache_name, 0)
        total = hits + misses
        return (hits / total) * 100.0 if total > 0 else 0.0

class LRUCache(Generic[T]):
    """Thread-safe LRU cache - HEAVILY OPTIMIZED."""
    __slots__ = ('max_size', 'name', '_cache', '_lock', '_metrics', '_hits', '_misses')
    
    def __init__(self, max_size: int = 1000, name: str = "unnamed"):
        self.max_size = max_size
        self.name = name
        self._cache: OrderedDict[Any, T] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: Any) -> Optional[T]:
        """Get value from cache - optimized."""
        with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                value = self._cache.pop(key)
                self._cache[key] = value
                self._hits += 1
                return value
            else:
                self._misses += 1
                return None
    
    def put(self, key: Any, value: T) -> None:
        """Put value in cache - optimized."""
        with self._lock:
            # Remove if already exists
            if key in self._cache:
                del self._cache[key]
            # Add to end
            self._cache[key] = value
            # Evict oldest if over capacity
            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)  # Remove oldest
    
    def clear(self) -> None:
        """Clear cache."""
        with self._lock:
            self._cache.clear()
    
    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)
    
    def get_hit_rate(self) -> float:
        """Get cache hit rate."""
        total = self._hits + self._misses
        return (self._hits / total) * 100.0 if total > 0 else 0.0

class BatchProcessor:
    """Batch processing - OPTIMIZED."""
    __slots__ = ('batch_size', 'flush_interval', '_batches', '_processors', 
                 '_last_flush', '_lock')
    
    def __init__(self, batch_size: int = 50, flush_interval: float = 0.1):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._batches: Dict[str, List[Any]] = {}
        self._processors: Dict[str, Callable] = {}
        self._last_flush: Dict[str, float] = {}
        self._lock = threading.Lock()
    
    def register_processor(self, batch_type: str, processor: Callable[[List[Any]], None]) -> None:
        """Register batch processor - optimized."""
        with self._lock:
            self._processors[batch_type] = processor
            self._batches[batch_type] = []
            self._last_flush[batch_type] = time.time()
    
    def add_item(self, batch_type: str, item: Any) -> None:
        """Add item to batch - optimized."""
        current_time = time.time()
        
        with self._lock:
            if batch_type not in self._batches:
                return
            
            self._batches[batch_type].append(item)
            
            # Check flush conditions
            should_flush = (
                len(self._batches[batch_type]) >= self.batch_size or
                current_time - self._last_flush[batch_type] >= self.flush_interval
            )
            
            if should_flush:
                self._flush_batch_unsafe(batch_type, current_time)
    
    def _flush_batch_unsafe(self, batch_type: str, current_time: float) -> None:
        """Flush batch (called with lock held) - optimized."""
        if not self._batches[batch_type]:
            return
        
        batch = self._batches[batch_type]
        self._batches[batch_type] = []  # Reset to new list
        self._last_flush[batch_type] = current_time
        
        processor = self._processors[batch_type]
        
        # Release lock before processing
        self._lock.release()
        try:
            processor(batch)
        except Exception as e:
            logger.error("Error processing batch %s: %s", batch_type, e)
        finally:
            self._lock.acquire()
    
    def flush_all(self) -> None:
        """Flush all batches - optimized."""
        current_time = time.time()
        with self._lock:
            for batch_type in list(self._batches.keys()):
                self._flush_batch_unsafe(batch_type, current_time)

class PerformanceProfiler:
    """Performance profiler - OPTIMIZED."""
    __slots__ = ('_operation_times', '_active_operations', '_lock')
    
    def __init__(self):
        self._operation_times: Dict[str, deque] = {}
        self._active_operations: Dict[str, float] = {}
        self._lock = threading.Lock()
    
    def start_operation(self, operation: str) -> None:
        """Start timing operation - optimized."""
        with self._lock:
            self._active_operations[operation] = time.time()
    
    def end_operation(self, operation: str) -> float:
        """End timing operation - optimized."""
        end_time = time.time()
        
        with self._lock:
            start_time = self._active_operations.pop(operation, end_time)
            duration = end_time - start_time
            
            if operation not in self._operation_times:
                self._operation_times[operation] = deque(maxlen=100)
            self._operation_times[operation].append(duration)
            
            return duration
    
    def get_average_time(self, operation: str) -> Optional[float]:
        """Get average operation time."""
        with self._lock:
            times = self._operation_times.get(operation)
            return sum(times) / len(times) if times else None

def performance_monitor(operation_name: str, profiler: Optional[PerformanceProfiler] = None):
    """Decorator for monitoring function performance - optimized."""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                if profiler:
                    profiler.start_operation(operation_name)
                
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                
                if profiler:
                    profiler.end_operation(operation_name)
                
                # Log slow operations
                if duration > 0.1:
                    logger.warning("Slow operation %s: %.3fms", operation_name, duration * 1000)
        
        return wrapper
    return decorator

class MemoryPool:
    """Memory pool for object reuse - OPTIMIZED."""
    __slots__ = ('factory', 'max_size', '_pool', '_lock')
    
    def __init__(self, factory: Callable[[], T], max_size: int = 100):
        self.factory = factory
        self.max_size = max_size
        self._pool: List[T] = []
        self._lock = threading.Lock()
    
    def acquire(self) -> T:
        """Acquire object from pool - optimized."""
        with self._lock:
            return self._pool.pop() if self._pool else self.factory()
    
    def release(self, obj: T) -> None:
        """Return object to pool - optimized."""
        with self._lock:
            if len(self._pool) < self.max_size:
                # Reset object if possible
                if hasattr(obj, 'reset'):
                    try:
                        obj.reset()
                        self._pool.append(obj)
                    except Exception:
                        pass  # Don't add invalid objects
                else:
                    self._pool.append(obj)
    
    def clear(self) -> None:
        """Clear pool."""
        with self._lock:
            self._pool.clear()

class RenderingOptimizer:
    """Rendering optimization - OPTIMIZED."""
    __slots__ = ('stroke_cache', 'dirty_regions', '_lock')
    
    def __init__(self, max_cache_size: int = 1000):
        self.stroke_cache = LRUCache[List[Any]](max_cache_size, "stroke_rendering")
        self.dirty_regions: List[Tuple[int, int, int, int]] = []
        self._lock = threading.Lock()
    
    def cache_stroke_render(self, stroke_id: str, rendered_points: List[Any]) -> None:
        """Cache rendered stroke - optimized."""
        self.stroke_cache.put(stroke_id, rendered_points)
    
    def get_cached_stroke(self, stroke_id: str) -> Optional[List[Any]]:
        """Get cached stroke."""
        return self.stroke_cache.get(stroke_id)
    
    def mark_dirty_region(self, x: int, y: int, width: int, height: int) -> None:
        """Mark dirty region - optimized."""
        with self._lock:
            self.dirty_regions.append((x, y, width, height))
    
    def get_dirty_regions(self) -> List[Tuple[int, int, int, int]]:
        """Get and clear dirty regions - optimized."""
        with self._lock:
            regions = self.dirty_regions
            self.dirty_regions = []  # Reset to new list
            return regions
    
    def should_skip_render(self, complexity_score: float, target_fps: int = 60) -> bool:
        """Determine if rendering should be skipped."""
        target_frame_time = 1000.0 / target_fps  # Convert to ms
        return complexity_score > target_frame_time

class AdaptiveQuality:
    """Adaptive quality system - OPTIMIZED."""
    __slots__ = ('target_fps', 'target_frame_time', 'quality_level', 'frame_times', '_lock')
    
    def __init__(self, target_fps: int = 60):
        self.target_fps = target_fps
        self.target_frame_time = 1.0 / target_fps
        self.quality_level = 1.0
        self.frame_times: deque = deque(maxlen=30)
        self._lock = threading.Lock()
    
    def record_frame_time(self, frame_time: float) -> None:
        """Record frame time - optimized."""
        with self._lock:
            self.frame_times.append(frame_time)
            
            # Adjust quality periodically
            if len(self.frame_times) >= 10:
                recent_times = list(self.frame_times)[-10:]
                avg_frame_time = sum(recent_times) / 10
                
                if avg_frame_time > self.target_frame_time * 1.2:
                    # Poor performance - reduce quality
                    self.quality_level = max(0.3, self.quality_level - 0.1)
                elif avg_frame_time < self.target_frame_time * 0.8:
                    # Good performance - increase quality
                    self.quality_level = min(1.0, self.quality_level + 0.05)
    
    def get_quality_level(self) -> float:
        """Get current quality level."""
        with self._lock:
            return self.quality_level
    
    def get_stroke_detail_level(self) -> int:
        """Get stroke detail level based on quality."""
        quality = self.get_quality_level()
        if quality >= 0.8:
            return 1  # Full detail
        elif quality >= 0.5:
            return 2  # Medium detail
        else:
            return 4  # Low detail
    
    def should_use_antialiasing(self) -> bool:
        """Determine if antialiasing should be used."""
        return self.get_quality_level() >= 0.6

# Global instances - optimized singletons
_global_profiler = PerformanceProfiler()
_global_batch_processor = BatchProcessor()
_global_rendering_optimizer = RenderingOptimizer()
_global_adaptive_quality = AdaptiveQuality()

def get_global_profiler() -> PerformanceProfiler:
    """Get global profiler."""
    return _global_profiler

def get_global_batch_processor() -> BatchProcessor:
    """Get global batch processor."""
    return _global_batch_processor

def get_global_rendering_optimizer() -> RenderingOptimizer:
    """Get global rendering optimizer."""
    return _global_rendering_optimizer

def get_global_adaptive_quality() -> AdaptiveQuality:
    """Get global adaptive quality."""
    return _global_adaptive_quality

# Optimized decorators
def profile_operation(operation_name: str):
    """Decorator for profiling operations."""
    return performance_monitor(operation_name, _global_profiler)

def cached_operation(cache_name: str = "default", max_size: int = 100):
    """Decorator for caching operation results - optimized."""
    cache = LRUCache(max_size, cache_name)
    
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Simple cache key generation
            key = (func.__name__, args, tuple(sorted(kwargs.items())))
            
            # Try cache first
            result = cache.get(key)
            if result is not None:
                return result
            
            # Compute and cache
            result = func(*args, **kwargs)
            cache.put(key, result)
            return result
        
        return wrapper
    return decorator