import sympy as sp

def derivative(expression: str, variable: str = 'x'):
    """
    Computes the derivative of an expression with respect to a variable.

    Args:
        expression (str): The expression to differentiate.
        variable (str): The variable to differentiate with respect to.

    Returns:
        sympy.Basic: The resulting derivative.
    """
    var = sp.Symbol(variable)
    expr = sp.sympify(expression)
    return sp.diff(expr, var)


def integral(expression: str, variable: str = 'x'):
    """
    Computes the indefinite integral of an expression with respect to a variable.

    Args:
        expression (str): The expression to integrate.
        variable (str): The variable to integrate with respect to.

    Returns:
        sympy.Basic: The resulting integral.
    """
    var = sp.Symbol(variable)
    expr = sp.sympify(expression)
    return sp.integrate(expr, var)


def second_derivative(expression: str, variable: str = 'x'):
    """
    Computes the second derivative of an expression.

    Args:
        expression (str): The expression to differentiate twice.
        variable (str): The variable to differentiate with respect to.

    Returns:
        sympy.Basic: The second derivative.
    """
    var = sp.Symbol(variable)
    expr = sp.sympify(expression)
    return sp.diff(expr, var, 2)


def definite_integral(expression: str, variable: str = 'x', lower=0, upper=1):
    """
    Computes the definite integral from lower to upper bound.

    Args:
        expression (str): The expression to integrate.
        variable (str): The variable of integration.
        lower (float): Lower limit.
        upper (float): Upper limit.

    Returns:
        sympy.Basic: The evaluated integral.
    """
    var = sp.Symbol(variable)
    expr = sp.sympify(expression)
    return sp.integrate(expr, (var, lower, upper))
