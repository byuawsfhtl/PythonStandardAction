import re
import ast
from typing import Optional

import models as models
import checkers.error_creation as error_creation_module

# Patterns for detecting security issues
SECRET_PATTERNS = [ # TODO use something better, ideally from a 3rd party lib
    r'password\s*=\s*["\'][^"\']{8,}["\']',
    r'secret\s*=\s*["\'][^"\']{8,}["\']',
    r'api_key\s*=\s*["\'][^"\']{8,}["\']',
    r'token\s*=\s*["\'][^"\']{8,}["\']',
    r'key\s*=\s*["\'][^"\']{16,}["\']',
]

SQL_INJECTION_PATTERNS = [ # TODO use something better, ideally from a 3rd party lib
    r'[\"\'].*%.*[\"\'].*%',  # String formatting in SQL
    r'[\"\'].*\+.*[\"\']',    # String concatenation in SQL-like contexts
    r'execute\s*\(\s*["\'].*%.*["\']',  # Direct execute with formatting
    r'execute\s*\(\s*["\'].*\+.*["\']', # Direct execute with concatenation
]

def check_security_issues(tree: ast.AST, content: str, file_path: str, ignore_codes: set[str]) -> list[models.StyleError]:
    """Check for basic security issues."""
    errors = []
    errors.extend(_check_hardcoded_secrets(content, file_path, ignore_codes))
    errors.extend(_check_sql_and_shell_injection(tree, file_path, ignore_codes))
    errors.extend(_check_assert_statements(tree, file_path, ignore_codes))
    return errors


def _check_hardcoded_secrets(content: str, file_path: str, ignore_codes: set[str]) -> list[models.StyleError]:
    errors = []
    lines = content.split('\n')
    for line_num, line in enumerate(lines, 1):
        error = _check_secret_in_line(line, line_num, file_path, ignore_codes)
        if error:
            errors.append(error)
    return errors


def _check_secret_in_line(line: str, line_num: int, file_path: str, ignore_codes: set[str]) -> Optional[models.StyleError]:
    line_lower = line.lower()
    for pattern in SECRET_PATTERNS:
        if re.search(pattern, line_lower, re.IGNORECASE):
            dummy_node = ast.Constant(value="", lineno=line_num, col_offset=0)
            return error_creation_module.create_error(
                dummy_node, 'S001',
                "Potential hardcoded password or secret detected",
                file_path, ignore_codes
            )
    return None


def _check_sql_and_shell_injection(tree: ast.AST, file_path: str, ignore_codes: set[str]) -> list[models.StyleError]:
    errors = []
    for node in ast.walk(tree):
        errors.extend(_check_sql_injection_call(node, file_path, ignore_codes))
        errors.extend(_check_shell_injection_call(node, file_path, ignore_codes))
    return errors


def _check_sql_injection_call(node: ast.AST, file_path: str, ignore_codes: set[str]) -> list[models.StyleError]:
    errors = []
    if not isinstance(node, ast.Call):
        return errors
    if not (isinstance(node.func, ast.Attribute) and node.func.attr in ['execute', 'executemany']):
        return errors
    for arg in node.args:
        if has_sql_injection_in_node(arg):
            error = error_creation_module.create_error(
                node, 'S002',
                "Potential SQL injection - avoid string formatting in SQL queries",
                file_path, ignore_codes
            )
            if error:
                errors.append(error)
    return errors

def has_sql_injection_in_node(node: ast.AST) -> bool:
    """Check if an AST node contains patterns that could lead to SQL injection.
    
    Args:
        node: AST node to check
        
    Returns:
        True if potential SQL injection pattern found
    """
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
        # String formatting with %
        return True
    elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        # String concatenation
        return True
    elif isinstance(node, ast.Call):
        if (isinstance(node.func, ast.Attribute) and 
            node.func.attr == 'format'):
            # .format() method
            return True
    elif isinstance(node, ast.JoinedStr):
        # f-strings
        return True
    
    return False


def _check_shell_injection_call(node: ast.AST, file_path: str, ignore_codes: set[str]) -> list[models.StyleError]:
    errors = []
    if not isinstance(node, ast.Call):
        return errors
    is_bad_attr = isinstance(node.func, ast.Attribute) and node.func.attr in ['system', 'popen', 'spawn', 'exec']
    is_bad_name = isinstance(node.func, ast.Name) and node.func.id in ['system', 'popen', 'exec']
    if not (is_bad_attr or is_bad_name):
        return errors
    for arg in node.args:
        if isinstance(arg, (ast.BinOp, ast.JoinedStr)):
            error = error_creation_module.create_error(
                node, 'S003',
                "Potential shell injection - avoid dynamic command construction",
                file_path, ignore_codes
            )
            if error:
                errors.append(error)
            break
    return errors


def _check_assert_statements(tree: ast.AST, file_path: str, ignore_codes: set[str]) -> list[models.StyleError]:
    errors = []
    for node in ast.walk(tree):
        error = _check_single_assert(node, file_path, ignore_codes)
        if error:
            errors.append(error)
    return errors


def _check_single_assert(node: ast.AST, file_path: str, ignore_codes: set[str]) -> Optional[models.StyleError]:
    if isinstance(node, ast.Assert):
        return error_creation_module.create_error(
            node, 'S004',
            "Assert statement used - asserts are removed in optimized Python",
            file_path, ignore_codes
        )
    return None