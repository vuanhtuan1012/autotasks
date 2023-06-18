# -*- coding: utf-8 -*-
# @Author: VU Anh Tuan
# @Date:   2022-09-04 03:15:56
# @Email:  anh-tuan.vu@outlook.com
# @Last Modified by:   VU Anh Tuan
# @Last Modified time: 2023-05-27 14:55:03

"""
Automation tasks
"""

import logging
import os
import re
from enum import Enum
from string import Template
from textwrap import dedent
from typing import List, Optional

import coloredlogs
from fabric import task

coloredlogs.install()
LOGGER = logging.getLogger(__name__)
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CW_DIR = os.getcwd()  # current working directory


class DefaultValue(Enum):
    """
    DefaultValue class
    """

    ENV_NAME = "env"
    REQ_FILE = "requirements.txt"
    README_FILE = "README.md"
    HEADERS = Template("\n".join(["# $title", "", "## Reference"]))
    PYLINTRC_FILE = ".pylintrc"
    PYLINTRC_CONTENT = """
    [MAIN]
    init-hook='import sys; sys.path.append("{}")'
    """
    MYPY_FILE = "mypy.ini"
    MYPY_CONTENT = """
    [mypy]
    ignore_missing_imports = True
    explicit_package_bases = True
    """
    TESTS_DIRS = ["tests"]
    DEPTH = 2
    PACKAGES = [
        "coloredlogs",
        "decorator",
        "fabric",
        "black",
        "pylint",
        "pytest",
        "mypy",
    ]
    INCLUDE_FILES = ["'*.py'"]
    # EXCLUDE_FILES = ["'draft.py'", "'fabfile.py'"]
    EXCLUDE_FILES = ["'draft.py'"]
    EXCLUDE_DIRS = ["'**/__pycache__/*'", "'**/_build/*'", "'**/env/*'"]


@task
def generate_files(ctx, debug=False, cwd=False):
    """
    Generate essential files, directory for a Python project

    It contains a sub-directory which has same name of the
    current directory, README, pip requirements file, `mypy` config file
    and `pylint` resource control file

    Args:
        debug (bool, optional): display debug messages. Defaults to False.
        cwd (bool, optional): set current directory as root. Defaults to False.
    """
    # create subdirectory which has the same name of the current one
    # source code will be in this subdirectory
    # test files (if they exist) will be in the directory "tests"
    # which has the same level of subdirectory
    create_subdir(ctx, debug, cwd)

    working_dir = CW_DIR if cwd else ROOT_DIR
    # create __init__.py in subdir
    dirname = os.path.basename(working_dir)
    write_file(
        file_path=os.path.join(working_dir, dirname, "__init__.py"),
        additional_msg="__init__.py",
    )

    # create README file if it doesn't exist
    title = dirname.replace("_", " ").title()
    headers = DefaultValue.HEADERS.value.substitute(title=title)
    write_file(
        file_path=os.path.join(working_dir, DefaultValue.README_FILE.value),
        content=headers,
        additional_msg="README",
    )

    # create pip requirements file if it doesn't exist
    write_file(
        file_path=os.path.join(working_dir, DefaultValue.REQ_FILE.value),
        content="\n".join(DefaultValue.PACKAGES.value),
        additional_msg="pip requirements",
    )

    # create pylint resource control file if it doesn't exist
    full_path = os.path.join(working_dir, dirname)
    write_file(
        file_path=os.path.join(working_dir, DefaultValue.PYLINTRC_FILE.value),
        content=dedent(DefaultValue.PYLINTRC_CONTENT.value.format(full_path)).strip(),
        additional_msg="pylint resource control",
    )


@task
def env(ctx, debug=False, cwd=False):
    """
    Create a new pure virtual environment, no additional packages installed

    Args:
        debug (bool, optional): display debug messages. Defaults to False.
        cwd (bool, optional): set current directory as root. Defaults to False.
    """
    working_dir = CW_DIR if cwd else ROOT_DIR
    env_path = os.path.join(working_dir, DefaultValue.ENV_NAME.value)
    if os.path.isdir(env_path):
        LOGGER.info("Directory `%s` already exists.", DefaultValue.ENV_NAME.value)
        return
    with ctx.cd(working_dir):
        ctx.run(
            f"python -m venv {DefaultValue.ENV_NAME.value}",
            env=os.environ,
            hide=not debug,
        )
    LOGGER.info(
        "Create successfully virtual environment `%s`.",
        DefaultValue.ENV_NAME.value,
    )
    # update pip of virtual environment
    with ctx.cd(working_dir):
        ctx.run(
            (
                f"source {DefaultValue.ENV_NAME.value}/bin/activate && "
                f"pip install --upgrade pip"
            ),
            env=os.environ,
            hide=not debug,
        )
    LOGGER.info("Update successfully pip.")


