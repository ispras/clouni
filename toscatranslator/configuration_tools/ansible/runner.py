import os
import yaml
from distutils.dir_util import copy_tree

from toscatranslator.common.utils import get_random_int

from cotea.runner import runner
from cotea.arguments_maker import argument_maker

TMP_DIR = '/tmp/clouni'


def run_ansible(ansible_playbook, artifacts_directory):
    """

    :param ansible_playbook: dict which is equal to Ansible playbook in YAML
    :return: empty
    """
    random_id = get_random_int(1000, 9999)
    os.makedirs(TMP_DIR, exist_ok=True)
    tmp_current_dir = os.path.join(TMP_DIR, str(random_id))
    os.makedirs(tmp_current_dir)
    playbook_path = os.path.join(tmp_current_dir, 'ansible_playbook.yaml')
    with open(playbook_path, 'w') as playbook_file:
        playbook_file.write(yaml.dump(ansible_playbook, default_flow_style=False, sort_keys=False))

    if not os.path.isabs(artifacts_directory):
        tmp_artifacts_directory = os.path.join(tmp_current_dir, artifacts_directory)
        os.makedirs(tmp_artifacts_directory)
        copy_tree(artifacts_directory, tmp_artifacts_directory)

    am = argument_maker()

    r = runner(playbook_path, am)

    results = []
    while r.has_next_play():
        current_play = r.get_cur_play_name()
        # print("PLAY:", current_play)

        while r.has_next_task():
            next_task = r.get_next_task_name()
            # print("\tTASK:", next_task)

            task_results = r.run_next_task()
            results.extend(task_results)

    r.finish_ansible()
    return results
