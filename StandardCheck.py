
import ast
import re
import sys
import argparse
import pathspec
from pathlib import Path
from dataclasses import dataclass
from typing import Any, FrozenSet, Optional

@dataclass
class StyleError:
    """Represents a style violation."""
    file_path: str
    line_number: int
    column: int
    error_code: str
    message: str
    
    def __str__(self) -> str:
        """Converts the error dataclass to a string.

        Returns:
            str: the error as a str
        """
        return f"{self.file_path}:{self.line_number}:{self.column}: {self.error_code} {self.message}"


# Error codes following industry conventions (similar to flake8)
ERROR_CODES = {
    'N801': 'class name should use PascalCase',
    'N802': 'function name should use snake_case',
    'N803': 'argument name should use snake_case',
    'N804': 'variable name should use snake_case',
    'N805': 'inappropriate use of name mangling',
    'ANN001': 'missing type annotation for function argument',
    'ANN002': 'missing return type annotation',
    'D100': 'missing docstring in public module',
    'D101': 'missing docstring in public class',
    'D102': 'missing docstring in public method',
    'D103': 'missing docstring in public function',
    'D200': 'docstring should start with capital letter',
    'D201': 'docstring should end with period',
    'D300': 'missing Args section in docstring',
    'D301': 'missing Returns section in docstring',
    'D302': 'docstring Args section is malformed',
    'D303': 'docstring Returns section is malformed',
    'D304': 'argument not documented in docstring',
    'D305': 'documented argument not found in function signature',
    'D306': 'type mismatch between annotation and docstring',
    'B006': 'mutable default argument',
}

# Standard special methods and variables
SPECIAL_METHODS: FrozenSet[str] = frozenset([
    '__init__', '__del__', '__repr__', '__str__', '__bytes__', '__format__',
    '__lt__', '__le__', '__eq__', '__ne__', '__gt__', '__ge__', '__hash__',
    '__bool__', '__call__', '__len__', '__getitem__', '__setitem__',
    '__delitem__', '__iter__', '__next__', '__reversed__', '__contains__',
    '__add__', '__sub__', '__mul__', '__matmul__', '__truediv__',
    '__floordiv__', '__mod__', '__divmod__', '__pow__', '__lshift__',
    '__rshift__', '__and__', '__xor__', '__or__', '__iadd__', '__isub__',
    '__imul__', '__imatmul__', '__itruediv__', '__ifloordiv__', '__imod__',
    '__ipow__', '__ilshift__', '__irshift__', '__iand__', '__ixor__',
    '__ior__', '__neg__', '__pos__', '__abs__', '__invert__', '__complex__',
    '__int__', '__float__', '__round__', '__index__', '__enter__',
    '__exit__', '__await__', '__aiter__', '__anext__', '__aenter__',
    '__aexit__', '__new__'
])

SPECIAL_VARIABLES: FrozenSet[str] = frozenset(['self', 'cls'])

PYTEST_METHODS: FrozenSet[str] = frozenset([
    'setup_module', 'teardown_module', 'setup_class', 'teardown_class',
    'setup_method', 'teardown_method', 'setup_function', 'teardown_function'
])


def load_config(config_file: Optional[Path]) -> dict[str, Any]:
    """Load configuration from file or use defaults.
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        Configuration dictionary
    """
    # Default configuration
    config = {
        'ignore_codes': set(),
        'max_line_length': 88,  # Black default
        'exclude_dirs': {'.git', '__pycache__', '.pytest_cache', '.mypy_cache'},
    }
    
    # TODO: Implement TOML/INI config file loading for production use
    return config


def load_ignore_patterns() -> Optional[pathspec.PathSpec]:
    """Load ignore patterns from .standardignore file.
    
    Returns:
        PathSpec object for pattern matching, or None if no patterns
    """
    ignore_file = Path('.standardignore')
    if not ignore_file.exists():
        return None

    with open(ignore_file, 'r', encoding='utf-8') as f:
        patterns = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return pathspec.PathSpec.from_lines('gitwildmatch', patterns)

