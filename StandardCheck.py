import ast
import fnmatch
import os
import re
import sys
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass
from pathlib import Path
import importlib.util

@dataclass
class CodeError:
    """Represents a code formatting error."""
    filename: str
    line_number: int
    function_name: Optional[str]
    message: str
    
    def __str__(self) -> str:
        function_part = f"Function {self.function_name}: " if self.function_name else ""
        return f"{self.filename}:{self.line_number}: {function_part}{self.message}"

@dataclass
class IgnoreRule:
    """Represents a rule for ignoring specific standards in specific locations."""
    standard_type: str  # e.g., 'naming', 'docstring', 'type_annotation'
    location_type: str  # e.g., 'function', 'class', 'variable'
    location_path: str  # e.g., 'MyClass.my_method', 'global.my_variable'
    specific_name: Optional[str] = None  # specific item name to ignore

# Standard sets for reference
SPECIAL_METHODS = {
    '__init__', '__del__', '__repr__', '__str__', '__bytes__', '__format__', '__lt__',
    '__le__', '__eq__', '__ne__', '__gt__', '__ge__', '__hash__', '__bool__', '__call__',
    '__len__', '__getitem__', '__setitem__', '__delitem__', '__iter__', '__next__',
    '__reversed__', '__contains__', '__add__', '__sub__', '__mul__', '__matmul__',
    '__truediv__', '__floordiv__', '__mod__', '__divmod__', '__pow__', '__lshift__',
    '__rshift__', '__and__', '__xor__', '__or__', '__iadd__', '__isub__', '__imul__',
    '__imatmul__', '__itruediv__', '__ifloordiv__', '__imod__', '__ipow__', '__ilshift__',
    '__irshift__', '__iand__', '__ixor__', '__ior__', '__neg__', '__pos__', '__abs__',
    '__invert__', '__complex__', '__int__', '__float__', '__round__', '__index__',
    '__enter__', '__exit__', '__await__', '__aiter__', '__anext__', '__aenter__', '__aexit__',
    '__version__', '__new__'
}

PYTEST_METHODS = {
    'setup_module', 'teardown_module', 'setup_class', 'teardown_class',
    'setup_method', 'teardown_method', 'setup_function', 'teardown_function'
}

SPECIAL_VARIABLES = {'self', 'cls', '*args', '**kwargs'}

# Validation functions
def is_snake_case(name: str) -> bool:
    """Check if a name follows snake_case convention."""
    return re.fullmatch(r'^[a-z][a-z0-9_]*$', name) is not None

def is_pascal_case(name: str) -> bool:
    """Check if a name follows PascalCase convention."""
    return re.fullmatch(r'^[A-Z][A-Za-z0-9]*$', name) is not None

def is_screaming_snake_case(name: str) -> bool:
    """Check if a name follows SCREAMING_SNAKE_CASE convention."""
    return re.fullmatch(r'^[A-Z][A-Z0-9_]*$', name) is not None

def is_test_function_case(name: str) -> bool:
    """Check if a name follows test function naming convention."""
    return re.fullmatch(r'^test_[a-z][a-z0-9_]*$', name) is not None

def is_valid_variable_name(name: str, is_test_file: bool = False) -> bool:
    """Check if a variable name is valid according to our standards."""
    if name in SPECIAL_VARIABLES:
        return True
    if name.startswith('_'):
        return True
    if is_screaming_snake_case(name):  # Constants
        return True
    return is_snake_case(name)

def is_valid_function_name(name: str, is_test_file: bool = False) -> bool:
    """Check if a function name is valid according to our standards."""
    if name in SPECIAL_METHODS:
        return True
    if name in PYTEST_METHODS:
        return True
    if is_test_file and name.startswith('test_'):
        return is_test_function_case(name)
    return is_snake_case(name)

def is_valid_class_name(name: str) -> bool:
    """Check if a class name is valid according to our standards."""
    return is_pascal_case(name)

