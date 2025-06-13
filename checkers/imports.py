import ast

import models as models
import checkers.error_creation as error_creation_module

def get_import_module_name(node: ast.Import | ast.ImportFrom) -> str:
    """Get the base module name from an import statement.
    
    Args:
        node: Import or ImportFrom node
        
    Returns:
        Base module name
    """
    if isinstance(node, ast.Import):
        # For "import os.path", return "os"
        return node.names[0].name.split('.')[0]
    elif isinstance(node, ast.ImportFrom):
        if node.module:
            return node.module.split('.')[0]
        else:
            return ""  # Relative import
    return ""


def categorize_import(module_name: str) -> str:
    """Categorize an import as stdlib, third-party, or local.
    
    Args:
        module_name: Name of the imported module
        
    Returns:
        Category: 'stdlib', 'third-party', or 'local'
    """
    if not module_name:
        return 'local'  # Relative imports are local
    
    if module_name in models.STDLIB_MODULES:
        return 'stdlib'
    
    # If it starts with a dot, it's relative/local
    if module_name.startswith('.'):
        return 'local'
    
    # Simple heuristic: if it contains no dots and is lowercase, might be stdlib
    # This is imperfect but covers many common cases
    if '.' not in module_name and module_name.islower():
        # Check some common patterns
        common_stdlib = ['abc', 'io', 'gc', 'dis', 'imp', 'site', 'user']
        if module_name in common_stdlib:
            return 'stdlib'
    
    # Default to third-party for unknown modules
    return 'third-party'


def check_import_order(imports: list[ast.Import | ast.ImportFrom], file_path: str, ignore_codes: set[str]) -> list[models.StyleError]:
    """Check if imports are properly ordered according to PEP 8.
    
    Args:
        imports: List of import nodes
        file_path: Path to file being checked
        ignore_codes: set of error codes to ignore
        
    Returns:
        list of style errors found
    """
    errors = []
    
    if not imports:
        return errors
    
    # Categorize imports and track their order
    import_categories = []
    for imp in imports:
        module_name = get_import_module_name(imp)
        category = categorize_import(module_name)
        import_categories.append((category, imp))
    
    # Check ordering: stdlib -> third-party -> local
    expected_order = ['stdlib', 'third-party', 'local']
    current_category_index = 0
    
    for category, imp in import_categories:
        category_index = expected_order.index(category)
        
        if category_index < current_category_index:
            error = error_creation_module.create_error(imp, 'I100', f"Import '{get_import_module_name(imp)}' ({category}) should come before previous imports", file_path, ignore_codes)
            if error:
                errors.append(error)
        else:
            current_category_index = category_index
    
    return errors


def check_unused_imports(imports: list[ast.Import | ast.ImportFrom], names_used: set[str], file_path: str, ignore_codes: set[str]) -> list[models.StyleError]:
    """Check for unused imports."""
    errors = []

    for imp in imports:
        if isinstance(imp, ast.Import):
            errors.extend(_check_unused_import_nodes(imp, names_used, file_path, ignore_codes))
        elif isinstance(imp, ast.ImportFrom):
            errors.extend(_check_unused_from_import_nodes(imp, names_used, file_path, ignore_codes))

    return errors


def _check_unused_import_nodes(imp: ast.Import, names_used: set[str], file_path: str, ignore_codes: set[str]) -> list[models.StyleError]:
    """Check unused names in an ast.Import node."""
    errors = []
    for alias in imp.names:
        imported_name = alias.asname if alias.asname else alias.name.split('.')[0]
        if imported_name in names_used:
            continue
        error = error_creation_module.create_error(imp, 'I101', f"Unused import '{imported_name}'", file_path, ignore_codes)
        if error:
            errors.append(error)
    return errors


def _check_unused_from_import_nodes(imp: ast.ImportFrom, names_used: set[str], file_path: str, ignore_codes: set[str]) -> list[models.StyleError]:
    """Check unused names in an ast.ImportFrom node."""
    errors = []
    for alias in imp.names:
        if alias.name == '*':
            continue  # wildcard imports not checked here
        imported_name = alias.asname if alias.asname else alias.name
        if imported_name in names_used:
            continue
        error = error_creation_module.create_error(imp, 'I101', f"Unused import '{imported_name}' from '{imp.module or '.'}'", file_path, ignore_codes)
        if error:
            errors.append(error)
    return errors


def check_wildcard_imports(imports: list[ast.ImportFrom], file_path: str, ignore_codes: set[str]) -> list[models.StyleError]:
    """Check for wildcard imports.
    
    Args:
        imports: List of ImportFrom nodes
        file_path: Path to file being checked
        ignore_codes: set of error codes to ignore
        
    Returns:
        list of style errors found
    """
    errors = []
    for imp in imports:
        for alias in imp.names:
            if alias.name != '*':
                continue
            error = error_creation_module.create_error(imp, 'I102', f"Wildcard import from '{imp.module or '.'}' should be avoided", file_path, ignore_codes)
            if error:
                errors.append(error)
    
    return errors


def check_relative_imports(imports: list[ast.ImportFrom], file_path: str, ignore_codes: set[str]) -> list[models.StyleError]:
    """Check for relative imports that should be absolute.
    
    Args:
        imports: List of ImportFrom nodes
        file_path: Path to file being checked
        ignore_codes: set of error codes to ignore
        
    Returns:
        list of style errors found
    """
    errors = []
    for imp in imports:
        if imp.level <= 0:
            continue
        # Relative import (starts with dots)
        error = error_creation_module.create_error(imp, 'I103', f"Relative import should be absolute", file_path, ignore_codes)
        if error:
            errors.append(error)
    return errors