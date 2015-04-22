import six


class DictType(dict):
    def __init__(self, init):
        for k, v in six.iteritems(init):
            self[k] = v


class Ulimit(DictType):
    def __init__(self, **kwargs):
        name = kwargs.get('name', kwargs.get('Name'))
        soft = kwargs.get('soft', kwargs.get('Soft'))
        hard = kwargs.get('hard', kwargs.get('Hard'))
        if not isinstance(name, six.string_types):
            raise ValueError("Ulimit.name must be a string")
        if soft and not isinstance(soft, int):
            raise ValueError("Ulimit.soft must be an integer")
        if hard and not isinstance(hard, int):
            raise ValueError("Ulimit.hard must be an integer")
        super(Ulimit, self).__init__({
            'Name': name,
            'Soft': soft,
            'Hard': hard
        })

    @property
    def name(self):
        return self['Name']

    @name.setter
    def name(self, value):
        self['Name'] = value

    @property
    def soft(self):
        return self.get('Soft')

    @soft.setter
    def soft(self, value):
        self['Soft'] = value

    @property
    def hard(self):
        return self.get('Hard')

    @hard.setter
    def hard(self, value):
        self['Hard'] = value
