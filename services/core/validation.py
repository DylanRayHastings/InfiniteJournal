"""
Universal Validation System
Eliminates ALL scattered validation logic through composable validators.

This module consolidates validation from coordinates, colors, tools, files,
and all other domain areas into a single unified system.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ValidationError(Exception):
    """Base validation error with detailed context."""
    
    def __init__(self, message: str, field_name: str = None, value: Any = None):
        super().__init__(message)
        self.field_name = field_name
        self.value = value
        self.message = message


@dataclass(frozen=True)
class ValidationResult:
    """Result of validation operation."""
    is_valid: bool
    value: Any = None
    error_message: str = None
    normalized_value: Any = None
    
    @classmethod
    def success(cls, value: Any, normalized_value: Any = None):
        """Create successful validation result."""
        return cls(True, value, None, normalized_value or value)
    
    @classmethod
    def failure(cls, error_message: str, value: Any = None):
        """Create failed validation result."""
        return cls(False, value, error_message)


class ValidationRule(ABC):
    """Abstract base for composable validation rules."""
    
    @abstractmethod
    def validate(self, value: Any) -> ValidationResult:
        """Validate value according to rule."""
        pass
    
    def __call__(self, value: Any) -> ValidationResult:
        """Allow rule to be called like a function."""
        return self.validate(value)


class RequiredRule(ValidationRule):
    """Validates that value is not None or empty."""
    
    def validate(self, value: Any) -> ValidationResult:
        if value is None:
            return ValidationResult.failure("Value is required")
        
        if isinstance(value, str) and not value.strip():
            return ValidationResult.failure("Value cannot be empty")
        
        return ValidationResult.success(value)


class RangeRule(ValidationRule):
    """Validates numeric values within specified range."""
    
    def __init__(self, min_value: float, max_value: float):
        self.min_value = min_value
        self.max_value = max_value
    
    def validate(self, value: Any) -> ValidationResult:
        try:
            num_value = float(value)
        except (ValueError, TypeError):
            return ValidationResult.failure(f"Value must be numeric, got {type(value).__name__}")
        
        if not (self.min_value <= num_value <= self.max_value):
            return ValidationResult.failure(
                f"Value {num_value} must be between {self.min_value} and {self.max_value}"
            )
        
        return ValidationResult.success(value, num_value)


class CoordinateRule(ValidationRule):
    """Validates coordinate values with optional bounds checking."""
    
    def __init__(self, bounds: Optional[Tuple[int, int, int, int]] = None):
        self.bounds = bounds  # (min_x, min_y, max_x, max_y)
    
    def validate(self, value: Any) -> ValidationResult:
        if isinstance(value, (tuple, list)) and len(value) >= 2:
            try:
                x, y = float(value[0]), float(value[1])
            except (ValueError, TypeError):
                return ValidationResult.failure("Coordinates must be numeric")
        elif hasattr(value, 'x') and hasattr(value, 'y'):
            try:
                x, y = float(value.x), float(value.y)
            except (ValueError, TypeError):
                return ValidationResult.failure("Coordinates must be numeric")
        else:
            return ValidationResult.failure("Invalid coordinate format")
        
        if self.bounds:
            min_x, min_y, max_x, max_y = self.bounds
            if not (min_x <= x <= max_x and min_y <= y <= max_y):
                return ValidationResult.failure(f"Coordinates ({x}, {y}) out of bounds")
        
        return ValidationResult.success(value, (int(x), int(y)))


class ColorRule(ValidationRule):
    """Validates color values in various formats."""
    
    def validate(self, value: Any) -> ValidationResult:
        # RGB tuple
        if isinstance(value, (tuple, list)) and len(value) >= 3:
            try:
                r, g, b = value[:3]
                if all(0 <= int(c) <= 255 for c in [r, g, b]):
                    return ValidationResult.success(value, (int(r), int(g), int(b)))
            except (ValueError, TypeError):
                pass
        
        # Hex string
        if isinstance(value, str):
            if value.startswith('#'):
                value = value[1:]
            if len(value) == 6 and all(c in '0123456789abcdefABCDEF' for c in value):
                r = int(value[0:2], 16)
                g = int(value[2:4], 16)
                b = int(value[4:6], 16)
                return ValidationResult.success(value, (r, g, b))
        
        return ValidationResult.failure("Invalid color format")


class ToolKeyRule(ValidationRule):
    """Validates tool keys for hotkey mapping."""
    
    VALID_TOOLS = ["brush", "eraser", "line", "rect", "circle", "triangle", "parabola"]
    
    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, str):
            return ValidationResult.failure("Tool key must be string")
        
        tool_name = value.lower().strip()
        if tool_name not in self.VALID_TOOLS:
            return ValidationResult.failure(f"Invalid tool '{tool_name}'. Valid: {self.VALID_TOOLS}")
        
        return ValidationResult.success(value, tool_name)


class ValidationChain:
    """Chains multiple validation rules together."""
    
    def __init__(self, rules: List[ValidationRule]):
        self.rules = rules
    
    def validate(self, value: Any) -> ValidationResult:
        """Apply all rules in sequence."""
        current_value = value
        
        for rule in self.rules:
            result = rule.validate(current_value)
            if not result.is_valid:
                return result
            current_value = result.normalized_value or result.value
        
        return ValidationResult.success(value, current_value)


class ValidationService:
    """Universal validation service eliminating all scattered validation."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._validators: Dict[str, ValidationChain] = {}
        self._setup_standard_validators()
    
    def _setup_standard_validators(self):
        """Setup commonly used validators."""
        self._validators.update({
            'coordinate': ValidationChain([RequiredRule(), CoordinateRule()]),
            'color': ValidationChain([RequiredRule(), ColorRule()]),
            'brush_width': ValidationChain([RequiredRule(), RangeRule(1, 200)]),
            'tool_key': ValidationChain([RequiredRule(), ToolKeyRule()]),
            'file_path': ValidationChain([RequiredRule()]),
        })
    
    def validate(self, validator_name: str, value: Any) -> ValidationResult:
        """Validate using named validator."""
        if validator_name not in self._validators:
            return ValidationResult.failure(f"Unknown validator: {validator_name}")
        
        try:
            return self._validators[validator_name].validate(value)
        except Exception as error:
            self.logger.error(f"Validation error for {validator_name}: {error}")
            return ValidationResult.failure(f"Validation failed: {error}")
    
    def register_validator(self, name: str, chain: ValidationChain):
        """Register custom validator chain."""
        self._validators[name] = chain
        self.logger.debug(f"Registered validator: {name}")


