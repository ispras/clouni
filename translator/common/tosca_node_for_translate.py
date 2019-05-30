class ToscaNodeForTranslate(object):
    def __init__(self, name, template, facts):
        # Available schema for template
        self.template = dict(template)
        self.name = str(name)
        self.facts = dict(facts)
