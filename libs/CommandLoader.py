import importlib
import sys

from libs.Utility import getClassesInModule, getModuleNames, importAllModules


class CommandLoader:
    def __init__(self, base_path, base_class):
        self.path = base_path
        self.base_type = base_class
        self.modules = []

    def load(self):
        if not self.modules:  # load if empty
            self.modules = importAllModules(self.path)

        # return command class types
        return self.getCommandClasses()

    def reload(self) -> list:
        loaded_module_dic = {mod.__name__: mod for mod in self.modules}
        cur_module_names = getModuleNames(self.path)

        # Load only not loaded modules
        not_loaded_module_names = list(set(cur_module_names) - set(loaded_module_dic.keys()))
        if len(not_loaded_module_names) > 0:
            self.modules.extend(importAllModules(self.path, not_loaded_module_names))

        # Reload commands except deleted ones
        for mod_name in list(set(cur_module_names) & set(loaded_module_dic.keys())):
            try:
                importlib.reload(loaded_module_dic[mod_name])
            except ValueError as e:
                print(f"Import module Error at {mod_name}: {e} ", file=sys.stderr)
                pass
            except SyntaxError as e:
                print(f"Syntax Error at {mod_name}: {e} ", file=sys.stderr)
                pass
            except Exception as e:
                print(f"Error at {mod_name}: {e} ", file=sys.stderr)
                pass

        # Unload deleted commands
        for mod_name in list(set(loaded_module_dic.keys()) - set(cur_module_names)):
            self.modules.remove(loaded_module_dic[mod_name])
            sys.modules.pop(loaded_module_dic[mod_name].__name__)  # Un-import module forcefully

        # return command class types
        return self.getCommandClasses()

    def getCommandClasses(self) -> list:
        classes = []
        for mod in self.modules:
            classes.extend(
                [c for c in getClassesInModule(mod) if issubclass(c, self.base_type) and hasattr(c, "NAME") and c.NAME]
            )

        return classes
