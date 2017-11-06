#!/usr/bin/env python3
from setuptools import setup

import copydeps

setup(
    name=copydeps.__appname__,
    version=copydeps.__version__,
    description=copydeps.DESCRIPTION,
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
