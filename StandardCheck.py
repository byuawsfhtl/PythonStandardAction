import ast
import fnmatch
import os
import re
import sys

ITEMS_TO_IGNORE_SYMBOL = "!"
COMMENT_SYMBOL = "#"
NAME_MANGLE = "__"

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
            '__version__', '__new__'
        }
        self.itemsToIgnore = self.loadItemsToIgnore('.standardignore')
        self.specialVariables = [
            "self",
            "cls",
            "*args",
            "**kwargs"
        ]

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
                ignoreItems = [line.strip().strip(ITEMS_TO_IGNORE_SYMBOL) for line in file if line.strip() and line.startswith(ITEMS_TO_IGNORE_SYMBOL)]
        return ignoreItems

    def isValidFormat(self, name: str, type: str | None = None) -> bool:
        """Check if a name is in camel case or other valid format.

        Args:
            name (str): the name to check
            type (str | None, optional): the type of name to check; defaults to None

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

    def toString(self, node: ast.FunctionDef | ast.ClassDef, message: str) -> str:
        """Converts a node and a message to a string.

        Args:
            node (ast.FunctionDef | ast.ClassDef): the node to get the line number from
            message (str): the message to display

        Returns:
            str: the formatted string
        """
        functionMsg = ""
        if isinstance(node, ast.FunctionDef):
            functionMsg = f"Function {node.name}: "
        return f"{self.filename}:{node.lineno}: {functionMsg}{message}"

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit a FunctionDef node.

        Args:
            node (ast.FunctionDef): the node to visit
        """
        # Skip special methods
        self.verifyDocstring(node)

        if not self.isValidFormat(node.name):
            self.errors.append(self.toString(node, f"Function '{node.name}'  is not in camel case."))

        if NAME_MANGLE in node.name and node.name not in self.special_methods and node.name not in self.itemsToIgnore:
            self.errors.append(self.toString(node, f"Function '{node.name}'  uses '{NAME_MANGLE}' inappropriately."))

        for arg in node.args.args:
            if arg.annotation is None and arg.arg not in self.specialVariables and '*' not in arg.arg and '**' not in arg.arg:
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

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit a ClassDef node.

        Args:
            node (ast.ClassDef): the node to visit
        """
        if not self.isValidFormat(node.name, type='class'):
            self.errors.append(self.toString(node, f"Class '{node.name}' is not in Pascal case."))
        self.verifyDocstring(node)
        self.generic_visit(node)

    def visit_Name(self, node: ast) -> None:
        """Visit a Name node.

        Args:
            node (ast): the node to visit
        """
        if isinstance(node.ctx, (ast.Store, ast.Param)):
            if NAME_MANGLE in node.id and node.id not in self.special_methods and node.id not in self.itemsToIgnore:
                self.errors.append(self.toString(node, f"Variable '{node.id}'  uses '{NAME_MANGLE}' inappropriately."))
            if not self.isValidFormat(node.id):
                self.errors.append(self.toString(node, f"Variable '{node.id}' is not in camel case."))
        self.generic_visit(node)

    def verifyDocstring(self, node: ast.FunctionDef | ast.ClassDef) -> None:
        """Check the docstring of a node.

        Args:
            node (ast.FunctionDef | ast.ClassDef): the node to check
        """
        docstring = ast.get_docstring(node)
        if not docstring:
            self.errors.append(self.toString(node, f"'{node.name}' is missing a docstring."))
            return
        
        splitDocstring = docstring.split("\n\n")
        description = splitDocstring[0]
        self.docstringDescriptionCheck(node, description)

        argSectionFound = False
        returnSectionFound = False

        for i in range(1, len(splitDocstring)):
            section = splitDocstring[i]
            if "Args:" in section:
                argSectionFound = True
                self.docstringArgSection(node, section)
            if "Returns:" in section:
                returnSectionFound = True
                self.docstringReturnSection(node, section)

        if isinstance(node, ast.FunctionDef):
            args = node.args.args
            filteredArgs = []
            for arg in args:
                if arg.arg not in self.specialVariables:
                    filteredArgs.append(arg)

            if not argSectionFound and len(filteredArgs) > 0:
                self.errors.append(self.toString(node, "arguments not documented in docstring"))

            returnType = self._getDefinedType(node.returns)
            if returnType and not returnSectionFound and str(returnType) != "None":
                self.errors.append(self.toString(node, "return type not documented in docstring"))

    def docstringArgSection(self, node: ast.ClassDef | ast.FunctionDef, section: str) -> None:
        """Ensures the argument section is accurate.

        Args:
            node (ast.ClassDef | ast.FunctionDef): the current node for the docstring
            section (str): the argument section to evaluate
        """
        if not isinstance(node, ast.FunctionDef):
            self.errors.append(self.toString(node, f"Args Section found for non function: '{node.name}'"))
            return
        
        while "  " in section:
            section = section.replace("  ", " ")
        section = section.strip()

        argLines = self._parseArgLines(section)

        if not argLines:
            self.errors.append(self.toString(node, f"Function '{node.name}' docstring Args section is empty"))
            return

        docArgs = self._verifyArgLines(node, argLines)
        
        self._verifyFuncArgsInDoc(node, docArgs)

    def docstringReturnSection(self, node: ast.ClassDef | ast.FunctionDef, section: str) -> None:
        """Ensures the return section is accurate.

        Args:
            node (ast.ClassDef | ast.FunctionDef): the current node for the docstring
            section (str): the return section to evaluate
        """
        if not isinstance(node, ast.FunctionDef):
            self.errors.append(self.toString(node, f"Args Section found for non function: '{node.name}'"))
            return
        
        while "  " in section:
            section = section.replace("  ", " ")
        section = section.strip()

        splitReturnSection = section.split("\n")
        if len(splitReturnSection) < 2:
            self.errors.append(self.toString(node, f"'{node.name}' docstring return section is missing"))
            return
        
        returnLine = splitReturnSection[1]
        returnLineSplit = returnLine.split(":")
        if len(returnLineSplit) < 2:
            self.errors.append(self.toString(node, f"'{node.name}' docstring return section is missing a type definition"))
            return
        
        returnType = returnLineSplit[0]
        returnType = returnType.strip()
        returnType = returnType.replace(" ", "")

        funcReturnType = self._getDefinedType(node.returns)
        if funcReturnType is None:
            self.errors.append(self.toString(node, f"return type for '{node.name}' either is not defined or could not be constructed"))
            return

        funcReturnType = funcReturnType.replace(" ", "")
        if funcReturnType != returnType:
            self.errors.append(self.toString(node, 
                f"the documentation of the return type ({returnType}) does not match with function return type ({funcReturnType})"))

    def docstringDescriptionCheck(self, node: ast, section: str) -> None:
        """Ensures the description string is up to snuff.

        Args:
            node (ast): the current node being checked
            section (str): the description string to check
        """
        # Rules: Must begin with a Capital and end with a period
        section = section.strip()
        section = section.replace("\n", " ")
        section = section.replace("\t", " ")
        while "  " in section:
            section = section.replace("  ", " ")
        section = section.strip()
        
        if not section:
            self.errors.append(self.toString(node, f"'{node.name}' docstring description is missing"))
            return
        
        firstLetter = section[0]
        if firstLetter.isalpha() and firstLetter.capitalize() != firstLetter:
            self.errors.append(self.toString(node, f"'{node.name}' docstring description must begin with a capital letter"))
        
        if not section.endswith("."):
            self.errors.append(self.toString(node, f"'{node.name}' docstring description must end with a period"))

    def _docArgExists(self, docArgName: str, argList: list[ast.arg]) -> bool:
        """Checks if the docstring argument exists in the function argument list.

        Args:
            docArgName (str): the name to check for
            argList (list[ast.arg]): the function argument list

        Returns:
            bool: True if the arg exists, False otherwise
        """
        for arg in argList:
            if arg.arg == docArgName:
                return True
        return False
    
    def _parseArgLines(self, section: str) -> list[str]:
        """Parse out the argument descriptions from the docstring.

        Args:
            section (str): the section to parse args from

        Returns:
            list[str]: the parsed arg lines
        """
        splitArgsSection = section.split("\n")
        if len(splitArgsSection) < 2:
            return
        
        argLines = []
        index = 1
        while index < len(splitArgsSection):
            currentLine = splitArgsSection[index]
            if "):" not in currentLine:
                return

            additionalLineJump = 0
            if (index + 1) < len(splitArgsSection):
                tempIndex = index + 1
                while tempIndex < len(splitArgsSection) and "):" not in splitArgsSection[tempIndex]:
                    currentLine += splitArgsSection[tempIndex]
                    tempIndex += 1
                additionalLineJump = tempIndex - index
            else:
                additionalLineJump = 1

            argLines.append(currentLine)
            index += additionalLineJump
        return argLines
        
    def _verifyArgLines(self, node: ast, argLines: list[str]) -> list[str]:
        """Verifies that argument definitions from docstring are valid.

        Args:
            node (ast): the current node
            argLines (list[str]): the parsed lines of argument definitions

        Returns:
            list[str]: the names of the variables found
        """
        docArgs = []
        functionArgs: list[ast.arg] = node.args.args
        for argLine in argLines:
            splitOnOpen = argLine.split(" (")
            if len(splitOnOpen) == 1:
                self.errors.append(self.toString(node, f"an argument in the docstring does not have a type definition"))
                continue
            argName: str = splitOnOpen[0]
            argName = argName.strip()
            docArgs.append(argName)
            if not self._docArgExists(argName, functionArgs):
                self.errors.append(self.toString(node, f"docstring arg '{argName}' does not appear in '{node.name}' arguments"))

            midSplit = splitOnOpen[1].split("):")
            argType: str = midSplit[0]
            argType = argType.replace(" ", "")
            functionArgEndCol = -1
            correspondingDefault = None
            # Match the current argument line in the docstring to its corresponding function argument type annotation
            for arg in functionArgs:
                if arg.arg != argName:
                    continue
                definedType = self._getDefinedType(arg.annotation)
                functionArgEndCol = arg.end_col_offset
                functionArgEndRow = arg.end_lineno
                correspondingDefault = self._getArgDefault(node, functionArgEndCol, functionArgEndRow)
                if definedType is None:
                    self.errors.append(self.toString(node, f"type for arg '{argName}' could not be constructed"))
                    break
                if correspondingDefault is not None:
                    definedType += ", optional"
                definedType = definedType.replace(" ", "")
                if definedType != argType:
                    self.errors.append(self.toString(node, f"type for arg '{argName} ({argType})' in documentation does not match with '{argName} ({definedType})' definition"))
                break

            if functionArgEndCol != -1:
                definitionSentence = midSplit[1]
                if not definitionSentence:
                    self.errors.append(self.toString(node, f"description sentence for arg '{argName}' not provided in docstring"))
                
                self._verifySections(node, definitionSentence, correspondingDefault, argName)

        return docArgs
    
    def _verifySections(self, node: ast.FunctionDef, definition: str, correspondingDefault: ast.Constant | None, argName: str) -> None:
        """Verify that the descriptions of docstring arguments are accurate and follow standards.

        Args:
            node (ast.FunctionDef): the current node
            definition (str): the definition string of current argument
            correspondingDefault (ast.Constant | None): the default value for the current arguement
            argName (str): the name of the current arguement
        """
        sectionSplit = definition.split(";")
        foundDefault = False
        for section in sectionSplit:
            if not section:
                self.errors.append(self.toString(node, f"empty section provided in documentation for arg '{argName}'"))
                continue
            
            section = section.strip()
            if section[0].capitalize() == section[0]:
                self.errors.append(self.toString(node, f"capital letter in beginning of a section for documentation of arg '{argName}'"))

            if section.endswith("."):
                self.errors.append(self.toString(node, f"section of documentation for arg '{argName}' ends with ."))

            if ':' in section:
                self.errors.append(self.toString(node, f"section of documentation for arg '{argName}' contains disallowed character ':'"))

            if "defaults to" in section:
                foundDefault = True
                if correspondingDefault is not None:
                    if isinstance(correspondingDefault, ast.UnaryOp):
                        if isinstance(correspondingDefault.op, ast.USub):
                            defaultValue = -1 * correspondingDefault.operand.value
                        else:
                            defaultValue = correspondingDefault.operand.value
                    else:
                        defaultValue = correspondingDefault.value
                    if str(defaultValue) not in section:
                        self.errors.append(self.toString(node, f"the default value '({str(defaultValue)})' for arg '{argName}' is not reflected in the docstring"))
                else:
                    self.errors.append(self.toString(node, f"contains default documentation for arg '{argName}' which has no default"))

        if not foundDefault and correspondingDefault is not None:
            self.errors.append(self.toString(node, f"the default value '{str(correspondingDefault.value)}' for arg '{argName}' is not reflected in the docstring"))
    
    def _getArgDefault(self, node: ast.FunctionDef, endColOfArg: int, endRowOfArg: int) -> ast.Constant | None:
        """Finds a corresponding default using the end point of the argument wanted.

        Args:
            node (ast.FunctionDef): the current node
            endColOfArg (int): the last column index of the argument to find the default for
            endRowOfArg (int): the row index of the argument to find the default for

        Returns:
            ast.Constant | None: the found default, or None if none found
        """
        if endColOfArg == -1:
            return None
        defaults = node.args.defaults
        for default in defaults:
            defaultBegCol = default.col_offset
            defaultEndRow = default.end_lineno
            difference = defaultBegCol - endColOfArg
            if (difference == 1 or difference == 3) and endRowOfArg == defaultEndRow:
                return default
        return None
    
    def _getDefinedType(self, annotation: ast.BinOp | ast.Attribute | ast.Name | ast.List | ast.Subscript) -> str:
        """Iterates through an ast arg to create its full definition.

        Args:
            annotation (ast.BinOp | ast.Attribute | ast.Name): the arguement to get the specified type of

        Returns:
            str: the full type
        """
        if isinstance(annotation, ast.BinOp):
            leftAnnotation = annotation.left
            rightAnnotation = annotation.right
            leftDefinedType = self._getDefinedType(leftAnnotation)
            rightDefinedType = self._getDefinedType(rightAnnotation)
            return str(leftDefinedType) + "|" + str(rightDefinedType)
        elif isinstance(annotation, ast.Tuple):
            innerTypes = []
            for element in annotation.elts:
                innerTypes.append(self._getDefinedType(element))
            return ", ".join(innerTypes)
        elif isinstance(annotation, ast.Subscript):
            outside = annotation.value.id
            return outside + "[" +  self._getDefinedType(annotation.slice) + "]"
        elif isinstance(annotation, ast.Constant):
            return str(annotation.value)
        elif isinstance(annotation, ast.Attribute) or isinstance(annotation, ast.Name):
            return self._getTypeFromAttributeOrName(annotation)
        elif isinstance(annotation, ast.List):
            types = []
            for elt in annotation.elts:
                types.append(self._getDefinedType(elt)) # type: ignore
            return "[" + ",".join(types) + "]"
        
        
    def _getTypeFromAttributeOrName(self, annotation: ast.Attribute | ast.Name) -> str:
        """Reconstructs the full type name from the given annotation.

        Args:
            annotation (ast.Attribute | ast.Name): the annotation to pull the name from

        Returns:
            str: the full type name
        """
        definedType = []
        while not isinstance(annotation, ast.Name):
            definedType.append(annotation.attr)
            annotation = annotation.value
        else:
            definedType.append(annotation.id)

        returnType = ""
        for i in range(len(definedType) - 1, -1, -1):
            returnType += definedType[i]
            if i != 0:
                returnType += "."
        return returnType

    def _verifyFuncArgsInDoc(self, node: ast, docArgs: list[str]) -> None:
        """Ensures that the variables defined in the node args appear in the docstring.

        Args:
            node (ast): the current function node
            docArgs (list[str]): the arguments defined in the docstring
        """
        functionArgs: list[ast.arg] = node.args.args   
        for functionArg in functionArgs:
            functionArgName = functionArg.arg
            if functionArgName not in docArgs and functionArgName not in self.specialVariables:
                self.errors.append(self.toString(node, f"arguement '{functionArgName}' not documented"))

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
            patterns = [line.strip() for line in file if line.strip() and not line.startswith(COMMENT_SYMBOL) and not line.startswith(ITEMS_TO_IGNORE_SYMBOL)]
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