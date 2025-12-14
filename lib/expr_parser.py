#!/usr/bin/env python3
"""
Expression Parser for RESTest

This module provides arithmetic expression parsing and evaluation
without using Python's eval(). It supports:
- Basic arithmetic: +, -, *, /, %
- Parentheses for grouping
- Variable references
- Integer and float numbers

Grammar (EBNF):
    expression := term (('+' | '-') term)*
    term       := factor (('*' | '/' | '%') factor)*
    factor     := NUMBER | IDENTIFIER | '(' expression ')' | '-' factor
"""

import re


class ExpressionError(Exception):
    """Exception raised for expression parsing/evaluation errors."""

    pass


# Token types
TOKEN_NUMBER = "NUMBER"
TOKEN_IDENT = "IDENT"
TOKEN_OP = "OP"
TOKEN_LPAREN = "LPAREN"
TOKEN_RPAREN = "RPAREN"
TOKEN_EOF = "EOF"

# Regex pattern for tokenization
_rx_token = re.compile(
    r"""
    \s*                     # Skip whitespace
    (?:
        (\d+\.?\d*)         # Group 1: Numbers (int or float)
        |
        ([a-zA-Z_]\w*)      # Group 2: Identifiers
        |
        ([+\-*/%])          # Group 3: Operators
        |
        (\()                # Group 4: Left paren
        |
        (\))                # Group 5: Right paren
    )
""",
    re.VERBOSE,
)


def _tokenize(expr: str) -> list:
    """
    Convert expression string to list of tokens.

    Args:
        expr: Expression string like "my_var + 5"

    Returns:
        List of (token_type, value) tuples
    """
    tokens = []
    pos = 0

    while pos < len(expr):
        # Skip whitespace
        while pos < len(expr) and expr[pos].isspace():
            pos += 1

        if pos >= len(expr):
            break

        match = _rx_token.match(expr, pos)
        if not match:
            raise ExpressionError(
                f"Invalid character '{expr[pos]}' at position {pos} in expression: {expr}"
            )

        if match.group(1) is not None:  # Number
            val = match.group(1)
            if "." in val:
                tokens.append((TOKEN_NUMBER, float(val)))
            else:
                tokens.append((TOKEN_NUMBER, int(val)))
        elif match.group(2) is not None:  # Identifier
            tokens.append((TOKEN_IDENT, match.group(2)))
        elif match.group(3) is not None:  # Operator
            tokens.append((TOKEN_OP, match.group(3)))
        elif match.group(4) is not None:  # Left paren
            tokens.append((TOKEN_LPAREN, "("))
        elif match.group(5) is not None:  # Right paren
            tokens.append((TOKEN_RPAREN, ")"))

        pos = match.end()

    tokens.append((TOKEN_EOF, None))
    return tokens


