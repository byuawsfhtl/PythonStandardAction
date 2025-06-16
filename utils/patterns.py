import re
import models as models

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
    return (name.startswith('test_') and is_snake_case(name)) or name in models.PYTEST_METHODS