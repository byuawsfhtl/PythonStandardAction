from argparse import ArgumentParser
from pathlib import Path
from sys import stderr
from typing import Optional
from pathspec import PathSpec
from config import load_mypy_arguments, load_ignore_patterns
from utils.file_utils import should_ignore_file
from mypy.api import run as mypy_api_run


def main() -> int:
    """Main entry point for the style checker.
    
    Returns:
        Exit code (0 for success, 1 for errors found)
    """
    parser = ArgumentParser(description='Modern Python style checker')
    parser.add_argument('paths', nargs='*', default=['.'], help='Paths to check (default: current directory)')
    parser.add_argument('--config', type=Path, help='Path to configuration file')
    parser.add_argument('--ignore', action='append', help='Error codes to ignore')
    parser.add_argument('--max-complexity', type=int, default=15, help='Maximum cyclomatic complexity (default: 15)')
    
    args = parser.parse_args()

    ignore_patterns = load_ignore_patterns()
    mypy_args = load_mypy_arguments()

    all_errors: list = []

    for path_str in args.path:
        path = Path(path_str)
        if path.is_file():
            if should_ignore_file(path, ignore_patterns):
                continue
            else:
                ignored_mypy_normal_output, mypy_errors, ignored_mypy_return_value = run_mypy_on_file(path_str, mypy_args)
                all_errors.extend(mypy_errors) 
        elif path.is_dir():
            mypy_errors = run_mypy_on_directory(path, ignore_patterns, mypy_args)
            all_errors.extend(mypy_errors)
        else:
            print(f"Warning: Path not found: {path}", file=stderr)

    if all_errors:
        all_errors.sort(key=lambda e: (e.file_path, e.line_number))
        for mypy_error in all_errors:
            print(mypy_error)
        print(f"\nFound {len(all_errors)} mypy errors.")
        return 1

    else:
        print("Passed all mypy checks!")
        return 0


def run_mypy_on_directory(directory: Path, ignore_patterns: Optional[PathSpec], args: list[str] | None = None) -> list:
    """Check all Python files in a directory recursively.
    
    Args:
        directory: Directory to check
        ignore_patterns: Patterns for files to ignore
        
    Returns:
        list of style errors found
    """
    errors_in_directory: list = []
    
    for file_path in directory.rglob('*.py'):
        if should_ignore_file(file_path, ignore_patterns):
            continue
            
        else:
            ignored_mypy_normal_output, mypy_errors, ignored_mypy_return_value = run_mypy_on_file(str(file_path), args)
            errors_in_directory.extend(mypy_errors)
    
    return errors_in_directory


def run_mypy_on_file(file_path_string: str, args: list[str] | None = None) -> tuple:
    """Run mypy on a single python file.

    Args:
        file_path_string: The string representation of the path to the 
            file that should be checked
        args: The arguments that should be passed into the mypy call

    Returns:
        The result of calling mypy on the file
    """
    args_with_file_path_at_start = []

    if not args:
        args_with_file_path_at_start = [f"{file_path_string}", "--strict"]
    else: 
        args_with_file_path_at_start.insert(0, f"{file_path_string}")

    return mypy_api_run(args_with_file_path_at_start)