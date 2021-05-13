try:
    # Python 3
    import configparser
except:
    # Python 2
    import ConfigParser

import os
from toscaparser.common.exception import ExceptionCollector
from toscatranslator.common.exception import ConfigurationNotFound

from toscatranslator.common import utils

from toscatranslator.common.configuration import Configuration, CONFIG_FILE_EXT


class ConfigurationToolConfiguration (Configuration):

    def __init__(self, tool_name):
        self.tool_name = tool_name

        cwd_config_filename = os.path.join(os.getcwd(), tool_name + CONFIG_FILE_EXT)
        root_clouni_config_filename = os.path.join(utils.get_project_root_path(),
                                                   tool_name + CONFIG_FILE_EXT)

        tools_directory = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), tool_name)
        tool_config_filename = os.path.join(tools_directory, 'configuration_tool' + CONFIG_FILE_EXT)
        tool_name_config_filename = os.path.join(tools_directory, tool_name + CONFIG_FILE_EXT)

        filename_variants_priority = [
            cwd_config_filename,
            root_clouni_config_filename,
            tool_config_filename,
            tool_name_config_filename
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

        super(ConfigurationToolConfiguration, self).__init__(self.config_filename)
