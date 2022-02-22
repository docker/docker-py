#!/usr/bin/env python

import codecs
import os

from setuptools import find_packages
from setuptools import setup

ROOT_DIR = os.path.dirname(__file__)
SOURCE_DIR = os.path.join(ROOT_DIR)

requirements = [
    'websocket-client >= 0.32.0',
    'requests >= 2.14.2, != 2.18.0',
]

extras_require = {
    # win32 APIs if on Windows (required for npipe support)
    ':sys_platform == "win32" and python_version<"3.0"': 'pywin32>=228',
    ':sys_platform == "win32" and python_version>="3.0"': 'pywin32>=303',

    # If using docker-py over TLS, highly recommend this option is
    # pip-installed or pinned.

    # TODO: if pip installing both "requests" and "requests[security]", the
    # extra package from the "security" option are not installed (see
    # https://github.com/pypa/pip/issues/4391).  Once that's fixed, instead of
    # installing the extra dependencies, install the following instead:
    # 'requests[security] >= 2.5.2, != 2.11.0, != 2.12.2'
    'tls': ['pyOpenSSL>=17.5.0', 'cryptography>=3.4.7', 'idna>=2.0.0'],

    # Only required when connecting using the ssh:// protocol
    'ssh': ['paramiko>=2.4.3'],

}

version = None
exec(open('docker/version.py').read())

with open('./test-requirements.txt') as test_reqs_txt:
    test_requirements = [line for line in test_reqs_txt]


long_description = ''
with codecs.open('./README.md', encoding='utf-8') as readme_md:
    long_description = readme_md.read()

setup(
    name="docker",
    version=version,
    description="A Python library for the Docker Engine API.",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/docker/docker-py',
    project_urls={
        'Documentation': 'https://docker-py.readthedocs.io',
        'Changelog': 'https://docker-py.readthedocs.io/en/stable/change-log.html',  # noqa: E501
        'Source': 'https://github.com/docker/docker-py',
        'Tracker': 'https://github.com/docker/docker-py/issues',
    },
    packages=find_packages(exclude=["tests.*", "tests"]),
    install_requires=requirements,
    tests_require=test_requirements,
    extras_require=extras_require,
    python_requires='>=3.6',
    zip_safe=False,
    test_suite='tests',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Software Development',
        'Topic :: Utilities',
        'License :: OSI Approved :: Apache Software License',
    ],
    maintainer='Ulysses Souza',
    maintainer_email='ulysses.souza@docker.com',
)
