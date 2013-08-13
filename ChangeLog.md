ChangeLog
=========

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