import re
import sympy as symbolic_math
from icecream import ic

from parser import translate_expression

import algebra
import calculus
import trig
import plotter

from algebra import (
    solve,
    simplify,
    expand,
    factor
)
from calculus import (
    definite_integral,
    derivative,
    second_derivative as compute_second_derivative,
    integral
)
from trig import (
    simplify_trig,
    expand_trig,
    rewrite_trig
)


def analyze_and_solve_expression(user_input_expression: str) -> str:
    """
    Analyzes the input expression and performs the most appropriate mathematical operation(s).

    Args:
        user_input_expression (str): Raw user input as a string.

    Returns:
        str: The result or results of mathematical operations.
    """
    ic(user_input_expression)
    cleaned_expression = translate_expression(user_input_expression)
    ic(cleaned_expression)

    try:
        # If equation with "="
        if '=' in cleaned_expression:
            result = solve(cleaned_expression)
            ic(result)
            return f"Solved Equation: {result}"

        # Definite integrals: "integral x^2 from 0 to 2"
        if "from" in cleaned_expression and "to" in cleaned_expression:
            without_keyword = cleaned_expression.lower().replace("integral", "")
            parts = without_keyword.split("from")
            if len(parts) == 2:
                integral_expression = translate_expression(parts[0].strip())
                bounds = parts[1].split("to")
                if len(bounds) == 2:
                    lower_bound = float(bounds[0].strip())
                    upper_bound = float(bounds[1].strip())
                    result = definite_integral(integral_expression, 'x', lower_bound, upper_bound)
                    ic(result)
                    return f"Definite Integral: {result}"

        # Trigonometric expressions
        if any(func in cleaned_expression for func in ["sin", "cos", "tan", "cot", "sec", "csc"]):
            translated = translate_expression(user_input_expression)
            simplified = simplify_trig(translated)
            expanded = expand_trig(translated)
            rewritten = rewrite_trig(translated)
            ic(simplified, expanded, rewritten)
            return (
                f"Trigonometric Simplified: {simplified}\n"
                f"Trigonometric Expanded: {expanded}\n"
                f"Trigonometric Rewritten (exp form): {rewritten}"
            )

        # Generic symbolic math
        simplified_result = simplify(cleaned_expression)
        expanded_result = expand(cleaned_expression)
        factored_result = factor(cleaned_expression)
        evaluated_result = algebra.evaluate(cleaned_expression)

        first_derivative = derivative(cleaned_expression)
        second_derivative_result = compute_second_derivative(cleaned_expression)
        indefinite_integral = integral(cleaned_expression)

        ic(simplified_result, expanded_result, factored_result, evaluated_result)
        ic(first_derivative, second_derivative_result, indefinite_integral)

        return (
            f"Simplified: {simplified_result}\n"
            f"Expanded: {expanded_result}\n"
            f"Factored: {factored_result}\n"
            f"Evaluated: {evaluated_result}\n"
            f"First Derivative: {first_derivative}\n"
            f"Second Derivative: {second_derivative_result}\n"
            f"Indefinite Integral: {indefinite_integral}"
        )

    except Exception as error:
        ic(error)
        return f"Error during analysis: {error}"


def display_user_instructions():
    """
    Prints usage instructions for the user.
    """
    print("\nUsage Instructions:")
    print(" - Type any mathematical expression or equation.")
    print(" - Examples:")
    print("     2x + 3 = 7                     → Solves equation")
    print("     (x + 1)^2                     → Algebra operations (simplify, expand, etc.)")
    print("     sin(x)^2 + cos(x)^2          → Trigonometric identities")
    print("     integral x^2 from 0 to 2     → Definite integral")
    print("     plot x^2 + 2x - 1            → Graph the expression")
    print(" - Type 'quit' to exit.\n")


def load_and_process_example_file(file_path: str):
    """
    Loads and evaluates expressions from a file, one per line.

    Args:
        file_path (str): Path to the text file with expressions.
    """
    try:
        with open(file_path, 'r') as file:
            print(f"\nLoaded expressions from {file_path}:\n")
            for line in file:
                expression = line.strip()
                if not expression:
                    continue
                print(f">>> {expression}")
                if expression.lower().startswith("plot "):
                    plotter.plot(translate_expression(expression[5:]))
                    print("Graph has been displayed.")
                else:
                    result = analyze_and_solve_expression(expression)
                    print(result)
                print()
    except Exception as file_error:
        ic(file_error)
        print(f"Could not load examples from file: {file_error}")


def launch_calculator(example_file_path: str = "services/calculator/calculator_examples.txt"):
    """
    Launches the interactive or batch calculator.

    Args:
        example_file_path (str): Optional path to a file with predefined expressions.
    """
    print("Mathematical Expression Analyzer and Calculator")
    print("Type 'help' for instructions or 'quit' to exit.\n")

    if example_file_path:
        load_and_process_example_file(example_file_path)

    while True:
        user_input = input("Enter expression: ").strip()

        if not user_input:
            continue

        if user_input.lower() in ['quit', 'exit']:
            print("Exiting the calculator. Goodbye.")
            break

        if user_input.lower() == 'help':
            display_user_instructions()
            continue

        try:
            if user_input.lower().startswith("plot "):
                expression_to_plot = user_input[5:]
                plotter.plot(translate_expression(expression_to_plot))
                print("Graph has been displayed.")
            else:
                result = analyze_and_solve_expression(user_input)
                print(result)
        except Exception as general_error:
            ic(general_error)
            print(f"An error occurred: {general_error}")


if __name__ == "__main__":
    launch_calculator()
