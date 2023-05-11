Changelog
==========

6.1.2
-----

#### Bugfixes
- Fix for socket timeouts on long `docker exec` calls 

6.1.1
-----

#### Bugfixes
- Fix `containers.stats()` hanging with `stream=True`
- Correct return type in docs for `containers.diff()` method


6.1.0
-----

### Upgrade Notes
- Errors are no longer returned during client initialization if the credential helper cannot be found. A warning will be emitted instead, and an error is returned if the credential helper is used.

### Features
- Python 3.11 support
- Use `poll()` instead of `select()` on non-Windows platforms
- New API fields
  - `network_driver_opt` on container run / create
  - `one-shot` on container stats
  - `status` on services list

### Bugfixes
- Support for requests 2.29.0+ and urllib3 2.x
- Do not strip characters from volume names
- Fix connection leak on container.exec_* operations
- Fix errors closing named pipes on Windows

6.0.1
-----

### Bugfixes
- Fix for `The pipe has been ended errors` on Windows
- Support floats for container log filtering by timestamp (`since` / `until`)

6.0.0
-----

### Upgrade Notes
- Minimum supported Python version is 3.7+
- When installing with pip, the `docker[tls]` extra is deprecated and a no-op,
  use `docker` for same functionality (TLS support is always available now)
- Native Python SSH client (used by default / `use_ssh_client=False`) will now
  reject unknown host keys with `paramiko.ssh_exception.SSHException`
- Short IDs are now 12 characters instead of 10 characters (same as Docker CLI)

### Features
- Python 3.10 support
- Automatically negotiate most secure TLS version
- Add `platform` (e.g. `linux/amd64`, `darwin/arm64`) to container create & run
- Add support for `GlobalJob` and `ReplicatedJobs` for Swarm
- Add `remove()` method on `Image`
- Add `force` param to `disable()` on `Plugin`

### Bugfixes
- Fix install issues on Windows related to `pywin32`
- Do not accept unknown SSH host keys in native Python SSH mode
- Use 12 character short IDs for consistency with Docker CLI
- Ignore trailing whitespace in `.dockerignore` files
- Fix IPv6 host parsing when explicit port specified
- Fix `ProxyCommand` option for SSH connections
- Do not spawn extra subshell when launching external SSH client
- Improve exception semantics to preserve context
- Documentation improvements (formatting, examples, typos, missing params)

### Miscellaneous
- Upgrade dependencies in `requirements.txt` to latest versions
- Remove extraneous transitive dependencies
- Eliminate usages of deprecated functions/methods
- Test suite reliability improvements
- GitHub Actions workflows for linting, unit tests, integration tests, and
  publishing releases

5.0.3
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/76?closed=1)

### Features
- Add `cap_add` and `cap_drop` parameters to service create and ContainerSpec
- Add `templating` parameter to config create

### Bugfixes
- Fix getting a read timeout for logs/attach with a tty and slow output

### Miscellaneous
- Fix documentation examples

5.0.2
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/75?closed=1)

### Bugfixes
- Fix `disable_buffering` regression

5.0.1
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/74?closed=1)

### Bugfixes
- Bring back support for ssh identity file
- Cleanup remaining python-2 dependencies
- Fix image save example in docs

### Miscellaneous
- Bump urllib3 to 1.26.5
- Bump requests to 2.26.0

5.0.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/70?closed=1)

### Breaking changes
- Remove support for Python 2.7
- Make Python 3.6 the minimum version supported

### Features
- Add `limit` parameter to image search endpoint

### Bugfixes
- Fix `KeyError` exception on secret create
- Verify TLS keys loaded from docker contexts
- Update PORT_SPEC regex to allow square brackets for IPv6 addresses
- Fix containers and images documentation examples

4.4.4
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/73?closed=1)

### Bugfixes
- Remove `LD_LIBRARY_PATH` and `SSL_CERT_FILE` environment variables when shelling out to the ssh client

4.4.3
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/72?closed=1)

### Features
- Add support for docker.types.Placement.MaxReplicas

### Bugfixes
- Fix SSH port parsing when shelling out to the ssh client

4.4.2
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/71?closed=1)

### Bugfixes
- Fix SSH connection bug where the hostname was incorrectly trimmed and the error was hidden
- Fix docs example

### Miscellaneous
- Add Python3.8 and 3.9 in setup.py classifier list

4.4.1
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/69?closed=1)

### Bugfixes
- Avoid setting unsuported parameter for subprocess.Popen on Windows
- Replace use of deprecated "filter" argument on ""docker/api/image"

4.4.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/67?closed=1)

### Features
- Add an alternative SSH connection to the paramiko one, based on shelling out to the SSh client. Similar to the behaviour of Docker cli
- Default image tag to `latest` on `pull`

### Bugfixes
- Fix plugin model upgrade
- Fix examples URL in ulimits

### Miscellaneous
- Improve exception messages for server and client errors
- Bump cryptography from 2.3 to 3.2

4.3.1
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/68?closed=1)

### Miscellaneous
- Set default API version to `auto`
- Fix conversion to bytes for `float`
- Support OpenSSH `identityfile` option

4.3.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/64?closed=1)

### Features
- Add `DeviceRequest` type to expose host resources such as GPUs
- Add support for `DriverOpts` in EndpointConfig
- Disable compression by default when using container.get_archive method

### Miscellaneous
- Update default API version to v1.39
- Update test engine version to 19.03.12

4.2.2
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/66?closed=1)

### Bugfixes

- Fix context load for non-docker endpoints

4.2.1
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/65?closed=1)

### Features

- Add option on when to use `tls` on Context constructor
- Make context orchestrator field optional

4.2.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/63?closed=1)

### Bugfixes

- Fix `win32pipe.WaitNamedPipe` throw exception in Windows containers
- Use `Hostname`, `Username`, `Port` and `ProxyCommand` settings from `.ssh/config` when on SSH
- Set host key policy for ssh transport to `paramiko.WarningPolicy()`
- Set logging level of `paramiko` to warn

### Features

- Add support for docker contexts through `docker.ContextAPI`

4.1.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/61?closed=1)

### Bugfixes

- Correct `INDEX_URL` logic in build.py _set_auth_headers
- Fix for empty auth keys in config.json

### Features

- Add `NetworkAttachmentConfig` for service create/update

### Miscellaneous

- Bump pytest to 4.3.1
- Adjust `--platform` tests for changes in docker engine
- Update credentials-helpers to v0.6.3

4.0.2
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/62?closed=1)

### Bugfixes

- Unified the way `HealthCheck` is created/configured

### Miscellaneous

- Bumped version of websocket-client

4.0.1
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/60?closed=1)

### Bugfixes

- Fixed an obsolete import in the `credentials` subpackage that caused import errors in
  Python 3.7

### Miscellaneous

- Docs building has been repaired

4.0.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/57?closed=1)

### Breaking changes

- Support for Python 3.3 and Python 3.4 has been dropped
- `APIClient.update_service`, `APIClient.init_swarm`, and
  `DockerClient.swarm.init` now return a `dict` from the API's response body
- In `APIClient.build` and `DockerClient.images.build`, the `use_config_proxy`
  parameter now defaults to True
- `init_path` is no longer a valid parameter for `HostConfig`

### Features

- It is now possible to provide `SCTP` ports for port mappings
- `ContainerSpec`s now support the `init` parameter
- `DockerClient.swarm.init` and `APIClient.init_swarm` now support the
  `data_path_addr` parameter
- `APIClient.update_swarm` and `DockerClient.swarm.update` now support the
  `rotate_manager_unlock_key` parameter
- `APIClient.update_service` returns the API's response body as a `dict`
- `APIClient.init_swarm`, and `DockerClient.swarm.init` now return the API's
  response body as a `dict`

### Bugfixes

- Fixed `PlacementPreference` instances to produce a valid API type
- Fixed a bug where not setting a value for `buildargs` in `build` could cause
  the library to attempt accessing attributes of a `None` value
- Fixed a bug where setting the `volume_driver` parameter in
  `DockerClient.containers.create` would result in an error
- `APIClient.inspect_distribution` now correctly sets the authentication
  headers on the request, allowing it to be used with private repositories
  This change also applies to `DockerClient.get_registry_data`

3.7.2
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/59?closed=1)

### Bugfixes

* Fix base_url to keep TCP protocol on utils.py by letting the responsibility of changing the
protocol to `parse_host` afterwards, letting `base_url` with the original value.
* XFAIL test_attach_stream_and_cancel on TLS

