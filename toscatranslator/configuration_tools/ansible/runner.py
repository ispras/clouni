import copy
import os
import sys
from multiprocessing import Process

import yaml
from distutils.dir_util import copy_tree

from toscatranslator.common.utils import get_random_int

from cotea.runner import runner
from cotea.arguments_maker import argument_maker


from multiprocessing.connection import Client

TMP_DIR = '/tmp/clouni'


def prepare_for_run(artifacts_directory):
    os.makedirs(TMP_DIR, exist_ok=True)
    tmp_current_dir = os.path.join(TMP_DIR)
    if not os.path.isdir(TMP_DIR):
        os.makedirs(tmp_current_dir)
    if not os.path.isabs(artifacts_directory):
        tmp_artifacts_directory = os.path.join(tmp_current_dir, artifacts_directory)
        if not os.path.isdir(tmp_artifacts_directory):
            os.makedirs(tmp_artifacts_directory)
        copy_tree(artifacts_directory, tmp_artifacts_directory)


def run_ansible(ansible_playbook):
    """

    :param ansible_playbook: dict which is equal to Ansible playbook in YAML
    :return: empty
    """
    random_id = get_random_int(1000, 9999)
    os.makedirs(TMP_DIR, exist_ok=True)
    tmp_current_dir = os.path.join(TMP_DIR)
    if not os.path.isdir(TMP_DIR):
        os.makedirs(tmp_current_dir)
    playbook_path = os.path.join(tmp_current_dir, str(random_id) + '_ansible_playbook.yaml')
    with open(playbook_path, 'w') as playbook_file:
        playbook_file.write(yaml.dump(ansible_playbook, default_flow_style=False, sort_keys=False))

    am = argument_maker()
    r = runner(playbook_path, am)

    while r.has_next_play():
        current_play = r.get_cur_play_name()

        while r.has_next_task():
            next_task = r.get_next_task_name()
            r.run_next_task()

    r.finish_ansible()
    os.remove(playbook_path)


def run_and_finish(ansible_playbook, node, q):
    run_ansible(ansible_playbook)
    q.put(node.name)

def parallel_run_ansible(ansible_playbook, node, q):
    Process(target=run_and_finish, args=(ansible_playbook, node, q)).start()