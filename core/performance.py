# core/performance.py (NEW FILE: Performance optimization system)
"""
Performance optimization system for InfiniteJournal

Provides caching, batching, and performance monitoring capabilities.
"""

import time
import logging
import threading
import weakref
from typing import Any, Dict, List, Optional, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from collections import deque, OrderedDict
from abc import ABC, abstractmethod

from sympy import Tuple

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class PerformanceMetrics:
    """Performance metrics tracking."""
    operation_times: Dict[str, List[float]] = field(default_factory=dict)
    cache_hits: Dict[str, int] = field(default_factory=dict)
    cache_misses: Dict[str, int] = field(default_factory=dict)
    memory_usage: List[float] = field(default_factory=list)
    frame_times: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def record_operation(self, operation: str, duration: float) -> None:
        """Record operation timing."""
        if operation not in self.operation_times:
            self.operation_times[operation] = deque(maxlen=100)
        self.operation_times[operation].append(duration)
    
    def record_cache_hit(self, cache_name: str) -> None:
        """Record cache hit."""
        self.cache_hits[cache_name] = self.cache_hits.get(cache_name, 0) + 1
    
    def record_cache_miss(self, cache_name: str) -> None:
        """Record cache miss."""
        self.cache_misses[cache_name] = self.cache_misses.get(cache_name, 0) + 1
    
    def get_average_operation_time(self, operation: str) -> Optional[float]:
        """Get average time for an operation."""
        times = self.operation_times.get(operation)
        if times:
            return sum(times) / len(times)
        return None
    
    def get_cache_hit_rate(self, cache_name: str) -> float:
        """Get cache hit rate as percentage."""
        hits = self.cache_hits.get(cache_name, 0)
        misses = self.cache_misses.get(cache_name, 0)
        total = hits + misses
        if total == 0:
            return 0.0
        return (hits / total) * 100.0


class LRUCache(Generic[T]):
    """Thread-safe LRU cache with performance monitoring."""
    
    def __init__(self, max_size: int = 1000, name: str = "unnamed"):
        self.max_size = max_size
        self.name = name
        self._cache: OrderedDict[Any, T] = OrderedDict()
        self._lock = threading.Lock()
        self._metrics = PerformanceMetrics()
    
    def get(self, key: Any) -> Optional[T]:
        """Get value from cache."""
        with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                value = self._cache.pop(key)
                self._cache[key] = value
                self._metrics.record_cache_hit(self.name)
                logger.debug("Cache hit for %s: %r", self.name, key)
                return value
            else:
                self._metrics.record_cache_miss(self.name)
                logger.debug("Cache miss for %s: %r", self.name, key)
                return None
    
    def put(self, key: Any, value: T) -> None:
        """Put value in cache."""
        with self._lock:
            # Remove if already exists
            if key in self._cache:
                del self._cache[key]
            # Add to end
            self._cache[key] = value
            # Evict oldest if over capacity
            while len(self._cache) > self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                logger.debug("Evicted from cache %s: %r", self.name, oldest_key)
    
    def clear(self) -> None:
        """Clear all cached values."""
        with self._lock:
            self._cache.clear()
            logger.debug("Cleared cache: %s", self.name)
    
    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)
    
    def get_metrics(self) -> PerformanceMetrics:
        """Get cache performance metrics."""
        return self._metrics


class BatchProcessor:
    """Batch processing for better performance."""
    
    def __init__(self, batch_size: int = 50, flush_interval: float = 0.1):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._batches: Dict[str, List[Any]] = {}
        self._processors: Dict[str, Callable] = {}
        self._last_flush: Dict[str, float] = {}
        self._lock = threading.Lock()
    
    def register_processor(self, batch_type: str, processor: Callable[[List[Any]], None]) -> None:
        """Register a batch processor function."""
        with self._lock:
            self._processors[batch_type] = processor
            self._batches[batch_type] = []
            self._last_flush[batch_type] = time.time()
        logger.debug("Registered batch processor: %s", batch_type)
    
    def add_item(self, batch_type: str, item: Any) -> None:
        """Add item to batch."""
        with self._lock:
            if batch_type not in self._batches:
                logger.warning("Unknown batch type: %s", batch_type)
                return
            
            self._batches[batch_type].append(item)
            
            # Check if we should flush
            should_flush = (
                len(self._batches[batch_type]) >= self.batch_size or
                time.time() - self._last_flush[batch_type] >= self.flush_interval
            )
            
            if should_flush:
                self._flush_batch(batch_type)
    
    def _flush_batch(self, batch_type: str) -> None:
        """Flush a specific batch (called with lock held)."""
        if not self._batches[batch_type]:
            return
        
        batch = self._batches[batch_type].copy()
        self._batches[batch_type].clear()
        self._last_flush[batch_type] = time.time()
        
        processor = self._processors[batch_type]
        
        # Release lock before processing
        self._lock.release()
        try:
            processor(batch)
            logger.debug("Processed batch %s with %d items", batch_type, len(batch))
        except Exception as e:
            logger.error("Error processing batch %s: %s", batch_type, e)
        finally:
            self._lock.acquire()
    
    def flush_all(self) -> None:
        """Flush all pending batches."""
        with self._lock:
            for batch_type in list(self._batches.keys()):
                self._flush_batch(batch_type)


