import six


class LogConfigTypesEnum(object):
    _values = (
        'json-file',
        'syslog',
        'none'
    )
    JSON, SYSLOG, NONE = _values


class DictType(dict):
    def __init__(self, init):
        for k, v in six.iteritems(init):
            self[k] = v


class LogConfig(DictType):
    types = LogConfigTypesEnum

    def __init__(self, **kwargs):
        type_ = kwargs.get('type', kwargs.get('Type'))
        config = kwargs.get('config', kwargs.get('Config'))
        if type_ not in self.types._values:
            raise ValueError("LogConfig.type must be one of ({0})".format(
                ', '.join(self.types._values)
            ))
        if config and not isinstance(config, dict):
            raise ValueError("LogConfig.config must be a dictionary")

        super(LogConfig, self).__init__({
            'Type': type_,
            'Config': config or {}
        })

    @property
    def type(self):
        return self['Type']

    @type.setter
    def type(self, value):
        if value not in self.types._values:
            raise ValueError("LogConfig.type must be one of {0}".format(
                ', '.join(self.types._values)
            ))
        self['Type'] = value

    @property
    def config(self):
        return self['Config']

    def set_config_value(self, key, value):
        self.config[key] = value

    def unset_config(self, key):
        if key in self.config:
            del self.config[key]


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
