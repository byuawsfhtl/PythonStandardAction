import ast

import models as models

def check_complexity(node: ast.FunctionDef, file_path: str, ignore_codes: set[str], max_complexity: int = 10, max_indentation: int = 4) -> list[models.StyleError]:
    """Check cyclomatic complexity and indentation depth of a function.
    
    Args:
        node: Function definition node
        file_path: Path to file being checked
        ignore_codes: set of error codes to ignore
        max_complexity: Maximum allowed complexity
        max_indentation: Maximum allowed indentation depth
        
    Returns:
        list of style errors found
    """
    errors = []
    print(file_path)
    
    # Check cyclomatic complexity
    if 'C901' not in ignore_codes:
        complexity = _calculate_cyclomatic_complexity(node)
        if complexity > max_complexity:
            error = models.StyleError(
                file_path=file_path,
                line_number=getattr(node, 'lineno', 0),
                column=getattr(node, 'col_offset', 0),
                error_code='C901',
                message=f"Function '{node.name}' is too complex ({complexity}), consider breaking into helper functions"
            )
            errors.append(error)
    
    # Check indentation depth
    if 'C902' not in ignore_codes:  # Using C902 for indentation depth
        max_depth = get_max_indent_depth(node) # TODO rewrite, but without ast- ast can't do this. It needs the original source code of the function as a string or something
        if max_depth > max_indentation:
            error = models.StyleError(
                file_path=file_path,
                line_number=getattr(node, 'lineno', 0),
                column=getattr(node, 'col_offset', 0),
                error_code='C902',
                message=f"Function '{node.name}' has excessive nesting depth ({max_depth}). Consider flattening your code structure. See: https://www.youtube.com/watch?v=CFRhGnuXG-4"
            )
            errors.append(error)
    
    return errors




def get_max_indent_depth(node): # TODO rewrite
    return 0




def _calculate_cyclomatic_complexity(node: ast.FunctionDef) -> int:
    """Calculate cyclomatic complexity of a function.
    
    Args:
        node: Function definition node
        
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
            # Each additional condition in and/or adds complexity
            complexity += len(child.values) - 1
        elif isinstance(child, ast.ListComp|ast.SetComp|ast.DictComp|ast.GeneratorExp):
            # List comprehensions with conditions add complexity
            for generator in child.generators:
                complexity += len(generator.ifs)
    
    return complexity
