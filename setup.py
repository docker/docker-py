#/usr/bin/env python
import os
from setuptools import setup, find_packages

ROOT_DIR = os.path.dirname(__file__)
SOURCE_DIR = os.path.join(ROOT_DIR)

test_requirements = []
setup(
    name="docker-py",
    version='0.0.1',
    description="Python client for Docker.",
    packages=find_packages(),
    install_requires=[] + test_requirements,
    zip_safe=False,
    classifiers=['Development Status :: 3 - Alpha',
                 'Environment :: Other Environment',
                 'Intended Audience :: Developers',
                 'Operating System :: OS Independent',
                 'Programming Language :: Python',
                 'Topic :: Utilities'],
    )
