#!/usr/bin/env python
from __future__ import print_function

import codecs
import os
import sys

import pip

from setuptools import setup, find_packages

if 'docker-py' in [x.project_name for x in pip.get_installed_distributions()]:
    print(
        'ERROR: "docker-py" needs to be uninstalled before installing this'
        ' package:\npip uninstall docker-py', file=sys.stderr
    )
    sys.exit(1)

ROOT_DIR = os.path.dirname(__file__)
SOURCE_DIR = os.path.join(ROOT_DIR)

requirements = [
    'requests >= 2.14.2, != 2.18.0',
    'six >= 1.4.0',
    'websocket-client >= 0.32.0',
    'docker-pycreds >= 0.2.2'
]

extras_require = {
    ':python_version < "3.5"': 'backports.ssl_match_hostname >= 3.5',
    # While not imported explicitly, the ipaddress module is required for
    # ssl_match_hostname to verify hosts match with certificates via
    # ServerAltname: https://pypi.python.org/pypi/backports.ssl_match_hostname
    ':python_version < "3.3"': 'ipaddress >= 1.0.16',

    # win32 APIs if on Windows (required for npipe support)
    # Python 3.6 is only compatible with v220 ; Python < 3.5 is not supported
    # on v220 ; ALL versions are broken for v222 (as of 2018-01-26)
    ':sys_platform == "win32" and python_version < "3.6"': 'pypiwin32==219',
    ':sys_platform == "win32" and python_version >= "3.6"': 'pypiwin32==220',

    # If using docker-py over TLS, highly recommend this option is
    # pip-installed or pinned.

    # TODO: if pip installing both "requests" and "requests[security]", the
    # extra package from the "security" option are not installed (see
    # https://github.com/pypa/pip/issues/4391).  Once that's fixed, instead of
    # installing the extra dependencies, install the following instead:
    # 'requests[security] >= 2.5.2, != 2.11.0, != 2.12.2'
    'tls': ['pyOpenSSL>=0.14', 'cryptography>=1.3.4', 'idna>=2.0.0'],
}

version = None
exec(open('docker/version.py').read())

with open('./test-requirements.txt') as test_reqs_txt:
    test_requirements = [line for line in test_reqs_txt]


long_description = ''
try:
    with codecs.open('./README.rst', encoding='utf-8') as readme_rst:
        long_description = readme_rst.read()
except IOError:
    # README.rst is only generated on release. Its absence should not prevent
    # setup.py from working properly.
    pass

setup(
    name="docker",
    version=version,
    description="A Python library for the Docker Engine API.",
    long_description=long_description,
    url='https://github.com/docker/docker-py',
    packages=find_packages(exclude=["tests.*", "tests"]),
    install_requires=requirements,
    tests_require=test_requirements,
    extras_require=extras_require,
    zip_safe=False,
    test_suite='tests',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Utilities',
        'License :: OSI Approved :: Apache Software License',
    ],
    maintainer='Joffrey F',
    maintainer_email='joffrey@docker.com',
)
