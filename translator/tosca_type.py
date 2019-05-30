def parse(_type):
    tosca_type = _type.split(".", 2)
    namespace = tosca_type[0]
    category = tosca_type[1]
    type_name = tosca_type[2]
    return namespace, category, type_name
