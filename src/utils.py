import json


def sort_lists(obj):
    if isinstance(obj, dict):
        return {k: sort_lists(v) for k, v in sorted(obj.items())}
    elif isinstance(obj, list):
        return sorted(obj, key=lambda x: (isinstance(x, dict), str(x)))
    return obj


def dump_json(obj, fp, **kwargs):
    json.dump(sort_lists(obj), fp, **kwargs)


def dumps_json(obj, **kwargs) -> str:
    return json.dumps(sort_lists(obj), **kwargs)
