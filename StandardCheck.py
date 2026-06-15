import ast
import sys
import argparse
from pathlib import Path
from typing import Any, Optional

import pathspec

import models as models
import config as config_module
import utils.file_utils as file_utils_module
import utils.ast_helpers as ast_helpers_module
import checkers.common_nodes as common_nodes_module
import checkers.imports as imports_module
import checkers.security as security_module
import checkers.complexity as complexity_module


def visit_node(node: ast.AST, file_path: str, ignore_codes: set[str], ignore_names: set[str] = set()) -> list[models.StyleError]:
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
    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return common_nodes_module.check_function(node, file_path, ignore_codes, ignore_names)
    elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
        return common_nodes_module.check_variable(node, file_path, ignore_codes, ignore_names)
    else:
        return []


def check_file(file_path: Path, ignore_codes: set[str], ignore_names: set[str] = set(), config: dict[str, Any] = {}) -> list[models.StyleError]:
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
    max_complexity = config.get('max_complexity', 15)
    max_indentation = config.get('max_indentation', 4)

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    tree = ast_helpers_module.parse_ast_safely(content, file_path)
    if isinstance(tree, list):  # list means syntax error already returned
        return tree

    all_imports, import_froms = imports_module.collect_imports(tree)
    used_names = ast_helpers_module.collect_used_names(tree)

    errors.extend(imports_module.check_imports(all_imports, import_froms, used_names, file_path, ignore_codes))
    errors.extend(security_module.check_security_issues(tree, content, str(file_path), ignore_codes))
    errors.extend(complexity_module.check_complexity(tree, content, str(file_path), ignore_codes, max_complexity, max_indentation))

    for node in ast.walk(tree):
        errors.extend(visit_node(node, str(file_path), ignore_codes, ignore_names))

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
    parser.add_argument('--max-complexity', type=int, default=15, help='Maximum cyclomatic complexity (default: 15)')
    
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