@task
def install(ctx, debug=False, cwd=False):
    """
    Install packages declared in the requirements file to virtual environment

    Args:
        debug (bool, optional): display debug messages. Defaults to False.
        cwd (bool, optional): set current directory as root. Defaults to False.
    """
    working_dir = CW_DIR if cwd else ROOT_DIR
    env_path = os.path.join(working_dir, DefaultValue.ENV_NAME.value)
    if not os.path.isdir(env_path):
        LOGGER.info(
            "Virtual environment `%s` does not exist.", DefaultValue.ENV_NAME.value
        )
        return
    # install packages
    with ctx.cd(working_dir):
        ctx.run(
            (
                f"source {DefaultValue.ENV_NAME.value}/bin/activate && "
                f"pip install -r {DefaultValue.REQ_FILE.value}"
            ),
            env=os.environ,
            hide=not debug,
        )
    LOGGER.info(
        "Install successfully packages from file `%s`.",
        DefaultValue.REQ_FILE.value,
    )


@task
def develop(ctx, debug=False, cwd=False):
    """
    Setup a virtual environment with minimal packages installed for developers

    Args:
        debug (bool, optional): display debug messages. Defaults to False.
        cwd (bool, optional): set current directory as root. Defaults to False.
    """

    # generate README and pip requirements files if needed
    generate_files(ctx, debug, cwd)  # type: ignore

    # create virtual environment venv
    env(ctx, debug, cwd)  # type: ignore

    # install requirement packages
    install(ctx, debug, cwd)  # type: ignore


@task
def autotest(ctx, warnings=False, cwd=False):
    """
    Launch all unit tests in `tests` directory with `pytest`

    Args:
        warnings (bool, optional): display warnings. Defaults to False.
        cwd (bool, optional): set current directory as root. Defaults to False.
    """
    tests_dirs = verify_directories(DefaultValue.TESTS_DIRS.value, cwd)
    if not tests_dirs:
        LOGGER.info("No test directory.")
        return

    find_cmd = build_find_command(
        include_files=DefaultValue.INCLUDE_FILES.value,
        exclude_dirs=DefaultValue.EXCLUDE_DIRS.value,
    )

    disable_warnings = ""
    if not warnings:
        disable_warnings = " --disable-pytest-warnings"

    working_dir = CW_DIR if cwd else ROOT_DIR
    test_dirs_str = " ".join(tests_dirs)
    with ctx.cd(working_dir):
        ctx.run(
            (
                f"{find_cmd} | entr -c python -m pytest -v "
                f"{test_dirs_str} {disable_warnings}".strip()
            ),
            pty=True,
            env=os.environ,
        )


@task
def analyse(ctx, debug=False, cwd=False):
    """
    Analyse coding standard with `pylint`

    Args:
        debug (bool, optional): display debug messages. Defaults to False.
        cwd (bool, optional): set current directory as root. Defaults to False.
    """
    if debug:
        coloredlogs.install(level="DEBUG")
    LOGGER.debug("Included files: %s", ", ".join(DefaultValue.INCLUDE_FILES.value))
    LOGGER.debug("Excluded files: %s", ", ".join(DefaultValue.EXCLUDE_FILES.value))
    LOGGER.debug("Excluded directories: %s", ", ".join(DefaultValue.EXCLUDE_DIRS.value))

    find_cmd = build_find_command(
        include_files=DefaultValue.INCLUDE_FILES.value,
        exclude_files=DefaultValue.EXCLUDE_FILES.value,
        exclude_dirs=DefaultValue.EXCLUDE_DIRS.value,
    )

    working_dir = CW_DIR if cwd else ROOT_DIR
    with ctx.cd(working_dir):
        res = ctx.run(f"{find_cmd} | xargs echo", hide=True)
    files = res.stdout.strip()
    if not files:
        LOGGER.info("No files to analyse.")
        return
    LOGGER.debug("Files to analyse:\n%s\n", "\n".join(files.split()))
    LOGGER.info("Analyzing %s files...", len(files.split()))
    with ctx.cd(working_dir):
        ctx.run(f"python -m pylint {' '.join(files.split())}", pty=True, env=os.environ)


