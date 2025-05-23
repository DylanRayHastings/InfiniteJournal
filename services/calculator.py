#!/usr/bin/env python3
"""
Calculator application with GUI and shape generators.
Fixed to work properly with the journal system.
"""

import os
import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import sympy as sp
import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import simpledialog, messagebox

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Raised when configuration is invalid."""
    pass


@dataclass
class Config:
    """Configuration for the calculator application."""
    debug: bool = True
    independent_mode: bool = True
    history_file: str = 'history.json'

    def __post_init__(self):
        """Validate configuration and initialize logging."""
        self._validate_history_file()
        log_level = logging.DEBUG if self.debug else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='[%(asctime)s] [%(levelname)s] %(message)s'
        )
        logger.debug("Calculator configuration initialized: %s", self)

    def _validate_history_file(self) -> None:
        """Ensure the history directory exists or can be created."""
        directory = os.path.dirname(self.history_file) or '.'
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)


class History:
    """Manages persistence of calculation history to a JSON file."""
    
    def __init__(self, path: str):
        """Initialize history manager."""
        self.path = path
        self.records: List[Dict[str, Any]] = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        """Load history records from file, returning empty list on error."""
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError):
            return []

    def add(self, mode: str, expression: str, result: Any) -> None:
        """Add a record to history and save to file."""
        record = {'mode': mode, 'expression': expression, 'result': str(result)}
        self.records.append(record)
        self._save()

    def _save(self) -> None:
        """Save current records to the history file."""
        try:
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(self.records, f, indent=2)
        except IOError as e:
            logger.error("Failed to save history: %s", e)


class Calculator:
    """Performs mathematical operations using Sympy."""

    TRANSLATIONS = {
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

    @staticmethod
    def translate(expr: str) -> str:
        """Translate common mathematical symbols to Sympy syntax."""
        for key, val in Calculator.TRANSLATIONS.items():
            expr = expr.replace(key, val)
        expr = re.sub(r'(\d)([a-zA-Z])', r'\1*\2', expr)
        expr = re.sub(r'([a-zA-Z])(\()', r'\1*\2', expr)
        expr = re.sub(r'(\))([a-zA-Z0-9])', r'\1*\2', expr)
        expr = re.sub(r'(\d)(\()', r'\1*\2', expr)
        return expr.strip()

    @staticmethod
    def solve_equation(expr: str) -> Tuple[sp.Eq, List[Any]]:
        """Solve an equation of the form 'lhs=rhs'."""
        if '=' not in expr:
            raise ValueError("Expression must contain '=' for solving.")
        lhs, rhs = expr.split('=', 1)
        eq = sp.Eq(sp.sympify(lhs), sp.sympify(rhs))
        solutions = sp.solve(eq, sp.Symbol('x'))
        return eq, solutions

    @staticmethod
    def simplify_expression(expr: str) -> Any:
        """Simplify a mathematical expression."""
        return sp.simplify(sp.sympify(expr))

    @staticmethod
    def expand_expression(expr: str) -> Any:
        """Expand a mathematical expression."""
        return sp.expand(sp.sympify(expr))

    @staticmethod
    def factor_expression(expr: str) -> Any:
        """Factor a mathematical expression."""
        return sp.factor(sp.sympify(expr))

    @staticmethod
    def differentiate_expression(expr: str) -> Any:
        """Differentiate an expression with respect to x."""
        return sp.diff(expr, sp.Symbol('x'))

    @staticmethod
    def integrate_expression(expr: str) -> Any:
        """Integrate an expression with respect to x."""
        return sp.integrate(expr, sp.Symbol('x'))


class CalculatorUI:
    """Handles user interaction for the calculator via Tkinter dialogs."""

    def __init__(self, calculator: Calculator, history: History):
        """Initialize the UI with a Calculator and History manager."""
        self.calculator = calculator
        self.history = history
        self._modes = {
            'solve': self._do_solve,
            'simplify': self._do_simplify,
            'expand': self._do_expand,
            'factor': self._do_factor,
            'derivative': self._do_derivative,
            'integral': self._do_integral,
            'plot': self._do_plot,
        }

    def run(self) -> None:
        """Run the calculator UI loop once."""
        root = tk.Tk()
        root.withdraw()
        mode = simpledialog.askstring(
            "Mode", "Choose mode:\n" + "\n".join(self._modes.keys())
        )
        if not mode:
            return
        raw_expr = simpledialog.askstring("Expression", "Enter your expression:")
        if not raw_expr:
            return
        expr = self.calculator.translate(raw_expr)
        logger.debug("Translated expression: %s", expr)
        action = self._modes.get(mode.lower())
        if not action:
            messagebox.showerror("Error", f"Invalid mode: {mode}")
            return
        try:
            result = action(expr)
            if mode != 'plot':
                messagebox.showinfo("Result", str(result))
            self.history.add(mode, raw_expr, result or 'plot displayed')
        except Exception as e:
            logger.error("Error in mode '%s': %s", mode, e, exc_info=True)
            messagebox.showerror("Error", str(e))

    def _do_solve(self, expr: str) -> str:
        eq, solutions = self.calculator.solve_equation(expr)
        return f"{eq}\nSolutions: {solutions}"

    def _do_simplify(self, expr: str) -> str:
        simplified = self.calculator.simplify_expression(expr)
        return f"Simplified: {simplified}"

    def _do_expand(self, expr: str) -> str:
        expanded = self.calculator.expand_expression(expr)
        return f"Expanded: {expanded}"

    def _do_factor(self, expr: str) -> str:
        factored = self.calculator.factor_expression(expr)
        return f"Factored: {factored}"

    def _do_derivative(self, expr: str) -> str:
        derivative = self.calculator.differentiate_expression(expr)
        return f"d/dx {expr} = {derivative}"

    def _do_integral(self, expr: str) -> str:
        integral = self.calculator.integrate_expression(expr)
        return f"∫ {expr} dx = {integral} + C"

    def _do_plot(self, expr: str) -> None:
        x = sp.Symbol('x')
        func = sp.sympify(expr)
        lam = sp.lambdify(x, func, 'numpy')
        x_vals = np.linspace(-10, 10, 500)
        y_vals = lam(x_vals)
        plt.figure()
        plt.plot(x_vals, y_vals, label=f"y = {expr}")
        plt.axhline(0, linewidth=0.5)
        plt.axvline(0, linewidth=0.5)
        plt.grid(True)
        plt.legend()
        plt.title("Plot")
        plt.show()


# Shape generators for InfiniteJournal compatibility

def get_line(x1: int, y1: int, x2: int, y2: int) -> List[Tuple[float, float]]:
    """
    Generate interpolated points between two coordinates.

    Args:
        x1: Start x-coordinate.
        y1: Start y-coordinate.
        x2: End x-coordinate.
        y2: End y-coordinate.

    Returns:
        List of (x, y) tuples.
    """
    points: List[Tuple[float, float]] = []
    dx = x2 - x1
    dy = y2 - y1
    steps = max(abs(dx), abs(dy), 1)
    
    for i in range(steps + 1):
        t = i / steps if steps > 0 else 0
        x = x1 + dx * t
        y = y1 + dy * t
        points.append((x, y))
    
    logger.debug("Generated line with %d points from (%d,%d) to (%d,%d)", 
                len(points), x1, y1, x2, y2)
    return points


def get_triangle(x1: int, y1: int, x2: int, y2: int, x3: int, y3: int) -> List[Tuple[float, float]]:
    """
    Generate outline points of a triangle given three vertices.

    Args:
        x1, y1: First vertex.
        x2, y2: Second vertex.
        x3, y3: Third vertex.

    Returns:
        List of points outlining the triangle.
    """
    points = []
    points.extend(get_line(x1, y1, x2, y2))
    points.extend(get_line(x2, y2, x3, y3))
    points.extend(get_line(x3, y3, x1, y1))
    
    logger.debug("Generated triangle with %d points", len(points))
    return points


def get_parabola(
    a: float, b: float, c: float,
    x_min: float = -10, x_max: float = 10, num: int = 100
) -> List[Tuple[float, float]]:
    """
    Generate points for the parabola y = a*x^2 + b*x + c.

    Args:
        a, b, c: Parabola coefficients.
        x_min: Minimum x-value.
        x_max: Maximum x-value.
        num: Number of points.

    Returns:
        List of (x, y) tuples.
    """
    if num <= 0:
        num = 100
        
    xs = np.linspace(x_min, x_max, num)
    points = [(float(x), float(a * x**2 + b * x + c)) for x in xs]
    
    logger.debug("Generated parabola with %d points", len(points))
    return points


def main() -> None:
    """Initialize and run the calculator application."""
    config = Config()
    if config.independent_mode:
        history = History(config.history_file)
        calculator = Calculator()
        ui = CalculatorUI(calculator, history)
        ui.run()


if __name__ == '__main__':
    main()