#!/usr/bin/env python3
import os
from setuptools import setup

import copydeps


def load_readme():
    path = os.path.join(os.path.dirname(__file__), 'README.md')
    with open(path) as f:
        return f.read()


setup(
    name=copydeps.__appname__,
    version=copydeps.__version__,
    description=copydeps.DESCRIPTION,
    long_description=load_readme(),
    long_description_content_type='text/markdown',
    author='Genymobile',
    author_email='opensource@genymobile.com',
    license=copydeps.__license__,
    platforms=['Linux'],
    url='https://github.com/genymobile/copydeps',
    py_modules=['copydeps'],
    install_requires=['pyelftools'],
    entry_points={
        'console_scripts': [
            'copydeps = copydeps:main',
        ],
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Build Tools',
    ]
)