3.7.1
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/58?closed=1)

### Bugfixes

* Set a different default number (which is now 9) for SSH pools
* Adds a BaseHTTPAdapter with a close method to ensure that the
pools is clean on close()
* Makes SSHHTTPAdapter reopen a closed connection when needed
like the others

3.7.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/56?closed=1)

### Features

* Added support for multiplexed streams (for `attach` and `exec_start`). Learn
  more at https://docker-py.readthedocs.io/en/stable/user_guides/multiplex.html
* Added the `use_config_proxy` parameter to the following methods:
  `APIClient.build`, `APIClient.create_container`, `DockerClient.images.build`
  and `DockerClient.containers.run` (`False` by default). **This parameter**
  **will become `True` by default in the 4.0.0 release.**
* Placement preferences for Swarm services are better validated on the client
  and documentation has been updated accordingly

### Bugfixes

* Fixed a bug where credential stores weren't queried for relevant registry
  credentials with certain variations of the `config.json` file.
* `DockerClient.swarm.init` now returns a boolean value as advertised.

3.6.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone=55?closed=1)

### Features

* Added support for connecting to the Docker Engine over SSH. Additional
  dependencies for this feature can be installed with
  `pip install "docker[ssh]"`
* Added support for the `named` parameter in `Image.save`, which may be
  used to ensure the resulting tarball retains the image's name on save.

### Bugfixes

