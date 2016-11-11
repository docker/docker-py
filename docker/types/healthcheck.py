from .base import DictType

import six


class Healthcheck(DictType):
    def __init__(self, **kwargs):
        test = kwargs.get('test', kwargs.get('Test'))
        if isinstance(test, six.string_types):
            test = ["CMD-SHELL", test]

        interval = kwargs.get('interval', kwargs.get('Interval'))
        timeout = kwargs.get('timeout', kwargs.get('Timeout'))
        retries = kwargs.get('retries', kwargs.get('Retries'))

        super(Healthcheck, self).__init__({
            'Test': test,
            'Interval': interval,
            'Timeout': timeout,
            'Retries': retries
        })

    @property
    def test(self):
        return self['Test']

    @test.setter
    def test(self, value):
        self['Test'] = value

    @property
    def interval(self):
        return self['Interval']

    @interval.setter
    def interval(self, value):
        self['Interval'] = value

    @property
    def timeout(self):
        return self['Timeout']

    @timeout.setter
    def timeout(self, value):
        self['Timeout'] = value

    @property
    def retries(self):
        return self['Retries']

    @retries.setter
    def retries(self, value):
        self['Retries'] = value
