import copy
import logging
import os
import sys
from multiprocessing import Process
from shutil import copyfile

import yaml
from distutils.dir_util import copy_tree

from toscatranslator.common import utils
from toscatranslator.common.utils import get_random_int


import ast

SEPARATOR = '.'


def prepare_for_run():
    successful_tasks_path = os.path.join(utils.get_tmp_clouni_dir(), 'successful_tasks.yaml')
    if os.path.isfile(successful_tasks_path):
        os.remove(successful_tasks_path)


def run_ansible(ansible_playbook, cluster_name):
    """

    :param ansible_playbook: dict which is equal to Ansible playbook in YAML
    :param cluster_name: name of cluster
    :return: empty
    """

    # this strange thing recomended for cotea for using local modules in every process
    from cotea.runner import runner
    from cotea.arguments_maker import argument_maker

    random_id = get_random_int(1000, 9999)
    os.makedirs(utils.get_tmp_clouni_dir(), exist_ok=True)
    os.makedirs(os.path.join(utils.get_tmp_clouni_dir(), cluster_name), exist_ok=True)
    tmp_current_dir = os.path.join(utils.get_tmp_clouni_dir(), cluster_name)
    playbook_path = os.path.join(tmp_current_dir, str(random_id) + '_ansible_playbook.yaml')
    successful_tasks_path = os.path.join(utils.get_tmp_clouni_dir(), 'successful_tasks.yaml')
    with open(playbook_path, 'w') as playbook_file:
        playbook_file.write(yaml.dump(ansible_playbook, default_flow_style=False, sort_keys=False))
        logging.info("Running ansible playbook from: %s" % playbook_path)

    am = argument_maker()
    am.add_arg("-i", os.path.join(tmp_current_dir, 'hosts.ini'))

    r = runner(playbook_path, am)
    results = []
    with open(successful_tasks_path, "a") as successful_tasks_file:
        while r.has_next_play():
            current_play = r.get_cur_play_name()

            while r.has_next_task():
                task_results = r.run_next_task()
                results.extend(task_results)
                succ_task = r.get_prev_task()
                for status in r.get_last_task_result():
                    if status.is_unreachable or status.is_failed:
                        continue
                if succ_task is not None and succ_task.get_ds() is not None:
                    if 'meta' not in succ_task.get_ds():
                        d = str(succ_task.get_ds())
                        successful_tasks_file.write(
                            yaml.dump([ast.literal_eval(d)], default_flow_style=False, sort_keys=False))

    r.finish_ansible()
    return results


def run_and_finish(ansible_playbook, name, op, q, cluster_name):
    results = run_ansible(ansible_playbook, cluster_name)
    if name is not None and op is not None:
        if name == 'artifacts' or op == 'artifacts':
            q.put(results)
        else:
            q.put(name + SEPARATOR + op)
    else:
        q.put('Done')


def parallel_run_ansible(ansible_playbook, name, op, q, cluster_name):
    Process(target=run_and_finish, args=(ansible_playbook, name, op, q, cluster_name)).start()