* Fixed a bug where builds on Windows with a context path using the `\\?\`
  prefix would fail with some relative Dockerfile paths.
* Fixed an issue where pulls made with the `DockerClient` would fail when
  setting the `stream` parameter to `True`.

### Miscellaneous

* The minimum requirement for the `requests` dependency has been bumped
  to 2.20.0

3.5.1
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/54?closed=1)

### Miscellaneous

* Bumped version of `pyOpenSSL` in `requirements.txt` and `setup.py` to prevent
  installation of a vulnerable version

* Docs fixes

3.5.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/53?closed=1)

### Deprecation warning

* Support for Python 3.3 will be dropped in the 4.0.0 release

### Features

* Updated dependencies to ensure support for Python 3.7 environments
* Added support for the `uts_mode` parameter in `HostConfig`
* The `UpdateConfig` constructor now allows `rollback` as a valid
  value for `failure_action`
* Added support for `rollback_config` in `APIClient.create_service`,
  `APIClient.update_service`, `DockerClient.services.create` and
  `Service.update`.

### Bugfixes

* Credential helpers are now properly leveraged by the `build` method
* Fixed a bug that caused placement preferences to be ignored when provided
  to `DockerClient.services.create`
* Fixed a bug that caused a `user` value of `0` to be ignored in
  `APIClient.create_container` and `DockerClient.containers.create`

3.4.1
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/52?closed=1)

### Bugfixes

* Fixed a bug that caused auth values in config files written using one of the
  legacy formats to be ignored
* Fixed issues with handling of double-wildcard `**` patterns in
  `.dockerignore` files

3.4.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/51?closed=1)

### Features

* The `APIClient` and `DockerClient` constructors now accept a `credstore_env`
  parameter. When set, values in this dictionary are added to the environment
  when executing the credential store process.

### Bugfixes

* `DockerClient.networks.prune` now properly returns the operation's result
* Fixed a bug that caused custom Dockerfile paths in a subfolder of the build
  context to be invalidated, preventing these builds from working
* The `plugin_privileges` method can now be called for plugins requiring
  authentication to access
* Fixed a bug that caused attempts to read a data stream over an unsecured TCP
  socket to crash on Windows clients
* Fixed a bug where using the `read_only` parameter when creating a service using
  the `DockerClient` was being ignored
* Fixed an issue where `Service.scale` would not properly update the service's
  mode, causing the operation to fail silently

3.3.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/49?closed=1)

### Features

* Added support for `prune_builds` in `APIClient` and `DockerClient.images`
* Added support for `ignore_removed` parameter in
  `DockerClient.containers.list`

### Bugfixes

* Fixed an issue that caused builds to fail when an in-context Dockerfile
  would be specified using its absolute path
* Installation with pip 10.0.0 and above no longer fails
* Connection timeout for `stop` and `restart` now gets properly adjusted to
  allow for the operation to finish in the specified time
* Improved docker credential store support on Windows

3.2.1
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/50?closed=1)

### Bugfixes

* Fixed a bug with builds not properly identifying Dockerfile paths relative
  to the build context
* Fixed an issue where builds would raise a `ValueError` when attempting to
  build with a Dockerfile on a different Windows drive.

3.2.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/45?closed=1)

### Features

* Generators returned by `attach()`, `logs()` and `events()` now have a
  `cancel()` method to let consumers stop the iteration client-side.
* `build()` methods can now handle Dockerfiles supplied outside of the
  build context.
* Added `sparse` argument to `DockerClient.containers.list()`
* Added `isolation` parameter to `build()` methods.
* Added `close()` method to `DockerClient`
* Added `APIClient.inspect_distribution()` method and
  `DockerClient.images.get_registry_data()`
  * The latter returns an instance of the new `RegistryData` class

3.1.4
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/48?closed=1)

### Bugfixes

* Fixed a bug where build contexts containing directory symlinks would produce
  invalid tar archives

3.1.3
-----

### Bugfixes

* Regenerated invalid wheel package

3.1.2
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/47?closed=1)

### Bugfixes

* Fixed a bug that led to a Dockerfile not being included in the build context
  in some situations when the Dockerfile's path was prefixed with `./`

3.1.1
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/46?closed=1)

### Bugfixes

* Fixed a bug that caused costly DNS lookups on Mac OSX when connecting to the
  engine through UNIX socket
* Fixed a bug that caused `.dockerignore` comments to be read as exclusion
  patterns

3.1.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/44?closed=1)

### Features

* Added support for `device_cgroup_rules` in host config
* Added support for `generic_resources` when creating a `Resources`
  object.
* Added support for a configurable `chunk_size` parameter in `export`,
  `get_archive` and `get_image` (`Image.save`)
* Added a `force_update` method to the `Service` class.
* In `Service.update`, when the `force_update` parameter is set to `True`,
  the current `force_update` counter is incremented by one in the update
  request.

### Bugfixes

* Fixed a bug where authentication through `login()` was being ignored if the
  SDK was configured to use a credential store.
* Fixed a bug where download methods would use an absurdly small chunk size,
  leading to slow data retrieval
* Fixed a bug where using `DockerClient.images.pull` to pull an image by digest
  would lead to an exception being raised.
* `.dockerignore` rules should now be respected as defined by the spec,
  including respect for last-line precedence and proper handling of absolute
  paths
* The `pass` credential store is now properly supported.

3.0.1
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/43?closed=1)

### Bugfixes

* Fixed a bug where `APIClient.login` didn't populate the `_auth_configs`
  dictionary properly, causing subsequent `pull` and `push` operations to fail
* Fixed a bug where some build context files were incorrectly recognized as
  being inaccessible.
* Fixed a bug where files with a negative mtime value would
  cause errors when included in a build context

3.0.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/39?closed=1)

### Breaking changes

* Support for API version < 1.21 has been removed.
* The following methods have been removed:
  * `APIClient.copy` has been removed. Users should use `APIClient.get_archive`
    instead.
  * `APIClient.insert` has been removed. Users may use `APIClient.put_archive`
    combined with `APIClient.commit` to replicate the method's behavior.
  * `utils.ping_registry` and `utils.ping` have been removed.
* The following parameters have been removed:
  * `stream` in `APIClient.build`
  * `cpu_shares`, `cpuset`, `dns`, `mem_limit`, `memswap_limit`,
    `volume_driver`, `volumes_from` in `APIClient.create_container`. These are
    all replaced by their equivalent in `create_host_config`
  * `insecure_registry` in `APIClient.login`, `APIClient.pull`,
    `APIClient.push`, `DockerClient.images.push` and `DockerClient.images.pull`
  * `viz` in `APIClient.images`
* The following parameters have been renamed:
  * `endpoint_config` in `APIClient.create_service` and
    `APIClient.update_service` is now `endpoint_spec`
  * `name` in `DockerClient.images.pull` is now `repository`
* The return value for the following methods has changed:
  * `APIClient.wait` and `Container.wait` now return a ``dict`` representing
    the API's response instead of returning the status code directly.
  * `DockerClient.images.load` now returns a list of `Image` objects that have
    for the images that were loaded, instead of a log stream.
  * `Container.exec_run` now returns a tuple of (exit_code, output) instead of
    just the output.
  * `DockerClient.images.build` now returns a tuple of (image, build_logs)
    instead of just the image object.
  * `APIClient.export`, `APIClient.get_archive` and `APIClient.get_image` now
    return generators streaming the raw binary data from the server's response.
  * When no tag is provided, `DockerClient.images.pull` now returns a list of
    `Image`s associated to the pulled repository instead of just the `latest`
    image.

### Features

* The Docker Python SDK is now officially supported on Python 3.6
* Added `scale` method to the `Service` model ; this method is a shorthand
  that calls `update_service` with the required number of replicas
* Added support for the `platform` parameter in `APIClient.build`,
  `DockerClient.images.build`, `APIClient.pull` and `DockerClient.images.pull`
* Added support for the `until` parameter in `APIClient.logs` and
  `Container.logs`
* Added support for the `workdir` argument in `APIClient.exec_create` and
  `Container.exec_run`
* Added support for the `condition` argument in `APIClient.wait` and
  `Container.wait`
* Users can now specify a publish mode for ports in `EndpointSpec` using
  the `{published_port: (target_port, protocol, publish_mode)}` syntax.
* Added support for the `isolation` parameter in `ContainerSpec`,
  `DockerClient.services.create` and `Service.update`
* `APIClient.attach_socket`, `APIClient.exec_create` now allow specifying a
  `detach_keys` combination. If unspecified, the value from the `config.json`
  file will be used
* TLS connections now default to using the TLSv1.2 protocol when available


### Bugfixes

* Fixed a bug where whitespace-only lines in `.dockerignore` would break builds
  on Windows
* Fixed a bug where broken symlinks inside a build context would cause the
  build to fail
* Fixed a bug where specifying volumes with Windows drives would cause
  incorrect parsing in `DockerClient.containers.run`
* Fixed a bug where the `networks` data provided to `create_service` and
  `update_service` would be sent incorrectly to the Engine with API < 1.25
* Pulling all tags from a repository with no `latest` tag using the
  `DockerClient` will no longer raise a `NotFound` exception

2.7.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/41?closed=1)

### Features

* Added `unlock_swarm` and `get_unlock_key` methods to the `APIClient`.
    * Added `unlock` and `get_unlock_key` to `DockerClient.swarm`.
* Added a `greedy` parameter to `DockerClient.networks.list`, yielding
  additional details about the listed networks.
* Added `cpu_rt_runtime` and `cpu_rt_period` as parameters to
  `APIClient.create_host_config` and `DockerClient.containers.run`.
* Added the `order` argument to `UpdateConfig`.
* Added `fetch_current_spec` to `APIClient.update_service` and `Service.update`
  that will retrieve the current configuration of the service and merge it with
  the provided parameters to determine the new configuration.

### Bugfixes

* Fixed a bug where the `build` method tried to include inaccessible files
  in the context, leading to obscure errors during the build phase
  (inaccessible files inside the context now raise an `IOError` instead).
* Fixed a bug where the `build` method would try to read from FIFOs present
  inside the build context, causing it to hang.
* `APIClient.stop` will no longer override the `stop_timeout` value present
  in the container's configuration.
* Fixed a bug preventing removal of networks with names containing a space.
* Fixed a bug where `DockerClient.containers.run` would crash if the
  `auto_remove` parameter was set to `True`.
* Changed the default value of `listen_addr` in `join_swarm` to match the
  one in `init_swarm`.
* Fixed a bug where handling HTTP errors with no body would cause an unexpected
  exception to be thrown while generating an `APIError` object.

2.6.1
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/40?closed=1)

### Bugfixes

* Fixed a bug on Python 3 installations preventing the use of the `attach` and
  `exec_run` methods.


2.6.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/38?closed=1)

### Features

* Added support for `mounts` in `APIClient.create_host_config` and
  `DockerClient.containers.run`
* Added support for `consistency`, `tmpfs_size` and `tmpfs_mode` when
  creating mount objects.
* `Mount` objects now support the `tmpfs` and `npipe` types.
* Added support for `extra_hosts` in the `build` methods.
* Added support for the configs API:
    * In `APIClient`: `create_config`, `inspect_config`, `remove_config`,
      `configs`
    * In `DockerClient`: `configs.create`, `configs.get`, `configs.list` and
      the `Config` model.
    * Added `configs` parameter to `ContainerSpec`. Each item in the `configs`
      list must be a `docker.types.ConfigReference` instance.
* Added support for the following parameters when creating a `ContainerSpec`
  object: `groups`, `open_stdin`, `read_only`, `stop_signal`, `helathcheck`,
  `hosts`, `ns_config`, `configs`, `privileges`.
* Added the following configuration classes to `docker.types`:
  `ConfigReference`, `DNSConfig`, `Privileges`, `SwarmExternalCA`.
* Added support for `driver` in `APIClient.create_secret` and
  `DockerClient.secrets.create`.
* Added support for `scope` in `APIClient.inspect_network` and
  `APIClient.create_network`, and their `DockerClient` equivalent.
* Added support for the following parameters to `create_swarm_spec`:
  `external_cas`, `labels`, `signing_ca_cert`, `signing_ca_key`,
  `ca_force_rotate`, `autolock_managers`, `log_driver`. These additions
  also apply to `DockerClient.swarm.init`.
* Added support for `insert_defaults` in `APIClient.inspect_service` and
  `DockerClient.services.get`.

### Bugfixes

* Fixed a bug where reading a 0-length frame in log streams would incorrectly
  interrupt streaming.
* Fixed a bug where the `id` member on `Swarm` objects wasn't being populated.
* Fixed a bug that would cause some data at the beginning of an upgraded
  connection stream (`attach`, `exec_run`) to disappear.

2.5.1
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/37?closed=1)

### Bugfixes

* Fixed a bug where patterns ending with `**` in `.dockerignore` would
  raise an exception
* Fixed a bug where using `attach` with the `stream` argument set to `False`
  would raise an exception

2.5.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/34?closed=1)

### Features

* Added support for the `squash` parameter in `APIClient.build` and
  `DockerClient.images.build`.
* When using API version 1.23 or above, `load_image` will now return a
  generator of progress as JSON `dict`s.
* `remove_image` now returns the content of the API's response.


### Bugfixes

* Fixed an issue where the `auto_remove` parameter in
  `DockerClient.containers.run` was not taken into account.
* Fixed a bug where `.dockerignore` patterns starting with a slash
  were ignored.
* Fixed an issue with the handling of `**` patterns in `.dockerignore`
* Fixed a bug where building `FROM` a private Docker Hub image when not
  using a cred store would fail.
* Fixed a bug where calling `create_service` or `update_service` with
  `task_template` as a `dict` would raise an exception.
* Fixed the handling of TTY-enabled containers in `attach` and `exec_run`.
* `DockerClient.containers.run` will no longer attempt to stream logs if the
  log driver doesn't support the operation.

### Miscellaneous

* Added extra requirements for better TLS support on some platforms.
  These can be installed or required through the `docker[tls]` notation.

2.4.2
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/36?closed=1)

### Bugfixes

* Fixed a bug where the `split_port` utility would raise an exception when
  passed a non-string argument.

2.4.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/33?closed=1)

### Features

* Added support for the `target` and `network_mode` parameters in
  `APIClient.build` and `DockerClient.images.build`.
* Added support for the `runtime` parameter in `APIClient.create_container`
  and `DockerClient.containers.run`.
* Added support for the `ingress` parameter in `APIClient.create_network` and
  `DockerClient.networks.create`.
* Added support for `placement` configuration in `docker.types.TaskTemplate`.
* Added support for `tty` configuration in `docker.types.ContainerSpec`.
* Added support for `start_period` configuration in `docker.types.Healthcheck`.
* The `credHelpers` section in Docker's configuration file is now recognized.
* Port specifications including IPv6 endpoints are now supported.

### Bugfixes

* Fixed a bug where instantiating a `DockerClient` using `docker.from_env`
  wouldn't correctly set the default timeout value.
* Fixed a bug where `DockerClient.secrets` was not accessible as a property.
* Fixed a bug where `DockerClient.build` would sometimes return the wrong
  image.
* Fixed a bug where values for `HostConfig.nano_cpus` exceeding 2^32 would
  raise a type error.
* `Image.tag` now properly returns `True` when the operation is successful.
* `APIClient.logs` and `Container.logs` now raise an exception if the `since`
  argument uses an unsupported type instead of ignoring the value.
* Fixed a bug where some methods would raise a `NullResource` exception when
  the resource ID was provided using a keyword argument.

### Miscellaneous

* `APIClient` instances can now be pickled.

2.3.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/31?closed=1)

### Features

* Added support for the following `HostConfig` parameters: `volume_driver`,
  `cpu_count`, `cpu_percent`, `nano_cpus`, `cpuset_mems`.
* Added support for `verbose` parameter in `APIClient.inspect_network` and
  `DockerClient.networks.get`.
* Added support for the `environment` parameter in `APIClient.exec_create`
  and `Container.exec_run`
* Added `reload_config` method to `APIClient`, that lets the user reload
  the `config.json` data from disk.
* Added `labels` property to the `Image` and `Container` classes.
* Added `image` property to the `Container` class.

### Bugfixes

* Fixed a bug where setting `replicas` to zero in `ServiceMode` would not
  register as a valid entry.
* Fixed a bug where `DockerClient.images.build` would report a failure after
  a successful build if a `tag` was set.
* Fixed an issue where `DockerClient.images.pull` would fail to return the
  corresponding image object if a `tag` was set.
* Fixed a bug where a list of `mounts` provided to `APIClient.create_service`
  would sometimes be parsed incorrectly.
* Fixed a bug where calling `Network.containers` would crash when no containers
  were associated with the network.
* Fixed an issue where `Network.connect` and `Network.disconnect` would not
  accept some of the documented parameters.
* Fixed a bug where the `cpuset_cpus` parameter would not be properly set in
  `APIClient.create_host_config`.

### Miscellaneous

* The invalid `networks` argument in `DockerClient.containers.run` has been
  replaced with a (working) singular `network` argument.


2.2.1
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/32?closed=1)

### Bugfixes

* Fixed a bug where the `status_code` attribute of `APIError` exceptions would
  not reflect the expected value.
* Fixed an issue where the `events` method would time out unexpectedly if no
  data was sent by the engine for a given amount of time.


2.2.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/30?closed=1)

### Features

* Default API version has been bumped to `1.26` (Engine 1.13.1+)
* Upgrade plugin:
  * Added the `upgrade_plugin` method to the `APIClient` class
  * Added the `upgrade` method to the `Plugin` class
* Service logs:
  * Added the `service_logs` method to the `APIClient` class
  * Added the `logs` method to the `Service` class
* Added the `df` method to `APIClient` and `DockerClient`
* Added support for `init` and `init_path` parameters in `HostConfig`
  and `DockerClient.containers.run`
* Added support for `hostname` parameter in `ContainerSpec` and
  `DockerClient.service.create`
* Added support for port range to single port in port mappings
  (e.g. `8000-8010:80`)

### Bugfixes

* Fixed a bug where a missing container port in a port mapping would raise
  an unexpected `TypeError`
* Fixed a bug where the `events` method in `APIClient` and `DockerClient`
  would not respect custom headers set in `config.json`


2.1.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/27?closed=1)

### Features

* Added the following pruning methods:
    * In `APIClient`: `prune_containers`, `prune_images`, `prune_networks`,
      `prune_volumes`
    * In `DockerClient`: `containers.prune`, `images.prune`, `networks.prune`,
      `volumes.prune`
* Added support for the plugins API:
    * In `APIClient`: `configure_plugin`, `create_plugin`, `disable_plugin`,
      `enable_plugin`, `inspect_plugin`, `pull_plugin`, `plugins`,
      `plugin_privileges`, `push_plugin`, `remove_plugin`
    * In `DockerClient`: `plugins.create`, `plugins.get`, `plugins.install`,
      `plugins.list`, and the `Plugin` model.
* Added support for the secrets API:
    * In `APIClient`: `create_secret`, `inspect_secret`, `remove_secret`,
      `secrets`
    * In `DockerClient`: `secret.create`, `secret.get`, `secret.list` and
      the `Secret` model.
    * Added `secrets` parameter to `ContainerSpec`. Each item in the `secrets`
      list must be a `docker.types.SecretReference` instance.
* Added support for `cache_from` in `APIClient.build` and
  `DockerClient.images.build`.
* Added support for `auto_remove` and `storage_opt` in
  `APIClient.create_host_config` and `DockerClient.containers.run`
* Added support for `stop_timeout` in `APIClient.create_container` and
  `DockerClient.containers.run`
* Added support for the `force` parameter in `APIClient.remove_volume` and
  `Volume.remove`
* Added support for `max_failure_ratio` and `monitor` in `UpdateConfig`
* Added support for `force_update` in `TaskTemplate`
* Made `name` parameter optional in `APIClient.create_volume` and
  `DockerClient.volumes.create`

### Bugfixes

* Fixed a bug where building from a directory containing socket-type files
  would raise an unexpected `AttributeError`.
* Fixed an issue that was preventing the `DockerClient.swarm.init` method to
  take into account arguments passed to it.
* `Image.tag` now correctly returns a boolean value upon completion.
* Fixed several issues related to passing `volumes` in
  `DockerClient.containers.run`
* Fixed an issue where `DockerClient.image.build` wouldn't return an `Image`
  object even when the build was successful


2.0.2
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/29?closed=1)

### Bugfixes

* Installation of the package now fails if the `docker-py` package is
  installed in order to prevent obscure naming conflicts when both
  packages co-exist.
* Added missing `filters` parameter to `APIClient.networks`.
* Resource objects generated by the `DockerClient` are now hashable.
* Fixed a bug where retrieving untagged images using `DockerClient`
  would raise a `TypeError` exception.
* `mode` parameter in `create_service` is now properly converted to
  a valid data type for the Engine API. Use `ServiceMode` for advanced
  configurations.
* Fixed a bug where the decoded `APIClient.events` stream would sometimes raise
  an exception when a container is stopped or restarted.

2.0.1
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/28?closed=1)

### Bugfixes

* Fixed a bug where forward slashes in some .dockerignore patterns weren't
  being parsed correctly on Windows
* Fixed a bug where `Mount.parse_mount_string` would never set the read_only
  parameter on the resulting `Mount`.
* Fixed a bug where `Mount.parse_mount_string` would incorrectly mark host
  binds as being of `volume` type.

2.0.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/22?closed=1)

### Breaking changes

* Dropped support for Python 2.6
* `docker.Client` has been renamed to `docker.APIClient`
* `docker.from_env` now creates a `DockerClient` instance instead of an
  `APIClient` instance.
* Removed HostConfig parameters from `APIClient.start`
* The minimum supported API version is now 1.21 (Engine version 1.9.0+)
* The name of the `pip` package is now `docker` (was: `docker-py`). New
  versions of this library will only be published as `docker` from now on.
* `docker.ssladapter` is now `docker.transport.ssladapter`
* The package structure has been flattened in certain cases, which may affect
  import for `docker.auth` and `docker.utils.ports`
* `docker.utils.types` has been moved to `docker.types`
* `create_host_config`, `create_ipam_pool` and `create_ipam_config` have been
  removed from `docker.utils`. They have been replaced by the following classes
  in `docker.types`: `HostConfig`, `IPAMPool` and `IPAMCOnfig`.

### Features

* Added a high-level, user-focused API as `docker.DockerClient`. See the
  README and documentation for more information.
* Implemented `update_node` method in `APIClient`.
* Implemented `remove_node` method in `APIClient`.
* Added support for `restart_policy` in `update_container`.
* Added support for `labels` and `shmsize` in `build`.
* Added support for `attachable` in `create_network`
* Added support for `healthcheck` in `create_container`.
* Added support for `isolation` in `HostConfig`.
* Expanded support for `pid_mode` in `HostConfig` (now supports arbitrary
  values for API version >= 1.24).
* Added support for `options` in `IPAMConfig`
* Added a `HealthCheck` class to `docker.types` to be used in
  `create_container`.
* Added an `EndpointSpec` class to `docker.types` to be used in
  `create_service` and `update_service`.


### Bugfixes

* Fixed a bug where auth information would not be properly passed to the engine
  during a `build` if the client used a credentials store.
* Fixed an issue with some exclusion patterns in `build`.
* Fixed an issue where context files were bundled with the wrong permissions
  when calling `build` on Windows.
* Fixed an issue where auth info would not be retrieved from its default location
  on Windows.
* Fixed an issue where lists of `networks` in `create_service` and
  `update_service` wouldn't be properly converted for the engine.
* Fixed an issue where `endpoint_config` in `create_service` and
  `update_service` would be ignored.
* `endpoint_config` in `create_service` and `update_service` has been
  deprecated in favor of `endpoint_spec`
* Fixed a bug where `constraints` in a `TaskTemplate` object wouldn't be
  properly converted for the engine.
* Fixed an issue where providing a dictionary for `env` in `ContainerSpec`
  would provoke an `APIError` when sent to the engine.
* Fixed a bug where providing an `env_file` containing empty lines in
  `create_container`would raise an exception.
* Fixed a bug where `detach` was being ignored by `exec_start`.

### Documentation

* Documentation for classes and methods is now included alongside the code as
  docstrings.

1.10.6
------

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/26?closed=1)

### Bugfixes

* Fixed an issue where setting a `NpipeSocket` instance to blocking mode would
  put it in non-blocking mode and vice-versa.


1.10.5
------

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/25?closed=1)

### Bugfixes

* Fixed an issue where concurrent attempts to access to a named pipe by the
  client would sometimes cause recoverable exceptions to be raised.


1.10.4
------

[List of PRs / issues for this release](https://github.com/docker/docker-py/milestone/24?closed=1)

### Bugfixes

* Fixed an issue where `RestartPolicy.condition_types.ON_FAILURE` would yield
  an invalid value.
* Fixed an issue where the SSL connection adapter would receive an invalid
  argument.
* Fixed an issue that caused the Client to fail to reach API endpoints when
  the provided `base_url` had a trailing slash.
* Fixed a bug where some `environment` values in `create_container`
  containing unicode characters would raise an encoding error.
* Fixed a number of issues tied with named pipe transport on Windows.
* Fixed a bug where inclusion patterns in `.dockerignore` would cause some
  excluded files to appear in the build context on Windows.

### Miscellaneous

* Adjusted version requirements for the `requests` library.
* It is now possible to run the docker-py test suite on Windows.


1.10.3
------

[List of PRs / issues for this release](https://github.com/docker/docker-py/issues?q=milestone%3A1.10.3+is%3Aclosed)

### Bugfixes

* Fixed an issue where identity tokens in configuration files weren't handled
  by the library.

### Miscellaneous

* Increased the default number of connection pools from 10 to 25. This number
  can now be configured using the `num_pools` parameter in the `Client`
  constructor.


1.10.2
------

[List of PRs / issues for this release](https://github.com/docker/docker-py/issues?q=milestone%3A1.10.0+is%3Aclosed)

### Bugfixes

* Updated the docker-pycreds dependency as it was causing issues for some
  users with dependency resolution in applications using docker-py.


1.10.1
------

[List of PRs / issues for this release](https://github.com/docker/docker-py/issues?q=milestone%3A1.10.0+is%3Aclosed)

### Bugfixes

* The docker.utils.types module was removed in favor of docker.types, but some
  applications imported it explicitly. It has been re-added with an import
  warning advising to use the new module path.

1.10.0
------

[List of PRs / issues for this release](https://github.com/docker/docker-py/issues?q=milestone%3A1.10.0+is%3Aclosed)

### Features

* Added swarm mode and service management methods. See the documentation for
  details.
* Added support for IPv6 Docker host addresses in the `Client` constructor.
* Added (read-only) support for the Docker credentials store.
* Added support for custom `auth_config` in `Client.push`.
* Added support for `labels` in `Client.create_volume`.
* Added support for `labels` and `enable_ipv6` in `Client.create_network`.
* Added support for `force` param in
  `Client.disconnect_container_from_network`.
* Added support for `pids_limit`, `sysctls`, `userns_mode`, `cpuset_cpus`,
  `cpu_shares`, `mem_reservation` and `kernel_memory` parameters in
  `Client.create_host_config`.
* Added support for `link_local_ips` in `create_endpoint_config`.
* Added support for a `changes` parameter in `Client.import_image`.
* Added support for a `version` parameter in `Client.from_env`.

### Bugfixes

* Fixed a bug where `Client.build` would crash if the `config.json` file
  contained a `HttpHeaders` entry.
* Fixed a bug where passing `decode=True` in some streaming methods would
  crash when the daemon's response had an unexpected format.
* Fixed a bug where `environment` values with unicode characters weren't
  handled properly in `create_container`.
* Fixed a bug where using the `npipe` protocol would sometimes break with
  `ValueError: buffer size must be strictly positive`.

### Miscellaneous

* Fixed an issue where URL-quoting in docker-py was inconsistent with the
  quoting done by the Docker CLI client.
* The client now sends TCP upgrade headers to hint potential proxies about
  connection hijacking.
* The client now defaults to using the `npipe` protocol on Windows.


1.9.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/issues?q=milestone%3A1.9.0+is%3Aclosed)

### Features

* Added **experimental** support for Windows named pipes (`npipe://` protocol).
* Added support for Block IO constraints in `Client.create_host_config`. This
  includes parameters `blkio_weight`, `blkio_weight_device`, `device_read_bps`,
  `device_write_bps`, `device_read_iops` and `device_write_iops`.
