import ast
import re

import models as models
import utils.file_utils as file_utils_module
import utils.patterns as patterns_module
import checkers.error_creation as error_creation_module

def check_variable(node: ast.Name, file_path: str, ignore_codes: set[str], ignore_names: set[str] = None) -> list[models.StyleError]:
    """Check variable naming.
    
    Args:
        node: Variable name node
        file_path: Path to file being checked
        ignore_codes: set of error codes to ignore
        ignore_names: set of names to ignore
        
    Returns:
        list of style errors found
    """
    errors = []
    ignore_names = ignore_names or set()
    
    # Skip if name should be ignored
    if file_utils_module.should_ignore_name(node.id, ignore_names):
        return errors
    
    if not patterns_module.is_snake_case(node.id):
        error = error_creation_module.create_error(node, 'N804', f"Variable name '{node.id}' should use snake_case", file_path, ignore_codes)
        if error:
            errors.append(error)
    
    if '__' in node.id and not node.id.startswith('__'):
        error = error_creation_module.create_error(node, 'N805', f"Inappropriate use of name mangling in variable '{node.id}'", file_path, ignore_codes)
        if error:
            errors.append(error)
    
    return errors


def check_class(node: ast.ClassDef, file_path: str, ignore_codes: set[str], ignore_names: set[str] = None) -> list[models.StyleError]:
    """Check class definition.
    
    Args:
        node: Class definition node
        file_path: Path to file being checked
        ignore_codes: set of error codes to ignore
        ignore_names: set of names to ignore
        
    Returns:
        list of style errors found
    """
    errors = []
    ignore_names = ignore_names or set()
    
    # Skip if name should be ignored
    if file_utils_module.should_ignore_name(node.name, ignore_names):
        return errors
    
    # Check naming convention
    if not patterns_module.is_pascal_case(node.name):
        error = error_creation_module.create_error(node, 'N801', f"Class name '{node.name}' should use PascalCase", file_path, ignore_codes)
        if error:
            errors.append(error)
    
    # Check docstring
    docstring = ast.get_docstring(node)
    if not docstring:
        error = error_creation_module.create_error(node, 'D101', f"Missing docstring in class '{node.name}'", file_path, ignore_codes)
        if error:
            errors.append(error)
    else:
        errors.extend(_check_docstring_format(node, docstring, file_path, ignore_codes))
    
    return errors


def check_function(node: ast.FunctionDef, file_path: str, ignore_codes: set[str], ignore_names: set[str] = None) -> list[models.StyleError]:
    """Check function definition.

    Args:
        node: Function definition node
        file_path: Path to file being checked
        ignore_codes: set of error codes to ignore
        ignore_names: set of names to ignore

    Returns:
        list of style errors found
    """
    errors = []
    ignore_names = ignore_names or set()
    is_test_file = 'test' in file_path.lower()

    if file_utils_module.should_ignore_name(node.name, ignore_names):
        return errors

    errors.extend(_check_function_name(node, file_path, ignore_codes, is_test_file))
    errors.extend(_check_name_mangling(node, file_path, ignore_codes))
    errors.extend(_check_function_docstrings(node, file_path, ignore_codes))
    errors.extend(_check_function_annotations(node, file_path, ignore_codes))
    errors.extend(_check_mutable_defaults(node, file_path, ignore_codes))

    return errors


def _check_function_name(node: ast.FunctionDef, file_path: str, ignore_codes: set[str], is_test_file: bool) -> list[models.StyleError]:
    """Check function naming convention.

    Args:
        node: Function definition node
        file_path: Path to file being checked
        ignore_codes: set of error codes to ignore
        is_test_file: whether the file is a test file

    Returns:
        list of style errors related to function naming
    """
    if node.name in models.SPECIAL_METHODS:
        return []
    if is_test_file and patterns_module.is_test_function_name(node.name):
        return []
    if not patterns_module.is_snake_case(node.name):
        error = error_creation_module.create_error(
            node, 'N802', f"Function name '{node.name}' should use snake_case", file_path, ignore_codes
        )
        return [error] if error else []
    return []


def _check_name_mangling(node: ast.FunctionDef, file_path: str, ignore_codes: set[str]) -> list[models.StyleError]:
    """Check for inappropriate name mangling.

    Args:
        node: Function definition node
        file_path: Path to file being checked
        ignore_codes: set of error codes to ignore

    Returns:
        list of style errors related to name mangling
    """
    if '__' in node.name and node.name not in models.SPECIAL_METHODS:
        error = error_creation_module.create_error(
            node, 'N805', f"Inappropriate use of name mangling in '{node.name}'", file_path, ignore_codes
        )
        return [error] if error else []
    return []


def _check_function_docstrings(node: ast.FunctionDef, file_path: str, ignore_codes: set[str]) -> list[models.StyleError]:
    """Check for missing or incorrect function docstring.

    Args:
        node: Function definition node
        file_path: Path to file being checked
        ignore_codes: set of error codes to ignore

    Returns:
        list of style errors related to function docstrings
    """
    errors = []
    docstring = ast.get_docstring(node)
    if not docstring:
        error = error_creation_module.create_error(
            node, 'D102', f"Missing docstring in function '{node.name}'", file_path, ignore_codes
        )
        if error:
            errors.append(error)
    else:
        errors.extend(_check_docstring_format(node, docstring, file_path, ignore_codes))
        errors.extend(_check_function_docstring(node, file_path, ignore_codes))
    return errors


