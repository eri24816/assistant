from .util import generate_spec_from_function

import importlib
import pkgutil

tool_list = []

# Automatically import function with same name as module from all submodules
for module_info in pkgutil.iter_modules(__path__):
    mod_name = module_info.name
    try:
        mod = importlib.import_module(f'.{mod_name}', __name__)
        # Import the function with the same name as the module, if it exists
        if hasattr(mod, mod_name):
            globals()[mod_name] = getattr(mod, mod_name)
            tool_list.append(getattr(mod, mod_name))
    except Exception:
        # Skip modules that can't be imported this way
        pass


tools = {func.__name__: func for func in tool_list}