* Added support for the `internal` param in `Client.create_network`.
* Added support for `ipv4_address` and `ipv6_address` in utils function
  `create_endpoint_config`.
* Added support for custom user agent setting in the `Client` constructor.
  By default, docker-py now also declares itself in the `User-Agent` header.

### Bugfixes

* Fixed an issue where the HTTP timeout on streaming responses would sometimes
  be set incorrectly.
* Fixed an issue where explicit relative paths in `.dockerignore` files were
  not being recognized.

1.8.1
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/issues?q=milestone%3A1.8.1+is%3Aclosed)

### Bugfixes

* Fixed a bug where calling `login()` against the default registry would fail
  with the 1.10.x engine
* Fixed a bug where values in environment files would be parsed incorrectly if
  they contained an equal sign.
* Switched to a better supported backport of the `match_hostname` function,
  fixing dependency issues in some environments.


1.8.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/issues?q=milestone%3A1.8.0+is%3Aclosed)

### Features

* Added `Client.update_container` method (Update resource configs of a
  container)
* Added support for gzipped context in `Client.build`
* Added ability to specify IP address when connecting a container to a
  network
* Added `tmpfs` support to `Client.create_host_config`
* Added support for the `changes` param in `Client.commit`
* Added support for the `follow` param in `Client.logs`
* Added support for the `check_duplicate` param in `Client.create_network`
* Added support for the `decode` param in `Client.push` and `Client.pull`
* Added `docker.from_env` shortcut function. Instantiates a client with
  `kwargs_from_env`
