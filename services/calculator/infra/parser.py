import re

def translate_expression(expr: str) -> str:
    """
    Translates user-entered math expression into sympy-compatible syntax.

    Supports:
    - Constants: π, ∞, inf
    - Operators: ^, ÷, •, mod
    - Functions: ln, log₂, abs, floor, ceil, exp, sqrt, sin, cos, tan, etc.
    - Calculus: ∫, ∑, d/dx, integrate, diff
    - Combinatorics: nCr, nPr
    - Lists, matrices, logic
    - Safe implicit multiplication
    """

    # Symbol and function replacements
    replacements = {
        'π': 'pi',
        '∞': 'oo',
        'inf': 'oo',
        '-inf': '-oo',
        '√': 'sqrt',
        '∑': 'Sum',
        '∫': 'integrate',
        '÷': '/',
        '•': '*',
        '^': '**',
        'ln': 'log',
        'mod': '%',
        'abs': 'Abs',
        'floor': 'floor',
        'ceil': 'ceiling',
        'e^': 'exp',
        'd/dx': 'diff',
    }
    expr = re.sub(r'exp\*\(', 'exp(', expr)

    for key, val in replacements.items():
        expr = expr.replace(key, val)

    # Function-specific regex
    expr = re.sub(r'log\s*₂\s*\(\s*(.*?)\s*\)', r'log(\1, 2)', expr)
    expr = re.sub(r'nCr\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)', r'binomial(\1, \2)', expr)
    expr = re.sub(r'nPr\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)', r'factorial(\1)/factorial(\1 - \2)', expr)
    expr = re.sub(r'd/d([a-zA-Z])\s*(.+)', r'diff(\2, \1)', expr)
    expr = re.sub(r'integrate\s+(.*?)\s*d([a-zA-Z])', r'integrate(\1, \2)', expr)

    # List and matrix support
    expr = expr.replace('{', '[').replace('}', ']')

    def convert_matrix(match):
        raw = match.group(1)
        rows = raw.strip().split(';')
        return str([[val.strip() for val in row.strip().split()] for row in rows])
    expr = re.sub(r'\[\s*([\d\w\s;]+)\s*\]', convert_matrix, expr)

    # Implicit multiplication handling
    expr = re.sub(r'(\d)([a-zA-Z\(])', r'\1*\2', expr)
    expr = re.sub(r'([a-zA-Z])(\()', r'\1*\2', expr)
    expr = re.sub(r'(\))(\d|[a-zA-Z\(])', r'\1*\2', expr)

    # Final cleanup: fix function calls (no multiplication symbol before parentheses)
    for fn in ['sqrt', 'sin', 'cos', 'tan', 'cot', 'sec', 'csc', 'log', 'Abs', 'floor', 'ceiling', 'exp']:
        expr = re.sub(rf'{fn}\*\(', f'{fn}(', expr)

    # Auto-close unmatched parentheses
    open_count = expr.count('(')
    close_count = expr.count(')')
    expr += ')' * max(0, open_count - close_count)

    return expr
