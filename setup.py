import os
from setuptools import setup

setup(
    name = "s-tui",
    packages=['s_tui'],
    version = "0.2.2",
    author = "Alex Manuskin",
    author_email = "alex.manuskin@gmail.com",
    description = "Terminal UI stress test and monitoring tool",
    license = "GPL2",
    url = "https://github.com/amanusk/s-tui",
    download_url = 'https://github.com/amanusk/s-tui/archive/v0.2.1.tar.gz',
    keywords = ['stress', 'monitoring', 'TUI'], # arbitrary keywords

    entry_points = {
        'console_scripts' : ['s-tui=s_tui.s_tui:main']
    },
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Programming Language :: Python :: 2',
        'Topic :: System :: Monitoring',
    ],
    install_requires=[
        'urwid',
        'psutil',
    ],
)
