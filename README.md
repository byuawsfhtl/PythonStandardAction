# PythonStandardAction

*A github action to be used across python projects in the byuawsfhtl organization*

As a lab, certain standards have been generally adopted, but have had a hard time being actually implemented. This action intends to fix that by acting like a linter, enforcing certain styles.

## Enforced Styles

1. snake_case is enforced on all function and variable name.
2. The use of  or name mangling is disallowed.
3. Docstring argument definitions must start with a capital letter and must use a period at the end. To indicate additional information in a sentence like format, use semicolons to separate sections. The first letters of these sections should also be capitalized.
4. Functions are required to have a docstring.
5. Function arguments may not use mutable items(list, set, dict) as defaults, as python handles defaults stupidly.
6. Functions must specify a return type.
7. Class names must be in PascalCase
8. First line of docstring must end with period
9. Classes must have a docstring
10. Function arguments must be documented in a section started with `Args: \n`
11. Docstring argument names must be up to date with the function arguments' names
12. Argument defaults must be documented in the `Args:`  section in a section of their corresponding arguments saying `defaults to {default value}`
13. A function's return value must be documented in a section started with `Returns: \n` unless the function is anotated as returning None.

## Adding action to your workflow

This action is best used in the same section as the meds action. Just add it as another step like the following.

```github
        steps:
            - name: Follow Python Standard
              uses: byuawsfhtl/PythonStandardAction@v1.2.0
```

## Excluding files from the check

This action uses a local file `.standardignore` to specify files and other items to not check.

To use this, create a file named `.standardignore` and put in file paths like you would for a `.gitignore` file. The following is an example of entries you could put in your file.

```cmd
**/.*

**/__pycache__
**/img
**/TempFile.py
```

The above entries in a `.standardignore` would have the checker skip over the folders/files that match the pattern, such as private folders, pychache folders, img folders, and the TempFile.py file. The standard checker will already ignore any file not is not a `.py` file, this just allows you to have it ignore general areas and specific ones.

## Excluding variables and functions from the check

Using the `.standardignore` file specified in the section above, specific function and variable names can be skipped over on the check.

The syntax to do so is the use of the `name:` before the name of the variable/function to ignore.

For example

```cmd
name: sleep_for_retry
```

The above example ignores the sleep_for_retry function when applying standards as the name is required as it is an overwrite of an outside modules functionality.

## Running locally so you don't have to wait on github actions

From the root fo the repo you're trying to check, run the following in a terminal:

```cmd
python "path-to-this-repo/StandardCheck.py"
```

So, if I were trying to run it on TreeTapper, and both TreeTapper and PythonStandardAction were in the same folder, I would run:

```cmd
python "../PythonStandardAction/StandardCheck.py"
```

This can also be done for the linting step by running the same command, but replacing the `StandardCheck.py` reference with the `LintingCheck.py` referece as follows:

```cmd
python "path-to-this-repo/LintingCheck.py"
```

## Notes about the MyPy checker step

The MyPy checker step is going to default to running with the '--strict' call on every file in the application unless the entire file is ignored. Note that it doesn't ignore specific functions, classes, or lines since they are instead ignored with the usual "# type: ignore" comment that it otherwise uses. If you want to run this with different MyPy settings and arguments, simply add "mypyargs: [Your arguments here]"  to the ".standardignore" file in the format as follows:

```cmd
mypyargs: --ignore-missing-imports --deprecated-calls-exclude
```

Note that doing something like this will automatically disable the '--strict' tag in MyPy unless it is specifically included in the arguments. Regardless of if custom args are passed in or not, this step will automatically figure out the needed file path arguments so it is not necessary to add this to the beginning and will actually cause errors if you do.

