#!/usr/bin/env python
import os
import sys

from setuptools import setup


ROOT_DIR = os.path.dirname(__file__)
SOURCE_DIR = os.path.join(ROOT_DIR)

requirements = [
    'requests >= 2.5.2',
    'six >= 1.4.0',
    'websocket-client >= 0.32.0',
]

if sys.platform == 'win32':
    requirements.append('pypiwin32 >= 219')

extras_require = {
    ':python_version < "3.5"': 'backports.ssl_match_hostname >= 3.5',
    ':python_version < "3.3"': 'ipaddress >= 1.0.16',
}

version = None
exec(open('docker/version.py').read())

with open('./test-requirements.txt') as test_reqs_txt:
    test_requirements = [line for line in test_reqs_txt]


setup(
    name="docker-py",
    version=version,
    description="Python client for Docker.",
    url='https://github.com/docker/docker-py/',
    packages=[
        'docker', 'docker.api', 'docker.auth', 'docker.transport',
        'docker.utils', 'docker.utils.ports', 'docker.ssladapter'
    ],
    install_requires=requirements,
    tests_require=test_requirements,
    extras_require=extras_require,
    zip_safe=False,
    test_suite='tests',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Utilities',
        'License :: OSI Approved :: Apache Software License',
    ],
)