# Ignore system functions
def load_ignore_config(ignore_file: str = '.standardignore.py') -> Dict[str, Any]:
    """Load ignore configuration from Python file."""
    if not os.path.exists(ignore_file):
        return {}
    
    spec = importlib.util.spec_from_file_location(".standardignore", ignore_file)
    if spec is None or spec.loader is None:
        return {}
    
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        return vars(module)
    except:
        return {}

def extract_ignore_rules_from_config(config: Dict[str, Any]) -> List[IgnoreRule]:
    """Extract ignore rules from loaded configuration."""
    rules = []
    for attr_name, attr_value in config.items():
        if attr_name.startswith('_') and isinstance(attr_value, dict):
            continue
        if not all(key in attr_value for key in ['standard_type', 'location_type', 'location_path']):
            continue
        rule = IgnoreRule(
            standard_type=attr_value['standard_type'],
            location_type=attr_value['location_type'],
            location_path=attr_value['location_path'],
            specific_name=attr_value.get('specific_name')
        )
        rules.append(rule)
    return rules

def should_ignore_error(error_type: str, location_path: str, item_name: str, rules: List[IgnoreRule]) -> bool:
    """Check if an error should be ignored based on ignore rules."""
    for rule in rules:
        if rule.standard_type != error_type:
            continue
        if rule.location_path not in location_path:
            continue
        if rule.specific_name is not None and rule.specific_name != item_name:
            continue
        return True
    return False

def should_ignore_file(file_path: str, filename: str, config: Dict[str, Any]) -> bool:
    """Check if an entire file should be ignored."""
    # Check file patterns
    ignore_patterns = config.get('ignore_file_patterns', [])
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(file_path, pattern):
            return True
    
    # Check specific files
    ignore_files = config.get('ignore_files', [])
    if filename in ignore_files or file_path in ignore_files:
        return True
    
    return False

def get_location_path(context_stack: List[str]) -> str:
    """Get the location path for a node (e.g., 'MyClass.my_method')."""
    return '.'.join(context_stack) if context_stack else 'global'

