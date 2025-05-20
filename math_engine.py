import numpy as np
import math
from config import FPS

EPSILON = 1e-3

class MathEngine:
    """Numeric evaluation and differentiation of expressions."""
    def __init__(self):
        self.functions = []  # list[(expr_str, func_callable, color)]

    def register(self, expr_str, color=(0,255,0)):
        func = lambda x, expr=expr_str: eval(expr, {'x':x, 'math':math, 'np':np})
        deriv = lambda x, f=func: (f(x+EPSILON) - f(x-EPSILON)) / (2*EPSILON)
        self.functions.append((expr_str, func, color))
        self.functions.append((expr_str+"'", deriv, (255,255,0)))