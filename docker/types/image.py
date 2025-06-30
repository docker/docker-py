from .base import DictType


class Platform(DictType):
    def __init__(self, **kwargs):
        architecture = kwargs.get('architecture', kwargs.get('Architecture'))
        os = kwargs.get('os', kwargs.get('OS'))

        if architecture is None and os is None:
            raise ValueError("At least one of 'architecture' or 'os' must be provided")


        super().__init__({
            'Architecture': architecture,
            'OS': os,
            'OSVersion': kwargs.get('os_version', kwargs.get('OSVersion')),
            'OSFeatures': kwargs.get('os_features', kwargs.get('OSFeatures')),
            'Variant': kwargs.get('variant', kwargs.get('Variant'))
        })

    @property
    def architecture(self):
        return self['Architecture']

    @property
    def os(self):
        return self['OS']

    @architecture.setter
    def architecture(self, value):
        self['Architecture'] = value

    @os.setter
    def os(self, value):
        self['OS'] = value
