def pluck(items, fields):
    """Return a list of dictionaries with a subset of keys

    Parameters
    ----------
    items : list of dicts
    fields : list-like of strs

    Returns
    -------
    list of dicts
    """
    out = []
    for item in items:
        out.append({k: v for k, v in item.items() if k in fields})

    return out


def subset_dict(d, fields):
    """Return dictionary with a subset of keys

    Parameters
    ----------
    d : dict
    fields : list-like of strs
    """

    return {k: v for k, v in d.items() if k in (fields)}
