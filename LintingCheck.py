from argparse import ArgumentParser
from pathlib import Path
from sys import stderr, exit
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
    print("Starting the Linting Check")

    parser = ArgumentParser(description='Modern Python style checker')
    parser.add_argument('paths', nargs='*', default=['.'], help='Paths to check (default: current directory)')
    
    args = parser.parse_args()

    ignore_patterns = load_ignore_patterns()
    mypy_args = load_mypy_arguments()

    all_errors: list = []

    for path_str in args.paths:
        path = Path(path_str)
        if path.is_file():
            print("Found a file")
            if should_ignore_file(path, ignore_patterns):
                continue
            else:
                mypy_return = run_mypy_on_file(path_str, mypy_args)
                all_errors.extend(mypy_return) 
        elif path.is_dir():
            print("Found a directory")
            mypy_return = run_mypy_on_directory(path, ignore_patterns, mypy_args)
            all_errors.extend(mypy_return)
        else:
            print(f"Warning: Path not found: {path}", file=stderr)

    if all_errors:
        for mypy_error in all_errors:
            print(mypy_error)
        print(f"\nFound {len(all_errors)} MyPy errors.")
        return 1

    else:
        print("Passed all MyPy checks!")
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
            mypy_errors = run_mypy_on_file(str(file_path), args)
            errors_in_directory.extend(mypy_errors)
    
    return errors_in_directory


def run_mypy_on_file(file_path_string: str, args: list[str] | None = None) -> list:
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

    mypy_output_to_standard, mypy_output_to_error, mypy_return_value = mypy_api_run(args_with_file_path_at_start)

    # Note that despite what mypy says, it actually writes the various linting errors to the *standard*
    # output, not the error output. It writes fatal errors caused by odds and ends to it's error output,
    # so it's necessary to check both the standard the the error output to actually find all of the
    # desired errors

    # If mypy returns with no errors, we can return an empty list of errors
    if mypy_return_value == 0:
        return []
    
    # Otherwise we need to filter everything mypy prints so that we only have the return errors
    errors_to_return = []
    for output_source in (mypy_output_to_standard, mypy_output_to_error):
        for line in output_source.splitlines():
            if "error:" in line:
                errors_to_return.append(line)

    return errors_to_return

        



if __name__ == '__main__':
    exit(main())