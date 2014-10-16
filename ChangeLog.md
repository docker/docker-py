ChangeLog
=========

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
