#!/usr/bin/env python

import codecs
import os

from setuptools import find_packages
from setuptools import setup

ROOT_DIR = os.path.dirname(__file__)
SOURCE_DIR = os.path.join(ROOT_DIR)

requirements = [
    'packaging >= 14.0',
    'requests >= 2.26.0',
    'urllib3 >= 1.26.0',
    'websocket-client >= 0.32.0',
]

extras_require = {
    # win32 APIs if on Windows (required for npipe support)
    ':sys_platform == "win32"': 'pywin32>=304',

    # This is now a no-op, as similarly the requests[security] extra is
    # a no-op as of requests 2.26.0, this is always available/by default now
    # see https://github.com/psf/requests/pull/5867
    'tls': [],

    # Only required when connecting using the ssh:// protocol
    'ssh': ['paramiko>=2.4.3'],
}

with open('./test-requirements.txt') as test_reqs_txt:
    test_requirements = [line for line in test_reqs_txt]


long_description = ''
with codecs.open('./README.md', encoding='utf-8') as readme_md:
    long_description = readme_md.read()

setup(
    name="docker",
    use_scm_version={
        'write_to': 'docker/_version.py'
    },
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
    setup_requires=['setuptools_scm'],
    install_requires=requirements,
    tests_require=test_requirements,
    extras_require=extras_require,
    python_requires='>=3.7',
    zip_safe=False,
    test_suite='tests',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Software Development',
        'Topic :: Utilities',
        'License :: OSI Approved :: Apache Software License',
    ],
    maintainer='Ulysses Souza',
    maintainer_email='ulysses.souza@docker.com',
)
