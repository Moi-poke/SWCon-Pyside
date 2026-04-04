from __future__ import annotations

import importlib
import inspect
import sys
from logging import NullHandler, getLogger
from types import ModuleType
from typing import Any

from libs.Utility import getClassesInModule, getModuleNames, import_all_modules

logger = getLogger(__name__)
logger.addHandler(NullHandler())
logger.propagate = True


CommandEntry = list[Any]
LoaderErrors = dict[str, list[str]]


class CommandLoader:
    def __init__(self, base_path: str, base_class: type) -> None:
        self.path = base_path
        self.base_type = base_class
        self.modules: list[ModuleType] = []

    def load(self) -> tuple[CommandEntry, LoaderErrors]:
        """
        Load command modules if not loaded yet.
        """
        error_dict: LoaderErrors = {}
        if not self.modules:
            self.modules, error_dict = import_all_modules(self.path)
        return self.get_command_classes(), error_dict

    def reload(self) -> tuple[CommandEntry, LoaderErrors]:
        """
        Reload existing modules, import new modules, and unload deleted modules.

        Policy
        ------
        - If reload fails, keep the previous module object in self.modules
        - Surface the error through error_dict
        - Command instances are expected to be stopped before reload
        """
        importlib.invalidate_caches()

        loaded_module_dic = {mod.__name__: mod for mod in self.modules}
        cur_module_names = getModuleNames(self.path)

        error_dict: LoaderErrors = {}

        cur_set = set(cur_module_names)
        old_set = set(loaded_module_dic.keys())

        not_loaded_module_names = sorted(cur_set - old_set)
        reload_target_names = sorted(cur_set & old_set)
        removed_module_names = sorted(old_set - cur_set)

        # Import newly added modules
        if not_loaded_module_names:
            res, err = import_all_modules(self.path, not_loaded_module_names)
            self.modules.extend(res)
            error_dict.update(err)

        # Reload existing modules
        for mod_name in reload_target_names:
            try:
                importlib.reload(loaded_module_dic[mod_name])
            except Exception as exc:
                error_dict[mod_name] = [
                    type(exc).__name__,
                    str(exc),
                    __import__("traceback").format_exc(),
                ]
                logger.exception("Failed to reload module: %s", mod_name)

        # Unload removed modules
        for mod_name in removed_module_names:
            mod = loaded_module_dic[mod_name]
            if mod in self.modules:
                self.modules.remove(mod)
            sys.modules.pop(mod.__name__, None)

        return self.get_command_classes(), error_dict

    def get_command_classes(self) -> CommandEntry:
        """
        Return classes matching the command base type.

        Returned format is kept compatible with current UI code:
            [[ClassType, True], ...]
        """
        classes: CommandEntry = []
        name_seen: dict[str, str] = {}

        for mod in self.modules:
            for cls in getClassesInModule(mod):
                if cls is self.base_type:
                    continue
                if not issubclass(cls, self.base_type):
                    continue
                if inspect.isabstract(cls):
                    continue
                name = getattr(cls, "NAME", None)
                if not name:
                    continue
                if name in name_seen:
                    logger.warning(
                        "Duplicate command NAME detected: %s (%s and %s)",
                        name,
                        name_seen[name],
                        cls.__module__,
                    )
                else:
                    name_seen[name] = cls.__module__
                classes.append([cls, True])

        classes.sort(key=lambda item: str(getattr(item[0], "NAME", "")))
        return classes
