import ast
from pathlib import Path

import models as models
import checkers.error_creation as error_creation_module

def collect_imports(tree: ast.AST) -> tuple[list[ast.Import | ast.ImportFrom], list[ast.ImportFrom]]:
    """Collect import statements from an AST.

    Args:
        tree: Parsed AST of the Python file

    Returns:
        Tuple of (all imports, from-imports only)
    """
    imports = []
    import_froms = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.append(node)
        elif isinstance(node, ast.ImportFrom):
            import_froms.append(node)
    return imports + import_froms, import_froms


def check_imports(all_imports: list[ast.AST], import_froms: list[ast.ImportFrom], used_names: set[str], file_path: Path, ignore_codes: set[str]) -> list[models.StyleError]:
    """Run all import-related checks.

    Args:
        all_imports: List of all import and from-import AST nodes
        import_froms: List of from-import AST nodes
        used_names: Set of names used in the file
        file_path: Path to the file being checked
        ignore_codes: set of error codes to ignore

    Returns:
        List of style errors related to import statements
    """
    errors = []
    errors.extend(_check_import_order(all_imports, str(file_path), ignore_codes))
    errors.extend(_check_unused_imports(all_imports, used_names, str(file_path), ignore_codes))
    errors.extend(_check_wildcard_imports(import_froms, str(file_path), ignore_codes))
    errors.extend(_check_relative_imports(import_froms, str(file_path), ignore_codes))
    return errors


def _check_import_order(imports: list[ast.Import | ast.ImportFrom], file_path: str, ignore_codes: set[str]) -> list[models.StyleError]:
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
        module_name = _get_import_module_name(imp)
        category = _categorize_import(module_name)
        import_categories.append((category, imp))
    
    # Check ordering: stdlib -> third-party -> local
    expected_order = ['stdlib', 'third-party', 'local']
    max_seen_category_index = -1
    
    for category, imp in import_categories:
        category_index = expected_order.index(category)
        
        if category_index >= max_seen_category_index:
            continue

        error = error_creation_module.create_error(
            imp, 
            'I100', 
            f"Import '{_get_import_module_name(imp)}' ({category}) should come before previous imports", 
            file_path, 
            ignore_codes
        )
        if error:
            errors.append(error)
        
        # Update max_seen_category_index to track the highest category we've seen
        max_seen_category_index = max(max_seen_category_index, category_index)
    
    return errors


def _get_import_module_name(node: ast.Import | ast.ImportFrom) -> str:
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



def _categorize_import(module_name: str) -> str:
    """Categorize an import as stdlib, third-party, or local.
    
    Args:
        module_name: Name of the imported module
        
    Returns:
        'stdlib', 'third-party', or 'local'
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


def _check_unused_imports(imports: list[ast.Import | ast.ImportFrom], names_used: set[str], file_path: str, ignore_codes: set[str]) -> list[models.StyleError]:
    """Check for unused imports.
    
    Args:
        imports: List of import nodes
        names_used: the complete set of the lib names used within the file
        file_path: Path to file being checked
        ignore_codes: set of error codes to ignore

    Returns:
        the list of unused import errors, if any
    """
    errors = []

    for imp in imports:
        if isinstance(imp, ast.Import):
            errors.extend(_check_unused_import_nodes(imp, names_used, file_path, ignore_codes))
        elif isinstance(imp, ast.ImportFrom):
            errors.extend(_check_unused_from_import_nodes(imp, names_used, file_path, ignore_codes))

    return errors


def _check_unused_import_nodes(imp: ast.Import, names_used: set[str], file_path: str, ignore_codes: set[str]) -> list[models.StyleError]:
    """Check unused names in an ast.Import node.
    
    Args:
        imp: the import within the file
        names_used: the complete set of the lib names used within the file
        file_path: Path to file being checked
        ignore_codes: set of error codes to ignore

    Returns:
        the list of unused import errors, if any
    """
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
    """Check unused names in an ast.ImportFrom node.
    
    Args:
        imp: the import within the file
        names_used: the complete set of the lib names used within the file
        file_path: Path to file being checked
        ignore_codes: set of error codes to ignore

    Returns:
        an unused import error, or None
    """
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


def _check_wildcard_imports(imports: list[ast.ImportFrom], file_path: str, ignore_codes: set[str]) -> list[models.StyleError]:
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


def _check_relative_imports(imports: list[ast.ImportFrom], file_path: str, ignore_codes: set[str]) -> list[models.StyleError]:
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