* `kwargs_from_env` now supports an optional `environment` parameter.
  If present, values will be fetched from this dictionary instead of
  `os.environ`


### Bugfixes

* Fixed a bug where TLS verification would fail when using IP addresses
  in the certificate's `subjectAltName` fields
* Fixed an issue where the default TLS version in TLSConfig would
  break in some environments. `docker-py` now uses TLSv1 by default
  This setting can be overridden using the `ssl_version` param in
  `kwargs_from_env` or the `TLSConfig` constructor
* Fixed a bug where `tcp` hosts would fail to connect to TLS-enabled
  endpoints
* Fixed a bug where loading a valid docker configuration file would fail
* Fixed a bug where some environment variables specified through
  `create_container` would be improperly formatted
* Fixed a bug where using the unix socket connection would raise
  an error in some edge-case situations

### Miscellaneous

* Default API version is now 1.22 (introduced in Docker 1.10.0)


1.7.2
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/issues?q=milestone%3A1.7.2+is%3Aclosed)

### Bugfixes

* Fixed a bug where TLS verification was improperly executed when providing
  a custom CA certificate.

1.7.1
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/issues?q=milestone%3A1.7.1+is%3Aclosed)

### Features

* Added support for `shm_size` in `Client.create_host_config`

### Bugfixes

* Fixed a bug where Dockerfile would sometimes be excluded from the build
  context.
* Fixed a bug where a docker config file containing unknown keys would raise
  an exception.
* Fixed an issue with SSL connections behaving improperly when pyOpenSSL
  was installed in the same environment.
* Several TLS configuration improvements


1.7.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/issues?q=milestone%3A1.7.0+is%3Aclosed)

### Features

