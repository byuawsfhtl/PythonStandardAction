from typing import FrozenSet
from dataclasses import dataclass

@dataclass
class StyleError:
    """Represents a style violation."""
    file_path: str
    line_number: int
    column: int
    error_code: str
    message: str
    
    def __str__(self) -> str:
        """Converts the error dataclass to a string.

        Returns:
            str: the error as a str
        """
        return f"{self.file_path}:{self.line_number}:{self.column}: {self.error_code} {self.message}"


# Error codes following industry conventions (similar to flake8)
ERROR_CODES = {
    'N801': 'class name should use PascalCase',
    'N802': 'function name should use snake_case',
    'N803': 'argument name should use snake_case',
    'N804': 'variable name should use snake_case',
    'N805': 'inappropriate use of name mangling',
    'ANN001': 'missing type annotation for function argument',
    'ANN002': 'missing return type annotation',
    'D100': 'missing docstring in public module',
    'D101': 'missing docstring in public class',
    'D102': 'missing docstring in public method',
    'D103': 'missing docstring in public function',
    'D200': 'docstring should start with capital letter',
    'D201': 'docstring should end with period',
    'D300': 'missing Args section in docstring',
    'D301': 'missing Returns section in docstring',
    'D302': 'docstring Args section is malformed',
    'D303': 'docstring Returns section is malformed',
    'D304': 'argument not documented in docstring',
    'D305': 'documented argument not found in function signature',
    'D306': 'type mismatch between annotation and docstring',
    'B006': 'mutable default argument',
    # Import-related errors
    'I100': 'imports not properly ordered (stdlib, third-party, local)',
    'I101': 'unused import',
    'I102': 'wildcard import should be avoided',
    'I103': 'import should be absolute',
    # Complexity errors
    'C901': 'function is too complex, consider breaking into helper functions',
    # Security errors
    'S001': 'potential hardcoded password or secret',
    'S002': 'potential SQL injection vulnerability',
    'S003': 'potential shell injection vulnerability',
    'S004': 'assert statement used in production code',
}

# Standard special methods and variables
SPECIAL_METHODS: FrozenSet[str] = frozenset([
    '__init__', '__del__', '__repr__', '__str__', '__bytes__', '__format__',
    '__lt__', '__le__', '__eq__', '__ne__', '__gt__', '__ge__', '__hash__',
    '__bool__', '__call__', '__len__', '__getitem__', '__setitem__',
    '__delitem__', '__iter__', '__next__', '__reversed__', '__contains__',
    '__add__', '__sub__', '__mul__', '__matmul__', '__truediv__',
    '__floordiv__', '__mod__', '__divmod__', '__pow__', '__lshift__',
    '__rshift__', '__and__', '__xor__', '__or__', '__iadd__', '__isub__',
    '__imul__', '__imatmul__', '__itruediv__', '__ifloordiv__', '__imod__',
    '__ipow__', '__ilshift__', '__irshift__', '__iand__', '__ixor__',
    '__ior__', '__neg__', '__pos__', '__abs__', '__invert__', '__complex__',
    '__int__', '__float__', '__round__', '__index__', '__enter__',
    '__exit__', '__await__', '__aiter__', '__anext__', '__aenter__',
    '__aexit__', '__new__'
])

SPECIAL_VARIABLES: FrozenSet[str] = frozenset(['self', 'cls'])

PYTEST_METHODS: FrozenSet[str] = frozenset([
    'setup_module', 'teardown_module', 'setup_class', 'teardown_class',
    'setup_method', 'teardown_method', 'setup_function', 'teardown_function'
])

# Standard library modules (partial list - could be expanded)
STDLIB_MODULES: FrozenSet[str] = frozenset([
    'os', 'sys', 'ast', 're', 'json', 'urllib', 'http', 'pathlib', 'datetime',
    'collections', 'itertools', 'functools', 'operator', 'typing', 'dataclasses',
    'argparse', 'logging', 'unittest', 'subprocess', 'threading', 'multiprocessing',
    'sqlite3', 'csv', 'xml', 'email', 'hashlib', 'hmac', 'base64', 'pickle',
    'tempfile', 'shutil', 'glob', 'fnmatch', 'linecache', 'textwrap', 'string',
    'math', 'random', 'statistics', 'decimal', 'fractions', 'cmath', 'time',
    'calendar', 'zoneinfo', 'locale', 'gettext', 'struct', 'codecs', 'unicodedata',
    'io', 'gzip', 'bz2', 'lzma', 'zipfile', 'tarfile', 'configparser', 'netrc',
    'xdrlib', 'plistlib', 'token', 'tokenize', 'keyword', 'pkgutil', 'modulefinder',
    'runpy', 'importlib', 'parser', 'symbol', 'compiler', 'dis', 'pickletools',
    'formatter', 'errno', 'ctypes', 'platform', 'curses', 'getpass', 'getopt',
    'shlex', 'socketserver', 'wsgiref', 'webbrowser', 'cgi', 'cgitb', 'wsgiref',
    'ftplib', 'poplib', 'imaplib', 'nntplib', 'smtplib', 'smtpd', 'telnetlib',
    'uuid', 'socketserver', 'xmlrpc', 'ipaddress', 'mailcap', 'mailbox',
    'mimetypes', 'uu', 'binascii', 'binhex', 'quopri', 'pty', 'fcntl', 'pipes',
    'posixpath', 'ntpath', 'macpath', 'stat', 'statvfs', 'filecmp', 'tempfile',
    'glob', 'fnmatch', 'linecache', 'shutil', 'macpath', 'dircache'
])
