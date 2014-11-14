# Contributing
See the [Docker contributing guidelines](https://github.com/docker/docker/blob/master/CONTRIBUTING.md).
The following is specific to docker-py.

## Running the tests & Code Quality


To get the source source code and run the unit tests, run:
```
$ git clone git://github.com/docker/docker-py.git
$ cd docker-py
$ pip install tox
$ tox
```

## Building the docs
Docs are built with [MkDocs](http://www.mkdocs.org/). For development, you can
run the following in the project directory:
```
$ pip install -r docs-requirements.txt
$ mkdocs serve
```

## Release Checklist

Before a new release, please go through the following checklist:

* Bump version in docker/version.py
* Add a release note in docs/change_log.md
* Git tag the version
* Upload to pypi

## Vulnerability Reporting
For any security issues, please do NOT file an issue or pull request on github!
Please contact [security@docker.com](mailto:security@docker.com) or read [the
Docker security page](https://www.docker.com/resources/security/).
