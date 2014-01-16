#!/usr/bin/env python
import os
from setuptools import setup

ROOT_DIR = os.path.dirname(__file__)
SOURCE_DIR = os.path.join(ROOT_DIR)

test_requirements = []
with open('./requirements.txt') as requirements_txt:
    requirements = [line for line in requirements_txt]

setup(
    name="docker-py",
    version='0.2.3',
    description="Python client for Docker.",
    packages=['docker', 'docker.auth', 'docker.unixconn', 'docker.utils'],
    install_requires=requirements + test_requirements,
    zip_safe=False,
    test_suite='tests',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Topic :: Utilities',
        'License :: OSI Approved :: Apache Software License',
    ],
)
