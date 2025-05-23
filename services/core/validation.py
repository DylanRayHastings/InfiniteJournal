"""Simplified validation service."""

import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Validation error."""
    pass


class ValidationService:
    """Simple validation service."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def validate(self, validator_name, value):
        """Validate value using named validator."""
        if validator_name == 'coordinate':
            return self._validate_coordinate(value)
        elif validator_name == 'color':
            return self._validate_color(value)
        elif validator_name == 'brush_width':
            return self._validate_brush_width(value)
        return value
        
    def _validate_coordinate(self, value):
        if isinstance(value, (tuple, list)) and len(value) >= 2:
            try:
                return (int(value[0]), int(value[1]))
            except:
                pass
        raise ValidationError("Invalid coordinate")
        
    def _validate_color(self, value):
        if isinstance(value, (tuple, list)) and len(value) >= 3:
            try:
                return tuple(max(0, min(255, int(c))) for c in value[:3])
            except:
                pass
        raise ValidationError("Invalid color")
        
    def _validate_brush_width(self, value):
        try:
            w = int(value)
            return max(1, min(100, w))
        except:
            raise ValidationError("Invalid brush width")


def validate_coordinate(x, y):
    """Validate coordinates."""
    try:
        return int(x), int(y)
    except:
        raise ValidationError("Invalid coordinates")


def validate_color(color):
    """Validate color."""
    if isinstance(color, (tuple, list)) and len(color) >= 3:
        try:
            return tuple(max(0, min(255, int(c))) for c in color[:3])
        except:
            pass
    raise ValidationError("Invalid color")


def validate_brush_width(width):
    """Validate brush width."""
    try:
        w = int(width)
        return max(1, min(100, w))
    except:
        raise ValidationError("Invalid brush width")


def validate_tool_key(tool):
    """Validate tool key."""
    valid_tools = ["brush", "eraser", "line", "rect", "circle"]
    if str(tool).lower() in valid_tools:
        return str(tool).lower()
    raise ValidationError("Invalid tool")


def create_validator_chain(*validators):
    """Create validator chain."""
    return validators
