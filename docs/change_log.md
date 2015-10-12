Change Log
==========

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
* Added support for the CPU CFS (`cpu_quota` and `cpu_period`) parameteres
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
  See [docs](http://docker-py.readthedocs.org/en/latest/api/#create_container)
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
  [ReadTheDocs](http://docker-py.readthedocs.org/en/latest/)

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
