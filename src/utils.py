import json


def _recursive_sort(obj):
    if isinstance(obj, dict):
        return {k: _recursive_sort(v) for k, v in sorted(obj.items())}
    elif isinstance(obj, list):
        return sorted([_recursive_sort(item) for item in obj], key=str)
    return obj


def dump_json(obj, fp, **kwargs):
    json.dump(_recursive_sort(obj), fp, **kwargs)


def dumps_json(obj, **kwargs) -> str:
    return json.dumps(_recursive_sort(obj), **kwargs)