# Type annotation handling
def extract_type_from_simple_node(node: ast.expr) -> str:
    """Extract type from simple AST nodes."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant):
        return repr(node.value)
    return "Unknown"

def extract_type_from_complex_node(node: ast.expr) -> str:
    """Extract type from complex AST nodes."""
    if isinstance(node, ast.Attribute):
        return f"{extract_type_annotation(node.value)}.{node.attr}"
    if isinstance(node, ast.Subscript):
        return f"{extract_type_annotation(node.value)}[{extract_type_annotation(node.slice)}]"
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return f"{extract_type_annotation(node.left)} | {extract_type_annotation(node.right)}"
    if isinstance(node, ast.Tuple):
        elements = [extract_type_annotation(elt) for elt in node.elts]
        return f"({', '.join(elements)})"
    return "Unknown"

def extract_type_annotation(annotation: Optional[ast.expr]) -> Optional[str]:
    """Extract type annotation as string from AST node."""
    if annotation is None:
        return None
    
    # Try simple nodes first
    simple_result = extract_type_from_simple_node(annotation)
    if simple_result != "Unknown":
        return simple_result
    
    # Handle complex nodes
    return extract_type_from_complex_node(annotation)

# Docstring validation functions
def validate_docstring_description(description: str) -> List[str]:
    """Validate docstring description format."""
    issues = []
    if not description:
        issues.append("empty description")
        return issues
    
    if not description[0].isupper():
        issues.append("description must start with capital letter")
    if not description.endswith('.'):
        issues.append("description must end with period")
    
    return issues

def validate_docstring_format(docstring: str) -> List[str]:
    """Validate docstring format and return list of issues."""
    if not docstring:
        return ["missing docstring"]
    
    lines = docstring.strip().split('\n')
    description = lines[0].strip()
    return validate_docstring_description(description)

# Function checking functions
def check_function_naming(node: ast.FunctionDef, filename: str, location_path: str, ignore_rules: List[IgnoreRule]) -> Optional[CodeError]:
    """Check function naming conventions."""
    if should_ignore_error('naming', location_path, node.name, ignore_rules):
        return None
    
    is_test_file = '/tests/' in filename or filename.endswith('_test.py')
    if is_valid_function_name(node.name, is_test_file):
        return None
    
    return CodeError(
        filename, node.lineno, node.name,
        f"Function '{node.name}' does not follow naming convention"
    )

def check_function_name_mangling(node: ast.FunctionDef, filename: str, location_path: str,ignore_rules: List[IgnoreRule]) -> Optional[CodeError]:
    """Check for inappropriate name mangling."""
    if '__' not in node.name or node.name in SPECIAL_METHODS:
        return None
    
    if should_ignore_error('name_mangling', location_path, node.name, ignore_rules):
        return None
    
    return CodeError(
        filename, node.lineno, node.name,
        f"Function '{node.name}' uses inappropriate name mangling"
    )

def check_parameter_naming(arg: ast.arg, node: ast.FunctionDef, filename: str, location_path: str, ignore_rules: List[IgnoreRule]) -> Optional[CodeError]:
    """Check parameter naming convention."""
    if arg.arg in SPECIAL_VARIABLES:
        return None
    
    param_location = f"{location_path}.{arg.arg}"
    if should_ignore_error('naming', param_location, arg.arg, ignore_rules):
        return None
    
    if is_valid_variable_name(arg.arg):
        return None
    
    return CodeError(
        filename, node.lineno, node.name,
        f"Parameter '{arg.arg}' does not follow naming convention"
    )

def check_parameter_type_annotation(arg: ast.arg, node: ast.FunctionDef, filename: str, location_path: str, ignore_rules: List[IgnoreRule]) -> Optional[CodeError]:
    """Check parameter type annotation."""
    if arg.arg in SPECIAL_VARIABLES:
        return None
    
    param_location = f"{location_path}.{arg.arg}"
    if should_ignore_error('type_annotation', param_location, arg.arg, ignore_rules):
        return None
    
    if arg.annotation is not None:
        return None
    
    return CodeError(
        filename, node.lineno, node.name,
        f"Parameter '{arg.arg}' missing type annotation"
    )

def check_return_type_annotation(node: ast.FunctionDef, filename: str, location_path: str, ignore_rules: List[IgnoreRule]) -> Optional[CodeError]:
    """Check return type annotation."""
    if should_ignore_error('type_annotation', location_path, 'return', ignore_rules):
        return None
    
    if node.returns is not None:
        return None
    
    return CodeError(
        filename, node.lineno, node.name,
        "Function missing return type annotation"
    )

def check_mutable_defaults(node: ast.FunctionDef, filename: str, location_path: str, ignore_rules: List[IgnoreRule]) -> List[CodeError]:
    """Check for mutable default arguments."""
    errors = []
    
    for default in node.args.defaults:
        if not isinstance(default, (ast.Dict, ast.List, ast.Set)):
            continue
        
        if should_ignore_error('mutable_default', location_path, node.name, ignore_rules):
            continue
        
        error = CodeError(
            filename, node.lineno, node.name,
            "Function has mutable default argument"
        )
        errors.append(error)
    
    return errors

def check_function_docstring(node: ast.FunctionDef, filename: str, location_path: str, ignore_rules: List[IgnoreRule]) -> List[CodeError]:
    """Check function docstring."""
    if should_ignore_error('docstring', location_path, node.name, ignore_rules):
        return []
    
    docstring = ast.get_docstring(node)
    if not docstring:
        return [CodeError(
            filename, node.lineno, node.name,
            "Function missing docstring"
        )]
    
    errors = []
    docstring_issues = validate_docstring_format(docstring)
    for issue in docstring_issues:
        errors.append(CodeError(
            filename, node.lineno, node.name,
            f"Docstring {issue}"
        ))
    
    return errors

def check_function_parameters(node: ast.FunctionDef, filename: str, location_path: str, ignore_rules: List[IgnoreRule]) -> List[CodeError]:
    """Check all function parameters."""
    errors = []
    
    for arg in node.args.args:
        # Check parameter naming
        naming_error = check_parameter_naming(arg, node, filename, location_path, ignore_rules)
        if naming_error:
            errors.append(naming_error)
        
        # Check type annotations
        type_error = check_parameter_type_annotation(arg, node, filename, location_path, ignore_rules)
        if type_error:
            errors.append(type_error)
    
    return errors

def check_function_node(node: ast.FunctionDef, filename: str, context_stack: List[str], ignore_rules: List[IgnoreRule]) -> List[CodeError]:
    """Check a function definition node for issues."""
    errors = []
    location_path = get_location_path(context_stack)
    
    # Check function naming
    naming_error = check_function_naming(node, filename, location_path, ignore_rules)
    if naming_error:
        errors.append(naming_error)
    
    # Check name mangling
    mangling_error = check_function_name_mangling(node, filename, location_path, ignore_rules)
    if mangling_error:
        errors.append(mangling_error)
    
    # Check parameters
    param_errors = check_function_parameters(node, filename, location_path, ignore_rules)
    errors.extend(param_errors)
    
    # Check return type
    return_error = check_return_type_annotation(node, filename, location_path, ignore_rules)
    if return_error:
        errors.append(return_error)
    
    # Check mutable defaults
    mutable_errors = check_mutable_defaults(node, filename, location_path, ignore_rules)
    errors.extend(mutable_errors)
    
    # Check docstring
    docstring_errors = check_function_docstring(node, filename, location_path, ignore_rules)
    errors.extend(docstring_errors)
    
    return errors

def check_class_naming(node: ast.ClassDef, filename: str, location_path: str, ignore_rules: List[IgnoreRule]) -> Optional[CodeError]:
    """Check class naming convention."""
    if should_ignore_error('naming', location_path, node.name, ignore_rules):
        return None
    
    if is_valid_class_name(node.name):
        return None
    
    return CodeError(
        filename, node.lineno, None,
        f"Class '{node.name}' does not follow PascalCase convention"
    )

def check_class_docstring(node: ast.ClassDef, filename: str, location_path: str, ignore_rules: List[IgnoreRule]) -> List[CodeError]:
    """Check class docstring."""
    if should_ignore_error('docstring', location_path, node.name, ignore_rules):
        return []
    
    docstring = ast.get_docstring(node)
    if not docstring:
        return [CodeError(
            filename, node.lineno, None,
            f"Class '{node.name}' missing docstring"
        )]
    
    errors = []
    docstring_issues = validate_docstring_format(docstring)
    for issue in docstring_issues:
        errors.append(CodeError(
            filename, node.lineno, None,
            f"Class '{node.name}' docstring {issue}"
        ))
    
    return errors

def check_class_node(node: ast.ClassDef, filename: str, context_stack: List[str], ignore_rules: List[IgnoreRule]) -> List[CodeError]:
    """Check a class definition node for issues."""
    errors = []
    location_path = get_location_path(context_stack)
    
    # Check class naming
    naming_error = check_class_naming(node, filename, location_path, ignore_rules)
    if naming_error:
        errors.append(naming_error)
    
    # Check docstring
    docstring_errors = check_class_docstring(node, filename, location_path, ignore_rules)
    errors.extend(docstring_errors)
    
    return errors

def check_variable_naming(node: ast.Name, filename: str, location_path: str, ignore_rules: List[IgnoreRule]) -> Optional[CodeError]:
    """Check variable naming convention."""
    if should_ignore_error('naming', location_path, node.id, ignore_rules):
        return None
    
    if is_valid_variable_name(node.id):
        return None
    
    return CodeError(
        filename, node.lineno, None,
        f"Variable '{node.id}' does not follow naming convention"
    )

def check_variable_name_mangling(node: ast.Name, filename: str, location_path: str, ignore_rules: List[IgnoreRule]) -> Optional[CodeError]:
    """Check variable name mangling."""
    if '__' not in node.id or node.id in SPECIAL_METHODS:
        return None
    
    if should_ignore_error('name_mangling', location_path, node.id, ignore_rules):
        return None
    
    return CodeError(
        filename, node.lineno, None,
        f"Variable '{node.id}' uses inappropriate name mangling"
    )

def check_variable_node(node: ast.Name, filename: str, context_stack: List[str], ignore_rules: List[IgnoreRule]) -> List[CodeError]:
    """Check a variable assignment node for issues."""
    if not isinstance(node.ctx, (ast.Store, ast.Param)):
        return []
    
    errors = []
    location_path = get_location_path(context_stack)
    
    # Check variable naming
    naming_error = check_variable_naming(node, filename, location_path, ignore_rules)
    if naming_error:
        errors.append(naming_error)
    
    # Check name mangling
    mangling_error = check_variable_name_mangling(node, filename, location_path, ignore_rules)
    if mangling_error:
        errors.append(mangling_error)
    
    return errors

class CodeVisitor(ast.NodeVisitor):
    """AST visitor for checking code standards."""
    
    def __init__(self, filename: str, ignore_rules: List[IgnoreRule]):
        self.filename = filename
        self.ignore_rules = ignore_rules
        self.errors: List[CodeError] = []
        self.context_stack: List[str] = []
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.errors.extend(check_function_node(
            node, self.filename, self.context_stack, self.ignore_rules
        ))
        
        self.context_stack.append(node.name)
        self.generic_visit(node)
        self.context_stack.pop()
    
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.errors.extend(check_class_node(
            node, self.filename, self.context_stack, self.ignore_rules
        ))
        
        self.context_stack.append(node.name)
        self.generic_visit(node)
        self.context_stack.pop()
    
    def visit_Name(self, node: ast.Name) -> None:
        self.errors.extend(check_variable_node(
            node, self.filename, self.context_stack, self.ignore_rules
        ))
        self.generic_visit(node)

def check_file(filename: str, ignore_rules: List[IgnoreRule]) -> List[CodeError]:
    """Check a single Python file for standards violations."""
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read()
        
        tree = ast.parse(content, filename)
        visitor = CodeVisitor(filename, ignore_rules)
        visitor.visit(tree)
        return visitor.errors
    
    except (SyntaxError, UnicodeDecodeError) as e:
        return [CodeError(filename, 0, None, f"Failed to parse file: {e}")]

def find_python_files(root_dir: str = '.', config: Dict[str, Any] = None) -> List[str]:
    """Find all Python files in the directory tree."""
    if config is None:
        config = {}
    
    python_files = []
    for root, dirs, files in os.walk(root_dir):
        # Filter out ignored directories early
        dirs[:] = [d for d in dirs if not should_ignore_file(os.path.join(root, d), d, config)]
        
        if should_ignore_file(root, os.path.basename(root), config):
            continue
            
        for file in files:
            if not file.endswith('.py'):
                continue
                
            file_path = os.path.join(root, file)
            if should_ignore_file(file_path, file, config):
                continue
                
            python_files.append(file_path)
    
    return python_files

def main() -> None:
    """Main function to check all Python files in the current directory."""
    config = load_ignore_config()
    ignore_rules = extract_ignore_rules_from_config(config)
    
    python_files = find_python_files(config=config)
    all_errors = []
    
    for file_path in python_files:
        errors = check_file(file_path, ignore_rules)
        all_errors.extend(errors)
    
    if all_errors:
        for error in all_errors:
            print(error)
        sys.exit(1)
    else:
        print("All checks passed!")

if __name__ == "__main__":
    main()