"""
Grid widget for background grid rendering.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class GridWidget:
    """Grid background widget with neon-style lines."""
    
    def __init__(self, engine: Any, settings: Any):
        self.engine = engine
        self.settings = settings
        self.grid_spacing = getattr(settings, 'GRID_SPACING', 40)
        self.grid_color = getattr(settings, 'GRID_COLOR', (40, 40, 40))
        self.enabled = True
        
    def render(self) -> None:
        """Render grid background."""
        if not self.enabled:
            return
            
        try:
            if not hasattr(self.engine, 'screen'):
                return
                
            width, height = self.engine.get_size()
            
            # Draw vertical lines
            for x in range(0, width, self.grid_spacing):
                try:
                    # Vary color slightly for visual interest
                    color = (
                        min(255, self.grid_color[0] + (x % 20)),
                        min(255, self.grid_color[1] + (x % 15)),
                        min(255, self.grid_color[2] + (x % 10))
                    )
                    self.engine.draw_line((x, 0), (x, height), 1, color)
                except Exception:
                    continue
            
            # Draw horizontal lines
            for y in range(0, height, self.grid_spacing):
                try:
                    # Vary color slightly for visual interest
                    color = (
                        min(255, self.grid_color[0] + (y % 15)),
                        min(255, self.grid_color[1] + (y % 20)),
                        min(255, self.grid_color[2] + (y % 25))
                    )
                    self.engine.draw_line((0, y), (width, y), 1, color)
                except Exception:
                    continue
                    
            logger.debug("Grid rendered with spacing %d", self.grid_spacing)
                    
        except Exception as e:
            logger.error("Error rendering grid: %s", e)
    
    def toggle(self) -> None:
        """Toggle grid visibility."""
        self.enabled = not self.enabled
        logger.info("Grid %s", "enabled" if self.enabled else "disabled")