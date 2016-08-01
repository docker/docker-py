import six


class LogConfigTypesEnum(object):
    _values = (
        'json-file',
        'syslog',
        'journald',
        'gelf',
        'fluentd',
        'none'
    )
    JSON, SYSLOG, JOURNALD, GELF, FLUENTD, NONE = _values


class DictType(dict):
    def __init__(self, init):
        for k, v in six.iteritems(init):
            self[k] = v


class LogConfig(DictType):
    types = LogConfigTypesEnum

    def __init__(self, **kwargs):
        log_driver_type = kwargs.get('type', kwargs.get('Type'))
        config = kwargs.get('config', kwargs.get('Config')) or {}

        if config and not isinstance(config, dict):
            raise ValueError("LogConfig.config must be a dictionary")

        super(LogConfig, self).__init__({
            'Type': log_driver_type,
            'Config': config
        })

    @property
    def type(self):
        return self['Type']

    @type.setter
    def type(self, value):
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


class SwarmSpec(DictType):
    def __init__(self, policies=None, task_history_retention_limit=None,
                 snapshot_interval=None, keep_old_snapshots=None,
                 log_entries_for_slow_followers=None, heartbeat_tick=None,
                 election_tick=None, dispatcher_heartbeat_period=None,
                 node_cert_expiry=None, external_ca=None):
        if policies is not None:
            self['AcceptancePolicy'] = {'Policies': policies}
        if task_history_retention_limit is not None:
            self['Orchestration'] = {
                'TaskHistoryRetentionLimit': task_history_retention_limit
            }
        if any(snapshot_interval, keep_old_snapshots,
               log_entries_for_slow_followers, heartbeat_tick, election_tick):
            self['Raft'] = {
                'SnapshotInterval': snapshot_interval,
                'KeepOldSnapshots': keep_old_snapshots,
                'LogEntriesForSlowFollowers': log_entries_for_slow_followers,
                'HeartbeatTick': heartbeat_tick,
                'ElectionTick': election_tick
            }

        if dispatcher_heartbeat_period:
            self['Dispatcher'] = {
                'HeartbeatPeriod': dispatcher_heartbeat_period
            }

        if node_cert_expiry or external_ca:
            self['CAConfig'] = {
                'NodeCertExpiry': node_cert_expiry,
                'ExternalCA': external_ca
            }


class SwarmAcceptancePolicy(DictType):
    def __init__(self, role, auto_accept=False, secret=None):
        self['Role'] = role.upper()
        self['Autoaccept'] = auto_accept
        if secret is not None:
            self['Secret'] = secret


class SwarmExternalCA(DictType):
    def __init__(self, url, protocol=None, options=None):
        self['URL'] = url
        self['Protocol'] = protocol
        self['Options'] = options
