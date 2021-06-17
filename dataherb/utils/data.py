def flatten_dict(nested_dict, sep=None):
    """
    flatten_dict flattens a dictionary,

    The flattened keys are joined using a separater which is default to '__'.

    :param nested_dict: input nested dictionary to be flattened.
    :type nested_dict: dict
    :param sep: seperator for the joined keys, defaults to __
    :type sep: str, optional
    :return: flattened dictionar
    :rtype: dict
    """
    if sep is None:
        sep = "__"
    res = {}

    def flatten(x, name=""):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + sep)
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + sep)
                i += 1
        else:
            res[name[:-2]] = x

    flatten(nested_dict)

    return res
