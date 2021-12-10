import itertools
import os
import importlib

from random import randint,seed
from time import time


def tosca_type_parse(_type):
    tosca_type = _type.split(".", 2)
    if len(tosca_type) == 3:
        tosca_type_iter = iter(tosca_type)
        namespace = next(tosca_type_iter)
        category = next(tosca_type_iter)
        type_name = next(tosca_type_iter)
        return namespace, category, type_name
    return None, None, None


def snake_case(name):
    import re

    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def execute_function(module_name, function_name, params):
    m = importlib.import_module(module_name)
    if hasattr(m, function_name):
        function_name = getattr(m, function_name)
        return function_name(**params)
    else:
        try:
            for p, _ in params.items():
                exec(p + ' = params[\''+ p + '\']')
            r = eval(function_name)
            return r
        except:
            return


def deep_update_dict(source, overrides):
    assert isinstance(source, dict)
    assert isinstance(overrides, dict)

    for k, v in overrides.items():
        if isinstance(v, dict) and isinstance(source.get(k), dict):
            source[k] = deep_update_dict(source.get(k, {}), v)
        elif isinstance(v, (list, set, tuple)) and isinstance(source.get(k), type(v)):
            type_save = type(v)
            source[k] = type_save(itertools.chain(iter(source[k]), iter(v)))
        else:
            source[k] = v
    return source


def get_project_root_path():
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def get_random_int(start, end):
    seed(time())
    r = randint(start, end)
    return r