class PerformanceProfiler:
    """Performance profiler for measuring operation times."""
    
    def __init__(self):
        self._metrics = PerformanceMetrics()
        self._active_operations: Dict[str, float] = {}
        self._lock = threading.Lock()
    
    def start_operation(self, operation: str) -> None:
        """Start timing an operation."""
        with self._lock:
            self._active_operations[operation] = time.time()
    
    def end_operation(self, operation: str) -> float:
        """End timing an operation and record duration."""
        with self._lock:
            if operation not in self._active_operations:
                logger.warning("Operation not started: %s", operation)
                return 0.0
            
            start_time = self._active_operations.pop(operation)
            duration = time.time() - start_time
            self._metrics.record_operation(operation, duration)
            
            logger.debug("Operation %s took %.3fms", operation, duration * 1000)
            return duration
    
    def get_metrics(self) -> PerformanceMetrics:
        """Get performance metrics."""
        return self._metrics


def performance_monitor(operation_name: str, profiler: Optional[PerformanceProfiler] = None):
    """Decorator for monitoring function performance."""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            if profiler:
                profiler.start_operation(operation_name)
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if profiler:
                    profiler.end_operation(operation_name)
                
                if duration > 0.1:  # Log slow operations
                    logger.warning("Slow operation %s: %.3fms", operation_name, duration * 1000)
        
        return wrapper
    return decorator


class MemoryPool:
    """Memory pool for reusing objects to reduce allocation overhead."""
    
    def __init__(self, factory: Callable[[], T], max_size: int = 100):
        self.factory = factory
        self.max_size = max_size
        self._pool: List[T] = []
        self._lock = threading.Lock()
    
    def acquire(self) -> T:
        """Acquire an object from the pool."""
        with self._lock:
            if self._pool:
                obj = self._pool.pop()
                logger.debug("Acquired object from pool (remaining: %d)", len(self._pool))
                return obj
            else:
                obj = self.factory()
                logger.debug("Created new object (pool empty)")
                return obj
    
    def release(self, obj: T) -> None:
        """Return an object to the pool."""
        with self._lock:
            if len(self._pool) < self.max_size:
                # Reset object state if it has a reset method
                if hasattr(obj, 'reset'):
                    try:
                        obj.reset()
                    except Exception as e:
                        logger.warning("Error resetting pooled object: %s", e)
                        return
                
                self._pool.append(obj)
                logger.debug("Released object to pool (total: %d)", len(self._pool))
    
    def clear(self) -> None:
        """Clear the pool."""
        with self._lock:
            count = len(self._pool)
            self._pool.clear()
            logger.debug("Cleared memory pool (%d objects)", count)


class RenderingOptimizer:
    """Optimization system for rendering operations."""
    
    def __init__(self, max_cache_size: int = 1000):
        self.stroke_cache = LRUCache[List[Any]](max_cache_size, "stroke_rendering")
        self.dirty_regions: List[Tuple[int, int, int, int]] = []
        self._lock = threading.Lock()
    
    def cache_stroke_render(self, stroke_id: str, rendered_points: List[Any]) -> None:
        """Cache rendered stroke points."""
        self.stroke_cache.put(stroke_id, rendered_points)
    
    def get_cached_stroke(self, stroke_id: str) -> Optional[List[Any]]:
        """Get cached stroke rendering."""
        return self.stroke_cache.get(stroke_id)
    
    def mark_dirty_region(self, x: int, y: int, width: int, height: int) -> None:
        """Mark a screen region as dirty for partial rerendering."""
        with self._lock:
            self.dirty_regions.append((x, y, width, height))
    
    def get_dirty_regions(self) -> List[Tuple[int, int, int, int]]:
        """Get and clear dirty regions."""
        with self._lock:
            regions = self.dirty_regions.copy()
            self.dirty_regions.clear()
            return regions
    
    def should_skip_render(self, complexity_score: float, target_fps: int = 60) -> bool:
        """Determine if rendering should be skipped for performance."""
        target_frame_time = 1.0 / target_fps
        
        # Skip if complexity is too high
        if complexity_score > target_frame_time * 1000:  # Convert to ms
            logger.debug("Skipping render due to complexity: %.2fms", complexity_score)
            return True
        
        return False


