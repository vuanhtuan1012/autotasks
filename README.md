# Autotasks

This directory contains the Fabfile which is used to execute administration tasks:

- [ ] `fab analyse` analyses coding standard with `pylint`.
- [ ] `fab autoformat` formats code files following PEP8 with `black`.
- [ ] `fab autotest` launches all unit tests in the `tests` directory with `pytest`.
- [ ] `fab check-types` verifies the type of variables with `mypy`.
- [ ] `fab clean` cleans the virtual environment.
- [ ] `fab develop` setups a virtual environment with minimal packages installed for developers.
- [ ] `fab env` creates a pure environment, no additional packages installed.
- [ ] `fab fixtures` shows all `pytest` fixtures used in unit tests.
- [ ] `fab generate-files` generates essential files, directory for a Python project.
- [ ] `fab install` installs packages declared in the requirements file to virtual environment.
- [ ] `fab tree` to list files, sub-directories of current directory in a tree-like format.

This Fabfile inspired by fabric tool of POST Luxembourg which is written by Frank Lazzarini <frank.lazzarini@post.lu>

## Packages
- `fabric`: to create autotasks
- `entr`: to re-run automatically unittests if there's a change in source files
- `coloredlogs`: to color logging
- `venv`: create a virtual environment
- `tree`: list contents of directories in a tree-like format
