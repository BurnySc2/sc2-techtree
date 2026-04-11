import json


def _recursive_sort(obj):
    if isinstance(obj, dict):
        return {k: _recursive_sort(v) for k, v in sorted(obj.items())}
    elif isinstance(obj, list):
        items = [_recursive_sort(item) for item in obj]
        if items and all(isinstance(item, str) for item in items):
            items = list(dict.fromkeys(items))
        return sorted(items, key=str)
    return obj


def dump_json(obj, fp, **kwargs):
    json.dump(_recursive_sort(obj), fp, **kwargs)


def dumps_json(obj, **kwargs) -> str:
    return json.dumps(_recursive_sort(obj), **kwargs)
