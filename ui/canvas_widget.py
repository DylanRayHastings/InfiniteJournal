"""
CanvasWidget with performance optimizations, error boundaries, and persistent display.

Enhanced with caching, dirty region tracking, and comprehensive error handling.
"""

from core.event_bus import EventBus
from core.interfaces import Renderer
from core.error_boundary import rendering_boundary, ErrorContext, get_global_error_boundary
from core.performance import profile_operation, get_global_rendering_optimizer, get_global_adaptive_quality
from services.journal import JournalService
import logging
import time
from typing import Optional, Set, Tuple

logger = logging.getLogger(__name__)


class CanvasWidget:
    """
    CanvasWidget: Connects JournalService (data/model) to Renderer (view) with performance optimizations.
    Ensures all drawn content persists visually until explicitly cleared.

    Args:
        journal (JournalService): Provides page and stroke data.
        renderer (Renderer): Handles drawing operations.
        bus (EventBus): Event bus for subscribing to journal changes.
    """

    def __init__(
        self,
        journal: JournalService,
        renderer: Renderer,
        bus: EventBus
    ) -> None:
        # Validate inputs
        if not journal:
            raise ValueError("JournalService cannot be None")
        if not renderer:
            raise ValueError("Renderer cannot be None")
        if not bus:
            raise ValueError("EventBus cannot be None")
            
        self._journal = journal
        self._renderer = renderer
        self._always_render = True  # Always render content for persistence

        # Performance optimization systems
        self._error_boundary = get_global_error_boundary()
        self._rendering_optimizer = get_global_rendering_optimizer()
        self._adaptive_quality = get_global_adaptive_quality()
        
        # Rendering state and optimization
        self._last_render_time = 0.0
        self._render_throttle_interval = 1.0 / 60.0  # 60 FPS max
        self._cache_invalidated = True
        self._last_stroke_count = 0
        self._dirty_regions: Set[Tuple[int, int, int, int]] = set()
        
        # Performance tracking
        self._render_count = 0
        self._skip_count = 0
        
        try:
            # Subscribe to stroke or page update events with error handling
            bus.subscribe('stroke_added', self._on_update)
            bus.subscribe('page_cleared', self._on_page_cleared)
            bus.subscribe('stroke_invalidated', self._on_stroke_invalidated)
            bus.subscribe('rendering_recovery', self._on_rendering_recovery)
            
            logger.info("CanvasWidget initialized with performance optimizations")
            
        except Exception as e:
            logger.error("Error subscribing to canvas events: %s", e)
            context = ErrorContext("canvas_initialization", "canvas_widget")
            self._error_boundary.handle_error(e, context)

    def _on_update(self, data=None) -> None:
        """
        Handles update notifications (e.g., a new stroke was added) with performance optimization.
        """
        try:
            # Invalidate cache to ensure fresh rendering
            self._journal.invalidate_cache()
            self._cache_invalidated = True
            
            # Track dirty regions for partial updates
            if data and isinstance(data, dict):
                region = data.get('dirty_region')
                if region:
                    self._dirty_regions.add(region)
            
            logger.debug("Canvas update triggered")
            
        except Exception as e:
            logger.error("Error handling canvas update: %s", e)

    def _on_page_cleared(self, data=None) -> None:
        """
        Handles page clear notifications with state reset.
        """
        try:
            self._cache_invalidated = True
            self._last_stroke_count = 0
            self._dirty_regions.clear()
            logger.debug("Canvas cleared, cache invalidated")
            
        except Exception as e:
            logger.error("Error handling page clear: %s", e)

    def _on_stroke_invalidated(self, data=None) -> None:
        """
        Handles stroke invalidation for partial updates.
        """
        try:
            self._cache_invalidated = True
            
            # Add specific region if provided
            if data and isinstance(data, dict):
                region = data.get('region')
                if region:
                    self._dirty_regions.add(region)
                    
        except Exception as e:
            logger.error("Error handling stroke invalidation: %s", e)

    def _on_rendering_recovery(self, data=None) -> None:
        """
        Handle rendering recovery events.
        """
        try:
            # Reset rendering state
            self._cache_invalidated = True
            self._dirty_regions.clear()
            self._last_render_time = 0
            logger.info("Canvas rendering recovery triggered")
            
        except Exception as e:
            logger.error("Error in rendering recovery: %s", e)

    @rendering_boundary("canvas_render", "canvas_widget")
    @profile_operation("canvas_rendering")
    def render(self) -> None:
        """
        Render the current journal state to the canvas with performance optimization.
        This method is called every frame to ensure persistent visibility.
        """
        current_time = time.time()
        
        try:
            # Performance throttling - skip render if too soon
            if (current_time - self._last_render_time) < self._render_throttle_interval:
                self._skip_count += 1
                return
            
            # Check if render is needed
            if not self._should_render():
                self._skip_count += 1
                return
            
            # Adaptive quality check
            quality_level = self._adaptive_quality.get_quality_level()
            if quality_level < 0.3 and self._render_count % 2 == 0:
                # Skip every other frame at very low quality
                self._skip_count += 1
                return
            
            # Perform the actual rendering
            self._perform_render(quality_level)
            
            # Update performance tracking
            self._last_render_time = current_time
            self._render_count += 1
            
            # Log performance statistics periodically
            if self._render_count % 300 == 0:  # Every ~5 seconds at 60fps
                total_calls = self._render_count + self._skip_count
                skip_rate = (self._skip_count / total_calls) * 100 if total_calls > 0 else 0
                logger.debug("Canvas render stats: %d renders, %d skips (%.1f%% skip rate)", 
                           self._render_count, self._skip_count, skip_rate)
            
        except Exception as e:
            logger.error("Critical error in canvas render: %s", e)
            # Try fallback rendering
            self._fallback_render()

    def _should_render(self) -> bool:
        """
        Determine if rendering is necessary based on state changes.
        """
        try:
            # Always render if cache is invalidated
            if self._cache_invalidated:
                return True
            
            # Check if stroke count changed
            current_stroke_count = self._journal.get_stroke_count()
            if current_stroke_count != self._last_stroke_count:
                self._last_stroke_count = current_stroke_count
                return True
            
            # Check if there are dirty regions
            if self._dirty_regions:
                return True
            
            # Check if journal has any changes (fallback check)
            if hasattr(self._journal, '_cache_valid') and not self._journal._cache_valid:
                return True
            
            return False
            
        except Exception as e:
            logger.error("Error checking render necessity: %s", e)
            return True  # Render on error to be safe

    def _perform_render(self, quality_level: float) -> None:
        """
        Perform the actual rendering with quality-based optimizations.
        """
        try:
            # Determine rendering strategy based on quality
            if quality_level >= 0.8:
                # High quality - full render
                self._render_full()
            elif quality_level >= 0.5:
                # Medium quality - partial render if possible
                if self._dirty_regions:
                    self._render_partial()
                else:
                    self._render_full()
            else:
                # Low quality - simplified render
                self._render_simplified()
            
            # Clear dirty regions after successful render
            self._dirty_regions.clear()
            self._cache_invalidated = False
            
        except Exception as e:
            logger.error("Error in render performance: %s", e)
            # Fallback to simple render
            self._render_fallback()

    def _render_full(self) -> None:
        """
        Full quality rendering with all optimizations.
        """
        try:
            # Use caching if available
            cache_key = f"canvas_full_{self._journal.get_stroke_count()}"
            cached_result = self._rendering_optimizer.get_cached_stroke(cache_key)
            
            if cached_result is None:
                # Render and cache
                self._journal.render(self._renderer)
                # Note: Actual caching would need renderer cooperation
                self._rendering_optimizer.cache_stroke_render(cache_key, [])
            else:
                # Use cached rendering (would need renderer cooperation)
                self._journal.render(self._renderer)
            
            logger.debug("Full render completed")
            
        except Exception as e:
            logger.error("Error in full render: %s", e)
            raise

    def _render_partial(self) -> None:
        """
        Partial rendering for dirty regions only.
        """
        try:
            # For now, fall back to full render
            # TODO: Implement true partial rendering with clipping regions
            self._render_full()
            logger.debug("Partial render completed (using full render fallback)")
            
        except Exception as e:
            logger.error("Error in partial render: %s", e)
            raise

    def _render_simplified(self) -> None:
        """
        Simplified rendering for low quality/performance situations.
        """
        try:
            # Render with reduced detail level
            detail_level = self._adaptive_quality.get_stroke_detail_level()
            
            # TODO: Pass detail level to journal renderer
            # For now, use standard rendering
            self._journal.render(self._renderer)
            
            logger.debug("Simplified render completed with detail level %d", detail_level)
            
        except Exception as e:
            logger.error("Error in simplified render: %s", e)
            raise

    def _render_fallback(self) -> None:
        """
        Ultra-safe fallback rendering that should never fail.
        """
        try:
            # Minimal, safe rendering without optimizations
            if hasattr(self._journal, 'render') and hasattr(self._renderer, 'draw_line'):
                self._journal.render(self._renderer)
            logger.debug("Fallback render completed")
            
        except Exception as e:
            logger.error("Even fallback render failed: %s", e)
            # At this point, we just log and continue

    def _fallback_render(self) -> None:
        """
        Emergency fallback when main render fails completely.
        """
        try:
            # Reset all state and try minimal render
            self._cache_invalidated = True
            self._dirty_regions.clear()
            
            # Try the most basic rendering possible
            if self._journal and self._renderer:
                self._journal.render(self._renderer)
                
            logger.warning("Emergency fallback render completed")
            
        except Exception as e:
            logger.critical("Emergency fallback render failed: %s", e)
            # Nothing more we can do

    def invalidate_cache(self) -> None:
        """
        Force cache invalidation for next render.
        """
        try:
            self._cache_invalidated = True
            self._dirty_regions.clear()
            logger.debug("Canvas cache manually invalidated")
        except Exception as e:
            logger.error("Error invalidating canvas cache: %s", e)

    def add_dirty_region(self, x: int, y: int, width: int, height: int) -> None:
        """
        Mark a specific region as dirty for partial rerendering.
        """
        try:
            region = (max(0, int(x)), max(0, int(y)), max(1, int(width)), max(1, int(height)))
            self._dirty_regions.add(region)
            logger.debug("Added dirty region: %s", region)
        except Exception as e:
            logger.error("Error adding dirty region: %s", e)

    def get_render_stats(self) -> dict:
        """
        Get rendering performance statistics.
        """
        try:
            total_calls = self._render_count + self._skip_count
            return {
                'render_count': self._render_count,
                'skip_count': self._skip_count,
                'skip_rate': (self._skip_count / total_calls) * 100 if total_calls > 0 else 0,
                'cache_invalidated': self._cache_invalidated,
                'dirty_regions': len(self._dirty_regions),
                'last_stroke_count': self._last_stroke_count
            }
        except Exception as e:
            logger.error("Error getting render stats: %s", e)
            return {}