@task
def autoformat(ctx, debug=False, cwd=False):
    """
    Format code files following PEP8 with `black`

    Args:
        debug (bool, optional): display debug messages. Defaults to False.
        cwd (bool, optional): set current directory as root. Defaults to False.
    """
    if debug:
        coloredlogs.install(level="DEBUG")
    LOGGER.debug("Included files: %s", ", ".join(DefaultValue.INCLUDE_FILES.value))
    LOGGER.debug("Excluded directories: %s", ", ".join(DefaultValue.EXCLUDE_DIRS.value))

    find_cmd = build_find_command(
        include_files=DefaultValue.INCLUDE_FILES.value,
        exclude_dirs=DefaultValue.EXCLUDE_DIRS.value,
    )

    working_dir = CW_DIR if cwd else ROOT_DIR
    with ctx.cd(working_dir):
        res = ctx.run(f"{find_cmd} | xargs echo", hide=True)
    files = res.stdout.strip()
    if not files:
        LOGGER.info("No files to format.")
        return
    LOGGER.debug("Files to format:\n%s\n", "\n".join(files.split()))
    with ctx.cd(working_dir):
        ctx.run(f"black {' '.join(files.split())}", pty=True, env=os.environ)


@task
def fixtures(ctx, whole=False, warnings=False, cwd=False):
    """
    Show all `pytest` fixtures used in unit tests

    Args:
        whole (bool, optional): display whole fixtures. Defaults to False.
        warnings (bool, optional): display warnings. Defaults to False.
        cwd (bool, optional): set current directory as root. Defaults to False.
    """
    disable_warnings = ""
    if not warnings:
        disable_warnings = " --disable-pytest-warnings"

    working_dir = CW_DIR if cwd else ROOT_DIR
    option = "--fixtures" if whole else "--fixtures-per-test"
    with ctx.cd(working_dir):
        ctx.run(
            f"python -m pytest {option} {disable_warnings}".strip(),
            pty=True,
            env=os.environ,
        )


@task
def check_types(ctx, debug=False, cwd=False):
    """
    Verify variables types with `mypy`

    Args:
        debug (bool, optional): display debug messages. Defaults to False.
        cwd (bool, optional): set current directory as root. Defaults to False.
    """
    if debug:
        coloredlogs.install(level="DEBUG")
    LOGGER.debug("Included files: %s", ", ".join(DefaultValue.INCLUDE_FILES.value))
    LOGGER.debug("Excluded files: %s", ", ".join(DefaultValue.EXCLUDE_FILES.value))
    LOGGER.debug("Excluded directories: %s", ", ".join(DefaultValue.EXCLUDE_DIRS.value))

    find_cmd = build_find_command(
        include_files=DefaultValue.INCLUDE_FILES.value,
        exclude_files=DefaultValue.EXCLUDE_FILES.value,
        exclude_dirs=DefaultValue.EXCLUDE_DIRS.value,
    )

    working_dir = CW_DIR if cwd else ROOT_DIR
    with ctx.cd(working_dir):
        res = ctx.run(f"{find_cmd} | xargs echo", hide=True)
    files = res.stdout.strip()
    if not files:
        LOGGER.info("No files to check types.")
        return

    # create mypy config file if it doesn't exist
    conf_file = os.path.join(working_dir, DefaultValue.MYPY_FILE.value)
    write_file(
        file_path=conf_file,
        content=dedent(DefaultValue.MYPY_CONTENT.value).strip(),
        additional_msg="mypy config",
    )

    LOGGER.debug("Files to check types:\n%s\n", "\n".join(files.split()))
    LOGGER.info("Checking %s files...", len(files.split()))

    try:
        with ctx.cd(working_dir):
            ctx.run(
                f"python -m mypy {' '.join(files.split())}", pty=True, env=os.environ
            )
    finally:
        # remove mypy config file if it exists
        if os.path.isfile(conf_file):
            os.remove(conf_file)
            LOGGER.info("Remove successfully file mypy config `%s`.", conf_file)


@task
def tree(ctx, depth=DefaultValue.DEPTH.value):
    """
    List files, sub-directories of current directory in a tree-like format

    Args:
        depth (str, optional): depth to list contents. Defaults to 2.
    """
    exclude_dirs = [DefaultValue.ENV_NAME.value, "*pycache*"]
    exclude_dirs_str = "|".join(exclude_dirs)
    tree_cmd = f"tree -vI '{exclude_dirs_str}' --dirsfirst "
    if int(depth) > 0:
        tree_cmd += f"-L {depth}"
    ctx.run(tree_cmd, pty=True, env=os.environ)


