def flatten_dict(d, parent_key='', sep='.'):
  items = {}
  for k, v in d.items():
    new_key = f"{parent_key}{sep}{k}" if parent_key else k
    if isinstance(v, dict):
      items.update(flatten_dict(v, new_key, sep=sep))
    elif isinstance(v, list):
      for i, item in enumerate(v):
        if isinstance(item, dict):
          items.update(flatten_dict(item, f"{new_key}[{i}]", sep=sep))
        else:
          items[f"{new_key}[{i}]"] = '' if item is None else item
    else:
      items[new_key] = '' if v is None else v
  return items
