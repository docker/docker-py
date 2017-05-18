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
        start_period = kwargs.get('start_period', kwargs.get('StartPeriod'))

        super(Healthcheck, self).__init__({
            'Test': test,
            'Interval': interval,
            'Timeout': timeout,
            'Retries': retries,
            'StartPeriod': start_period
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

    @property
    def start_period(self):
        return self['StartPeriod']

    @start_period.setter
    def start_period(self, value):
        self['StartPeriod'] = value
