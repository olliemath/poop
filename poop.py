"""poop - for when pip is too slow 💩"""
from __future__ import annotations

import os as _os
import re as _re
import shutil as _shutil
import site as _site
import stat as _stat
import sys as _sys
from argparse import ArgumentParser as _ArgumentParser, _StoreTrueAction
from pathlib import Path as _Path

_IGNORE = _shutil.ignore_patterns("tests", "test_*.py")


def install(package: str, editable: bool = True, user: bool = False) -> None:
    """Install a local package.

    Essentially we will just copy or symlink this to the correct site-packages
    directory. I'm not sure how something so simple got so complicated?
    """
    # TODO: normalise package name?

    source_dir = _Path(package).resolve()
    if not source_dir.exists():
        _printerr(f"Error: 🕵️ couldn't find '{package}' 🤷")

    if user:
        site = _Path(_site.getusersitepackages())
    else:
        site = _Path(_site.getsitepackages()[0])

    try:
        _install_impl(source_dir, site, editable)
    except PermissionError:
        _printerr(
            f"Error: 👮 insufficient permissions to write '{site}' 🤷"
            "\n       you could try using the --user flag or in a venv?",
            code=3,
        )


def _install_impl(source_dir: _Path, target_dir: _Path, editable: bool) -> None:
    _version, scripts = _parse_pyproject(source_dir)
    source = _get_top_level(source_dir)
    if editable:
        target = target_dir / (source_dir.name + ".pth")
    else:
        target = target_dir / source.name

    if target.exists():
        _printerr(
            f"Error: 👯 duplicate installed package found at '{target}' 🤷"
            "\n       you might want to remove this somehow?"
            "\n       we'll try and add 'uninstall' soon!",
            code=5,
        )

    if editable:
        with target.open("w") as f:
            f.write(str(source.parent.resolve()) + _os.linesep)
    elif source.is_file():
        _shutil.copy(source, target)
    else:
        _shutil.copytree(source, target, ignore=_IGNORE)

    _install_scripts(scripts)


def _install_scripts(scripts: dict[str, str]) -> None:
    bin = _Path(_sys.executable).parent
    for name, spec in scripts.items():
        module, func = spec.split(":")

        script: _Path = bin / name
        with script.open("w") as f:
            f.write(
                f"""#!{_sys.executable}
# -*- coding: utf-8 -*-
import re
import sys
from {module} import {func}
if __name__ == '__main__':
    sys.argv[0] = re.sub(r'(-script\\.pyw|\\.exe)?$', '', sys.argv[0])
    sys.exit({func}())
"""
            )

        # make our script executable
        script.chmod(
            script.stat().st_mode | _stat.S_IXUSR | _stat.S_IXGRP | _stat.S_IXOTH
        )


def _parse_pyproject(source_dir: _Path) -> tuple[str, dict[str, str]]:
    scripts = {}
    version = "0.0.0"
    if (pyproject := source_dir / "pyproject.toml").exists():
        try:
            import tomllib

            with pyproject.open("rb") as f:
                parsed = tomllib.load(f).get("project")

            if parsed is not None:
                version = parsed.get("version", "0.0.0")
                scripts = parsed.get("scripts", {})

        except ModuleNotFoundError:
            # ugh, nasty.. but gone by 3.11
            with pyproject.open("r") as f:
                raw = f.read()

            project_spec = _re.split(r"^\[project\]|\n\[project\]", raw, maxsplit=1)
            if len(project_spec) > 1:
                project_spec = _re.split(r"\n\[", project_spec[1], maxsplit=1)
                for line in project_spec[0].split("\n"):
                    if match := _re.match(r'^version\s+=\s+"([.\w.]+)"', line):
                        version = match.groups()[0]

            script_spec = _re.split(r"\n\[project.scripts\]", raw, maxsplit=1)
            if len(script_spec) > 1:
                script_spec = _re.split(r"\n\[", script_spec[1], maxsplit=1)
                for line in script_spec[0].split("\n"):
                    if "=" in line:
                        name, spec = line.split("=")
                        scripts[name.strip()] = spec.strip()[1:-1]

    return version, scripts


def _get_top_level(source_dir: _Path) -> _Path:
    """Determine the top-level file/directory for the package.

    We try only package/package.py, package/package and package/src/package
    TODO: support some subset of pyproject.toml
    """
    candidate: _Path = source_dir / (source_dir.name + ".py")
    if candidate.exists() and candidate.is_file():
        return candidate

    candidate = source_dir / source_dir.name
    if candidate.exists() and candidate.is_dir():
        return candidate

    candidate = source_dir / "src" / source_dir.name
    if candidate.exists() and candidate.is_dir():
        return candidate

    return _printerr(
        "Error: 🔖 incorrectly labelled or non-existant source 🤷"
        "\n       name your stuff right, or else use a python with toml support!"
    )  # type: ignore


def _get_parser() -> _ArgumentParser:
    """Build and return a decent-ish arg parser."""

    parser = _ArgumentParser(
        prog="poop",
        description="""install local pure python packages super quickly!
        for when pip is too slow 💩 and you're not doing anything fancy 🧐 """,
        epilog="""pip is advanced and complex 🔬 for serious professionals 🤵
        poop is basic and simple 🔨 for impatient children 🦄""",
    )

    parser.add_argument(
        "command",
        type=str,
        choices=["install", "develop"],
        help="action to perform on the package",
    )
    parser.add_argument("package", type=str, help="name or path of the package")
    parser.add_argument(
        "--user", action=_StoreTrueAction, help="install as user-local package"
    )
    return parser


def _printerr(err: str, code: int = 1) -> None:
    print(err, file=_sys.stderr)
    exit(code)


def main() -> None:
    parser = _get_parser()
    args = parser.parse_args()
    if args.command == "install":
        install(args.package, False, args.user)
    elif args.command == "develop":
        install(args.package, True, args.user)


if __name__ == "__main__":
    main()
