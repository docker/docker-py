Contributing
============

Running the tests & Code Quality
--------------------------------

To get the source source code and run the unit tests, run::

    $ git clone git://github.com/docker/docker-py.git
    $ cd docker-py
    $ virtualenv env
    $ . env/bin/activate
    $ pip install tox
    $ tox

Building the docs
-----------------

When in the project directory::

    $ pip install -r requirements/docs.txt
    $ pip uninstall -y docker-py && python setup.py install
    $ cd docs && make html
    $ open docs/_build/html/index.html

Release Checklist
-----------------

Before a new release, please go through the following checklist:

* Bump version in docker/version.py
* Add a release note in docs/release_notes.rst
* Git tag the version
* Upload to pypi

Vulnerability Reporting
-----------------------

For any security issues, please do NOT file an issue or pull request on github!
Please contact `security@docker.com`_ or read https://www.docker.com/resources/security/.

.. _security@docker.com: mailto:security@docker.com