# Convenience functions for common validations
def validate_coordinate(x: Any, y: Any, bounds: Optional[Tuple[int, int, int, int]] = None) -> Tuple[int, int]:
    """Universal coordinate validation."""
    rule = CoordinateRule(bounds)
    result = rule.validate((x, y))
    
    if not result.is_valid:
        raise ValidationError(result.error_message, "coordinate", (x, y))
    
    return result.normalized_value


def validate_color(color: Any) -> Tuple[int, int, int]:
    """Universal color validation."""
    rule = ColorRule()
    result = rule.validate(color)
    
    if not result.is_valid:
        raise ValidationError(result.error_message, "color", color)
    
    return result.normalized_value


def validate_brush_width(width: Any) -> float:
    """Universal brush width validation."""
    rule = RangeRule(1, 200)
    result = rule.validate(width)
    
    if not result.is_valid:
        raise ValidationError(result.error_message, "brush_width", width)
    
    return result.normalized_value


def validate_file_path(path: Any) -> Path:
    """Universal file path validation."""
    if not isinstance(path, (str, Path)):
        raise ValidationError("Path must be string or Path object", "file_path", path)
    
    try:
        validated_path = Path(path)
        return validated_path
    except Exception as error:
        raise ValidationError(f"Invalid path: {error}", "file_path", path)


def validate_tool_key(tool: Any) -> str:
    """Universal tool key validation."""
    rule = ToolKeyRule()
    result = rule.validate(tool)
    
    if not result.is_valid:
        raise ValidationError(result.error_message, "tool_key", tool)
    
    return result.normalized_value


def create_validator_chain(*rules: ValidationRule) -> ValidationChain:
    """Create validation chain from rules."""
    return ValidationChain(list(rules))


def create_coordinate_validator(bounds: Optional[Tuple[int, int, int, int]] = None) -> ValidationChain:
    """Create coordinate validator with optional bounds."""
    return ValidationChain([RequiredRule(), CoordinateRule(bounds)])


def create_numeric_validator(min_val: float, max_val: float) -> ValidationChain:
    """Create numeric range validator."""
    return ValidationChain([RequiredRule(), RangeRule(min_val, max_val)])