* Added support for cusom IPAM configuration in `Client.create_network`
* Added input support to `Client.exec_create`
* Added support for `stop_signal` in `Client.create_host_config`
* Added support for custom HTTP headers in Docker config file.
* Added support for unspecified transfer protocol in `base_url` when TLS is
  enabled.


### Bugfixes

* Fixed a bug where the `filters` parameter in `Client.volumes` would not be
  applied properly.
* Fixed a bug where memory limits would parse to incorrect values.
* Fixed a bug where the `devices` parameter in `Client.create_host_config`
  would sometimes be misinterpreted.
* Fixed a bug where instantiating a `Client` object would sometimes crash if
  `base_url` was unspecified.
* Fixed a bug where an error message related to TLS configuration would link
  to a non-existent (outdated) docs page.


### Miscellaneous

* Processing of `.dockerignore` has been made significantly faster.
* Dropped explicit support for Python 3.2

1.6.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/issues?q=milestone%3A1.6.0+is%3Aclosed)

### Features

* Added support for the `since` param in `Client.logs` (introduced in API
  version 1.19)
* Added support for the `DOCKER_CONFIG` environment variable when looking up
  auth config
* Added support for the `stream` param in `Client.stats` (when set to `False`,
  allows user to retrieve a single snapshot instead of a constant data stream)
* Added support for the `mem_swappiness`, `oom_kill_disable` params
  in `Client.create_host_config`
* Added support for build arguments in `Client.build` through the `buildargs`
  param.


### Bugfixes

* Fixed a bug where streaming data over HTTPS would sometimes behave
  incorrectly with Python 3.x
* Fixed a bug where commands containing unicode characters would be incorrectly
  handled by `Client.create_container`.
* Fixed a bug where auth config credentials containing unicode characters would
  cause failures when pushing / pulling images.
* Setting `tail=0` in `Client.logs` no longer shows past logs.
* Fixed a bug where `Client.pull` and `Client.push` couldn't handle image names
  containing a dot.


### Miscellaneous

* Default API version is now 1.21 (introduced in Docker 1.9.0)
* Several test improvements and cleanup that should make the suite easier to
  expand and maintain moving forward.


1.5.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/issues?q=milestone%3A1.5.0+is%3Aclosed)

### Features

* Added support for the networking API introduced in Docker 1.9.0
  (`Client.networks`, `Client.create_network`, `Client.remove_network`,
  `Client.inspect_network`, `Client.connect_container_to_network`,
  `Client.disconnect_container_from_network`).
* Added support for the volumes API introduced in Docker 1.9.0
  (`Client.volumes`, `Client.create_volume`, `Client.inspect_volume`,
  `Client.remove_volume`).
* Added support for the `group_add` parameter in `create_host_config`.
* Added support for the CPU CFS (`cpu_quota` and `cpu_period`) parameters
  in `create_host_config`.
* Added support for the archive API endpoint (`Client.get_archive`,
  `Client.put_archive`).
* Added support for `ps_args` parameter in `Client.top`.


### Bugfixes

* Fixed a bug where specifying volume binds with unicode characters would
  fail.
* Fixed a bug where providing an explicit protocol in `Client.port` would fail
  to yield the expected result.
* Fixed a bug where the priority protocol returned by `Client.port` would be UDP
  instead of the expected TCP.

### Miscellaneous

* Broke up Client code into several files to facilitate maintenance and
  contribution.
* Added contributing guidelines to the repository.

1.4.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/issues?q=milestone%3A1.4.0+is%3Aclosed)

### Deprecation warning

* `docker.utils.create_host_config` is deprecated in favor of
  `Client.create_host_config`.

### Features

* Added `utils.parse_env_file` to support env-files.
  See [docs](https://docker-py.readthedocs.io/en/latest/api/#create_container)
  for usage.
* Added support for arbitrary log drivers
* Added support for URL paths in the docker host URL (`base_url`)
* Drastically improved support for .dockerignore syntax

### Bugfixes

* Fixed a bug where exec_inspect would allow invocation when the API version
  was too low.
* Fixed a bug where `docker.utils.ports.split_port` would break if an open
  range was provided.
* Fixed a bug where invalid image IDs / container IDs could be provided to
  bypass or reroute request URLs
* Default `base_url` now adapts depending on the OS (better Windows support)
* Fixed a bug where using an integer as the user param in
  `Client.create_container` would result in a failure.

### Miscellaneous

* Docs fixes
* Integration tests are now run as part of our continuous integration.
* Updated dependency on `six` library

1.3.1
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/issues?q=milestone%3A1.3.1+is%3Aclosed)

### Bugfixes

* Fixed a bug where empty chunks in streams was misinterpreted as EOF.
* `datetime` arguments passed to `Client.events` parameters `since` and
  `until` are now always considered to be UTC.
* Fixed a bug with Docker 1.7.x where the wrong auth headers were being passed
  in `Client.build`, failing builds that depended on private images.
* `Client.exec_create` can now retrieve the `Id` key from a dictionary for its
  container param.

### Miscellaneous

* 404 API status now raises `docker.errors.NotFound`. This exception inherits
  `APIError` which was used previously.
* Docs fixes
* Test fixes

1.3.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/issues?q=milestone%3A1.3.0+is%3Aclosed)

### Deprecation warning

* As announced in the 1.2.0 release, `Client.execute` has been removed in favor
  of `Client.exec_create` and `Client.exec_start`.

### Features

* `extra_hosts` parameter in host config can now also be provided as a list.
* Added support for `memory_limit` and `memswap_limit` in host config to
  comply with recent deprecations.
* Added support for `volume_driver` in `Client.create_container`
* Added support for advanced modes in volume binds (using the `mode` key)
* Added support for `decode` in `Client.build` (decodes JSON stream on the fly)
* docker-py will now look for login configuration under the new config path,
  and fall back to the old `~/.dockercfg` path if not present.

### Bugfixes

* Configuration file lookup now also work on platforms that don't define a
  `$HOME` environment variable.
* Fixed an issue where pinging a v2 private registry wasn't working properly,
  preventing users from pushing and pulling.
* `pull` parameter in `Client.build` now defaults to `False`. Fixes a bug where
  the default options would try to force a pull of non-remote images.
* Fixed a bug where getting logs from tty-enabled containers wasn't working
  properly with more recent versions of Docker
* `Client.push` and `Client.pull` will now raise exceptions if the HTTP
  status indicates an error.
* Fixed a bug with adapter lookup when using the Unix socket adapter
  (this affected some weird edge cases, see issue #647 for details)
* Fixed a bug where providing `timeout=None` to `Client.stop` would result
  in an exception despite the usecase being valid.
* Added `git@` to the list of valid prefixes for remote build paths.

### Dependencies

* The websocket-client dependency has been updated to a more recent version.
  This new version also supports Python 3.x, making `attach_socket` available
  on those versions as well.

### Documentation

* Various fixes

1.2.3
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/issues?q=milestone%3A1.2.3+is%3Aclosed)

### Deprecation warning

* Passing host config in the `Client.start` method is now deprecated. Please
  use the `host_config` in `Client.create_container` instead.

### Features

* Added support for `privileged` param in `Client.exec_create`
  (only available in API >= 1.19)
* Volume binds can now also be specified as a list of strings.

### Bugfixes

* Fixed a bug where the `read_only` param in host_config wasn't handled
  properly.
* Fixed a bug in `Client.execute` (this method is still deprecated).
* The `cpuset` param in `Client.create_container` is also passed as
  the `CpusetCpus` param (`Cpuset` deprecated in recent versions of the API)
* Fixed an issue with integration tests being run inside a container
  (`make integration-test`)
* Fixed a bug where an empty string would be considered a valid container ID
  or image ID.
* Fixed a bug in `Client.insert`


### Documentation

* Various fixes

1.2.2
-----

### Bugfixes

