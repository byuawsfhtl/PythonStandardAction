import ast

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