def should_ignore_file(file_path: Path, ignore_patterns: Optional[pathspec.PathSpec]) -> bool:
    """Check if file should be ignored based on patterns.
    
    Args:
        file_path: Path to check
        ignore_patterns: Patterns to check against
        
    Returns:
        True if file should be ignored
    """
    if not ignore_patterns:
        return False
    path_str = str(file_path)
    return ignore_patterns.match_file(path_str)

def create_error(node: ast.AST, error_code: str, message: str, file_path: str, ignore_codes: set[str]) -> Optional[StyleError]:
    """Create a style error if not ignored.
    
    Args:
        node: AST node where error occurred
        error_code: Error code from ERROR_CODES
        message: Descriptive error message
        file_path: Path to file containing the error
        ignore_codes: set of error codes to ignore
        
    Returns:
        StyleError instance or None if ignored
    """
    if error_code in ignore_codes:
        return None
        
    return StyleError(
        file_path=file_path,
        line_number=getattr(node, 'lineno', 0),
        column=getattr(node, 'col_offset', 0),
        error_code=error_code,
        message=message
    )


def is_snake_case(name_of_var: str) -> bool:
    """Check if name follows snake_case convention.
    
    Args:
        name_of_var: Name to check
        
    Returns:
        True if name is valid snake_case
    """
    # Allow single letters, constants (ALL_CAPS), and private names
    if len(name_of_var) == 1 or name_of_var.isupper() or name_of_var.startswith('_'):
        return True
        
    # Standard snake_case pattern
    return bool(re.match(r'^[a-z][a-z0-9_]*$', name_of_var))


def is_pascal_case(name: str) -> bool:
    """Check if name follows PascalCase convention.
    
    Args:
        name: Name to check
        
    Returns:
        True if name is valid PascalCase
    """
    return bool(re.match(r'^[A-Z][A-Za-z0-9]*$', name))


def is_test_function_name(name: str) -> bool:
    """Check if name follows test function conventions.
    
    Args:
        name: Function name to check
        
    Returns:
        True if name follows test conventions
    """
    return (name.startswith('test_') and is_snake_case(name)) or name in PYTEST_METHODS


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
    
    for line in lines:
        line = line.strip()
        if line == 'Args:':
            in_args_section = True
            continue
        elif line.endswith(':') and in_args_section:
            # New section started
            break
        elif in_args_section and line:
            # Parse argument line: "name (type): description"
            match = re.match(r'^(\w+)\s*\(([^)]+)\):\s*(.+)$', line)
            if match:
                arg_name, arg_type, description = match.groups()
                args_section[arg_name.strip()] = arg_type.strip()
                
    return args_section


def check_docstring_format(node: ast.FunctionDef|ast.ClassDef, docstring: str, file_path: str, ignore_codes: set[str]) -> list[StyleError]:
    """Check docstring formatting rules.
    
    Args:
        node: AST node (function or class)
        docstring: The docstring content
        file_path: Path to file being checked
        ignore_codes: set of error codes to ignore
        
    Returns:
        list of style errors found
    """
    errors = []
    if not docstring:
        return errors
    first_line = docstring.split('\n')[0].strip()
    
    # Check capitalization
    if first_line and first_line[0].islower():
        error = create_error(node, 'D200', "Docstring should start with capital letter", file_path, ignore_codes)
        if error:
            errors.append(error)
    
    # Check ending punctuation
    if first_line and not first_line.endswith('.'):
        error = create_error(node, 'D201', "Docstring should end with period", file_path, ignore_codes)
        if error:
            errors.append(error)
    
    return errors


