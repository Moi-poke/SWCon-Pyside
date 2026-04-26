from __future__ import annotations

import hashlib
import importlib
import importlib.util
import inspect
import pkgutil
import sys
import traceback
from dataclasses import dataclass
from logging import NullHandler, getLogger
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable, Optional, Sequence

logger = getLogger(__name__)
logger.addHandler(NullHandler())
logger.propagate = True


CommandEntry = list[Any]
LoaderErrors = dict[str, list[str]]


@dataclass(frozen=True)
class CommandSource:
    """Metadata about where a command class was loaded from."""

    kind: str  # "user" | "builtin" | "dev" | "fs" | "pkg"
    location: str


@dataclass(frozen=True)
class _FsRoot:
    path: Path
    kind: str = "fs"


@dataclass(frozen=True)
class _PkgRoot:
    package: str
    kind: str = "pkg"


class CommandLoader:
    """Load command classes from multiple sources with stable precedence.

    Design goals
    ------------
    1. Support multiple *filesystem* roots (e.g. user command dir, dev repo dir).
    2. Support multiple *package* roots (e.g. libs.builtin_commands.python).
    3. Preserve caller compatibility with the legacy return shape:
           load()  -> tuple[list[list[Any]], dict[str, list[str]]]
           reload() -> same
       where each list element is `[command_class]`.
    4. Deduplicate by logical command name (`NAME` if present, else class name),
       keeping the first source by precedence order.

    Recommended precedence order
    ----------------------------
    Pass roots in this order:
      - user roots first (highest priority)
      - builtin package roots second
      - dev filesystem roots last (fallback)

    Example
    -------
    loader = CommandLoader(
        base_class=CommandBase,
        filesystem_roots=[user_dir, dev_dir],
        package_roots=["libs.builtin_commands.python"],
        fs_kinds=["user", "dev"],
        pkg_kinds=["builtin"],
    )
    items, errors = loader.load()
    """

    def __init__(
        self,
        base_class: type,
        filesystem_roots: Optional[Sequence[str | Path]] = None,
        package_roots: Optional[Sequence[str]] = None,
        *,
        fs_kinds: Optional[Sequence[str]] = None,
        pkg_kinds: Optional[Sequence[str]] = None,
    ) -> None:
        self.base_type = base_class

        filesystem_roots = list(filesystem_roots or [])
        package_roots = list(package_roots or [])
        fs_kinds = list(fs_kinds or ["fs"] * len(filesystem_roots))
        pkg_kinds = list(pkg_kinds or ["pkg"] * len(package_roots))

        if len(fs_kinds) != len(filesystem_roots):
            raise ValueError("len(fs_kinds) must match len(filesystem_roots)")
        if len(pkg_kinds) != len(package_roots):
            raise ValueError("len(pkg_kinds) must match len(package_roots)")

        self._fs_roots: list[_FsRoot] = [
            _FsRoot(Path(p).resolve(), kind=k)
            for p, k in zip(filesystem_roots, fs_kinds)
        ]
        self._pkg_roots: list[_PkgRoot] = [
            _PkgRoot(pkg, kind=k) for pkg, k in zip(package_roots, pkg_kinds)
        ]

        self.modules: list[ModuleType] = []
        self.classes: list[CommandEntry] = []
        self.errors: LoaderErrors = {}

        # For tracing where each class came from
        self._source_by_class: dict[type[Any], CommandSource] = {}
        self._module_names_loaded: set[str] = set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> tuple[list[CommandEntry], LoaderErrors]:
        self._reset_state()
        self._load_all()
        return self.classes, self.errors

    def reload(self) -> tuple[list[CommandEntry], LoaderErrors]:
        # purge previously loaded dynamic fs modules from sys.modules
        for mod_name in list(self._module_names_loaded):
            sys.modules.pop(mod_name, None)
        self._reset_state()
        self._load_all(force_reload_packages=True)
        return self.classes, self.errors

    def get_source_info(self, command_class: type[Any]) -> Optional[CommandSource]:
        return self._source_by_class.get(command_class)

    def get_source_location(self, command_class: type[Any]) -> Optional[str]:
        src = self.get_source_info(command_class)
        return src.location if src else None

    # ------------------------------------------------------------------
    # Internal lifecycle
    # ------------------------------------------------------------------

    def _reset_state(self) -> None:
        self.modules = []
        self.classes = []
        self.errors = {}
        self._source_by_class = {}
        self._module_names_loaded = set()

    def _load_all(self, *, force_reload_packages: bool = False) -> None:
        selected: dict[str, type[Any]] = {}

        # 1) filesystem roots in declared order
        for root in self._fs_roots:
            if not root.path.exists() or not root.path.is_dir():
                logger.debug("Command root missing: %s", root.path)
                continue
            for py_file in self._iter_python_files(root.path):
                module = self._import_fs_module(py_file)
                if module is None:
                    continue
                self.modules.append(module)
                self._collect_classes(
                    module, CommandSource(root.kind, py_file.as_posix()), selected
                )

        # 2) package roots in declared order
        for root in self._pkg_roots:
            for module in self._iter_package_modules(
                root.package, force_reload=force_reload_packages
            ):
                if module is None:
                    continue
                self.modules.append(module)
                self._collect_classes(
                    module, CommandSource(root.kind, module.__name__), selected
                )

        self.classes = [[cls] for cls in selected.values()]

    # ------------------------------------------------------------------
    # Discovery helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _iter_python_files(root: Path) -> Iterable[Path]:
        # Current project convention is .py files directly under command dirs,
        # but rglob keeps this flexible for future nested categories.
        for path in sorted(root.rglob("*.py")):
            if path.name == "__init__.py":
                continue
            if "__pycache__" in path.parts:
                continue
            yield path

    def _iter_package_modules(
        self, package_name: str, *, force_reload: bool = False
    ) -> Iterable[Optional[ModuleType]]:
        try:
            package = importlib.import_module(package_name)
            if force_reload:
                package = importlib.reload(package)
        except Exception:
            self._record_error(package_name, "package import failed")
            return []

        # If this is a simple module instead of a package, still support it.
        if not hasattr(package, "__path__"):
            yield package
            return

        for mod_info in pkgutil.walk_packages(
            package.__path__, prefix=package.__name__ + "."
        ):
            if mod_info.ispkg:
                continue
            mod_name = mod_info.name
            try:
                if force_reload and mod_name in sys.modules:
                    module = importlib.reload(sys.modules[mod_name])
                else:
                    module = importlib.import_module(mod_name)
                yield module
            except Exception:
                self._record_error(mod_name, "module import failed")
                yield None

    def _import_fs_module(self, py_file: Path) -> Optional[ModuleType]:
        unique_name = self._build_unique_module_name(py_file)
        try:
            spec = importlib.util.spec_from_file_location(unique_name, py_file)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not create spec for {py_file}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[unique_name] = module
            self._module_names_loaded.add(unique_name)
            spec.loader.exec_module(module)
            return module
        except Exception:
            self._record_error(py_file.as_posix(), "module import failed")
            return None

    @staticmethod
    def _build_unique_module_name(py_file: Path) -> str:
        digest = hashlib.sha1(py_file.as_posix().encode("utf-8")).hexdigest()[:12]
        stem = py_file.stem.replace("-", "_")
        return f"_swcon_cmd_{stem}_{digest}"

    # ------------------------------------------------------------------
    # Class extraction / precedence
    # ------------------------------------------------------------------

    def _collect_classes(
        self,
        module: ModuleType,
        source: CommandSource,
        selected: dict[str, type[Any]],
    ) -> None:
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if not issubclass(cls, self.base_type):
                continue
            if cls is self.base_type:
                continue
            # Only classes defined in this module, not imported re-exports.
            if cls.__module__ != module.__name__:
                continue

            key = self._command_key(cls)
            if key in selected:
                logger.debug(
                    "Duplicate command '%s' ignored from %s (already selected from %s)",
                    key,
                    source.location,
                    self._source_by_class[selected[key]].location,
                )
                continue

            selected[key] = cls
            self._source_by_class[cls] = source

    @staticmethod
    def _command_key(command_class: type[Any]) -> str:
        return str(getattr(command_class, "NAME", command_class.__name__))

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    def _record_error(self, key: str, headline: str) -> None:
        self.errors[key] = [headline, traceback.format_exc()]
        logger.debug("CommandLoader error at %s: %s", key, headline)


if __name__ == "__main__":
    # Minimal self-test / example usage
    class _Base:
        pass

    loader = CommandLoader(_Base)
    items, errors = loader.load()
    print(items)
    print(errors)
