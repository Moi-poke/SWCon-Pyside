import importlib
import sys

from libs.Utility import getClassesInModule, getModuleNames, import_all_modules


class CommandLoader:
    def __init__(self, base_path, base_class):
        self.path = base_path
        self.base_type = base_class
        self.modules = []

    def load(self) -> (list, list):
        error_ls = []
        if not self.modules:  # load if empty
            self.modules, error_ls = import_all_modules(self.path)

        # return command class types
        return self.get_command_classes(), error_ls

    def reload(self) -> (bool, dict):
        error_while_process = False
        loaded_module_dic = {mod.__name__: mod for mod in self.modules}
        cur_module_names = getModuleNames(self.path)

        # Load only not loaded modules
        error_dict = {}
        not_loaded_module_names = list(set(cur_module_names) - set(loaded_module_dic.keys()))
        if len(not_loaded_module_names) > 0:
            res, error_dict = import_all_modules(self.path, not_loaded_module_names)
            self.modules.extend(res)

        # Reload commands except deleted ones
        for mod_name in list(set(cur_module_names) & set(loaded_module_dic.keys())):
            try:
                importlib.reload(loaded_module_dic[mod_name])
            except Exception:
                type_, value_, traceback_ = sys.exc_info()
                error_dict |= {loaded_module_dic[mod_name].__name__: [type_, value_, traceback_]}

        # Unload deleted commands
        for mod_name in list(set(loaded_module_dic.keys()) - set(cur_module_names)):
            self.modules.remove(loaded_module_dic[mod_name])
            sys.modules.pop(loaded_module_dic[mod_name].__name__)  # Un-import module forcefully

        # return result and command class types
        return self.get_command_classes(), error_dict

    def get_command_classes(self) -> list:
        classes = []
        for mod in self.modules:
            classes.extend(
                [[c, True] for c in getClassesInModule(mod) if issubclass(c, self.base_type) and hasattr(c, "NAME") and c.NAME]
            )
        print(classes, file=sys.stderr)
        return classes
