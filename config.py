import pathspec
from pathlib import Path
from typing import Any, Optional
"""Configuration validation logic"""

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
        'max_complexity': 5,   # Cyclomatic complexity threshold
        'exclude_dirs': {'.git', '__pycache__', '.pytest_cache', '.mypy_cache'},
        'ignore_names': set(),  # Specific names to ignore
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


def load_ignore_names() -> set[str]:
    """Load specific names to ignore from .standardignore file.
    
    Returns:
        Set of names to ignore in style checking
    """
    ignore_names = set()
    ignore_file = Path('.standardignore')
    
    if not ignore_file.exists():
        return ignore_names

    with open(ignore_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line.startswith('name:'):
            continue
        # Extract name after 'name:'
        name = line[5:].strip()
        if name:
            ignore_names.add(name)

    return ignore_names