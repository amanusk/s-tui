#!/usr/bin/python

# Copyright (C) 2017-2020 Alex Manuskin
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA
from __future__ import absolute_import

from setuptools import setup
import s_tui.helper_functions as AUX

setup(
    name="s-tui",
    packages=['s_tui', 's_tui.sources', 's_tui.sturwid'],
    version=AUX.__version__,
    author="Alex Manuskin",
    author_email="amanusk@tuta.io",
    description="Stress Terminal UI stress test and monitoring tool",
    long_description=open('README.md', 'r').read(),
    long_description_content_type='text/markdown',
    license="GPLv2",
    url="https://github.com/amanusk/s-tui",
    keywords=['stress', 'monitoring', 'TUI'],  # arbitrary keywords

    entry_points={
        'console_scripts': ['s-tui=s_tui.s_tui:main']
    },
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: System :: Monitoring',
    ],
    install_requires=[
        'urwid>=2.0.1',
        'psutil>=5.6.0',
    ],
)
