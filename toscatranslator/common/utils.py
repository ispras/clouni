import itertools
import os
import importlib
import sys
import logging

import six
import yaml

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

def get_tmp_clouni_dir():
    return '/tmp/clouni'


def get_random_int(start, end):
    seed(time())
    r = randint(start, end)
    return r


def generate_artifacts(configuration_class, new_artifacts, directory, store=True):
    """
    From the info of new artifacts generate files which execute
    :param new_artifacts: list of dicts containing (value, source, parameters, executor, name, configuration_tool)
    :return: None
    """
    if not configuration_class:
        logging.error('Failed to generate artifact with configuration class <None>')
        sys.exit(1)
    r_artifacts = []
    tasks = []
    filename = os.path.join(directory, '_'.join(['tasks', str(get_random_int(1000, 9999))]) + configuration_class.get_artifact_extension())
    for art in new_artifacts:
        # filename = os.path.join(directory, art['name'])
        tasks.extend(configuration_class.create_artifact_data(art))
        # r_artifacts.append(filename)
    if not os.path.isdir(directory):
        os.makedirs(directory)

    with open(filename, "w") as f:
        filedata = yaml.dump(tasks, default_flow_style=False, sort_keys=False)
        f.write(filedata)
        logging.info("Artifact for executor %s was created: %s" % (configuration_class.TOOL_NAME, filename))

    # return r_artifacts
    return tasks, filename

def replace_brackets(data, with_splash=True):
    if isinstance(data, six.string_types):
        if with_splash:
            return data.replace("{", "\{").replace("}", "\}")
        else:
            return data.replace("\\\\{", "{").replace("\\{", "{").replace("\{", "{") \
                .replace("\\\\}", "}").replace("\\}", "}").replace("\}", "}")
    if isinstance(data, dict):
        r = {}
        for k, v in data.items():
            r[replace_brackets(k)] = replace_brackets(v, with_splash)
        return r
    if isinstance(data, list):
        r = []
        for i in data:
            r.append(replace_brackets(i, with_splash))
        return r
    return data