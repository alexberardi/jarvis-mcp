"""Tests for math evaluation service.

Tests the safe AST-based expression evaluator.
"""

import math

import pytest

from jarvis_mcp.services.math_service import evaluate_expression


class TestBasicArithmetic:
    """Tests for basic math operations."""

    def test_addition(self):
        assert evaluate_expression("2 + 3") == 5

    def test_subtraction(self):
        assert evaluate_expression("10 - 4") == 6

    def test_multiplication(self):
        assert evaluate_expression("6 * 7") == 42

    def test_division(self):
        assert evaluate_expression("15 / 3") == 5.0

    def test_floor_division(self):
        assert evaluate_expression("7 // 2") == 3

    def test_modulo(self):
        assert evaluate_expression("10 % 3") == 1

    def test_complex_expression(self):
        assert evaluate_expression("(10 * 3) / 2 + 7") == 22.0

    def test_parentheses(self):
        assert evaluate_expression("(2 + 3) * (4 + 5)") == 45

    def test_negative_numbers(self):
        assert evaluate_expression("-5 + 3") == -2

    def test_unary_minus(self):
        assert evaluate_expression("-(-5)") == 5


class TestExponents:
    """Tests for exponentiation."""

    def test_power(self):
        assert evaluate_expression("2 ** 10") == 1024

    def test_power_float(self):
        assert evaluate_expression("4 ** 0.5") == 2.0

    def test_power_zero(self):
        assert evaluate_expression("5 ** 0") == 1

    def test_power_large_exponent_rejected(self):
        with pytest.raises(ValueError, match="exponent too large"):
            evaluate_expression("2 ** 999999999")

    def test_power_moderate_exponent_allowed(self):
        assert evaluate_expression("2 ** 10000") == 2 ** 10000


class TestFloats:
    """Tests for floating point operations."""

    def test_float_multiplication(self):
        result = evaluate_expression("3.14 * 2")
        assert abs(result - 6.28) < 0.001

    def test_float_division(self):
        result = evaluate_expression("1 / 3")
        assert abs(result - 0.333333) < 0.001

    def test_float_literal(self):
        assert evaluate_expression("0.5 + 0.5") == 1.0


class TestFunctions:
    """Tests for safe math functions."""

    def test_sqrt(self):
        assert evaluate_expression("sqrt(144)") == 12.0

    def test_abs(self):
        assert evaluate_expression("abs(-42)") == 42

    def test_round(self):
        assert evaluate_expression("round(3.7)") == 4

    def test_ceil(self):
        assert evaluate_expression("ceil(3.2)") == 4

    def test_floor(self):
        assert evaluate_expression("floor(3.9)") == 3

    def test_log(self):
        result = evaluate_expression("log(1)")
        assert result == 0.0

    def test_log10(self):
        result = evaluate_expression("log10(100)")
        assert result == 2.0

    def test_sin(self):
        result = evaluate_expression("sin(0)")
        assert result == 0.0

    def test_cos(self):
        result = evaluate_expression("cos(0)")
        assert result == 1.0

    def test_tan(self):
        result = evaluate_expression("tan(0)")
        assert abs(result) < 0.001


class TestConstants:
    """Tests for math constants."""

    def test_pi(self):
        result = evaluate_expression("pi")
        assert abs(result - math.pi) < 0.00001

    def test_e(self):
        result = evaluate_expression("e")
        assert abs(result - math.e) < 0.00001

    def test_pi_in_expression(self):
        result = evaluate_expression("pi * 2")
        assert abs(result - 2 * math.pi) < 0.00001

    def test_e_in_expression(self):
        result = evaluate_expression("e ** 2")
        assert abs(result - math.e ** 2) < 0.00001


class TestErrors:
    """Tests for error handling."""

    def test_division_by_zero(self):
        with pytest.raises(ValueError, match="division by zero"):
            evaluate_expression("1 / 0")

    def test_invalid_expression(self):
        with pytest.raises(ValueError):
            evaluate_expression("not a math expression")

    def test_empty_expression(self):
        with pytest.raises(ValueError):
            evaluate_expression("")

    def test_unknown_function(self):
        with pytest.raises(ValueError, match="not allowed"):
            evaluate_expression("unknown_func(5)")


class TestSecurity:
    """Tests for security - rejecting dangerous expressions."""

    def test_rejects_import(self):
        with pytest.raises(ValueError):
            evaluate_expression("__import__('os')")

    def test_rejects_eval(self):
        with pytest.raises(ValueError):
            evaluate_expression("eval('1+1')")

    def test_rejects_exec(self):
        with pytest.raises(ValueError):
            evaluate_expression("exec('print(1)')")

    def test_rejects_os_system(self):
        with pytest.raises(ValueError):
            evaluate_expression("os.system('ls')")

    def test_rejects_attribute_access(self):
        with pytest.raises(ValueError):
            evaluate_expression("''.__class__")

    def test_rejects_dunder(self):
        with pytest.raises(ValueError):
            evaluate_expression("__builtins__")

    def test_rejects_import_keyword(self):
        with pytest.raises(ValueError, match="forbidden"):
            evaluate_expression("import os")

    def test_rejects_open(self):
        with pytest.raises(ValueError):
            evaluate_expression("open('/etc/passwd')")

    def test_rejects_lambda(self):
        with pytest.raises(ValueError):
            evaluate_expression("(lambda: 1)()")

    def test_rejects_list_comprehension(self):
        with pytest.raises(ValueError):
            evaluate_expression("[x for x in range(10)]")
