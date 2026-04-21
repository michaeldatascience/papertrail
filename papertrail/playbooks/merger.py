from typing import Any, Dict

def deep_merge(base_dict: Dict[str, Any], override_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merges two dictionaries. Override dict values take precedence.
    
    - Objects: recursively merged. Child wins on conflicts.
    - Arrays: child fully replaces parent (no concat).
    - Primitives: child wins.
    - None in override: removes the key from the base.
    """
    merged = base_dict.copy()

    for key, value in override_dict.items():
        if value is None:
            # Explicitly remove key if override value is None
            if key in merged:
                del merged[key]
        elif isinstance(value, dict) and isinstance(merged.get(key), dict):
            # Recursive merge for dictionaries
            merged[key] = deep_merge(merged[key], value)
        elif isinstance(value, list):
            # Child list fully replaces parent list
            merged[key] = value
        else:
            # Primitives and other types: child value takes precedence
            merged[key] = value
            
    return merged