def check_function_docstring(node: ast.FunctionDef, file_path: str, ignore_codes: set[str]) -> list[StyleError]:
    """Check function docstring completeness and accuracy.
    
    Args:
        node: Function definition node
        file_path: Path to file being checked
        ignore_codes: set of error codes to ignore
        
    Returns:
        list of style errors found
    """
    errors = []
    docstring = ast.get_docstring(node)
    
    if not docstring:
        return errors
        
    # Parse documented arguments
    doc_args = parse_docstring_args(docstring)
    
    # Check if all function arguments are documented
    for arg in node.args.args:
        if arg.arg in SPECIAL_VARIABLES:
            continue
            
        if arg.arg not in doc_args:
            error = create_error(node, 'D304', f"Argument '{arg.arg}' not documented in docstring", file_path, ignore_codes)
            if error:
                errors.append(error)
        else:
            # Check type consistency
            actual_type = get_type_string(arg.annotation)
            if actual_type and actual_type != doc_args[arg.arg]:
                error = create_error(node, 'D306',f"Type mismatch for '{arg.arg}': "f"annotation='{actual_type}', "f"docstring='{doc_args[arg.arg]}'", file_path, ignore_codes)
                if error:
                    errors.append(error)
    
    # Check for documented args that don't exist
    func_arg_names = {arg.arg for arg in node.args.args}
    for doc_arg in doc_args:
        if doc_arg not in func_arg_names:
            error = create_error(node, 'D305', f"Documented argument '{doc_arg}' not found in function signature", file_path, ignore_codes)
            if error:
                errors.append(error)
    
    return errors


def check_class(node: ast.ClassDef, file_path: str, ignore_codes: set[str]) -> list[StyleError]:
    """Check class definition.
    
    Args:
        node: Class definition node
        file_path: Path to file being checked
        ignore_codes: set of error codes to ignore
        
    Returns:
        list of style errors found
    """
    errors = []
    
    # Check naming convention
    if not is_pascal_case(node.name):
        error = create_error(node, 'N801', 
                           f"Class name '{node.name}' should use PascalCase", 
                           file_path, ignore_codes)
        if error:
            errors.append(error)
    
    # Check docstring
    docstring = ast.get_docstring(node)
    if not docstring:
        error = create_error(node, 'D101', 
                           f"Missing docstring in class '{node.name}'", 
                           file_path, ignore_codes)
        if error:
            errors.append(error)
    else:
        errors.extend(check_docstring_format(node, docstring, file_path, ignore_codes))
    
    return errors


def check_function(node: ast.FunctionDef, file_path: str, ignore_codes: set[str]) -> list[StyleError]:
    """Check function definition.
    
    Args:
        node: Function definition node
        file_path: Path to file being checked
        ignore_codes: set of error codes to ignore
        
    Returns:
        list of style errors found
    """
    errors = []
    is_test_file = 'test' in file_path.lower()
    
    # Check naming convention
    if node.name in SPECIAL_METHODS:
        pass  # Special methods are exempt
    elif is_test_file and is_test_function_name(node.name):
        pass  # Test functions follow different convention
    elif not is_snake_case(node.name):
        error = create_error(node, 'N802', f"Function name '{node.name}' should use snake_case", file_path, ignore_codes)
        if error:
            errors.append(error)
    
    # Check for inappropriate name mangling
    if '__' in node.name and node.name not in SPECIAL_METHODS:
        error = create_error(node, 'N805', f"Inappropriate use of name mangling in '{node.name}'", file_path, ignore_codes)
        if error:
            errors.append(error)
    
    # Check docstring
    docstring = ast.get_docstring(node)
    if not docstring:
        error = create_error(node, 'D102', f"Missing docstring in function '{node.name}'", file_path, ignore_codes)
        if error:
            errors.append(error)
    else:
        errors.extend(check_docstring_format(node, docstring, file_path, ignore_codes))
        errors.extend(check_function_docstring(node, file_path, ignore_codes))
    
    # Check type annotations
    errors.extend(check_function_annotations(node, file_path, ignore_codes))
    
    # Check for mutable defaults
    errors.extend(check_mutable_defaults(node, file_path, ignore_codes))
    
    return errors


