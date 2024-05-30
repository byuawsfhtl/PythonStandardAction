import ast
import fnmatch
import os
import re
import sys

class CodeChecker(ast.NodeVisitor):
    """Class to check Python code for formatting issues."""

    def __init__(self, filename: str) -> None:
        """Initializes the CodeChecker class.

        Args:
            filename (str): the current file being checked
        """
        self.errors = []
        self.filename = filename
        self.special_methods = {
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
            '__version__'
        }
        self.itemsToIgnore = self.loadItemsToIgnore('.standardignore')

    def loadItemsToIgnore(self, ignoreFile: str) -> list:
        """Load items to ignore from a file.

        Args:
            ignoreFile (str): the file to load items from

        Returns:
            list: the items to ignore
        """
        ignoreItems = []
        if os.path.exists(ignoreFile):
            with open(ignoreFile, 'r', encoding='utf-8') as file:
                ignoreItems = [line.strip().strip("!") for line in file if line.strip() and line.startswith('!')]
        return ignoreItems

    def isValidFormat(self, name: str, type: str = None) -> bool:
        """Check if a name is in camel case or other valid format.

        Args:
            name (str): the name to check
            type (str): the type of name to check

        Returns:
            bool: true if the name is in camel case or other valid format, False otherwise
        """
        if name in self.itemsToIgnore:
            return True
        if all(char.isupper() for char in name):
            return True
        if name[0] == "_":
            return True
        if "_" in name:
            for side in name.split("_"):
                for char in side:
                    if not char.isupper():
                        return False
            return True
        if type:
            return self.isPascalCase(name)
        return self.isCamelCase(name)
    
    def isCamelCase(self, name: str) -> bool:
        """Check if a name is in camel case.

        Args:
            name (str): the name to check

        Returns:
            bool: true if the name is in camel case, False otherwise
        """
        return re.match(r'^[a-z0-9]+(?:[A-Z][a-z0-9]*)*$', name) is not None
    
    def isPascalCase(self, name: str) -> bool:
        """Check if a name is in pascal case.

        Args:
            name (str): the name to check

        Returns:
            bool: true if the name is in pascal case, False otherwise
        """
        return re.match(r'^[A-Z][A-Za-z0-9]+(?:[A-Z][a-z0-9]*)*$', name) is not None

    def toString(self, node: ast, message: str) -> str:
        """Converts a node and a message to a string.

        Args:
            node (ast): the node to get the line number from
            message (str): the message to display

        Returns:
            str: the formatted string
        """
        return f"{self.filename}:{node.lineno}: {message}"

    def visit_FunctionDef(self, node: ast) -> None:
        """Visit a FunctionDef node.

        Args:
            node (ast): the node to visit
        """
        # Skip special methods
        self.checkDocstring(node)

        if not self.isValidFormat(node.name):
            self.errors.append(self.toString(node, f"Function '{node.name}'  is not in camel case."))

        if '__' in node.name and node.name not in self.special_methods:
            self.errors.append(self.toString(node, f"Function '{node.name}'  uses '__' inappropriately."))

        for arg in node.args.args:
            if arg.annotation is None and arg.arg != 'self' and arg.arg != 'cls' and '*' not in arg.arg and '**' not in arg.arg:
                self.errors.append(self.toString(node, f"Function '{node.name}'  has parameter '{arg.arg}' without type annotation."))

            if not self.isValidFormat(arg.arg):
                self.errors.append(self.toString(node, f"Function '{node.name}'  has parameter '{arg.arg}' that is not in camel case."))

        for default in node.args.defaults:
            if isinstance(default, ast.Dict) or isinstance(default, ast.List) or isinstance(default, ast.Set):
                self.errors.append(self.toString(node, f"Function '{node.name}' has a mutable default argument."))

        # Check for return type annotation
        if node.returns is None:
            self.errors.append(self.toString(node, f"Function '{node.name}'  is missing a return type annotation."))
        
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast) -> None:
        """Visit a ClassDef node.

        Args:
            node (ast): the node to visit
        """
        if not self.isValidFormat(node.name, type='class'):
            self.errors.append(self.toString(node, f"Class '{node.name}' is not in Pascal case."))
        self.checkDocstring(node)
        self.generic_visit(node)

    def checkDocstring(self, node: ast) -> None:
        """Check the docstring of a node.

        Args:
            node (ast): the node to check
        """
        docstring = ast.get_docstring(node)
        if docstring:
            # Split docstring into sections
            sections = re.split(r'Args:|Returns:|Notes:|Yields:|Raises:|Updates:', docstring, flags=re.IGNORECASE)[1:]
            firstLineEndIndex = docstring.find('\n\n')
            if firstLineEndIndex == -1:
                firstLine = docstring.strip()
            else: 
                firstLine = docstring[0:firstLineEndIndex].strip()

            if not firstLine or ':' in firstLine:
                self.errors.append(self.toString(node, f"'{node.name}' docstring description is missing."))
            if ':' not in firstLine and not firstLine.endswith('.'):
                self.errors.append(self.toString(node, f"'{node.name}' docstring description does not end with a period."))

            if sections:
                lines = sections[0].split('\n')
                for line in lines:
                    if line.strip() and ':' in line:
                        line = line.strip()
                        argumentDefinition = line.split(':')[1].strip()
                        if not argumentDefinition:
                            continue
                        if argumentDefinition[0].isupper():
                            self.errors.append(self.toString(node, f"'{node.name}' has beginning capital letter in argument definition"))
                        if argumentDefinition.endswith('.'):
                            self.errors.append(self.toString(node, f"'{node.name}' has invalid ending character(.) in argument definition"))
                        colonSplit = argumentDefinition.split(';')
                        if len(colonSplit) > 1:
                            for additionalInfo in colonSplit[1:]:
                                if not additionalInfo:
                                    continue
                                if additionalInfo.strip()[0].isupper():
                                    self.errors.append(self.toString(node, f"'{node.name}' has beginning capital letter in argument definition"))
                                if additionalInfo.strip().endswith('.'):
                                    self.errors.append(self.toString(node, f"'{node.name}' has invalid ending character(.) in argument definition"))
        else:
            self.errors.append(self.toString(node, f"'{node.name}' is missing a docstring."))

    def visit_Name(self, node: ast) -> None:
        """Visit a Name node.

        Args:
            node (ast): the node to visit
        """
        if isinstance(node.ctx, (ast.Store, ast.Param)):
            if '__' in node.id and node.id not in self.special_methods:
                self.errors.append(self.toString(node, f"Variable '{node.id}'  uses '__' inappropriately."))
            if not self.isValidFormat(node.id):
                self.errors.append(self.toString(node, f"Variable '{node.id}' is not in camel case."))
        self.generic_visit(node)

