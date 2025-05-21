import sympy as sp


def solve(equation: str, variable: str = 'x'):
    """
    Solves an algebraic equation for the given variable.

    Args:
        equation (str): The equation string, e.g. '2*x + 3 = 7'
        variable (str): Variable to solve for (default 'x')

    Returns:
        list: List of solutions.
    """
    if '=' not in equation:
        raise ValueError("Equation must contain '=' sign")

    lhs_str, rhs_str = equation.split('=')
    lhs = sp.sympify(lhs_str)
    rhs = sp.sympify(rhs_str)
    var = sp.Symbol(variable)
    return sp.solve(sp.Eq(lhs, rhs), var)


def simplify(expression: str):
    """
    Simplifies an algebraic expression.

    Args:
        expression (str): Any algebraic expression string.

    Returns:
        sympy.Basic: Simplified expression.
    """
    return sp.simplify(sp.sympify(expression))


def expand(expression: str):
    """
    Expands a factored expression.

    Args:
        expression (str): Expression to expand.

    Returns:
        sympy.Basic: Expanded form.
    """
    return sp.expand(sp.sympify(expression))


def factor(expression: str):
    """
    Factors a polynomial or expression.

    Args:
        expression (str): Expression to factor.

    Returns:
        sympy.Basic: Factored form.
    """
    return sp.factor(sp.sympify(expression))
