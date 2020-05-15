import itertools
import os
import importlib

ROOT_POINTER = 'clouni_root_pointer'


def execute_function(module_name, function_name, params):
    m = importlib.import_module(module_name)
    if hasattr(m, function_name):
        function_name = getattr(m, function_name)
        return function_name(**params)

def deep_update_dict(source, overrides):
    assert isinstance(source, dict)

    for k, v in overrides.items():
        if isinstance(v, dict):
            source[k] = deep_update_dict(source.get(k, {}), v)
        elif isinstance(v, (list, set, tuple)) and isinstance(source.get(k), type(v)):
            type_save = type(v)
            source[k] = type_save(itertools.chain(iter(source[k]), iter(v)))
        else:
            source[k] = v
    return source


def get_project_root_path():
    return os.path.dirname(os.path.abspath(ROOT_POINTER))