class AdaptiveQuality:
    """Adaptive quality system that adjusts rendering quality based on performance."""
    
    def __init__(self, target_fps: int = 60):
        self.target_fps = target_fps
        self.target_frame_time = 1.0 / target_fps
        self.quality_level = 1.0  # 0.0 to 1.0
        self.frame_times: deque = deque(maxlen=30)
        self._lock = threading.Lock()
    
    def record_frame_time(self, frame_time: float) -> None:
        """Record frame rendering time."""
        with self._lock:
            self.frame_times.append(frame_time)
            
            # Adjust quality based on performance
            if len(self.frame_times) >= 10:
                avg_frame_time = sum(list(self.frame_times)[-10:]) / 10
                
                if avg_frame_time > self.target_frame_time * 1.2:
                    # Performance is poor, reduce quality
                    self.quality_level = max(0.3, self.quality_level - 0.1)
                    logger.debug("Reduced quality to %.1f due to poor performance", self.quality_level)
                elif avg_frame_time < self.target_frame_time * 0.8:
                    # Performance is good, increase quality
                    self.quality_level = min(1.0, self.quality_level + 0.05)
                    logger.debug("Increased quality to %.1f due to good performance", self.quality_level)
    
    def get_quality_level(self) -> float:
        """Get current quality level (0.0 to 1.0)."""
        with self._lock:
            return self.quality_level
    
    def get_stroke_detail_level(self) -> int:
        """Get appropriate stroke detail level based on quality."""
        quality = self.get_quality_level()
        if quality >= 0.8:
            return 1  # Full detail
        elif quality >= 0.5:
            return 2  # Medium detail (every 2nd point)
        else:
            return 4  # Low detail (every 4th point)
    
    def should_use_antialiasing(self) -> bool:
        """Determine if antialiasing should be used."""
        return self.get_quality_level() >= 0.6


# Global performance system instance
_global_profiler = PerformanceProfiler()
_global_batch_processor = BatchProcessor()
_global_rendering_optimizer = RenderingOptimizer()
_global_adaptive_quality = AdaptiveQuality()


def get_global_profiler() -> PerformanceProfiler:
    """Get the global performance profiler."""
    return _global_profiler


def get_global_batch_processor() -> BatchProcessor:
    """Get the global batch processor."""
    return _global_batch_processor


def get_global_rendering_optimizer() -> RenderingOptimizer:
    """Get the global rendering optimizer."""
    return _global_rendering_optimizer


def get_global_adaptive_quality() -> AdaptiveQuality:
    """Get the global adaptive quality system."""
    return _global_adaptive_quality


# Convenience decorators
def profile_operation(operation_name: str):
    """Decorator for profiling operations."""
    return performance_monitor(operation_name, _global_profiler)


def cached_operation(cache_name: str = "default", max_size: int = 100):
    """Decorator for caching operation results."""
    cache = LRUCache(max_size, cache_name)
    
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key = (func.__name__, str(args), str(sorted(kwargs.items())))
            
            # Try cache first
            result = cache.get(key)
            if result is not None:
                return result
            
            # Compute and cache result
            result = func(*args, **kwargs)
            cache.put(key, result)
            return result
        
        return wrapper
    return decorator


# Example usage:
"""
# Using performance monitoring
@profile_operation("stroke_rendering")
def render_stroke(stroke):
    # Rendering logic here
    pass

# Using caching
@cached_operation("point_conversion", max_size=500)
def convert_points(points):
    # Expensive point conversion
    return converted_points

# Using batch processing
batch_processor = get_global_batch_processor()
batch_processor.register_processor("stroke_updates", process_stroke_batch)

# Add items to batch
batch_processor.add_item("stroke_updates", stroke_data)

# Using adaptive quality
quality = get_global_adaptive_quality()
if quality.should_use_antialiasing():
    enable_antialiasing()

detail_level = quality.get_stroke_detail_level()
render_stroke_with_detail(stroke, detail_level)
"""