def check_function_annotations(node: ast.FunctionDef, file_path: str, ignore_codes: set[str]) -> list[StyleError]:
    """Check function type annotations.
    
    Args:
        node: Function definition node
        file_path: Path to file being checked
        ignore_codes: set of error codes to ignore
        
    Returns:
        list of style errors found
    """
    errors = []
    
    # Check parameter annotations
    for arg in node.args.args:
        if arg.arg in SPECIAL_VARIABLES:
            continue
        if not arg.annotation:
            error = create_error(node, 'ANN001',f"Missing type annotation for argument '{arg.arg}'",file_path, ignore_codes)
            if error:
                errors.append(error)
    
    # Check return annotation
    if not node.returns:
        error = create_error(node, 'ANN002', f"Missing return type annotation for function '{node.name}'", file_path, ignore_codes)
        if error:
            errors.append(error)
    
    return errors


def check_mutable_defaults(node: ast.FunctionDef, file_path: str, ignore_codes: set[str]) -> list[StyleError]:
    """Check for mutable default arguments.
    
    Args:
        node: Function definition node
        file_path: Path to file being checked
        ignore_codes: set of error codes to ignore
        
    Returns:
        list of style errors found
    """
    errors = []
    
    for default in node.args.defaults:
        if not isinstance(default, (ast.List, ast.Dict, ast.Set)):
            continue
        error = create_error(node, 'B006', f"Mutable default argument in function '{node.name}'", file_path, ignore_codes)
        if error:
            errors.append(error)
    
    return errors


def check_variable(node: ast.Name, file_path: str, ignore_codes: set[str]) -> list[StyleError]:
    """Check variable naming.
    
    Args:
        node: Variable name node
        file_path: Path to file being checked
        ignore_codes: set of error codes to ignore
        
    Returns:
        list of style errors found
    """
    errors = []
    
    if not is_snake_case(node.id):
        error = create_error(node, 'N804', f"Variable name '{node.id}' should use snake_case", file_path, ignore_codes)
        if error:
            errors.append(error)
    
    if '__' in node.id and not node.id.startswith('__'):
        error = create_error(node, 'N805', f"Inappropriate use of name mangling in variable '{node.id}'", file_path, ignore_codes)
        if error:
            errors.append(error)
    
    return errors


def visit_node(node: ast.AST, file_path: str, ignore_codes: set[str]) -> list[StyleError]:
    """Visit an AST node and perform checks.
    
    Args:
        node: AST node to check
        file_path: Path to file containing the node
        ignore_codes: set of error codes to ignore
        
    Returns:
        list of style errors found
    """
    if isinstance(node, ast.ClassDef):
        return check_class(node, file_path, ignore_codes)
    elif isinstance(node, ast.FunctionDef):
        return check_function(node, file_path, ignore_codes)
    elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
        return check_variable(node, file_path, ignore_codes)
    else:
        return []


def check_file(file_path: Path, ignore_codes: set[str]) -> list[StyleError]:
    """Check a single Python file.
    
    Args:
        file_path: Path to Python file to check
        ignore_codes: set of error codes to ignore
        
    Returns:
        list of style errors found
    """
    errors = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        tree = ast.parse(content, filename=str(file_path))
        
        for node in ast.walk(tree):
            errors.extend(visit_node(node, str(file_path), ignore_codes))
            
    except SyntaxError as e:
        error = StyleError(
            file_path=str(file_path),
            line_number=e.lineno or 0,
            column=e.offset or 0,
            error_code='E999',
            message=f"Syntax error: {e.msg}"
        )
        errors.append(error)
    
    return errors


def check_directory(directory: Path, config: dict[str, Any], ignore_patterns: Optional[pathspec.PathSpec]) -> list[StyleError]:
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
        if should_ignore_file(file_path, ignore_patterns):
            continue
            
        if any(excluded in file_path.parts 
               for excluded in config['exclude_dirs']):
            continue
            
        errors = check_file(file_path, config['ignore_codes'])
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
    
    args = parser.parse_args()
    
    config = load_config(args.config)
    ignore_patterns = load_ignore_patterns()
    
    if args.ignore:
        config['ignore_codes'].update(args.ignore)
    
    all_errors = []
    
    # Check all specified paths
    for path_str in args.paths:
        path = Path(path_str)
        if path.is_file():
            if should_ignore_file(path, ignore_patterns):
                continue
            errors = check_file(path, config['ignore_codes'])
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