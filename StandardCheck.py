import ast
import sys
import argparse
import pathspec
from pathlib import Path
from typing import Any, Optional

import models as models
import config as config_module
import utils.file_utils as file_utils_module
import utils.ast_helpers as ast_helpers_module
import checkers.common_nodes as common_nodes_module
import checkers.imports as imports_module
import checkers.security as security_module


def visit_node(node: ast.AST, file_path: str, ignore_codes: set[str], ignore_names: set[str] = None) -> list[models.StyleError]:
    """Visit an AST node and perform checks.
    
    Args:
        node: AST node to check
        file_path: Path to file containing the node
        ignore_codes: set of error codes to ignore
        ignore_names: set of names to ignore
        
    Returns:
        list of style errors found
    """
    ignore_names = ignore_names or set()
    
    if isinstance(node, ast.ClassDef):
        return common_nodes_module.check_class(node, file_path, ignore_codes, ignore_names)
    elif isinstance(node, ast.FunctionDef):
        errors = common_nodes_module.check_function(node, file_path, ignore_codes, ignore_names)
        # Check cyclomatic complexity
        errors.extend(check_complexity(node, file_path, ignore_codes))
        return errors
    elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
        return common_nodes_module.check_variable(node, file_path, ignore_codes, ignore_names)
    else:
        return []


def check_complexity(node: ast.FunctionDef, file_path: str, ignore_codes: set[str], max_complexity: int = 5, max_indentation: int = 4) -> list[models.StyleError]:
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
    
    # Check cyclomatic complexity
    if 'C901' not in ignore_codes:
        complexity = ast_helpers_module.calculate_cyclomatic_complexity(node)
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
        max_depth = _calculate_max_indentation_depth(node)
        if max_depth > max_indentation:
            error = models.StyleError(
                file_path=file_path,
                line_number=getattr(node, 'lineno', 0),
                column=getattr(node, 'col_offset', 0),
                error_code='C902',
                message=f"Function '{node.name}' has excessive nesting depth ({max_depth}). "
                       f"Consider flattening your code structure. See: https://www.youtube.com/watch?v=CFRhGnuXG-4"
            )
            errors.append(error)
    
    return errors


def _calculate_max_indentation_depth(node: ast.AST, current_depth: int = 0) -> int:
    """Calculate the maximum indentation depth within a node.
    
    Args:
        node: AST node to analyze
        current_depth: Current nesting depth
        
    Returns:
        Maximum indentation depth found
    """
    max_depth = current_depth
    # Nodes that increase indentation depth
    nesting_nodes = (
        ast.If, ast.For, ast.While, ast.With, ast.Try, ast.ExceptHandler,
        ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Match
    )
    for child in ast.iter_child_nodes(node):
        if isinstance(child, nesting_nodes):
            # Skip function/class definitions as they don't count as "nesting" in the same way
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                child_depth = _calculate_max_indentation_depth(child, current_depth)
            else:
                child_depth = _calculate_max_indentation_depth(child, current_depth + 1)
            max_depth = max(max_depth, child_depth)
        else:
            child_depth = _calculate_max_indentation_depth(child, current_depth)
            max_depth = max(max_depth, child_depth)
    return max_depth


