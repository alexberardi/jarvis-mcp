"""Safe math expression evaluator.

Uses Python's AST to parse and evaluate math expressions with a strict
whitelist of allowed operations. No arbitrary code execution is possible.
"""

import ast
import math
import operator
from typing import Union

# Allowed binary operators
_BINARY_OPS: dict[type, object] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

# Allowed unary operators
_UNARY_OPS: dict[type, object] = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Allowed functions (name -> callable)
_SAFE_FUNCTIONS: dict[str, object] = {
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
    "ceil": math.ceil,
    "floor": math.floor,
    "log": math.log,
    "log10": math.log10,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
}

# Allowed constants (name -> value)
_SAFE_CONSTANTS: dict[str, float] = {
    "pi": math.pi,
    "e": math.e,
}

# Forbidden keywords in the raw expression string
_FORBIDDEN_KEYWORDS: set[str] = {
    "import", "__import__", "eval", "exec", "compile",
    "open", "getattr", "setattr", "delattr",
    "__builtins__", "__class__", "__subclasses__",
}

NumericResult = Union[int, float]


def evaluate_expression(expression: str) -> NumericResult:
    """Safely evaluate a math expression.

    Args:
        expression: Math expression string (e.g., "2 + 3", "sqrt(144)", "pi * 2")

    Returns:
        Numeric result of the expression.

    Raises:
        ValueError: If the expression is invalid, unsafe, or contains forbidden operations.
    """
    if not expression or not expression.strip():
        raise ValueError("empty expression")

    expression = expression.strip()

    # Pre-scan for forbidden keywords
    for keyword in _FORBIDDEN_KEYWORDS:
        if keyword in expression:
            raise ValueError(f"forbidden keyword: {keyword}")

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"invalid expression: {e}") from e

    try:
        result = _eval_node(tree.body)
    except ZeroDivisionError:
        raise ValueError("division by zero")

    return result


def _eval_node(node: ast.AST) -> NumericResult:
    """Recursively evaluate an AST node."""
    # Numeric literals
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"unsupported constant type: {type(node.value).__name__}")

    # Named constants (pi, e)
    if isinstance(node, ast.Name):
        if node.id in _SAFE_CONSTANTS:
            return _SAFE_CONSTANTS[node.id]
        raise ValueError(f"name '{node.id}' is not allowed")

    # Binary operations (a + b, a * b, etc.)
    if isinstance(node, ast.BinOp):
        op_func = _BINARY_OPS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"operator {type(node.op).__name__} is not allowed")
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        # Prevent DoS via huge exponents
        if isinstance(node.op, ast.Pow):
            if isinstance(right, (int, float)) and abs(right) > 10000:
                raise ValueError("exponent too large (max 10000)")
        return op_func(left, right)

    # Unary operations (-x, +x)
    if isinstance(node, ast.UnaryOp):
        op_func = _UNARY_OPS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"unary operator {type(node.op).__name__} is not allowed")
        operand = _eval_node(node.operand)
        return op_func(operand)

    # Function calls (sqrt(x), abs(x), etc.)
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("only simple function calls are allowed")
        func_name = node.func.id
        if func_name not in _SAFE_FUNCTIONS:
            raise ValueError(f"function '{func_name}' is not allowed")
        args = [_eval_node(arg) for arg in node.args]
        return _SAFE_FUNCTIONS[func_name](*args)

    raise ValueError(f"expression type '{type(node).__name__}' is not allowed")
