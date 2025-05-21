"""
Modular mathematical calculator with logging.

Supports algebra, calculus, trigonometry, and plotting functionalities.
"""

from pathlib import Path
from datetime import datetime
from icecream import ic

import sympy as sp

import algebra
import calculus
import trig
import plotter
from parser import translate_expression

LOG_FOLDER = Path(__file__).parent / "calculator_logs"
LOG_FOLDER.mkdir(exist_ok=True)

# --- Logging Functions ---

def rotate_logs(directory: Path, keep: int = 5):
    """Removes old log files, keeping only the specified number."""
    logs = sorted(directory.glob("log_*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old_log in logs[keep:]:
        old_log.unlink()


def create_log_file() -> Path:
    """Creates and initializes a new log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_path = LOG_FOLDER / f"log_{timestamp}.txt"
    with log_path.open("w") as f:
        f.write(f"Calculator log started at {timestamp}\n")
    rotate_logs(LOG_FOLDER)
    return log_path


LOG_FILE_PATH = create_log_file()


def log(text: str):
    """Appends text to the current log file."""
    with LOG_FILE_PATH.open("a") as f:
        f.write(text + "\n")

# --- Calculation Handlers ---

def handle_definite_integral(expression: str, lower: str, upper: str) -> str:
    lower_bound = sp.sympify(lower)
    upper_bound = sp.sympify(upper)
    result = calculus.definite_integral(expression, 'x', lower_bound, upper_bound)
    ic(result)
    log(f"Definite Integral Result: {result}")
    return f"Definite Integral: {result}"


def handle_trigonometry(expression: str) -> str:
    simplified = trig.simplify_trig(expression)
    expanded = trig.expand_trig(expression)
    rewritten = trig.rewrite_trig(expression)
    ic(simplified, expanded, rewritten)
    result = (
        f"Trigonometric Simplified: {simplified}\n"
        f"Trigonometric Expanded: {expanded}\n"
        f"Trigonometric Rewritten (exp form): {rewritten}"
    )
    log(f"Trigonometric Result:\n{result}")
    return result


def handle_generic_expression(expression: str) -> str:
    simplified = algebra.simplify_expression(expression)
    expanded = algebra.expand(expression)
    factored = algebra.factor(expression)
    evaluated = algebra.evaluate(expression)
    first_derivative = calculus.derivative(expression)
    second_derivative = calculus.second_derivative(expression)
    indefinite_integral = calculus.integral(expression)

    ic(simplified, expanded, factored, evaluated, first_derivative, second_derivative, indefinite_integral)

    result = (
        f"Simplified: {simplified}\nExpanded: {expanded}\nFactored: {factored}\n"
        f"Evaluated: {evaluated}\nFirst Derivative: {first_derivative}\n"
        f"Second Derivative: {second_derivative}\nIndefinite Integral: {indefinite_integral}"
    )

    log(f"Generic Expression Result:\n{result}")
    return result


def handle_derivative(expression: str) -> str:
    result = calculus.derivative(expression)
    ic(result)
    log(f"Derivative Result: {result}")
    return f"First Derivative: {result}"


def handle_second_derivative(expression: str) -> str:
    result = calculus.second_derivative(expression)
    ic(result)
    log(f"Second Derivative Result: {result}")
    return f"Second Derivative: {result}"


def handle_integral(expression: str) -> str:
    result = calculus.integral(expression)
    ic(result)
    log(f"Integral Result: {result}")
    return f"Indefinite Integral: {result}"

# --- Startup Test Runner ---

def run_startup_tests(expressions):
    print("Running startup tests...\n")
    passed_tests = []
    failed_tests = []

    for expr in expressions:
        try:
            print(f"PASS: Testing: {expr}")
            if expr.startswith("plot "):
                plotter.plot(translate_expression(expr[5:].strip()))
                print("    Graph displayed successfully.\n")
                log(f"PASS >>> {expr}\nGraph displayed successfully.")
            else:
                result = analyze_expression(expr)
                print(f"    {result}\n")
                log(f"PASS >>> {expr}\nResult: {result}")
            passed_tests.append(expr)
        except Exception as e:
            print(f"FAIL: {expr} | Error: {e}\n")
            log(f"FAIL >>> {expr} | Error: {e}")
            failed_tests.append((expr, str(e)))

    total = len(expressions)
    passed = len(passed_tests)
    failed = len(failed_tests)

    print("Startup Tests Summary:")
    print(f"Total: {total}, Passed: {passed}, Failed: {failed}")
    if failed_tests:
        print("\nFailed expressions:")
        for expr, error in failed_tests:
            print(f" - {expr}: {error}")
    print("\n--- End of startup tests ---\n")

# --- Main Expression Analysis ---

def analyze_expression(user_input: str) -> str:
    ic(user_input)
    log(f">>> {user_input}")

    try:
        lower_input = user_input.lower().strip()

        if lower_input.startswith("second_derivative "):
            inner = translate_expression(user_input[len("second_derivative "):].strip())
            return handle_second_derivative(inner)

        if lower_input.startswith("derivative "):
            inner = translate_expression(user_input[len("derivative "):].strip())
            return handle_derivative(inner)

        if lower_input.startswith("factor(") and user_input.endswith(")"):
            inner = translate_expression(user_input[7:-1].strip())
            result = algebra.factor(inner)
            log(f"Factored Result: {result}")
            return f"Factored: {result}"

        if lower_input.startswith("solve "):
            expr = translate_expression(user_input[6:].strip())
            result = algebra.solve_equation(expr)
            log(f"Solved Result: {result}")
            return f"Solved: {result}"

        if lower_input.startswith("simplify "):
            expr = translate_expression(user_input[9:].strip())
            result = algebra.simplify_expression(expr)
            log(f"Simplified Result: {result}")
            return f"Simplified: {result}"

        if lower_input.startswith("expand "):
            expr = translate_expression(user_input[7:].strip())
            result = algebra.expand(expr)
            log(f"Expanded Result: {result}")
            return f"Expanded: {result}"

        if lower_input.startswith("integral") and "from" in user_input and "to" in user_input:
            integral_part = user_input[8:].strip()
            expr, bounds_part = integral_part.split("from")
            lower_bound, upper_bound = bounds_part.split("to")

            expr = translate_expression(expr.strip())
            lower_bound = lower_bound.strip().replace('inf', 'oo').replace('-inf', '-oo')
            upper_bound = upper_bound.strip().replace('inf', 'oo').replace('-inf', '-oo')

            return handle_definite_integral(expr, lower_bound, upper_bound)

        if '=' in user_input:
            result = algebra.solve_equation(translate_expression(user_input))
            log(f"Solved Equation Result: {result}")
            return f"Solved Equation: {result}"

        if any(trig_func in user_input for trig_func in ['sin', 'cos', 'tan', 'cot', 'sec', 'csc']):
            return handle_trigonometry(translate_expression(user_input))

        return handle_generic_expression(translate_expression(user_input))

    except Exception as e:
        error_message = f"Error: {e}"
        ic(e)
        log(error_message)
        return error_message


if __name__ == "__main__":
    startup_test_expressions = [
        "2x + 3 = 7",
        "(x + 1)^2",
        "integral x^2 from 0 to 3",
        "plot x^2 - 4x + 4",
        "integral exp(-x^2) from -oo to oo",
        "second_derivative sin(x^2)",
        "derivative ln(x^2 + sqrt(x))",
        "factor(x^5 - x^4 + x^3 - x^2 + x - 1)",
        "simplify (sin(x)**2 + cos(x)**2)**2",
        "solve exp(x) - 3*x = 0"
    ]

    run_startup_tests(startup_test_expressions)

    print("Calculator ready.")