def checkFile(filename: str) -> list:
    """Check a file for formatting issues.

    Args:
        filename (str): the file to check

    Returns:
        list: the errors found
    """
    with open(filename, 'r', encoding='utf-8') as file:
        tree = ast.parse(file.read(), filename)
        checker = CodeChecker(filename)
        checker.visit(tree)
        return checker.errors
    
def loadIgnorePatterns(ignoreFile: str) -> list:
    """Load ignore patterns from a file.

    Args:
        ignoreFile (str): the file to load patterns from

    Returns:
        list: the patterns to ignore
    """
    patterns = []
    if os.path.exists(ignoreFile):
        with open(ignoreFile, 'r', encoding='utf-8') as file:
            patterns = [line.strip() for line in file if line.strip() and not line.startswith('#') and not line.startswith('!')]
    return patterns

def shouldIgnore(filePath: str, patterns: list) -> bool:
    """Check if a file should be ignored based on patterns.

    Args:
        filePath (str): the file to check
        patterns (list): the patterns to check against

    Returns:
        bool: true if the file should be ignored, False otherwise
    """    
    for pattern in patterns:
        if fnmatch.fnmatch(filePath, pattern):
            return True
    return False

def main() -> None:
    """Main function to check all files in the current directory.
    """
    ignore = loadIgnorePatterns('.standardignore')
    errors = []
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if not shouldIgnore(os.path.join(root, d), ignore)]
        if shouldIgnore(root, ignore):
            continue
        for file in files:
            if file.endswith('.py'):
                filePath = os.path.join(root, file)
                if shouldIgnore(filePath, ignore):
                    continue
                errors.extend(checkFile(filePath))
    
    if errors:
        for error in errors:
            print(error)
        sys.exit(1)  # Exit with a non-zero status to indicate failure
    else:
        print("All checks passed.")

if __name__ == "__main__":
    main()
