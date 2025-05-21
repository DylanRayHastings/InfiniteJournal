import tkinter as tk
from tkinter import simpledialog, messagebox
from dataclasses import dataclass
from icecream import ic
import sympy as sp
import matplotlib.pyplot as plt
import numpy as np
import re

# CONFIGURATION
DEBUG = True
INDEPENDENT_MODE = True

if DEBUG:
    ic.configureOutput(prefix='[calculator] ')
    ic("Debugging Enabled")


@dataclass
class Point:
    x: int
    y: int
    width: int = 1


def translate_expression(expr: str):
    replacements = {
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

    # Symbol replacements
    for key, val in replacements.items():
        expr = expr.replace(key, val)

    # Insert * where needed
    expr = re.sub(r'(\d)([a-zA-Z])', r'\1*\2', expr)              # 2x → 2*x
    expr = re.sub(r'([a-zA-Z])(\()', r'\1*\2', expr)              # x( → x*(
    expr = re.sub(r'(\))([a-zA-Z0-9])', r'\1*\2', expr)           # )x → )*x
    expr = re.sub(r'(\d)(\()', r'\1*\2', expr)                    # 2(x) → 2*(x)
    return expr


def show_popup(message: str):
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("Math Result", message)


def plot_expression(expr: str):
    x = sp.Symbol('x')
    try:
        func = sp.sympify(expr)
        lam = sp.lambdify(x, func, 'numpy')
        x_vals = np.linspace(-10, 10, 500)
        y_vals = lam(x_vals)
        plt.plot(x_vals, y_vals, label=f"y = {expr}")
        plt.axhline(0, color='black', lw=0.5)
        plt.axvline(0, color='black', lw=0.5)
        plt.grid(True)
        plt.legend()
        plt.title("Plot")
        plt.show()
    except Exception as e:
        if DEBUG: ic(e)
        show_popup(f"Plot error: {e}")


def solve_equation(expr: str):
    x = sp.Symbol('x')
    try:
        lhs, rhs = expr.split('=')
        eq = sp.Eq(sp.sympify(lhs), sp.sympify(rhs))
        sol = sp.solve(eq, x)
        if DEBUG: ic(eq, sol)
        show_popup(f"{eq}\n\nSolutions: {sol}")
    except Exception as e:
        if DEBUG: ic(e)
        show_popup(f"Solve error: {e}")


def simplify_expression(expr: str):
    try:
        simplified = sp.simplify(expr)
        show_popup(f"Simplified:\n{simplified}")
    except Exception as e:
        show_popup(f"Simplify error: {e}")


def expand_expression(expr: str):
    try:
        expanded = sp.expand(expr)
        show_popup(f"Expanded:\n{expanded}")
    except Exception as e:
        show_popup(f"Expand error: {e}")


def factor_expression(expr: str):
    try:
        factored = sp.factor(expr)
        show_popup(f"Factored:\n{factored}")
    except Exception as e:
        show_popup(f"Factor error: {e}")


def differentiate_expression(expr: str):
    x = sp.Symbol('x')
    try:
        result = sp.diff(expr, x)
        show_popup(f"d/dx of {expr} = {result}")
    except Exception as e:
        show_popup(f"Derivative error: {e}")


def integrate_expression(expr: str):
    x = sp.Symbol('x')
    try:
        result = sp.integrate(expr, x)
        show_popup(f"∫ {expr} dx = {result} + C")
    except Exception as e:
        show_popup(f"Integral error: {e}")


def run_calculator():
    root = tk.Tk()
    root.withdraw()

    mode = simpledialog.askstring("Mode", "Choose mode:\nsolve, plot, simplify, expand, factor, derivative, integral")
    if not mode:
        return

    raw_expr = simpledialog.askstring("Expression", "Enter your expression:")
    if not raw_expr:
        return

    expr = translate_expression(raw_expr)
    if DEBUG: ic(expr)

    if mode == "solve":
        solve_equation(expr)
    elif mode == "plot":
        plot_expression(expr)
    elif mode == "simplify":
        simplify_expression(expr)
    elif mode == "expand":
        expand_expression(expr)
    elif mode == "factor":
        factor_expression(expr)
    elif mode == "derivative":
        differentiate_expression(expr)
    elif mode == "integral":
        integrate_expression(expr)
    else:
        show_popup("Invalid mode.")


if __name__ == "__main__":
    if INDEPENDENT_MODE:
        run_calculator()
