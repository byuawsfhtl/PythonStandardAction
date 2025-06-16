import ast
from typing import Optional

import models as models

def create_error(node: ast.AST, error_code: str, message: str, file_path: str, ignore_codes: set[str]) -> Optional[models.StyleError]:
    """Create a style error if not ignored.
    
    Args:
        node: AST node where error occurred
        error_code: Error code from ERROR_CODES
        message: Descriptive error message
        file_path: Path to file containing the error
        ignore_codes: set of error codes to ignore
        
    Returns:
        models.StyleError instance or None if ignored
    """
    if error_code in ignore_codes:
        return None
        
    return models.StyleError(
        file_path=file_path,
        line_number=getattr(node, 'lineno', 0),
        column=getattr(node, 'col_offset', 0),
        error_code=error_code,
        message=message
    )