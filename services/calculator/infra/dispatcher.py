from .parser import translate_expression
from . import algebra
from . import calculus
from . import plotter


def dispatch(mode: str, raw_expr: str, variable: str = 'x') -> str:
    """
    Main dispatcher for math operations.

    Args:
        mode (str): Operation type ('solve', 'plot', 'derivative', etc.).
        raw_expr (str): Input expression (can contain symbols like π, ∫, etc.).
        variable (str): Variable in expression (default is 'x').

    Returns:
        str: Result or status message.
    """
    try:
        if mode == 'def_integral':
            # Handle: "expression from a to b"
            raw = raw_expr.lower()
            if "from" in raw and "to" in raw:
                expr_part = raw.split("from")[0].strip()
                bounds = raw.split("from")[1].split("to")
                if len(bounds) == 2:
                    lower = float(bounds[0].strip())
                    upper = float(bounds[1].strip())
                    expr_clean = translate_expression(expr_part)
                    return str(calculus.definite_integral(expr_clean, variable, lower, upper))
            return "Format error: Use 'expression from a to b'"

        expr = translate_expression(raw_expr)

        if mode == 'solve':
            return str(algebra.solve(expr, variable))
        elif mode == 'simplify':
            return str(algebra.simplify(expr))
        elif mode == 'expand':
            return str(algebra.expand(expr))
        elif mode == 'factor':
            return str(algebra.factor(expr))
        elif mode == 'derivative':
            return str(calculus.derivative(expr, variable))
        elif mode == 'second_derivative':
            return str(calculus.second_derivative(expr, variable))
        elif mode == 'integral':
            return str(calculus.integral(expr, variable))
        elif mode == 'plot':
            plotter.plot(expr)
            return "Graph displayed"
        else:
            return f"Unknown mode: {mode}"

    except Exception as e:
        return f"Error: {e}"
