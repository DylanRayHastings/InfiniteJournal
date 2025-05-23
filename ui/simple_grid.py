"""
Simple grid widget as fallback when main grid is not available.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class SimpleGridWidget:
    """Simple grid background renderer."""
    
    def __init__(self, engine: Any, settings: Any):
        self.engine = engine
        self.settings = settings
        self.grid_spacing = 40
        self.grid_color = (30, 30, 30)  # Dark gray grid
        
    def render(self) -> None:
        """Render a simple grid background."""
        try:
            if not hasattr(self.engine, 'screen'):
                return
                
            width, height = self.engine.get_size()
            
            # Draw vertical lines
            for x in range(0, width, self.grid_spacing):
                try:
                    self.engine.draw_line((x, 0), (x, height), 1, self.grid_color)
                except Exception:
                    continue
            
            # Draw horizontal lines  
            for y in range(0, height, self.grid_spacing):
                try:
                    self.engine.draw_line((0, y), (width, y), 1, self.grid_color)
                except Exception:
                    continue
                    
        except Exception as e:
            logger.debug("Error rendering simple grid: %s", e)