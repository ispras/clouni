def deep_update_dict(source, overrides):
    for k, v in overrides.items():
        if isinstance(v, dict):
            source[k] = deep_update_dict(source.get(k, {}), v)
        else:
            source[k] = v
    return source
