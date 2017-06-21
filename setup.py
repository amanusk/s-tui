import os
from setuptools import setup

setup(
    name = "s-tui",
    version = "0.2.1",
    author = "Alex Manuskin",
    author_email = "alex.manuskin@gmail.com",
    description = "Terminal UI stress test and monitoring tool",
    license = "GPL2",
    url = "https://amanusk.github.io/s-tui/",
    packages=['s_tui'],
    entry_points = {
        'console_scripts' : ['s-tui=s_tui.s_tui:main']
    },
    classifiers=[
        "License :: OSI Approved :: GPL2 License",
    ],
    install_requires=[ 'urwid', 'psutil', ],
)
