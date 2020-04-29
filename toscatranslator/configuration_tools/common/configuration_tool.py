
class ConfigurationTool(object):

    def to_dsl_for_create(self, provider, nodes_queue):
        raise NotImplementedError()

    def create_artifact(self, filename, data):
        raise NotImplementedError()
