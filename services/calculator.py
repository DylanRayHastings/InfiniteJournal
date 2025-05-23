#!/usr/bin/env python3
"""
Production Calculator System.

Unified mathematical computation, shape generation, and user interface system
designed for high-performance interactive applications with comprehensive
validation, error handling, and extensibility.

Quick start:
    calculator_system = CalculatorSystemFactory.create_default_system()
    result = calculator_system.execute_operation("solve", "x^2 + 2*x - 3 = 0")

Extension points:
    - Add operation types: Extend OperationType enum and OperationProcessor
    - Add shape types: Extend ShapeType enum and ShapeGenerator
    - Add storage backends: Implement HistoryStorage interface
    - Add UI frameworks: Implement UserInterface interface
    - Add validation rules: Extend ValidationService
"""

import os
import json
import logging
import re
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, Optional, Union, Protocol, runtime_checkable
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path

import sympy as sp
import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import simpledialog, messagebox

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Mathematical operation types supported by the calculator."""
    SOLVE = "solve"
    SIMPLIFY = "simplify"
    EXPAND = "expand"
    FACTOR = "factor"
    DERIVATIVE = "derivative"
    INTEGRAL = "integral"
    PLOT = "plot"


class ShapeType(Enum):
    """Geometric shape types supported by the generator."""
    LINE = "line"
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    TRIANGLE = "triangle"
    PARABOLA = "parabola"


class ValidationLevel(Enum):
    """Validation strictness levels."""
    STRICT = "strict"
    PERMISSIVE = "permissive"
    SILENT = "silent"


@dataclass(frozen=True)
class SystemConfiguration:
    """Immutable system configuration with validation and defaults."""
    debug_mode: bool = True
    independent_mode: bool = True
    history_file_path: str = "calculator_history.json"
    validation_level: ValidationLevel = ValidationLevel.STRICT
    plot_x_range: Tuple[float, float] = (-10.0, 10.0)
    plot_points_count: int = 500
    circle_default_points: int = 100
    log_level: str = "DEBUG"
    
    def __post_init__(self):
        """Initialize logging based on configuration."""
        log_level = getattr(logging, self.log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s'
        )
        logger.debug("System configuration initialized with debug_mode=%s", self.debug_mode)


@dataclass(frozen=True)
class OperationResult:
    """Immutable operation result container."""
    operation_type: OperationType
    input_expression: str
    output_result: Any
    execution_time_ms: float
    success: bool
    error_message: Optional[str] = None


@dataclass(frozen=True)
class ShapeGenerationResult:
    """Immutable shape generation result container."""
    shape_type: ShapeType
    parameters: Dict[str, Any]
    points: List[Tuple[float, float]]
    point_count: int
    
    def __post_init__(self):
        object.__setattr__(self, 'point_count', len(self.points))


class CalculatorError(Exception):
    """Base exception for calculator system errors."""
    pass


class ValidationError(CalculatorError):
    """Raised when input validation fails."""
    pass


class OperationError(CalculatorError):
    """Raised when mathematical operation fails."""
    pass


class StorageError(CalculatorError):
    """Raised when history storage operations fail."""
    pass


@runtime_checkable
class HistoryStorage(Protocol):
    """Interface for history persistence implementations."""
    
    def save_operation_result(self, result: OperationResult) -> None:
        """Save operation result to storage."""
        ...
    
    def load_operation_history(self) -> List[OperationResult]:
        """Load complete operation history from storage."""
        ...
    
    def clear_operation_history(self) -> None:
        """Clear all operation history from storage."""
        ...


@runtime_checkable
class UserInterface(Protocol):
    """Interface for user interaction implementations."""
    
    def get_operation_type(self) -> Optional[OperationType]:
        """Get operation type from user input."""
        ...
    
    def get_expression_input(self) -> Optional[str]:
        """Get mathematical expression from user input."""
        ...
    
    def display_operation_result(self, result: OperationResult) -> None:
        """Display operation result to user."""
        ...
    
    def display_error_message(self, error_message: str) -> None:
        """Display error message to user."""
        ...


class ValidationService:
    """Centralized validation service for all input types."""
    
    MATHEMATICAL_SYMBOL_TRANSLATIONS = {
        'π': 'pi',
        '√': 'sqrt',
        '∑': 'Sum',
        '∫': 'integrate',
        '∞': 'oo',
        'ln': 'log',
        'e^': 'exp',
        '÷': '/',
        '•': '*',
        '^': '**',
        'd/dx': 'diff',
    }
    
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    EXPRESSION_PATTERN = re.compile(r'^[a-zA-Z0-9+\-*/()^=.,\s√πeℯ∞∑∫]+$')
    
    def __init__(self, validation_level: ValidationLevel):
        self.validation_level = validation_level
    
    def validate_expression_format(self, expression: str) -> str:
        """Validate and normalize mathematical expression format."""
        if not expression:
            return self._handle_validation_error("Expression cannot be empty")
        
        if not isinstance(expression, str):
            return self._handle_validation_error("Expression must be a string")
        
        expression = expression.strip()
        
        if len(expression) > 1000:
            return self._handle_validation_error("Expression too long (max 1000 characters)")
        
        if not self.EXPRESSION_PATTERN.match(expression):
            return self._handle_validation_error("Expression contains invalid characters")
        
        return self._translate_mathematical_symbols(expression)
    
    def validate_equation_format(self, expression: str) -> Tuple[str, str]:
        """Validate equation format and return left and right sides."""
        normalized_expression = self.validate_expression_format(expression)
        
        if '=' not in normalized_expression:
            return self._handle_validation_error("Equation must contain '=' symbol")
        
        equation_parts = normalized_expression.split('=')
        
        if len(equation_parts) != 2:
            return self._handle_validation_error("Equation must have exactly one '=' symbol")
        
        left_side = equation_parts[0].strip()
        right_side = equation_parts[1].strip()
        
        if not left_side:
            return self._handle_validation_error("Left side of equation cannot be empty")
        
        if not right_side:
            return self._handle_validation_error("Right side of equation cannot be empty")
        
        return left_side, right_side
    
    def validate_coordinate_values(self, x: Union[int, float], y: Union[int, float]) -> Tuple[float, float]:
        """Validate coordinate values for shape generation."""
        try:
            x_float = float(x)
            y_float = float(y)
        except (TypeError, ValueError):
            return self._handle_validation_error("Coordinates must be numeric values")
        
        if not (-1e6 <= x_float <= 1e6):
            return self._handle_validation_error("X coordinate out of reasonable range")
        
        if not (-1e6 <= y_float <= 1e6):
            return self._handle_validation_error("Y coordinate out of reasonable range")
        
        if math.isnan(x_float) or math.isnan(y_float):
            return self._handle_validation_error("Coordinates cannot be NaN")
        
        if math.isinf(x_float) or math.isinf(y_float):
            return self._handle_validation_error("Coordinates cannot be infinite")
        
        return x_float, y_float
    
    def validate_radius_value(self, radius: Union[int, float]) -> float:
        """Validate radius value for circular shapes."""
        try:
            radius_float = float(radius)
        except (TypeError, ValueError):
            return self._handle_validation_error("Radius must be a numeric value")
        
        if radius_float <= 0:
            return self._handle_validation_error("Radius must be positive")
        
        if radius_float > 1e6:
            return self._handle_validation_error("Radius too large")
        
        if math.isnan(radius_float) or math.isinf(radius_float):
            return self._handle_validation_error("Radius must be a finite number")
        
        return radius_float
    
    def validate_points_count(self, points_count: Union[int, float]) -> int:
        """Validate points count for shape generation."""
        try:
            points_int = int(points_count)
        except (TypeError, ValueError):
            return self._handle_validation_error("Points count must be an integer")
        
        if points_int < 3:
            return self._handle_validation_error("Points count must be at least 3")
        
        if points_int > 10000:
            return self._handle_validation_error("Points count too large (max 10000)")
        
        return points_int
    
    def validate_file_path_format(self, file_path: str) -> Path:
        """Validate file path format and accessibility."""
        if not file_path:
            return self._handle_validation_error("File path cannot be empty")
        
        if not isinstance(file_path, str):
            return self._handle_validation_error("File path must be a string")
        
        try:
            path_object = Path(file_path)
        except (TypeError, ValueError) as error:
            return self._handle_validation_error(f"Invalid file path format: {error}")
        
        if path_object.is_absolute() and not path_object.parent.exists():
            return self._handle_validation_error("Parent directory does not exist")
        
        return path_object
    
    def _translate_mathematical_symbols(self, expression: str) -> str:
        """Translate common mathematical symbols to sympy syntax."""
        translated_expression = expression
        
        for symbol, replacement in self.MATHEMATICAL_SYMBOL_TRANSLATIONS.items():
            translated_expression = translated_expression.replace(symbol, replacement)
        
        translated_expression = re.sub(r'(\d)([a-zA-Z])', r'\1*\2', translated_expression)
        translated_expression = re.sub(r'([a-zA-Z])(\()', r'\1*\2', translated_expression)
        translated_expression = re.sub(r'(\))([a-zA-Z0-9])', r'\1*\2', translated_expression)
        translated_expression = re.sub(r'(\d)(\()', r'\1*\2', translated_expression)
        
        return translated_expression.strip()
    
    def _handle_validation_error(self, error_message: str) -> Any:
        """Handle validation errors based on validation level."""
        if self.validation_level == ValidationLevel.STRICT:
            raise ValidationError(error_message)
        
        if self.validation_level == ValidationLevel.PERMISSIVE:
            logger.warning("Validation warning: %s", error_message)
            return None
        
        return None


class OperationProcessor:
    """Processes mathematical operations using sympy backend."""
    
    def __init__(self, validation_service: ValidationService):
        self.validation_service = validation_service
    
    def execute_solve_operation(self, expression: str) -> str:
        """Execute equation solving operation."""
        left_side, right_side = self.validation_service.validate_equation_format(expression)
        
        try:
            equation_object = sp.Eq(sp.sympify(left_side), sp.sympify(right_side))
            solutions = sp.solve(equation_object, sp.Symbol('x'))
            
            return f"Equation: {equation_object}\nSolutions: {solutions}"
        
        except Exception as error:
            raise OperationError(f"Failed to solve equation: {error}") from error
    
    def execute_simplify_operation(self, expression: str) -> str:
        """Execute expression simplification operation."""
        normalized_expression = self.validation_service.validate_expression_format(expression)
        
        try:
            simplified_result = sp.simplify(sp.sympify(normalized_expression))
            return f"Simplified: {simplified_result}"
        
        except Exception as error:
            raise OperationError(f"Failed to simplify expression: {error}") from error
    
    def execute_expand_operation(self, expression: str) -> str:
        """Execute expression expansion operation."""
        normalized_expression = self.validation_service.validate_expression_format(expression)
        
        try:
            expanded_result = sp.expand(sp.sympify(normalized_expression))
            return f"Expanded: {expanded_result}"
        
        except Exception as error:
            raise OperationError(f"Failed to expand expression: {error}") from error
    
    def execute_factor_operation(self, expression: str) -> str:
        """Execute expression factorization operation."""
        normalized_expression = self.validation_service.validate_expression_format(expression)
        
        try:
            factored_result = sp.factor(sp.sympify(normalized_expression))
            return f"Factored: {factored_result}"
        
        except Exception as error:
            raise OperationError(f"Failed to factor expression: {error}") from error
    
    def execute_derivative_operation(self, expression: str) -> str:
        """Execute differentiation operation."""
        normalized_expression = self.validation_service.validate_expression_format(expression)
        
        try:
            derivative_result = sp.diff(sp.sympify(normalized_expression), sp.Symbol('x'))
            return f"d/dx {normalized_expression} = {derivative_result}"
        
        except Exception as error:
            raise OperationError(f"Failed to differentiate expression: {error}") from error
    
    def execute_integral_operation(self, expression: str) -> str:
        """Execute integration operation."""
        normalized_expression = self.validation_service.validate_expression_format(expression)
        
        try:
            integral_result = sp.integrate(sp.sympify(normalized_expression), sp.Symbol('x'))
            return f"∫ {normalized_expression} dx = {integral_result} + C"
        
        except Exception as error:
            raise OperationError(f"Failed to integrate expression: {error}") from error
    
    def execute_plot_operation(self, expression: str, x_range: Tuple[float, float], points_count: int) -> None:
        """Execute plotting operation."""
        normalized_expression = self.validation_service.validate_expression_format(expression)
        
        try:
            x_symbol = sp.Symbol('x')
            function_expression = sp.sympify(normalized_expression)
            lambda_function = sp.lambdify(x_symbol, function_expression, 'numpy')
            
            x_values = np.linspace(x_range[0], x_range[1], points_count)
            y_values = lambda_function(x_values)
            
            plt.figure(figsize=(10, 6))
            plt.plot(x_values, y_values, label=f"y = {normalized_expression}", linewidth=2)
            plt.axhline(0, color='black', linewidth=0.5)
            plt.axvline(0, color='black', linewidth=0.5)
            plt.grid(True, alpha=0.3)
            plt.legend()
            plt.title(f"Plot of y = {normalized_expression}")
            plt.xlabel("x")
            plt.ylabel("y")
            plt.show()
            
        except Exception as error:
            raise OperationError(f"Failed to plot expression: {error}") from error


class ShapeGenerator:
    """Generates geometric shapes with comprehensive validation."""
    
    def __init__(self, validation_service: ValidationService):
        self.validation_service = validation_service
    
    def generate_line_points(self, x1: Union[int, float], y1: Union[int, float], 
                           x2: Union[int, float], y2: Union[int, float]) -> ShapeGenerationResult:
        """Generate interpolated points between two coordinates."""
        start_x, start_y = self.validation_service.validate_coordinate_values(x1, y1)
        end_x, end_y = self.validation_service.validate_coordinate_values(x2, y2)
        
        delta_x = end_x - start_x
        delta_y = end_y - start_y
        steps_count = max(abs(int(delta_x)), abs(int(delta_y)), 1)
        
        points = []
        for step in range(steps_count + 1):
            interpolation_factor = step / steps_count if steps_count > 0 else 0
            point_x = start_x + delta_x * interpolation_factor
            point_y = start_y + delta_y * interpolation_factor
            points.append((float(point_x), float(point_y)))
        
        logger.debug("Generated line with %d points from (%.2f,%.2f) to (%.2f,%.2f)", 
                    len(points), start_x, start_y, end_x, end_y)
        
        return ShapeGenerationResult(
            shape_type=ShapeType.LINE,
            parameters={'x1': start_x, 'y1': start_y, 'x2': end_x, 'y2': end_y},
            points=points
        )
    
    def generate_rectangle_points(self, x1: Union[int, float], y1: Union[int, float],
                                x2: Union[int, float], y2: Union[int, float]) -> ShapeGenerationResult:
        """Generate outline points of a rectangle given two corner points."""
        corner1_x, corner1_y = self.validation_service.validate_coordinate_values(x1, y1)
        corner2_x, corner2_y = self.validation_service.validate_coordinate_values(x2, y2)
        
        min_x = min(corner1_x, corner2_x)
        max_x = max(corner1_x, corner2_x)
        min_y = min(corner1_y, corner2_y)
        max_y = max(corner1_y, corner2_y)
        
        top_edge = self.generate_line_points(min_x, min_y, max_x, min_y).points
        right_edge = self.generate_line_points(max_x, min_y, max_x, max_y).points
        bottom_edge = self.generate_line_points(max_x, max_y, min_x, max_y).points
        left_edge = self.generate_line_points(min_x, max_y, min_x, min_y).points
        
        all_points = top_edge + right_edge + bottom_edge + left_edge
        
        logger.debug("Generated rectangle with %d points", len(all_points))
        
        return ShapeGenerationResult(
            shape_type=ShapeType.RECTANGLE,
            parameters={'x1': corner1_x, 'y1': corner1_y, 'x2': corner2_x, 'y2': corner2_y},
            points=all_points
        )
    
    def generate_circle_points(self, center_x: Union[int, float], center_y: Union[int, float], 
                             radius: Union[int, float], points_count: int = 100) -> ShapeGenerationResult:
        """Generate points for a circle outline."""
        center_x_valid, center_y_valid = self.validation_service.validate_coordinate_values(center_x, center_y)
        radius_valid = self.validation_service.validate_radius_value(radius)
        points_count_valid = self.validation_service.validate_points_count(points_count)
        
        points = []
        for point_index in range(points_count_valid + 1):
            angle_radians = 2 * math.pi * point_index / points_count_valid
            point_x = center_x_valid + radius_valid * math.cos(angle_radians)
            point_y = center_y_valid + radius_valid * math.sin(angle_radians)
            points.append((float(point_x), float(point_y)))
        
        logger.debug("Generated circle with %d points, radius %.2f", len(points), radius_valid)
        
        return ShapeGenerationResult(
            shape_type=ShapeType.CIRCLE,
            parameters={'center_x': center_x_valid, 'center_y': center_y_valid, 'radius': radius_valid, 'points_count': points_count_valid},
            points=points
        )
    
    def generate_triangle_points(self, x1: Union[int, float], y1: Union[int, float],
                               x2: Union[int, float], y2: Union[int, float],
                               x3: Union[int, float], y3: Union[int, float]) -> ShapeGenerationResult:
        """Generate outline points of a triangle given three vertices."""
        vertex1_x, vertex1_y = self.validation_service.validate_coordinate_values(x1, y1)
        vertex2_x, vertex2_y = self.validation_service.validate_coordinate_values(x2, y2)
        vertex3_x, vertex3_y = self.validation_service.validate_coordinate_values(x3, y3)
        
        side1_points = self.generate_line_points(vertex1_x, vertex1_y, vertex2_x, vertex2_y).points
        side2_points = self.generate_line_points(vertex2_x, vertex2_y, vertex3_x, vertex3_y).points
        side3_points = self.generate_line_points(vertex3_x, vertex3_y, vertex1_x, vertex1_y).points
        
        all_points = side1_points + side2_points + side3_points
        
        logger.debug("Generated triangle with %d points", len(all_points))
        
        return ShapeGenerationResult(
            shape_type=ShapeType.TRIANGLE,
            parameters={'x1': vertex1_x, 'y1': vertex1_y, 'x2': vertex2_x, 'y2': vertex2_y, 'x3': vertex3_x, 'y3': vertex3_y},
            points=all_points
        )
    
    def generate_parabola_points(self, coefficient_a: float, coefficient_b: float, coefficient_c: float,
                               x_min: float = -10, x_max: float = 10, points_count: int = 50) -> ShapeGenerationResult:
        """Generate points for the parabola y = a*x^2 + b*x + c."""
        points_count_valid = self.validation_service.validate_points_count(points_count)
        
        if abs(coefficient_a) < 1e-10:
            raise ValidationError("Coefficient 'a' cannot be zero for parabola")
        
        x_values = np.linspace(x_min, x_max, points_count_valid)
        points = []
        
        for x_value in x_values:
            y_value = coefficient_a * x_value**2 + coefficient_b * x_value + coefficient_c
            points.append((float(x_value), float(y_value)))
        
        logger.debug("Generated parabola with %d points", len(points))
        
        return ShapeGenerationResult(
            shape_type=ShapeType.PARABOLA,
            parameters={'a': coefficient_a, 'b': coefficient_b, 'c': coefficient_c, 'x_min': x_min, 'x_max': x_max, 'points_count': points_count_valid},
            points=points
        )


class JSONHistoryStorage:
    """JSON file-based implementation of history storage."""
    
    def __init__(self, file_path: str, validation_service: ValidationService):
        self.file_path = validation_service.validate_file_path_format(file_path)
        self.validation_service = validation_service
        self._ensure_directory_exists()
    
    def save_operation_result(self, result: OperationResult) -> None:
        """Save operation result to JSON file."""
        try:
            existing_history = self.load_operation_history()
            
            result_data = {
                'operation_type': result.operation_type.value,
                'input_expression': result.input_expression,
                'output_result': str(result.output_result),
                'execution_time_ms': result.execution_time_ms,
                'success': result.success,
                'error_message': result.error_message,
                'timestamp': self._get_current_timestamp()
            }
            
            history_data = [self._convert_result_to_dict(r) for r in existing_history]
            history_data.append(result_data)
            
            with open(self.file_path, 'w', encoding='utf-8') as file:
                json.dump(history_data, file, indent=2, ensure_ascii=False)
            
            logger.debug("Operation result saved to history: %s", result.operation_type.value)
        
        except (IOError, OSError) as error:
            raise StorageError(f"Failed to save operation result: {error}") from error
    
    def load_operation_history(self) -> List[OperationResult]:
        """Load complete operation history from JSON file."""
        if not self.file_path.exists():
            return []
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                history_data = json.load(file)
            
            results = []
            for item in history_data:
                try:
                    operation_type = OperationType(item['operation_type'])
                    result = OperationResult(
                        operation_type=operation_type,
                        input_expression=item['input_expression'],
                        output_result=item['output_result'],
                        execution_time_ms=item['execution_time_ms'],
                        success=item['success'],
                        error_message=item.get('error_message')
                    )
                    results.append(result)
                except (KeyError, ValueError) as error:
                    logger.warning("Skipping invalid history item: %s", error)
            
            logger.debug("Loaded %d operation results from history", len(results))
            return results
        
        except (IOError, OSError, json.JSONDecodeError) as error:
            logger.warning("Failed to load operation history: %s", error)
            return []
    
    def clear_operation_history(self) -> None:
        """Clear all operation history from JSON file."""
        try:
            if self.file_path.exists():
                self.file_path.unlink()
            logger.debug("Operation history cleared")
        
        except (IOError, OSError) as error:
            raise StorageError(f"Failed to clear operation history: {error}") from error
    
    def _ensure_directory_exists(self) -> None:
        """Ensure parent directory exists for history file."""
        parent_directory = self.file_path.parent
        
        if not parent_directory.exists():
            try:
                parent_directory.mkdir(parents=True, exist_ok=True)
            except (IOError, OSError) as error:
                raise StorageError(f"Failed to create history directory: {error}") from error
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp as ISO format string."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
    
    def _convert_result_to_dict(self, result: OperationResult) -> Dict[str, Any]:
        """Convert OperationResult to dictionary for JSON serialization."""
        return {
            'operation_type': result.operation_type.value,
            'input_expression': result.input_expression,
            'output_result': str(result.output_result),
            'execution_time_ms': result.execution_time_ms,
            'success': result.success,
            'error_message': result.error_message,
            'timestamp': self._get_current_timestamp()
        }


class TkinterUserInterface:
    """Tkinter-based implementation of user interface."""
    
    def __init__(self):
        self.root_window = tk.Tk()
        self.root_window.withdraw()
    
    def get_operation_type(self) -> Optional[OperationType]:
        """Get operation type from user through dialog."""
        operation_options = [op.value for op in OperationType]
        dialog_text = "Choose operation:\n" + "\n".join(operation_options)
        
        user_input = simpledialog.askstring("Operation Selection", dialog_text)
        
        if not user_input:
            return None
        
        try:
            return OperationType(user_input.lower().strip())
        except ValueError:
            self.display_error_message(f"Invalid operation type: {user_input}")
            return None
    
    def get_expression_input(self) -> Optional[str]:
        """Get mathematical expression from user through dialog."""
        user_input = simpledialog.askstring("Expression Input", "Enter your mathematical expression:")
        
        if not user_input:
            return None
        
        return user_input.strip()
    
    def display_operation_result(self, result: OperationResult) -> None:
        """Display operation result to user through dialog."""
        if result.success:
            title = f"Result - {result.operation_type.value.title()}"
            message = str(result.output_result)
            messagebox.showinfo(title, message)
        else:
            self.display_error_message(result.error_message or "Operation failed")
    
    def display_error_message(self, error_message: str) -> None:
        """Display error message to user through dialog."""
        messagebox.showerror("Error", error_message)


class CalculatorSystemService:
    """Main service coordinating all calculator system components."""
    
    def __init__(self, 
                 configuration: SystemConfiguration,
                 validation_service: ValidationService,
                 operation_processor: OperationProcessor,
                 shape_generator: ShapeGenerator,
                 history_storage: HistoryStorage,
                 user_interface: UserInterface):
        self.configuration = configuration
        self.validation_service = validation_service
        self.operation_processor = operation_processor
        self.shape_generator = shape_generator
        self.history_storage = history_storage
        self.user_interface = user_interface
    
    def execute_operation(self, operation_type: OperationType, expression: str) -> OperationResult:
        """Execute mathematical operation and return result."""
        import time
        
        start_time = time.perf_counter()
        
        try:
            operation_processors = {
                OperationType.SOLVE: self.operation_processor.execute_solve_operation,
                OperationType.SIMPLIFY: self.operation_processor.execute_simplify_operation,
                OperationType.EXPAND: self.operation_processor.execute_expand_operation,
                OperationType.FACTOR: self.operation_processor.execute_factor_operation,
                OperationType.DERIVATIVE: self.operation_processor.execute_derivative_operation,
                OperationType.INTEGRAL: self.operation_processor.execute_integral_operation,
                OperationType.PLOT: lambda expr: self._execute_plot_operation_wrapper(expr)
            }
            
            processor_function = operation_processors.get(operation_type)
            
            if not processor_function:
                raise OperationError(f"Unsupported operation type: {operation_type}")
            
            operation_result = processor_function(expression)
            execution_time = (time.perf_counter() - start_time) * 1000
            
            result = OperationResult(
                operation_type=operation_type,
                input_expression=expression,
                output_result=operation_result,
                execution_time_ms=execution_time,
                success=True
            )
            
            self.history_storage.save_operation_result(result)
            logger.info("Operation completed successfully: %s in %.2fms", operation_type.value, execution_time)
            
            return result
        
        except (ValidationError, OperationError) as error:
            execution_time = (time.perf_counter() - start_time) * 1000
            
            result = OperationResult(
                operation_type=operation_type,
                input_expression=expression,
                output_result=None,
                execution_time_ms=execution_time,
                success=False,
                error_message=str(error)
            )
            
            logger.error("Operation failed: %s - %s", operation_type.value, error)
            return result
    
    def execute_shape_generation(self, shape_type: ShapeType, **parameters) -> ShapeGenerationResult:
        """Execute shape generation and return result."""
        shape_generators = {
            ShapeType.LINE: lambda p: self.shape_generator.generate_line_points(p['x1'], p['y1'], p['x2'], p['y2']),
            ShapeType.RECTANGLE: lambda p: self.shape_generator.generate_rectangle_points(p['x1'], p['y1'], p['x2'], p['y2']),
            ShapeType.CIRCLE: lambda p: self.shape_generator.generate_circle_points(p['center_x'], p['center_y'], p['radius'], p.get('points_count', self.configuration.circle_default_points)),
            ShapeType.TRIANGLE: lambda p: self.shape_generator.generate_triangle_points(p['x1'], p['y1'], p['x2'], p['y2'], p['x3'], p['y3']),
            ShapeType.PARABOLA: lambda p: self.shape_generator.generate_parabola_points(p['a'], p['b'], p['c'], p.get('x_min', -10), p.get('x_max', 10), p.get('points_count', 50))
        }
        
        generator_function = shape_generators.get(shape_type)
        
        if not generator_function:
            raise OperationError(f"Unsupported shape type: {shape_type}")
        
        try:
            result = generator_function(parameters)
            logger.info("Shape generation completed: %s with %d points", shape_type.value, result.point_count)
            return result
        
        except (ValidationError, OperationError) as error:
            logger.error("Shape generation failed: %s - %s", shape_type.value, error)
            raise
    
    def run_interactive_session(self) -> None:
        """Run interactive user session with UI dialogs."""
        if not self.configuration.independent_mode:
            logger.warning("Interactive session requires independent mode")
            return
        
        try:
            operation_type = self.user_interface.get_operation_type()
            
            if not operation_type:
                logger.info("User cancelled operation selection")
                return
            
            expression = self.user_interface.get_expression_input()
            
            if not expression:
                logger.info("User cancelled expression input")
                return
            
            result = self.execute_operation(operation_type, expression)
            self.user_interface.display_operation_result(result)
        
        except Exception as error:
            error_message = f"Unexpected error in interactive session: {error}"
            logger.error(error_message, exc_info=True)
            self.user_interface.display_error_message(error_message)
    
    def get_operation_history(self) -> List[OperationResult]:
        """Get complete operation history."""
        return self.history_storage.load_operation_history()
    
    def clear_operation_history(self) -> None:
        """Clear all operation history."""
        self.history_storage.clear_operation_history()
        logger.info("Operation history cleared")
    
    def _execute_plot_operation_wrapper(self, expression: str) -> str:
        """Wrapper for plot operation to return string result."""
        self.operation_processor.execute_plot_operation(
            expression, 
            self.configuration.plot_x_range, 
            self.configuration.plot_points_count
        )
        return "Plot displayed successfully"


class CalculatorSystemFactory:
    """Factory for creating calculator system instances with dependency injection."""
    
    @staticmethod
    def create_default_system() -> CalculatorSystemService:
        """Create calculator system with default configuration and dependencies."""
        configuration = SystemConfiguration()
        
        validation_service = ValidationService(configuration.validation_level)
        
        operation_processor = OperationProcessor(validation_service)
        
        shape_generator = ShapeGenerator(validation_service)
        
        history_storage = JSONHistoryStorage(configuration.history_file_path, validation_service)
        
        user_interface = TkinterUserInterface()
        
        return CalculatorSystemService(
            configuration=configuration,
            validation_service=validation_service,
            operation_processor=operation_processor,
            shape_generator=shape_generator,
            history_storage=history_storage,
            user_interface=user_interface
        )
    
    @staticmethod
    def create_custom_system(
        configuration: SystemConfiguration,
        history_storage: Optional[HistoryStorage] = None,
        user_interface: Optional[UserInterface] = None
    ) -> CalculatorSystemService:
        """Create calculator system with custom configuration and optional custom dependencies."""
        validation_service = ValidationService(configuration.validation_level)
        
        operation_processor = OperationProcessor(validation_service)
        
        shape_generator = ShapeGenerator(validation_service)
        
        if history_storage is None:
            history_storage = JSONHistoryStorage(configuration.history_file_path, validation_service)
        
        if user_interface is None:
            user_interface = TkinterUserInterface()
        
        return CalculatorSystemService(
            configuration=configuration,
            validation_service=validation_service,
            operation_processor=operation_processor,
            shape_generator=shape_generator,
            history_storage=history_storage,
            user_interface=user_interface
        )


def main() -> None:
    """Initialize and run the calculator system application."""
    try:
        calculator_system = CalculatorSystemFactory.create_default_system()
        calculator_system.run_interactive_session()
    
    except Exception as error:
        logger.error("Failed to start calculator system: %s", error, exc_info=True)
        print(f"Application error: {error}")


if __name__ == '__main__':
    main()