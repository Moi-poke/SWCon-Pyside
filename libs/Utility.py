from __future__ import annotations

import importlib
import inspect
import os
import sys
import traceback
from logging import NullHandler, getLogger
from pathlib import Path
from types import ModuleType
from typing import Sequence

logger = getLogger(__name__)
logger.addHandler(NullHandler())
logger.propagate = True


def ospath(path: str) -> str:
    """Normalize a filesystem path."""
    return os.path.normpath(path)


def browseFileNames(
    path: str = ".",
    ext: str = "",
    recursive: bool = True,
    name_only: bool = True,
) -> list[str]:
    """
    List file names under a directory.

    Parameters
    ----------
    path:
        Base directory.
    ext:
        File extension filter, e.g. '.py'. Empty means all files.
    recursive:
        Whether to search recursively.
    name_only:
        If True, return path relative to `path`. Otherwise return absolute paths.
    """
    base = Path(path).resolve()
    if not base.exists():
        return []

    pattern = f"**/*{ext}" if recursive else f"*{ext}"
    files = sorted([p for p in base.glob(pattern) if p.is_file()])

    if name_only:
        return [os.path.relpath(str(p), str(base)) for p in files]
    return [str(p) for p in files]


def getClassesInModule(module: ModuleType) -> list[type]:
    """Return classes defined in the target module itself."""
    return [
        cls
        for _, cls in inspect.getmembers(module, inspect.isclass)
        if cls.__module__ == module.__name__
    ]


def getModuleNames(base_path: str) -> list[str]:
    """
    Convert Python files under `base_path` into importable module names.

    Example
    -------
    base_path = '/project/Commands/Python'
    file      = '/project/Commands/Python/foo/bar.py'
    returns   = 'Commands.Python.foo.bar'
    """
    base = Path(base_path).resolve()
    if not base.exists():
        return []

    # project root (/project) を import root にする
    if len(base.parents) >= 2:
        import_root = base.parents[1]
    else:
        import_root = base.parent

    import_root_str = str(import_root)
    if import_root_str not in sys.path:
        sys.path.insert(0, import_root_str)

    modules: list[str] = []
    for py_file in sorted(base.rglob("*.py")):
        if py_file.name == "__init__.py":
            continue
        rel = py_file.relative_to(import_root).with_suffix("")
        modules.append(".".join(rel.parts))
    return modules


def import_all_modules(
    base_path: str,
    mod_names: str | Sequence[str] | None = None,
) -> tuple[list[ModuleType], dict[str, list[str]]]:
    """
    Import all modules or a subset of modules.

    Returns
    -------
    modules:
        Imported module list.
    error_dict:
        {
            module_name: [exception_type_name, exception_message, traceback_string]
        }
    """
    importlib.invalidate_caches()
    if mod_names is None:
        target_names = getModuleNames(base_path)
    elif isinstance(mod_names, str):
        target_names = [mod_names]
    else:
        target_names = list(mod_names)

    target_names = sorted(set(target_names))

    modules: list[ModuleType] = []
    error_dict: dict[str, list[str]] = {}

    for name in target_names:
        try:
            logger.debug("Import module: %s", name)
            modules.append(importlib.import_module(name))
        except Exception as exc:
            error_dict[name] = [
                type(exc).__name__,
                str(exc),
                traceback.format_exc(),
            ]
            logger.exception("Failed to import module: %s", name)

    return modules, error_dict
