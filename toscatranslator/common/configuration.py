try:
    # Python 3
    import configparser
except:
    # Python 2
    import ConfigParser

import os
from toscaparser.common.exception import ExceptionCollector
from toscatranslator.common.exception import ConfigurationNotFound, ConfigurationParameterError
from toscatranslator.common.tosca_reserved_keys import CLOUNI

from toscatranslator.common import utils

CONFIG_FILE_EXT = '.cfg'

SECTION_SEPARATOR = '.'
PARAMS_SEPARATOR = '\n'
PARAM_KEY_VALUE_SEPARATOR = '='
PARAM_LIST_SEPARATOR = ','


class Configuration:
    MAIN_SECTION = 'main'

    def __init__(self, file=None):
        if file is None:
            file = CLOUNI + CONFIG_FILE_EXT

        if os.path.isabs(file):
            if os.path.isfile(file):
                self.config_filename = file
            else:
                ExceptionCollector.appendException(FileNotFoundError(file))
        else:
            cwd_config_filename = os.path.join(os.getcwd(), file)
            root_clouni_config_filename = os.path.join(utils.get_project_root_path(),
                                                       'toscatranslator',
                                                       file)

            filename_variants_priority = [
                cwd_config_filename,
                root_clouni_config_filename,
            ]
            self.config_filename = None
            for filename in filename_variants_priority:
                if os.path.isfile(filename):
                    self.config_filename = filename
                    break

            if self.config_filename is None:
                ExceptionCollector.appendException(ConfigurationNotFound(
                    what=filename_variants_priority
                ))

        self.config_directory = os.path.dirname(self.config_filename)

        self.config = configparser.ConfigParser()

        self.config.read(self.config_filename)

        if not self.MAIN_SECTION in self.config.sections():
            ExceptionCollector.appendException(ConfigurationParameterError(
                what=self.MAIN_SECTION
            ))

    def parse_param(self, param):
        r = param
        param_split_key_value = param.split(PARAM_KEY_VALUE_SEPARATOR, 1)
        if len(param_split_key_value) > 1:
            r = {
                param_split_key_value[0].strip(): self.parse_param(param_split_key_value[1].strip())
            }
            return r
        param_split_list = param.split(PARAM_LIST_SEPARATOR)
        if len(param_split_list) > 1:
            r = param_split_list
            return r
        return r

    def get_section(self, sec):
        r_sec_config = None
        if sec in self.config.sections():
            r_sec_config = dict(self.config[sec])
            for k, v in r_sec_config.items():
                sec_config_raw = v.strip().split(PARAMS_SEPARATOR)
                if len(sec_config_raw) > 1:
                    r_sec_config[k] = {}
                    for i in range(len(sec_config_raw)):
                        r_sec_config[k].update(self.parse_param(sec_config_raw[i].strip()))
                else:
                    r_sec_config[k] = self.parse_param(v.strip())
        return r_sec_config

    def get_subsection(self, sec, sub):
        full_sec = SECTION_SEPARATOR.join([sec, sub])
        return self.get_section(full_sec)
