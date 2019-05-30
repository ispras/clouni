from translator.common.tosca_node_for_translate import ToscaNodeForTranslate


class ToscaComputeNode(ToscaNodeForTranslate):
    def __init__(self, name, template, facts):
        super(ToscaComputeNode, self).__init__(name, template, facts)


    def amazon_elements(self):
        return self.node_templates