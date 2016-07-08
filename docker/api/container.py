import six
import warnings
from datetime import datetime

from .. import errors
from .. import utils
from ..utils.utils import create_networking_config, create_endpoint_config


class ContainerApiMixin(object):
    @utils.check_resource
    def attach(self, container, stdout=True, stderr=True,
               stream=False, logs=False):
        params = {
            'logs': logs and 1 or 0,
            'stdout': stdout and 1 or 0,
            'stderr': stderr and 1 or 0,
            'stream': stream and 1 or 0
        }

        headers = {
            'Connection': 'Upgrade',
            'Upgrade': 'tcp'
        }

        u = self._url("/containers/{0}/attach", container)
        response = self._post(u, headers=headers, params=params, stream=stream)

        return self._read_from_socket(response, stream)

    @utils.check_resource
    def attach_socket(self, container, params=None, ws=False):
        if params is None:
            params = {
                'stdout': 1,
                'stderr': 1,
                'stream': 1
            }

        if ws:
            return self._attach_websocket(container, params)

        headers = {
            'Connection': 'Upgrade',
            'Upgrade': 'tcp'
        }

        u = self._url("/containers/{0}/attach", container)
        return self._get_raw_response_socket(
            self.post(
                u, None, params=self._attach_params(params), stream=True,
                headers=headers
            )
        )

    @utils.check_resource
    def commit(self, container, repository=None, tag=None, message=None,
               author=None, changes=None, conf=None):
        params = {
            'container': container,
            'repo': repository,
            'tag': tag,
            'comment': message,
            'author': author,
            'changes': changes
        }
        u = self._url("/commit")
        return self._result(self._post_json(u, data=conf, params=params),
                            json=True)

    def containers(self, quiet=False, all=False, trunc=False, latest=False,
                   since=None, before=None, limit=-1, size=False,
                   filters=None):
        params = {
            'limit': 1 if latest else limit,
            'all': 1 if all else 0,
            'size': 1 if size else 0,
            'trunc_cmd': 1 if trunc else 0,
            'since': since,
            'before': before
        }
        if filters:
            params['filters'] = utils.convert_filters(filters)
        u = self._url("/containers/json")
        res = self._result(self._get(u, params=params), True)

        if quiet:
            return [{'Id': x['Id']} for x in res]
        if trunc:
            for x in res:
                x['Id'] = x['Id'][:12]
        return res

    @utils.check_resource
    def copy(self, container, resource):
        if utils.version_gte(self._version, '1.20'):
            warnings.warn(
                'Client.copy() is deprecated for API version >= 1.20, '
                'please use get_archive() instead',
                DeprecationWarning
            )
        res = self._post_json(
            self._url("/containers/{0}/copy".format(container)),
            data={"Resource": resource},
            stream=True
        )
        self._raise_for_status(res)
        return res.raw

    def create_container(self, image, command=None, hostname=None, user=None,
                         detach=False, stdin_open=False, tty=False,
                         mem_limit=None, ports=None, environment=None,
                         dns=None, volumes=None, volumes_from=None,
                         network_disabled=False, name=None, entrypoint=None,
                         cpu_shares=None, working_dir=None, domainname=None,
                         memswap_limit=None, cpuset=None, host_config=None,
                         mac_address=None, labels=None, volume_driver=None,
                         stop_signal=None, networking_config=None):

        if isinstance(volumes, six.string_types):
            volumes = [volumes, ]

        if host_config and utils.compare_version('1.15', self._version) < 0:
            raise errors.InvalidVersion(
                'host_config is not supported in API < 1.15'
            )

        config = self.create_container_config(
            image, command, hostname, user, detach, stdin_open,
            tty, mem_limit, ports, environment, dns, volumes, volumes_from,
            network_disabled, entrypoint, cpu_shares, working_dir, domainname,
            memswap_limit, cpuset, host_config, mac_address, labels,
            volume_driver, stop_signal, networking_config,
        )
        return self.create_container_from_config(config, name)

    def create_container_config(self, *args, **kwargs):
        return utils.create_container_config(self._version, *args, **kwargs)

    def create_container_from_config(self, config, name=None):
        u = self._url("/containers/create")
        params = {
            'name': name
        }
        res = self._post_json(u, data=config, params=params)
        return self._result(res, True)

    def create_host_config(self, *args, **kwargs):
        if not kwargs:
            kwargs = {}
        if 'version' in kwargs:
            raise TypeError(
                "create_host_config() got an unexpected "
                "keyword argument 'version'"
            )
        kwargs['version'] = self._version
        return utils.create_host_config(*args, **kwargs)

    def create_networking_config(self, *args, **kwargs):
        return create_networking_config(*args, **kwargs)

    def create_endpoint_config(self, *args, **kwargs):
        return create_endpoint_config(self._version, *args, **kwargs)

    @utils.check_resource
    def diff(self, container):
        return self._result(
            self._get(self._url("/containers/{0}/changes", container)), True
        )

    @utils.check_resource
    def export(self, container):
        res = self._get(
            self._url("/containers/{0}/export", container), stream=True
        )
        self._raise_for_status(res)
        return res.raw

    @utils.check_resource
    @utils.minimum_version('1.20')
    def get_archive(self, container, path):
        params = {
            'path': path
        }
        url = self._url('/containers/{0}/archive', container)
        res = self._get(url, params=params, stream=True)
        self._raise_for_status(res)
        encoded_stat = res.headers.get('x-docker-container-path-stat')
        return (
            res.raw,
            utils.decode_json_header(encoded_stat) if encoded_stat else None
        )

    @utils.check_resource
    def inspect_container(self, container):
        return self._result(
            self._get(self._url("/containers/{0}/json", container)), True
        )

    @utils.check_resource
    def kill(self, container, signal=None):
        url = self._url("/containers/{0}/kill", container)
        params = {}
        if signal is not None:
            if not isinstance(signal, six.string_types):
                signal = int(signal)
            params['signal'] = signal
        res = self._post(url, params=params)

        self._raise_for_status(res)

    @utils.check_resource
    def logs(self, container, stdout=True, stderr=True, stream=False,
             timestamps=False, tail='all', since=None, follow=None):
        if utils.compare_version('1.11', self._version) >= 0:
            if follow is None:
                follow = stream
            params = {'stderr': stderr and 1 or 0,
                      'stdout': stdout and 1 or 0,
                      'timestamps': timestamps and 1 or 0,
                      'follow': follow and 1 or 0,
                      }
            if utils.compare_version('1.13', self._version) >= 0:
                if tail != 'all' and (not isinstance(tail, int) or tail < 0):
                    tail = 'all'
                params['tail'] = tail

            if since is not None:
                if utils.compare_version('1.19', self._version) < 0:
                    raise errors.InvalidVersion(
                        'since is not supported in API < 1.19'
                    )
                else:
                    if isinstance(since, datetime):
                        params['since'] = utils.datetime_to_timestamp(since)
                    elif (isinstance(since, int) and since > 0):
                        params['since'] = since
            url = self._url("/containers/{0}/logs", container)
            res = self._get(url, params=params, stream=stream)
            return self._get_result(container, stream, res)
        return self.attach(
            container,
            stdout=stdout,
            stderr=stderr,
            stream=stream,
            logs=True
        )

    @utils.check_resource
    def pause(self, container):
        url = self._url('/containers/{0}/pause', container)
        res = self._post(url)
        self._raise_for_status(res)

    @utils.check_resource
    def port(self, container, private_port):
        res = self._get(self._url("/containers/{0}/json", container))
        self._raise_for_status(res)
        json_ = res.json()
        private_port = str(private_port)
        h_ports = None

        # Port settings is None when the container is running with
        # network_mode=host.
        port_settings = json_.get('NetworkSettings', {}).get('Ports')
        if port_settings is None:
            return None

        if '/' in private_port:
            return port_settings.get(private_port)

        h_ports = port_settings.get(private_port + '/tcp')
        if h_ports is None:
            h_ports = port_settings.get(private_port + '/udp')

        return h_ports

    @utils.check_resource
    @utils.minimum_version('1.20')
    def put_archive(self, container, path, data):
        params = {'path': path}
        url = self._url('/containers/{0}/archive', container)
        res = self._put(url, params=params, data=data)
        self._raise_for_status(res)
        return res.status_code == 200

    @utils.check_resource
    def remove_container(self, container, v=False, link=False, force=False):
        params = {'v': v, 'link': link, 'force': force}
        res = self._delete(
            self._url("/containers/{0}", container), params=params
        )
        self._raise_for_status(res)

    @utils.minimum_version('1.17')
    @utils.check_resource
    def rename(self, container, name):
        url = self._url("/containers/{0}/rename", container)
        params = {'name': name}
        res = self._post(url, params=params)
        self._raise_for_status(res)

    @utils.check_resource
    def resize(self, container, height, width):
        params = {'h': height, 'w': width}
        url = self._url("/containers/{0}/resize", container)
        res = self._post(url, params=params)
        self._raise_for_status(res)

    @utils.check_resource
    def restart(self, container, timeout=10):
        params = {'t': timeout}
        url = self._url("/containers/{0}/restart", container)
        res = self._post(url, params=params)
        self._raise_for_status(res)

    @utils.check_resource
    def start(self, container, binds=None, port_bindings=None, lxc_conf=None,
              publish_all_ports=None, links=None, privileged=None,
              dns=None, dns_search=None, volumes_from=None, network_mode=None,
              restart_policy=None, cap_add=None, cap_drop=None, devices=None,
              extra_hosts=None, read_only=None, pid_mode=None, ipc_mode=None,
              security_opt=None, ulimits=None):

        if utils.compare_version('1.10', self._version) < 0:
            if dns is not None:
                raise errors.InvalidVersion(
                    'dns is only supported for API version >= 1.10'
                )
            if volumes_from is not None:
                raise errors.InvalidVersion(
                    'volumes_from is only supported for API version >= 1.10'
                )

        if utils.compare_version('1.15', self._version) < 0:
            if security_opt is not None:
                raise errors.InvalidVersion(
                    'security_opt is only supported for API version >= 1.15'
                )
            if ipc_mode:
                raise errors.InvalidVersion(
                    'ipc_mode is only supported for API version >= 1.15'
                )

        if utils.compare_version('1.17', self._version) < 0:
            if read_only is not None:
                raise errors.InvalidVersion(
                    'read_only is only supported for API version >= 1.17'
                )
            if pid_mode is not None:
                raise errors.InvalidVersion(
                    'pid_mode is only supported for API version >= 1.17'
                )

        if utils.compare_version('1.18', self._version) < 0:
            if ulimits is not None:
                raise errors.InvalidVersion(
                    'ulimits is only supported for API version >= 1.18'
                )

        start_config_kwargs = dict(
            binds=binds, port_bindings=port_bindings, lxc_conf=lxc_conf,
            publish_all_ports=publish_all_ports, links=links, dns=dns,
            privileged=privileged, dns_search=dns_search, cap_add=cap_add,
            cap_drop=cap_drop, volumes_from=volumes_from, devices=devices,
            network_mode=network_mode, restart_policy=restart_policy,
            extra_hosts=extra_hosts, read_only=read_only, pid_mode=pid_mode,
            ipc_mode=ipc_mode, security_opt=security_opt, ulimits=ulimits
        )
        start_config = None

        if any(v is not None for v in start_config_kwargs.values()):
            if utils.compare_version('1.15', self._version) > 0:
                warnings.warn(
                    'Passing host config parameters in start() is deprecated. '
                    'Please use host_config in create_container instead!',
                    DeprecationWarning
                )
            start_config = self.create_host_config(**start_config_kwargs)

        url = self._url("/containers/{0}/start", container)
        res = self._post_json(url, data=start_config)
        self._raise_for_status(res)

    @utils.minimum_version('1.17')
    @utils.check_resource
    def stats(self, container, decode=None, stream=True):
        url = self._url("/containers/{0}/stats", container)
        if stream:
            return self._stream_helper(self._get(url, stream=True),
                                       decode=decode)
        else:
            return self._result(self._get(url, params={'stream': False}),
                                json=True)

    @utils.check_resource
    def stop(self, container, timeout=10):
        params = {'t': timeout}
        url = self._url("/containers/{0}/stop", container)

        res = self._post(url, params=params,
                         timeout=(timeout + (self.timeout or 0)))
        self._raise_for_status(res)

    @utils.check_resource
    def top(self, container, ps_args=None):
        u = self._url("/containers/{0}/top", container)
        params = {}
        if ps_args is not None:
            params['ps_args'] = ps_args
        return self._result(self._get(u, params=params), True)

    @utils.check_resource
    def unpause(self, container):
        url = self._url('/containers/{0}/unpause', container)
        res = self._post(url)
        self._raise_for_status(res)

    @utils.minimum_version('1.22')
    @utils.check_resource
    def update_container(
        self, container, blkio_weight=None, cpu_period=None, cpu_quota=None,
        cpu_shares=None, cpuset_cpus=None, cpuset_mems=None, mem_limit=None,
        mem_reservation=None, memswap_limit=None, kernel_memory=None
    ):
        url = self._url('/containers/{0}/update', container)
        data = {}
        if blkio_weight:
            data['BlkioWeight'] = blkio_weight
        if cpu_period:
            data['CpuPeriod'] = cpu_period
        if cpu_shares:
            data['CpuShares'] = cpu_shares
        if cpu_quota:
            data['CpuQuota'] = cpu_quota
        if cpuset_cpus:
            data['CpusetCpus'] = cpuset_cpus
        if cpuset_mems:
            data['CpusetMems'] = cpuset_mems
        if mem_limit:
            data['Memory'] = utils.parse_bytes(mem_limit)
        if mem_reservation:
            data['MemoryReservation'] = utils.parse_bytes(mem_reservation)
        if memswap_limit:
            data['MemorySwap'] = utils.parse_bytes(memswap_limit)
        if kernel_memory:
            data['KernelMemory'] = utils.parse_bytes(kernel_memory)

        res = self._post_json(url, data=data)
        return self._result(res, True)

    @utils.check_resource
    def wait(self, container, timeout=None):
        url = self._url("/containers/{0}/wait", container)
        res = self._post(url, timeout=timeout)
        self._raise_for_status(res)
        json_ = res.json()
        if 'StatusCode' in json_:
            return json_['StatusCode']
        return -1
