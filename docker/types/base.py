import six


class DictType(dict):
    def __init__(self, init):
        for k, v in six.iteritems(init):
            self[k] = v
