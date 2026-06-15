import ast
from typing import Optional

import models as models

def check_complexity(tree: ast.AST, content: str, file_path: str, ignore_codes: set[str], max_complexity: int = 15, max_indentation: int = 4) -> list[models.StyleError]:
    """Check cyclomatic complexity and indentation depth for all functions in a file.
    
    Args:
        tree: AST module node representing the entire file
        content: Original file content as string
        file_path: Path to file being checked
        ignore_codes: set of error codes to ignore
        max_complexity: Maximum allowed complexity
        max_indentation: Maximum allowed indentation depth
        
    Returns:
        list of style errors found
    """
    errors = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        functional_error = _check_function_complexity(node, file_path, ignore_codes, max_complexity)
        if functional_error:
            errors.append(functional_error)
        indentation_error = _is_too_deeply_indented(node, content, file_path, ignore_codes, max_indentation)
        if indentation_error:
            errors.append(indentation_error)
    return errors


def _check_function_complexity(node: ast.FunctionDef | ast.AsyncFunctionDef, file_path: str, ignore_codes: set[str], max_complexity: int) -> Optional[models.StyleError]:
    """Check cyclomatic complexity of a single function.
    
    Args:
        node: an AST function definition
        file_path: Path to file being checked
        ignore_codes: set of error codes to ignore
        max_complexity: Maximum allowed complexity

    Returns:
        a function complexity error or None
    """
    if 'C901' in ignore_codes:
        return None
    complexity = _calculate_cyclomatic_complexity(node)
    if complexity <= max_complexity:
        return None
    return models.StyleError(file_path=file_path,
        line_number=getattr(node, 'lineno', 0),
        column=getattr(node, 'col_offset', 0),
        error_code='C901',
        message=f"Function '{node.name}' is too complex ({complexity} cyclomatic complexity where the max is {max_complexity}). Consider breaking into helper functions"
    )


def _calculate_cyclomatic_complexity(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Calculate cyclomatic complexity of a function.
    
    Args:
        node: an AST Function definition
        
    Returns:
        Cyclomatic complexity score
    """
    complexity = 1  # Base complexity
    
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
            complexity += 1
        elif isinstance(child, ast.ExceptHandler):
            complexity += 1
        elif isinstance(child, ast.With|ast.AsyncWith):
            complexity += 1
        elif isinstance(child, ast.Assert):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            # Each additional condition in and/or adds 1 to complexity
            complexity += len(child.values) - 1
        elif isinstance(child, (ast.ListComp|ast.SetComp|ast.DictComp|ast.GeneratorExp|ast.Call|ast.Lambda)):
            # Don't count these as complexity
            pass
    
    return complexity


def _is_too_deeply_indented(node: ast.FunctionDef | ast.AsyncFunctionDef, content: str, file_path: str, ignore_codes: set[str], max_allowed_depth: int) -> Optional[models.StyleError]:
    """Check indentation depth of a single function.
    
    Args:
        node: AST function definition
        content: Original file content as string
        file_path: Path to file being checked
        ignore_codes: set of error codes to ignore
        max_allowed_depth: Maximum allowed indentation depth

    Returns:
        an indentation error or None
    """
    
    if 'C902' in ignore_codes:
        return None
    
    deepest_depth = _get_max_indent_depth_from_source(node, content)

    if deepest_depth <= max_allowed_depth:
        return None
    
    return models.StyleError(
        file_path=file_path,
        line_number=getattr(node, 'lineno', 0),
        column=getattr(node, 'col_offset', 0),
        error_code='C902',
        message=f"Function '{node.name}' has excessive nesting depth of {deepest_depth} where the max is {max_allowed_depth}. Consider flattening your code structure. See: https://www.youtube.com/watch?v=CFRhGnuXG-4"
    )


def _get_max_indent_depth_from_source(node: ast.FunctionDef | ast.AsyncFunctionDef, content: str) -> int:
    """Calculate maximum indentation depth within a function using source code.
    
    Args:
        node: Function definition node
        content: Original file content as string
        
    Returns:
        Maximum indentation depth within the function
    """
    lines = content.split('\n')
    
    # Get the function's line range
    start_line = node.lineno - 1  # Convert to 0-based indexing
    
    # Find the end line of the function
    end_line = _find_function_end_line(lines, start_line)
    
    # Get function source lines
    function_lines = lines[start_line:end_line + 1]
    
    # Find the base indentation of the function definition
    func_def_line = function_lines[0]
    base_indent = len(func_def_line) - len(func_def_line.lstrip())
    
    max_depth = 0
    
    # Check indentation of each line within the function
    for line in function_lines[1:]:  # Skip the function definition line
        if not line.strip():
            continue
        current_indent = len(line) - len(line.lstrip())
        if current_indent <= base_indent:
            continue
        function_body_indent = base_indent + 4
        if current_indent < function_body_indent:
            continue
        depth = (current_indent - function_body_indent) // 4 + 1
        max_depth = max(max_depth, depth)
    
    return max_depth


def _find_function_end_line(lines: list[str], start_line: int) -> int:
    """Find the last line of a function definition.
    
    Args:
        lines: All lines in the file
        start_line: Starting line of the function (0-based)
        
    Returns:
        End line of the function (0-based)
    """
    # Get the base indentation level of the function
    func_line = lines[start_line]
    base_indent = len(func_line) - len(func_line.lstrip())
    
    # Start from the line after the function definition
    current_line = start_line + 1
    
    # Look for the next line that has the same or less indentation and contains code
    while current_line < len(lines):
        line = lines[current_line]
        
        # Skip empty lines and comments
        if line.strip() and not line.strip().startswith('#'):
            line_indent = len(line) - len(line.lstrip())
            
            # If we find a line with same or less indentation, the function ends at the previous line
            if line_indent <= base_indent:
                return current_line - 1
        
        current_line += 1
    
    # If we reach the end of the file, the function ends at the last line
    return len(lines) - 1