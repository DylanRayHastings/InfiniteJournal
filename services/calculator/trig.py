import sympy as sp


def simplify_trig(expression: str):
    """
    Simplifies trigonometric expressions using identities.

    Args:
        expression (str): Expression to simplify.

    Returns:
        sympy.Basic: Simplified result.
    """
    expr = sp.sympify(expression)
    return sp.trigsimp(expr)


def expand_trig(expression: str):
    """
    Expands trigonometric identities, like sin(a + b).

    Args:
        expression (str): Expression to expand.

    Returns:
        sympy.Basic: Expanded form.
    """
    expr = sp.sympify(expression)
    return sp.expand_trig(expr)


def rewrite_trig(expression: str, target='exp'):
    """
    Rewrites trig functions in terms of another form (e.g., exponential).

    Args:
        expression (str): Expression to rewrite.
        target (str): One of 'exp', 'sin', 'cos', 'tan', 'cot' etc.

    Returns:
        sympy.Basic: Rewritten form.
    """
    expr = sp.sympify(expression)
    return expr.rewrite(target)


def eval_trig(expression: str, degree_mode: bool = False):
    """
    Numerically evaluates a trig expression.

    Args:
        expression (str): Expression to evaluate.
        degree_mode (bool): If True, interprets angles in degrees.

    Returns:
        float: Evaluated result.
    """
    expr = sp.sympify(expression)
    if degree_mode:
        expr = expr.subs({sp.Symbol('x'): sp.rad(sp.Symbol('x'))})
    return expr.evalf()