* Fixed a bug where parameters passed to `Client.exec_resize` would be ignored (#576)
* Fixed a bug where auth config wouldn't be resolved properly in `Client.pull` (#577)

1.2.1
-----

### Bugfixes

* Fixed a bug where the check_resource decorator would break with some
  argument-passing methods. (#573)

1.2.0
-----

[List of PRs / issues for this release](https://github.com/docker/docker-py/issues?q=milestone%3A1.2.0+is%3Aclosed)

### Deprecation warning

* `Client.execute` is being deprecated in favor of the more dev-friendly
  `Client.exec_start` and `Client.exec_create`. **It will be removed in 1.3.0**

### Features

* Added `exec_create`, `exec_start`, `exec_inspect` and `exec_resize` to
  client, accurately mirroring the
  [Exec API](https://docs.docker.com/reference/api/docker_remote_api_v1.18/#exec-create)
* Added `auth_config` param to `Client.pull` (allows to use one-off credentials
  for this pull request)
* Added support for `ipc_mode` in host config.
* Added support for the `log_config` param in host config.
* Added support for the `ulimit` param in host config.
* Added support for container resource limits in `Client.build`.
* When a resource identifier (image or container ID) is passed to a Client
  method, we now check for `None` values to avoid crashing
  (now raises `docker.errors.NullResource`)
* Added tools to parse port ranges inside the new `docker.utils.ports` package.
* Added a `version_info` attribute to the `docker` package.

### Bugfixes

* Fixed a bug in `Client.port` where absence of a certain key in the
  container's JSON would raise an error (now just returns `None`)
* Fixed a bug with the `trunc` parameter in `Client.containers` having no
  effect (moved functionality to the client)
* Several improvements have been made to the `Client.import_image` method.
* Fixed pushing / pulling to
  [v2 registries](https://github.com/docker/distribution)
* Fixed a bug where passing a container dictionary to `Client.commit`
  would fail

### Miscellaneous

* Default API version has been bumped to 1.18 (Docker Engine 1.6.0)
* Several testing coverage improvements
* Docs fixes and improvements

1.1.0
-----

### Features

* Added `dockerfile` param support to `Client.build` (mirrors
  `docker build -f` behavior)
* Added the ability to specify `'auto'` as `version` in `Client.__init__`,
  allowing the constructor to autodetect the daemon's API version.

### Bugfixes

* Fixed a bug where decoding a result stream using the `decode` parameter
  would break when using Python 3.x
* Fixed a bug where some files in `.dockerignore` weren't being handled
  properly
* Fixed `resolve_authconfig` issues by bringing it closer to Docker Engine's
  behavior. This should fix all issues encountered with private registry auth
* Fixed an issue where passwords containing a colon weren't being handled
  properly.
* Bumped `requests` version requirement, which should fix most of the SSL
  issues encountered recently.

### Miscellaneous

* Several integration test improvements.
* Fixed some unclosed resources in unit tests.
* Several docs improvements.

1.0.0
-----

### Features

* Added new `Client.rename` method (`docker rename`)
* Added now `Client.stats` method (`docker stats`)
* Added `read_only` param support to `utils.create_host_config` and
  `Client.start` (`docker run --read-only`)
* Added `pid_mode` param support to `utils.create_host_config` and
  `Client.start` (`docker run --pid='host'`)
* Added `since`, `until` and `filters` params to `Client.events`.
* Added `decode` parameter to `Client.stats` and `Client.events` to decode
  JSON objects on the fly (False by default).

### Bugfixes

* Fixed a bug that caused `Client.build` to crash when the provided source was
  a remote source.

### Miscellaneous

* Default API version has been bumped to 1.17 (Docker Engine 1.5.0)
* `Client.timeout` is now a public attribute, and users are encouraged to use it
  when request timeouts need to be changed at runtime.
* Added `Client.api_version` as a read-only property.
* The `memswap_limit` argument in `Client.create_container` now accepts string
  type values similar to `mem_limit` ('6g', '120000k', etc.)
* Improved documentation

0.7.2
-----

### Features

* Added support for `mac_address` in `Client.create_container`

### Bugfixes

* Fixed a bug where streaming responses (`pull`, `push`, `logs`, etc.) were
  unreliable (#300)
* Fixed a bug where resolve_authconfig wouldn't properly resolve configuration
  for private repositories (#468)
* Fixed a bug where some errors wouldn't be properly constructed in
  `client.py`, leading to unhelpful exceptions bubbling up (#466)
* Fixed a bug where `Client.build` would try to close context when externally
  provided (`custom_context == True`) (#458)
* Fixed an issue in `create_host_config` where empty sequences wouldn't be
  interpreted properly (#462)

### Miscellaneous

* Added `resolve_authconfig` tests.

0.7.1
-----

### Bugfixes

* `setup.py` now indicates a maximum version of requests to work around the
  boot2docker / `assert_hostname` bug.
* Removed invalid exception when using the Registry Hub's FQDN when pulling.
* Fixed an issue where early HTTP errors weren't handled properly in streaming
  responses.
* Fixed a bug where sockets would close unexpectedly using Python 3.x
* Various fixes for integration tests.

### Miscellaneous

* Small doc fixes

0.7.0
-----

### Breaking changes

* Passing `dns` or `volumes_from` in `Client.start` with API version < 1.10
  will now raise an exception (previously only triggered a warning)

### Features

* Added support for `host_config` in `Client.create_container`
* Added utility method `docker.utils.create_host_config` to help build a
  proper `HostConfig` dictionary.
* Added support for the `pull` parameter in `Client.build`
* Added support for the `forcerm` parameter in `Client.build`
* Added support for `extra_hosts` in `Client.start`
* Added support for a custom `timeout` in `Client.wait`
* Added support for custom `.dockercfg` loading in `Client.login`
  (`dockercfg_path` argument)

### Bugfixes

* Fixed a bug where some output wouldn't be streamed properly in streaming
  chunked responses
* Fixed a bug where the `devices` param didn't recognize the proper delimiter
* `Client.login` now properly expands the `registry` URL if provided.
* Fixed a bug where unicode characters in passed for `environment` in
  `create_container` would break.

### Miscellaneous

* Several unit tests and integration tests improvements.
* `Client` constructor now enforces passing the `version` parameter as a
  string.
* Build context files are now ordered by filename when creating the archive
  (for consistency with docker mainline behavior)

0.6.0
-----
* **This version introduces breaking changes!**

### Breaking changes

* The default SSL protocol is now the highest TLS v1.x (was SSL v2.3 before)
  (Poodle fix)
* The `history` command now returns a dict instead of a raw JSON string.

### Features

* Added the `execute` command.
* Added `pause` and `unpause` commands.
* Added support fo the `cpuset` param in `create_container`
* Added support for host devices (`devices` param in `start`)
* Added support for the `tail` param in `logs`.
* Added support for the `filters` param in `images` and `containers`
* The `kwargs_from_env` method is now available in the `docker.utils`
  module. This should make it easier for boot2docker user to connect
  to their daemon.

### Bugfixes

* Fixed a bug where empty directories weren't correctly included when
  providing a context to `Client.build`.
* Fixed a bug where UNIX socket connections weren't properly cleaned up,
  causing `ResourceWarning`s to appear in some cases.
* Fixed a bug where docker-py would crash if the docker daemon was stopped
  while reading a streaming response
* Fixed a bug with streaming responses in Python 3
* `remove_image` now supports a dict containing an `Id` key as its `id`
  parameter (similar to other methods requiring a resource ID)

### Documentation

* Added new MkDocs documentation. Currently hosted on
  [ReadTheDocs](https://docker-py.readthedocs.io/en/latest/)

### Miscellaneous

* Added tests to sdist
* Added a Makefile for running tests in Docker
* Updated Dockerfile

0.5.3
-----

* Fixed attaching when connecting to the daemon over a UNIX socket.

0.5.2
-----

* Fixed a bug where sockets were closed immediately when attaching over
  TLS.

0.5.1
-----

* Added a `assert_hostname` option to `TLSConfig` which can be used to
  disable verification of hostnames.
* Fixed SSL not working due to an incorrect version comparison
* Fixed streams not working on Windows

0.5.0
-----

* **This version introduces breaking changes!**
* Added `insecure_registry` parameter in `Client.push` and `Client.pull`.
  *It defaults to False and code pushing to non-HTTPS private registries
  might break as a result.*
* Added support for adding and dropping capabilities
* Added support for restart policy
* Added support for string values in `Client.create_container`'s `mem_limit`
* Added support for `.dockerignore` file in `Client.build`

### Bugfixes

* Fixed timeout behavior in `Client.stop`

### Miscellaneous

* `Client.create_container` provides better validation of the `volumes`
  parameter
* Improved integration tests

0.4.0
-----

* **This version introduces breaking changes!**
* The `base_url` parameter in the `Client` constructor should now allow most
  of the `DOCKER_HOST` environment values (except for the fd:// protocol)
    * As a result, URLs that don't specify a port are now invalid (similar
    to the official client's behavior)
* Added TLS support (see [documentation](https://github.com/dotcloud/docker-py#connection-to-daemon-using-https))

### Bugfixes

* Fixed an issue with `Client.build` streamed logs in Python 3

### Miscellaneous

* Added unit tests coverage
* Various integration tests fixes

0.3.2
-----

* Default API version is now 1.12 (support for docker 1.0)
* Added new methods `Client.get_image` and `Client.load_image`
  (`docker save` and `docker load`)
* Added new method `Client.ping`
* Added new method `Client.resize`
* `Client.build` can now be provided with a custom context using the
  `custom_context` parameter.
* Added support for `memswap_limit` parameter in `create_container`
* Added support for `force` parameter in `remove_container`
* Added support for `force` and `noprune` parameters in `remove_image`
* Added support for `timestamps` parameter in `logs`
* Added support for `dns_search` parameter in `start`
* Added support for `network_mode` parameter in `start`
* Added support for `size` parameter in `containers`
* Added support for `volumes_from` and `dns` parameters in `start`. As of
  API version >= 1.10, these parameters no longer belong to `create_container`
* `Client.logs` now uses the logs endpoint when API version is sufficient

### Bugfixes

* Fixed a bug in pull where the `repo:tag` notation wasn't interpreted
  properly
* Fixed a bug in streaming methods with python 3 (unicode, bytes/str related)
* Fixed a bug in `Client.start` where legacy notation for volumes wasn't
  supported anymore.

### Miscellaneous

* The client now raises `DockerException`s when appropriate. You can import
  `DockerException` (and its subclasses) from the `docker.errors` module to
  catch them if needed.
* `docker.APIError` has been moved to the new `docker.errors` module as well.
* `Client.insert` is deprecated in API version > 1.11
* Improved integration tests should now run much faster.
* There is now a single source of truth for the docker-py version number.

0.3.1
-----

* Default API version is now 1.9
* Streaming responses no longer yield blank lines.
* `Client.create_container` now supports the `domainname` parameter.
* `volumes_from` parameter in `Client.create_container` now supports
  iterables.
* Auth credentials are provided to the docker daemon when using `Client.build`
  (new feature in API version 1.9)


### Bugfixes

* Various fixes for response streams (`logs`, `pull`, etc.).
* Fixed a bug with `Client.push` when using API version < 1.5
* Fixed a bug with API version checks.

### Miscellaneous

* `mock` has been removed from the runtime requirements.
* Added installation instructions in the README.

0.3.0
-----

* **This version introduces breaking changes!**
* Support for API version 1.7 through 1.9 (Docker 0.8.0+)
* Default API version is now 1.8
* The client has been updated to support Requests 2.x. `requests==2.2.1`
  is now the recommended version.
* Links can now be specified as tuples in `Client.start` (see docs for
  more information)
* Added support for various options in `Client.create_container`
  (`network_disabled`, `cpu_shares`, `working_dir` and `entrypoint`)
* `Client.attach` has been reworked to work similarly to `Client.logs`
  minus the historical data.
* Logs can now be streamed using the `stream` parameter.
* Added support for `tcp://` URLs as client `base_url`.
* Various auth improvements.
* Added support for custom `Client.build` timeout.


### Bugfixes

* Fixed a bug where determining the protocol of a private registry
  would sometimes yield the wrong result.
* Fixed a bug where `Client.copy` wouldn't accept a dict as argument.
* Fixed several streaming bugs.
* Removed unused parameter in `Client.import_image`.
* The client's `base_url` now tolerates trailing slashes.

#### Miscellaneous

* Updated integration tests
* Small doc fixes

0.2.3
-----

* Support for API version 1.6
* Added support for links
* Added support for global request timeout
* Added `signal` parameter in `Client.kill`
* Added support for `publish_all_ports` in `Client.start`
* `Client.pull`, `Client.push` and `Client.build` can be streamed now
* Added support for websockets in `Client.attach`
* Fixed ports for Docker 0.6.5+
* Added `Client.events` method (access to the `/events` endpoint)
* Changed the way the ports and volumes are provided in `Client.start` and
  `Client.create_container̀` to make them simpler and more intuitive.

### Bugfixes

* Fixed a bug where private registries on HTTPS weren't handled properly
* Fixed a bug where auth would break with Python 3

### Miscellaneous

* Test improvements
* Slight doc improvements


0.2.2
-----

* Added support for the `rm` parameter in `Client.build`
* Added support for tarball imports in `Client.import_image` through `data`
  parameter.
* The `command` parameter in `Client.create_container` is now optional (for
  containers that include a default run command)

### Bugfixes

* Fixed Python 3 support
* Fixed a bug where anonymous push/pull would break when no authconfig is
  present
* Fixed a bug where the `quiet` parameter wouldn't be taken into account in
  `Client.containers`
* Fixed a bug where `Client.push` would break when pushing to private
  registries.
* Removed unused `registry` parameter in `Client.pull`.
* Removed obsolete custom error message in `Client.create_container`.

### Miscellaneous

* docker-py is now unit-tested, and Travis-CI has been enabled on the
  source repository.

0.2.1
-----

* Improvements to the `tox.ini` file

### Bugfixes

* Fixed a bug where the package would fail with an `ImportError` if requests
  was installed using `apt-get`
* Fixed a bug where `Client.build` would fail if given a `path` parameter.
* Fixed several bugs in `Client.login`. It should now work with API versions
  1.4, 1.5.
* Please note that `Client.login` currently doesn't write auth to the
  `.dockercfg` file, thus **auth is not persistent when using this method.**

0.2.0
-----

* **This version introduces breaking changes!**
* `Client.kill`, `Client.remove_container`, `Client.remove_image`,
`Client.restart`, `Client.start`, `Client.stop` and `Client.wait` don't support
varargs anymore.
* Added commands `Client.top` and `Client.copy`
* Added `lxc_conf` parameter to `Client.start`
* Added support for authentication in `Client.pull` (API version >=1.5)
* Added support for privileged containers.
* Error management overhaul. The new version should be more consistent and
* All methods that expected a container ID as argument now also support a dict
containing an `Id` key.
* Added license header to python files.
* Several `README.md` updates.

### Bugfixes

* Fixed several bugs with auth config parsing.
* Fixed a bug in `Client.push` where it would raise an exception if
the auth config wasn't loaded.
* Fixed a bug in `Client.pull` where private registry images wouldn't be parsed
properly if it contained port information.


0.1.5
-----

* `Client.build` now uses tempfiles to store build context instead of storing
it in memory
* Added `nocache` option to `Client.build`
* `Client.remove_container` now raises an exception when trying to remove a
running container
* `Client.create_container` now accepts dicts for the `environment` parameter

### Bugfixes

* Fixed a bug in `Client.create_container` on Python 2.6 where unicode
commands would fail to be parsed
* Fixed a bug in `Client.build` where the `tag` parameter would not be taken
into account

0.1.4
-----

* Added support for API connection through UNIX socket (default for docker 0.5.2+)

0.1.3
-----

* The client now tries to load the auth config from `~/.dockercfg`. This is necessary to use the push command if API version is >1.0

0.1.2
-----

* Added a `quiet parameter` to `Client.build` (mirrors the `q` parameter in the API)

0.1.1
-----

* Fixed a bug where the build command would list tar contents before sending the request
* Fixed a bug in `Client.port`


0.1.0
-----
* **This version introduces breaking changes!**
* Switched to server side build system
* Removed the BuilderClient
* Added support for contextual builds
* Added support for remote URL builds
* Added python 3 support
* Added bind mounts support
* Added API version support
* Fixed a bug where `Client.port` would fail if provided with a port of type number
* Fixed a bug where `Client._post_json` wouldn't set the Content-Type header to `application/json`

0.0.6
-----
* Added support for custom loggers in `Client.build`
* Added `Client.attach` command
* Added support for `ADD` command in builder
* Fixed a bug in `Client.logs`
* Improved unit tests


0.0.5
-----
* Added tag support for the builder
* Use `shlex` to parse plain string commands when creating a container
* Fixed several bugs in the builder
* Fixed the `quiet` option in `Client.images`
* Unit tests

0.0.4
-----
* Improved error reporting

0.0.3
-----
* Fixed a bug in `Client.tag`
* Fixed a bug where generated images would be removed after a successful build

0.0.2
-----
* Implemented first version of the builder client