def _check_docstring_format(node: ast.FunctionDef|ast.ClassDef, docstring: str, file_path: str, ignore_codes: set[str]) -> list[models.StyleError]:
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
        error = error_creation_module.create_error(node, 'D200', "Docstring should start with capital letter", file_path, ignore_codes)
        if error:
            errors.append(error)
    
    # Check ending punctuation
    if first_line and not first_line.endswith('.'):
        error = error_creation_module.create_error(node, 'D201', "Docstring should end with period", file_path, ignore_codes)
        if error:
            errors.append(error)
    
    return errors


def _check_function_docstring(node: ast.FunctionDef, file_path: str, ignore_codes: set[str]) -> list[models.StyleError]:
    """Check function docstring completeness.

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

    doc_args = _parse_docstring_args(docstring)
    func_args = [arg.arg for arg in node.args.args if arg.arg not in models.SPECIAL_VARIABLES]

    if func_args:
        errors.extend(_check_missing_doc_args(node, func_args, doc_args, file_path, ignore_codes))
        errors.extend(_check_extra_doc_args(node, func_args, doc_args, file_path, ignore_codes))

    if node.name not in ['__init__', '__enter__', '__exit__']:
        errors.extend(_check_missing_returns_section(node, docstring, file_path, ignore_codes))

    return errors

def _check_missing_doc_args(node: ast.FunctionDef, func_args: list[str], doc_args: set[str], file_path: str, ignore_codes: set[str]) -> list[models.StyleError]:
    """Check for arguments in signature that are missing in the docstring.

    Args:
        node: AST node for the function definition
        func_args: List of argument names in the function signature
        doc_args: Set of argument names documented in the docstring
        file_path: Path to file being checked
        ignore_codes: set of error codes to ignore

    Returns:
        list of style errors for missing documented arguments
    """
    errors = []
    for arg in func_args:
        if arg not in doc_args:
            error = error_creation_module.create_error(node, 'D304', f"Argument '{arg}' not documented in docstring", file_path, ignore_codes)
            if error:
                errors.append(error)
    return errors

def _check_extra_doc_args(node: ast.FunctionDef, func_args: list[str], doc_args: set[str], file_path: str, ignore_codes: set[str]) -> list[models.StyleError]:
    """Check for arguments documented in the docstring but missing from the signature.

    Args:
        node: AST node for the function definition
        func_args: List of argument names in the function signature
        doc_args: Set of argument names documented in the docstring
        file_path: Path to file being checked
        ignore_codes: set of error codes to ignore

    Returns:
        list of style errors for undocumented parameters in the function signature
    """
    errors = []
    func_arg_set = set(func_args)
    for doc_arg in doc_args:
        if doc_arg not in func_arg_set:
            error = error_creation_module.create_error(node, 'D305', f"Documented argument '{doc_arg}' not found in function signature", file_path, ignore_codes)
            if error:
                errors.append(error)
    return errors

def _check_missing_returns_section(node: ast.FunctionDef, docstring: str, file_path: str, ignore_codes: set[str]) -> list[models.StyleError]:
    """Check if a Returns section is missing from the docstring.

    Args:
        node: AST node for the function definition
        docstring: The full docstring content of the function
        file_path: Path to file being checked
        ignore_codes: set of error codes to ignore

    Returns:
        list containing a style error if the Returns section is missing, or empty list otherwise
    """
    errors = []
    if not _has_returns_section(docstring):
        error = error_creation_module.create_error(node, 'D307', f"Function '{node.name}' missing Returns section in docstring", file_path, ignore_codes)
        if error:
            errors.append(error)
    return errors


def _parse_docstring_args(docstring: str) -> set[str]:
    """Parse arguments section from Google-style docstring.
    
    Args:
        docstring: The docstring to parse
        
    Returns:
        Set of documented argument names
    """
    args_section = set()
    
    # Find Args: section
    lines = docstring.split('\n')
    in_args_section = False
    
    for line in lines:
        stripped_line = line.strip()
        
        # Check if we're entering the Args section
        if stripped_line in ['Args:', 'Arguments:']:
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
            arg_match = re.match(r'^(\w+)\s*(?:\([^)]+\))?\s*:\s*(.*)$', stripped_line)
            if not arg_match:
                continue
            arg_name = arg_match.group(1).strip()
            args_section.add(arg_name)
    
    return args_section


def _has_returns_section(docstring: str) -> bool:
    """Check if docstring has a Returns section.
    
    Args:
        docstring: The docstring to check
        
    Returns:
        True if Returns section exists, False otherwise
    """
    lines = docstring.split('\n')
    
    for line in lines:
        stripped_line = line.strip()
        if stripped_line in ['Returns:', 'Return:']:
            return True
    
    return False


def _check_function_annotations(node: ast.FunctionDef, file_path: str, ignore_codes: set[str]) -> list[models.StyleError]:
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
        if arg.arg in models.SPECIAL_VARIABLES:
            continue
        if not arg.annotation:
            error = error_creation_module.create_error(node, 'ANN001',f"Missing type annotation for argument '{arg.arg}'",file_path, ignore_codes)
            if error:
                errors.append(error)
    
    # Check return annotation
    if not node.returns:
        error = error_creation_module.create_error(node, 'ANN002', f"Missing return type annotation for function '{node.name}'", file_path, ignore_codes)
        if error:
            errors.append(error)
    
    return errors


def _check_mutable_defaults(node: ast.FunctionDef, file_path: str, ignore_codes: set[str]) -> list[models.StyleError]:
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
        error = error_creation_module.create_error(node, 'B006', f"Mutable default argument in function '{node.name}'", file_path, ignore_codes)
        if error:
            errors.append(error)
    
    return errors