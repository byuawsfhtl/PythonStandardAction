import ast

import models as models
import utils.file_utils as file_utils_module
import utils.ast_helpers as ast_helpers_module
import utils.patterns as patterns_module
import checkers.error_creation as error_creation_module

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
    
    # Skip if name should be ignored
    if file_utils_module.should_ignore_name(node.name, ignore_names):
        return errors
    
    # Check naming convention
    if node.name in models.SPECIAL_METHODS:
        pass  # Special methods are exempt
    elif is_test_file and patterns_module.is_test_function_name(node.name):
        pass  # Test functions follow different convention
    elif not patterns_module.is_snake_case(node.name):
        error = error_creation_module.create_error(node, 'N802', f"Function name '{node.name}' should use snake_case", file_path, ignore_codes)
        if error:
            errors.append(error)
    
    # Check for inappropriate name mangling
    if '__' in node.name and node.name not in models.SPECIAL_METHODS:
        error = error_creation_module.create_error(node, 'N805', f"Inappropriate use of name mangling in '{node.name}'", file_path, ignore_codes)
        if error:
            errors.append(error)
    
    # Check docstring
    docstring = ast.get_docstring(node)
    if not docstring:
        error = error_creation_module.create_error(node, 'D102', f"Missing docstring in function '{node.name}'", file_path, ignore_codes)
        if error:
            errors.append(error)
    else:
        errors.extend(_check_docstring_format(node, docstring, file_path, ignore_codes))
        errors.extend(_check_function_docstring(node, file_path, ignore_codes))
    
    # Check type annotations
    errors.extend(_check_function_annotations(node, file_path, ignore_codes))
    
    # Check for mutable defaults
    errors.extend(_check_mutable_defaults(node, file_path, ignore_codes))
    
    return errors


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
    doc_args = ast_helpers_module.parse_docstring_args(docstring)
    
    # Get function argument names (excluding self/cls)
    func_args = [arg.arg for arg in node.args.args if arg.arg not in models.SPECIAL_VARIABLES]
    
    # Only check documentation if function has arguments
    if not func_args:
        return errors
    
    # Check if all function arguments are documented
    for arg in node.args.args:
        if arg.arg in models.SPECIAL_VARIABLES:
            continue
            
        if arg.arg not in doc_args:
            error = error_creation_module.create_error(node, 'D304', f"Argument '{arg.arg}' not documented in docstring", file_path, ignore_codes)
            if error:
                errors.append(error)
        else:
            # Check type consistency if both annotation and docstring type exist
            actual_type = ast_helpers_module.get_type_string(arg.annotation)
            doc_type = doc_args[arg.arg]
            inconsistent_typing = actual_type != doc_type
            
            # Only check type consistency if we have both and they're not generic
            if (actual_type and doc_type and inconsistent_typing and doc_type != "Any" and actual_type != "<unknown>"):
                error = error_creation_module.create_error(node, 'D306', f"Type mismatch for '{arg.arg}': annotation='{actual_type}' docstring='{doc_type}'", file_path, ignore_codes)
                if error:
                    errors.append(error)
    
    # Check for documented args that don't exist
    func_arg_names = {arg.arg for arg in node.args.args}
    for doc_arg in doc_args:
        if doc_arg in func_arg_names:
            continue
        error = error_creation_module.create_error(node, 'D305', f"Documented argument '{doc_arg}' not found in function signature", file_path, ignore_codes)
        if error:
            errors.append(error)
    
    return errors


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