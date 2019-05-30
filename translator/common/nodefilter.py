class ProviderNodeFilter(object):

    CAPABILITY_NAME = 'self'
    """
    facts attribute: Class has additional attribute filled in translator.providers.common.translator_to_ansible translate()
    """
    def __init__(self):
        assert self.FACTS_KEY is not None
        # assert self.NAME is not None

        self.facts = self.facts[self.FACTS_KEY]
        # Make dictionary plain
        for i in range(0, len(self.facts)):
            self.facts[i] = dict((str(k), str(v)) for k, v in self.facts[i].items())

    def filter_params(self, params):
        matched_objs = self.get_facts()
        for param, filter_value in params.items():
            filter_str = str(filter_value)
            matched_objs = (obj for obj in matched_objs if filter_str == obj.get(param))

        first_matched = next(iter(matched_objs), {})
        return first_matched

    def filter_node(self, req):
        filter_params = req.data.get('capabilities', {}).get(self.CAPABILITY_NAME, {}).get('properties', {})
        return self.filter_params(filter_params)

    def get_name_or_id(self, req):
        first_matched = self.filter_node(req)
        req.id = first_matched.get('id')
        req.name = first_matched.get('name')
        return req.id, req.name

    def get_name(self, req):
        first_matched = self.filter_node(req)
        return first_matched.get('name')

    def get_facts(self):
        return self.facts

