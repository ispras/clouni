import itertools
import os

ROOT_POINTER = 'clouni_root_pointer'


def deep_update_dict(source, overrides):
    assert isinstance(source, dict)

    for k, v in overrides.items():
        if isinstance(v, dict):
            source[k] = deep_update_dict(source.get(k, {}), v)
        elif isinstance(v, (list, set, tuple)) and isinstance(source.get(k), type(v)):
            type_save = type(v)
            source[k] = type_save(itertools.chain(iter(source[k]), iter(v)))
            # source[k] += v
        else:
            source[k] = v
    return source


def get_project_root_path():
    return os.path.dirname(os.path.abspath(ROOT_POINTER))