@task
def clean(ctx, cwd=False):
    """
    Clean the virtual environment

    Args:
        cwd (bool, optional): set current directory as root. Defaults to False.
    """
    working_dir = CW_DIR if cwd else ROOT_DIR
    env_dir = os.path.join(working_dir, DefaultValue.ENV_NAME.value)
    if not os.path.isdir(env_dir):
        LOGGER.info(
            "Virtual environment `%s` does not exist.", DefaultValue.ENV_NAME.value
        )
    else:
        with ctx.cd(working_dir):
            ctx.run(f"rm -rf {DefaultValue.ENV_NAME.value}")
        LOGGER.info(
            "Clean successfully virtual environment `%s`",
            DefaultValue.ENV_NAME.value,
        )

    pylintrc_file = os.path.join(working_dir, DefaultValue.PYLINTRC_FILE.value)
    if not os.path.isfile(pylintrc_file):
        LOGGER.info(
            "File pylint resource control `%s` does not exist.",
            DefaultValue.PYLINTRC_FILE.value,
        )
    else:
        with ctx.cd(working_dir):
            ctx.run(f"rm {DefaultValue.PYLINTRC_FILE.value}")
        LOGGER.info(
            "Clean successfully file pylint resource control `%s`",
            DefaultValue.PYLINTRC_FILE.value,
        )


def build_find_command(
    include_files: Optional[List[str]] = None,
    exclude_files: Optional[List[str]] = None,
    include_dirs: Optional[List[str]] = None,
    exclude_dirs: Optional[List[str]] = None,
) -> str:
    """
    Build find command to filter files
    """
    name_searching = " -name "
    not_path = " ! -path "
    not_files = " ! -name "

    include_files_syntax = ""
    exclude_files_syntax = ""
    include_dirs_syntax = ""
    exclude_dirs_syntax = ""

    if include_files:
        include_files_syntax = f"{name_searching} {name_searching.join(include_files)}"
    if exclude_files:
        exclude_files_syntax = f"{not_files} {not_files.join(exclude_files)}"
    if include_dirs:
        include_dirs_syntax = " ".join(include_dirs)
    if exclude_dirs:
        exclude_dirs_syntax = f"{not_path} {not_path.join(exclude_dirs)}"

    find_cmd = (
        f"find {include_dirs_syntax} {exclude_dirs_syntax}"
        f"{include_files_syntax} {exclude_files_syntax} -type f"
    )
    find_cmd = re.sub(r"\s+", " ", find_cmd)
    return find_cmd


def verify_directories(dir_names: List[str], cwd=False) -> List:
    """
    Returns list of dir paths existing
    """
    working_dir = CW_DIR if cwd else ROOT_DIR
    existing_directories = []
    for name in dir_names:
        dir_path = os.path.join(working_dir, name.strip("'").strip('"'))
        if not os.path.isdir(dir_path):
            LOGGER.debug("Directory %s does not exist.", dir_path)
        else:
            existing_directories.append(dir_path)
    return existing_directories


def write_file(file_path: str, content: str = "", additional_msg: str = "") -> None:
    """
    Create a file with content if it doesn't exist
    """
    msg = f"`{file_path}`"
    if additional_msg:
        msg = f"{additional_msg} `{file_path}`"

    if os.path.isfile(file_path):
        LOGGER.info("File %s already exists", msg)
        return

    # pylint: disable=invalid-name
    with open(file_path, "w", encoding="utf-8") as fp:
        content += "\n" if content else ""
        fp.write(content)
    LOGGER.info("Create successfully file %s", msg)


def create_subdir(ctx, debug=False, cwd=False):
    """
    Create subdirectory which has the same name of the current directory
    if it doesn't exist
    """
    working_dir = CW_DIR if cwd else ROOT_DIR
    dirname = os.path.basename(working_dir)
    code_dir = os.path.join(working_dir, dirname)
    if os.path.isdir(code_dir):
        LOGGER.info("Subdirectory `%s` already exists", dirname)
        return

    with ctx.cd(working_dir):
        ctx.run(f"mkdir {dirname}", hide=not debug)
    LOGGER.info("Create successfully subdirectory `%s`", dirname)
