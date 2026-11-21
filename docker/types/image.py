from .base import DictType


class Platform(DictType):
    def __init__(self, **kwargs):
        architecture = kwargs.get('architecture')
        os = kwargs.get('os')

        if architecture is None or os is None:
            raise ValueError("Both 'architecture' and 'os' must be provided")

        super().__init__({
            'architecture': architecture,
            'os': os,
            'os_version': kwargs.get('os_version'),
            'os_features': kwargs.get('os_features'),
            'variant': kwargs.get('variant')
        })

    @property
    def architecture(self):
        return self['architecture']

    @property
    def os(self):
        return self['os']

    @architecture.setter
    def architecture(self, value):
        self['architecture'] = value

    @os.setter
    def os(self, value):
        self['os'] = value
