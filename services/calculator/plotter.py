import matplotlib.pyplot as plt
import numpy as np
import sympy as sp


def plot(expression: str, variable: str = 'x', x_range=(-10, 10)):
    """
    Plots a symbolic expression over a specified x range.

    Args:
        expression (str): Expression to plot (e.g. 'x**2 + 2*x + 1').
        variable (str): Variable to plot against (default 'x').
        x_range (tuple): (min, max) range for the x-axis.

    Returns:
        None (displays a matplotlib window).
    """
    try:
        var = sp.Symbol(variable)
        expr = sp.sympify(expression)
        func = sp.lambdify(var, expr, 'numpy')

        x_vals = np.linspace(x_range[0], x_range[1], 500)
        y_vals = func(x_vals)

        plt.plot(x_vals, y_vals, label=f"${sp.latex(expr)}$")
        plt.axhline(0, color='black', linewidth=0.5)
        plt.axvline(0, color='black', linewidth=0.5)
        plt.title(f"Plot of: {expression}")
        plt.xlabel(variable)
        plt.ylabel("f({})".format(variable))
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        plt.show()

    except Exception as e:
        raise RuntimeError(f"Failed to plot expression: {e}")
