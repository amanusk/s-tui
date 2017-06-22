import os
from setuptools import setup
import s_tui.s_tui as STUI

setup(
    name = "s-tui",
    packages=['s_tui'],
    version=STUI.__version__,
    author="Alex Manuskin",
    author_email="alex.manuskin@gmail.com",
    description="Terminal UI stress test and monitoring tool",
    license="GPLv2",
    url="https://github.com/amanusk/s-tui",
    keywords=['stress', 'monitoring', 'TUI'], # arbitrary keywords

    entry_points = {
        'console_scripts' : ['s-tui=s_tui.s_tui:main']
    },
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2',
        'Topic :: System :: Monitoring',
    ],
    install_requires=[
        'urwid',
        'psutil',
    ],
)