class ExprParser:
    """
    Recursive descent parser for arithmetic expressions.

    Implements the following grammar:
        expression := term (('+' | '-') term)*
        term       := factor (('*' | '/' | '%') factor)*
        factor     := NUMBER | IDENTIFIER | '(' expression ')' | '-' factor
    """

    def __init__(self, expr: str, variables: dict):
        """
        Initialize the parser.

        Args:
            expr: Expression string to parse
            variables: Dictionary of variable name -> value
        """
        self.expr = expr
        self.variables = variables
        self.tokens = _tokenize(expr)
        self.pos = 0

    def _current(self):
        """Return current token."""
        return self.tokens[self.pos]

    def _current_type(self):
        """Return current token type."""
        return self.tokens[self.pos][0]

    def _current_value(self):
        """Return current token value."""
        return self.tokens[self.pos][1]

    def _consume(self):
        """Consume current token and return it."""
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def _expect(self, token_type):
        """Expect current token to be of given type, consume and return it."""
        if self._current_type() != token_type:
            raise ExpressionError(
                f"Expected {token_type}, got {self._current_type()} "
                f"at position {self.pos} in expression: {self.expr}"
            )
        return self._consume()

    def parse(self) -> float:
        """
        Parse and evaluate the expression.

        Returns:
            Numeric result of the expression
        """
        result = self._expression()

        if self._current_type() != TOKEN_EOF:
            raise ExpressionError(
                f"Unexpected token '{self._current_value()}' "
                f"at position {self.pos} in expression: {self.expr}"
            )

        return result

    def _expression(self) -> float:
        """
        Parse expression: term (('+' | '-') term)*
        """
        result = self._term()

        while self._current_type() == TOKEN_OP and self._current_value() in ("+", "-"):
            op = self._consume()[1]
            right = self._term()

            if op == "+":
                result = result + right
            else:
                result = result - right

        return result

    def _term(self) -> float:
        """
        Parse term: factor (('*' | '/' | '%') factor)*
        """
        result = self._factor()

        while self._current_type() == TOKEN_OP and self._current_value() in (
            "*",
            "/",
            "%",
        ):
            op = self._consume()[1]
            right = self._factor()

            if op == "*":
                result = result * right
            elif op == "/":
                if right == 0:
                    raise ExpressionError(
                        f"Division by zero in expression: {self.expr}"
                    )
                # Integer division if both operands are integers
                if isinstance(result, int) and isinstance(right, int):
                    result = result // right
                else:
                    result = result / right
            else:  # %
                if right == 0:
                    raise ExpressionError(
                        f"Modulo by zero in expression: {self.expr}"
                    )
                result = result % right

        return result

    def _factor(self) -> float:
        """
        Parse factor: NUMBER | IDENTIFIER | '(' expression ')' | '-' factor
        """
        # Unary minus
        if self._current_type() == TOKEN_OP and self._current_value() == "-":
            self._consume()
            return -self._factor()

        # Number
        if self._current_type() == TOKEN_NUMBER:
            return self._consume()[1]

        # Identifier (variable reference)
        if self._current_type() == TOKEN_IDENT:
            var_name = self._consume()[1]
            return self._get_variable(var_name)

        # Parenthesized expression
        if self._current_type() == TOKEN_LPAREN:
            self._consume()  # consume '('
            result = self._expression()
            self._expect(TOKEN_RPAREN)  # consume ')'
            return result

        raise ExpressionError(
            f"Unexpected token '{self._current_value()}' "
            f"at position {self.pos} in expression: {self.expr}"
        )

    def _get_variable(self, var_name: str) -> float:
        """
        Get variable value from variables dict.

        Args:
            var_name: Name of the variable

        Returns:
            Numeric value of the variable

        Raises:
            ExpressionError: If variable is undefined or non-numeric
        """
        if var_name not in self.variables:
            raise ExpressionError(
                f"Undefined variable '{var_name}' in expression: {self.expr}"
            )

        value = self.variables[var_name]

        # Try to convert to number
        if isinstance(value, (int, float)):
            return value

        if isinstance(value, str):
            try:
                if "." in value:
                    return float(value)
                return int(value)
            except ValueError:
                raise ExpressionError(
                    f"Cannot perform arithmetic on non-numeric value '{value}' "
                    f"(variable: {var_name}) in expression: {self.expr}"
                )

        raise ExpressionError(
            f"Cannot perform arithmetic on value of type {type(value).__name__} "
            f"(variable: {var_name}) in expression: {self.expr}"
        )


def is_expression(value) -> bool:
    """
    Check if a value is an expression (starts with '${' and ends with '}').

    Args:
        value: Value to check

    Returns:
        True if value is an expression, False otherwise
    """
    return isinstance(value, str) and value.startswith("${") and value.endswith("}")


def extract_expression(value: str) -> str:
    """
    Extract the expression content from '${...}' wrapper.

    Args:
        value: Expression string like '${a + b}'

    Returns:
        Expression content like 'a + b'
    """
    if not is_expression(value):
        return value
    return value[2:-1]


def evaluate_expr(expr_str: str, variables: dict):
    """
    Parse and evaluate an expression string.

    Args:
        expr_str: Expression like "my_var + 5" or "${my_var + 5}"
        variables: Dict of variable name -> value

    Returns:
        Numeric result of the expression (int or float)

    Raises:
        ExpressionError: On syntax or runtime errors
    """
    # Handle ${...} wrapper
    if is_expression(expr_str):
        expr_str = extract_expression(expr_str)

    parser = ExprParser(expr_str, variables)
    return parser.parse()


if __name__ == "__main__":
    # Test examples
    test_vars = {
        "a": 10,
        "b": 5,
        "count": "3",
        "price": 100,
    }

    test_cases = [
        ("5 + 3", 8),
        ("10 - 4", 6),
        ("3 * 4", 12),
        ("10 / 2", 5),
        ("10 % 3", 1),
        ("a + b", 15),
        ("a - b", 5),
        ("a * b", 50),
        ("a / b", 2),
        ("(a + b) * 2", 30),
        ("a + b * 2", 20),
        ("count + 1", 4),
        ("price * count", 300),
        ("-5 + 10", 5),
        ("-(a + b)", -15),
        ("${a + b}", 15),
    ]

    print("Testing expression parser:")
    print("=" * 50)

    for expr, expected in test_cases:
        try:
            result = evaluate_expr(expr, test_vars)
            status = "PASS" if result == expected else "FAIL"
            print(f"{status}: '{expr}' = {result} (expected {expected})")
        except ExpressionError as e:
            print(f"FAIL: '{expr}' raised {e}")

    # Test error cases
    print("\nTesting error cases:")
    print("=" * 50)

    error_cases = [
        ("undefined_var + 5", "Undefined variable"),
        ("5 / 0", "Division by zero"),
        ("5 + + 3", "Syntax error"),
        ("(5 + 3", "Unbalanced parens"),
    ]

    for expr, expected_error in error_cases:
        try:
            result = evaluate_expr(expr, test_vars)
            print(f"FAIL: '{expr}' should have raised error, got {result}")
        except ExpressionError as e:
            print(f"PASS: '{expr}' raised: {e}")
