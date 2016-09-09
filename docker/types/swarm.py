class SwarmSpec(dict):
    def __init__(self, task_history_retention_limit=None,
                 snapshot_interval=None, keep_old_snapshots=None,
                 log_entries_for_slow_followers=None, heartbeat_tick=None,
                 election_tick=None, dispatcher_heartbeat_period=None,
                 node_cert_expiry=None, external_ca=None, name=None):
        if task_history_retention_limit is not None:
            self['Orchestration'] = {
                'TaskHistoryRetentionLimit': task_history_retention_limit
            }
        if any([snapshot_interval, keep_old_snapshots,
               log_entries_for_slow_followers, heartbeat_tick, election_tick]):
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

        if name is not None:
            self['Name'] = name


class SwarmExternalCA(dict):
    def __init__(self, url, protocol=None, options=None):
        self['URL'] = url
        self['Protocol'] = protocol
        self['Options'] = options
