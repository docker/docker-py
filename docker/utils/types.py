import six


class DictType(dict):
    def __init__(self, init):
        for k, v in six.iteritems(init):
            self[k] = v


class Ulimit(DictType):
    def __init__(self, name, soft=None, hard=None):
        if not isinstance(name, six.string_types):
            raise ValueError("Ulimit.name must be a string")
        if soft and not isinstance(soft, int):
            raise ValueError("Ulimit.soft must be an integer")
        if hard and not isinstance(hard, int):
            raise ValueError("Ulimit.hard must be an integer")
        super(Ulimit, self).__init__({
            'name': name,
            'soft': soft,
            'hard': hard
        })

    @property
    def name(self):
        return self['name']

    @property
    def soft(self):
        return self.get('soft')

    @property
    def hard(self):
        return self.get('hard')
