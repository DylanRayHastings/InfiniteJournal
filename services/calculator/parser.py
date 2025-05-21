import re

def translate_expression(expr: str) -> str:
    """
    Translates human-friendly math symbols into sympy-compatible syntax.

    Args:
        expr (str): Raw user-entered expression.

    Returns:
        str: Transformed expression for sympy parsing.
    """
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

    # Apply symbolic replacements
    for key, val in replacements.items():
        expr = expr.replace(key, val)

    # Add implicit multiplication where needed
    expr = re.sub(r'(\d)([a-zA-Z])', r'\1*\2', expr)       # 2x → 2*x
    expr = re.sub(r'([a-zA-Z])(\()', r'\1*\2', expr)       # x( → x*(
    expr = re.sub(r'(\))([a-zA-Z0-9])', r'\1*\2', expr)    # )x or )2 → )*x or )*2
    expr = re.sub(r'(\d)(\()', r'\1*\2', expr)             # 2(x) → 2*(x)

    return expr
