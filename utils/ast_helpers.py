import ast
import re

"""Helper functions in AST traversal"""

def get_type_string(annotation: ast.AST) -> str:
    """Extract type string from AST annotation.
    
    Args:
        annotation: AST node representing type annotation
        
    Returns:
        String representation of the type
    """
    if annotation is None:
        return ""
        
    if isinstance(annotation, ast.Name):
        return annotation.id
    elif isinstance(annotation, ast.Attribute):
        return f"{get_type_string(annotation.value)}.{annotation.attr}"
    elif isinstance(annotation, ast.Subscript):
        return f"{get_type_string(annotation.value)}[{get_type_string(annotation.slice)}]"
    elif isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        # Union types (X | Y)
        left = get_type_string(annotation.left)
        right = get_type_string(annotation.right)
        return f"{left} | {right}"
    elif isinstance(annotation, ast.Constant):
        return repr(annotation.value)
    elif isinstance(annotation, ast.Tuple):
        elements = [get_type_string(elt) for elt in annotation.elts]
        return f"({', '.join(elements)})"
    else:
        # Fallback: use ast.unparse if available (Python 3.9+)
        try:
            return ast.unparse(annotation)
        except AttributeError:
            return "<unknown>"


def parse_docstring_args(docstring: str) -> dict[str, str]:
    """Parse arguments section from Google-style docstring.
    
    Args:
        docstring: The docstring to parse
        
    Returns:
        Dictionary mapping argument names to their documented types
    """
    args_section = {}
    
    # Find Args: section
    lines = docstring.split('\n')
    in_args_section = False
    current_arg = None
    
    for line in lines:
        stripped_line = line.strip()
        
        # Check if we're entering the Args section
        if stripped_line == 'Args:':
            in_args_section = True
            continue
        
        # Check if we're leaving the Args section (new section starts)
        if in_args_section and stripped_line.endswith(':') and not stripped_line.startswith(' '):
            # This is a new section header, stop parsing args
            if stripped_line not in ['Args:', 'Arguments:']:
                break
        
        # If we're in args section and have content
        if in_args_section and stripped_line:
            # Check for argument definition: "name (type): description" or "name: description"
            # Also handle multiline descriptions that are indented
            arg_match = re.match(r'^(\w+)\s*(?:\(([^)]+)\))?\s*:\s*(.*)$', stripped_line)
            if arg_match:
                arg_name, arg_type, description = arg_match.groups()
                current_arg = arg_name.strip()
                # If type is specified in parentheses, use it
                if arg_type:
                    args_section[current_arg] = arg_type.strip()
                else:
                    # Try to extract type from description or set as unknown
                    args_section[current_arg] = "Any"  # Default type when not specified
            elif current_arg and stripped_line and line.startswith('    '):
                # This is a continuation of the previous argument's description
                # We can extract additional type info if needed, but for now just continue
                pass
    
    return args_section

def collect_used_names(tree: ast.AST) -> set[str]:
    """Collect all names that are used in the AST.
    
    Args:
        tree: AST tree to analyze
        
    Returns:
        Set of names that are referenced
    """
    used_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used_names.add(node.id)
        elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
            # For attributes like os.path, we want to track 'os'
            if isinstance(node.value, ast.Name):
                used_names.add(node.value.id)
    return used_names

def calculate_cyclomatic_complexity(node: ast.FunctionDef) -> int:
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