def check_file(file_path: Path, ignore_codes: set[str], ignore_names: set[str] = None, config: dict[str, Any] = None) -> list[models.StyleError]:
    """Check a single Python file.
    
    Args:
        file_path: Path to Python file to check
        ignore_codes: set of error codes to ignore
        ignore_names: set of names to ignore
        config: Configuration dictionary
        
    Returns:
        list of style errors found
    """
    errors = []
    ignore_names = ignore_names or set()
    config = config or {}
    max_complexity = config.get('max_complexity', 10)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        tree = ast.parse(content, filename=str(file_path))
        
        # Collect imports and used names for import checking
        imports = []
        import_froms = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.append(node)
            elif isinstance(node, ast.ImportFrom):
                import_froms.append(node)
        
        all_imports = imports + import_froms
        used_names = ast_helpers_module.collect_used_names(tree)
        
        # Check imports
        errors.extend(imports_module.check_import_order(all_imports, str(file_path), ignore_codes))
        errors.extend(imports_module.check_unused_imports(all_imports, used_names, str(file_path), ignore_codes))
        errors.extend(imports_module.check_wildcard_imports(import_froms, str(file_path), ignore_codes))
        errors.extend(imports_module.check_relative_imports(import_froms, str(file_path), ignore_codes))
        
        # Check security issues
        errors.extend(security_module.check_security_issues(tree, content, str(file_path), ignore_codes))
        
        # Check individual nodes
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Pass max_complexity from config
                node_errors = visit_node(node, str(file_path), ignore_codes, ignore_names)
                complexity_errors = check_complexity(node, str(file_path), ignore_codes, max_complexity)
                errors.extend(node_errors)
                errors.extend(complexity_errors)
            else:
                errors.extend(visit_node(node, str(file_path), ignore_codes, ignore_names))
            
    except SyntaxError as e:
        error = models.StyleError(file_path=str(file_path),line_number=e.lineno or 0, column=e.offset or 0, error_code='E999', message=f"Syntax error: {e.msg}")
        errors.append(error)
    
    return errors


def check_directory(directory: Path, config: dict[str, Any], ignore_patterns: Optional[pathspec.PathSpec]) -> list[models.StyleError]:
    """Check all Python files in a directory recursively.
    
    Args:
        directory: Directory to check
        config: Configuration dictionary
        ignore_patterns: Patterns for files to ignore
        
    Returns:
        list of style errors found
    """
    all_errors = []
    
    for file_path in directory.rglob('*.py'):
        if file_utils_module.should_ignore_file(file_path, ignore_patterns):
            continue
            
        if any(excluded in file_path.parts 
               for excluded in config['exclude_dirs']):
            continue
            
        errors = check_file(file_path, config['ignore_codes'], config['ignore_names'], config)
        all_errors.extend(errors)
    
    return all_errors


def main() -> int:
    """Main entry point for the style checker.
    
    Returns:
        Exit code (0 for success, 1 for errors found)
    """
    parser = argparse.ArgumentParser(description='Modern Python style checker')
    parser.add_argument('paths', nargs='*', default=['.'], help='Paths to check (default: current directory)')
    parser.add_argument('--config', type=Path, help='Path to configuration file')
    parser.add_argument('--ignore', action='append', help='Error codes to ignore')
    parser.add_argument('--max-complexity', type=int, default=10, help='Maximum cyclomatic complexity (default: 10)')
    
    args = parser.parse_args()
    
    config = config_module.load_config(args.config)
    ignore_patterns = config_module.load_ignore_patterns()
    config['ignore_names'] = config_module.load_ignore_names()
    
    # Override complexity setting if provided
    if args.max_complexity:
        config['max_complexity'] = args.max_complexity
    
    if args.ignore:
        config['ignore_codes'].update(args.ignore)
    
    all_errors = []
    
    # Check all specified paths
    for path_str in args.paths:
        path = Path(path_str)
        if path.is_file():
            if file_utils_module.should_ignore_file(path, ignore_patterns):
                continue
            errors = check_file(path, config['ignore_codes'], config['ignore_names'], config)
            all_errors.extend(errors)
        elif path.is_dir():
            errors = check_directory(path, config, ignore_patterns)
            all_errors.extend(errors)
        else:
            print(f"Warning: Path not found: {path}", file=sys.stderr)
    
    # Sort and report results
    all_errors.sort(key=lambda e: (e.file_path, e.line_number))
    if all_errors:
        for error in all_errors:
            print(error)
        print(f"\nFound {len(all_errors)} style errors.")
        return 1
    else:
        print("All style checks passed!")
        return 0


if __name__ == '__main__':
    sys.exit(main())