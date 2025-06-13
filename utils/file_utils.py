from pathlib import Path
from typing import Optional

import pathspec

"""File-discovery filtering logic"""

def should_ignore_name(name: str, ignore_names: set[str]) -> bool:
    """Check if a specific name should be ignored.
    
    Args:
        name: Name to check (variable, function, class)
        ignore_names: Set of names to ignore
        
    Returns:
        True if name should be ignored
    """
    return name in ignore_names


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