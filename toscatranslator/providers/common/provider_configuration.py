try:
    # Python 3
    import configparser
except:
    # Python 2
    import ConfigParser

from toscatranslator.common import utils

from toscatranslator.common.configuration import Configuration, CONFIG_FILE_EXT

import logging, sys, json, os


class ProviderConfiguration (Configuration):

    def __init__(self, provider):
        self.provider = provider

        cwd_config_filename = os.path.join(os.getcwd(), provider + CONFIG_FILE_EXT)
        root_clouni_config_filename = os.path.join(utils.get_project_root_path(),
                                                   provider + CONFIG_FILE_EXT)

        providers_directory = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                                           provider)
        provider_config_filename = os.path.join(providers_directory, 'provider' + CONFIG_FILE_EXT)
        provider_name_config_filename = os.path.join(providers_directory, provider + CONFIG_FILE_EXT)

        filename_variants_priority = [
            cwd_config_filename,
            root_clouni_config_filename,
            provider_config_filename,
            provider_name_config_filename
        ]
        self.config_filename = None
        for filename in filename_variants_priority:
            if os.path.isfile(filename):
                self.config_filename = filename
                break
        if self.config_filename is None:
            logging.error("Configuration files were missing in possible locations: %s" % json.dumps(filename_variants_priority))
            sys.exit(1)

        super(ProviderConfiguration, self).__init__(self.config_filename)
