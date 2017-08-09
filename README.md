# The Stress Terminal UI: s-tui

[![Build Status](https://travis-ci.org/amanusk/s-tui.svg?branch=master)](https://travis-ci.org/amanusk/s-tui)
[![PyPI version](https://badge.fury.io/py/s-tui.svg)](https://badge.fury.io/py/s-tui)


s-tui is a terminal UI for monitoring your computer. s-tui allows to monitor CPU temperature, frequency and utilization in a graphical way from the terminal. 

## Screenshot
![](https://thumbs.gfycat.com/SaneBadFlea-size_restricted.gif)

* [The Stress Terminal UI: s-tui](#the-stress-terminal-ui-s-tui)
  * [Screenshot](#screenshot)
  * [What it does](#what-it-does)
  * [Usage](#usage)
  * [Simple installation](#simple-installation)
	 * [pip (x86   ARM)](#pip-x86--arm)
	 * [Run local executable (x86 only):](#run-local-executable-x86-only)
  * [Options](#options)
  * [Dependencies](#dependencies)
  * [Other installation methods](#other-installation-methods)
	 * [Ubuntu](#ubuntu)
	 * [Arch-Linux](#arch-linux)
  * [Build](#build)
  * [Compatibility](#compatibility)


## What it does
* Monitoring your CPU temperature/utilization/frequency
* Shows performance dips caused by thermal throttling 
* Requires minimal resources
* Requires no X-server
* Built in options for stressing the CPU (stress/stress-ng)


## Usage
```
s-tui
```
or  
```
sudo s-tui
```

## Simple installation
### pip (x86 + ARM)
```
sudo pip install s-tui
```
Or if you cannot use sudo:
```
pip install s-tui --user
```

If you are installing s-tui on a Raspberry-Pi you might need to install `python-dev` first

### Run local executable (x86 only):
* Download the latest release version from https://github.com/amanusk/s-tui/releases
* Change s-tui to executable `chmod +x s-tui`
* Run `(sudo) ./s-tui`

## Options
```
********s-tui manual********
Usage in graphical mode:
* Toggle between stressed and regular operation using the radio buttons.
* If you wish to alternate stress defaults, you can do it in 'stress options'
* If your system supports it, you can use the utf8 button to get a smoother graph
* Reset buttons resets the graph and the max statistics

optional arguments:
  -h, --help      show this help message and exit
  -d, --debug     Output debug log to _s-tui.log
  -c, --csv       Save stats to csv file
  -t, --terminal  Display a single line of stats without tui
  -j, --json      Display a single line of stats in JSON format
  -v, --version   Display version
```

## Dependencies
s-tui is a great tool for monitoring. If you would like to stress your computer, install stress. Stress options will then show up in s-tui
```
sudo apt-get install stress
```

## Other installation methods
### Ubuntu
Installation is available from ppa. Apt does not hold the latest versions of psutil and urwid. Some features will not work.
```
sudo add-apt-repository ppa:amanusk/python-s-tui
sudo apt-get update
sudo apt-get install python-s-tui
```
### Arch-Linux
An AUR package is available called 's-tui-git'
Thanks to @DonOregano

## Build
If you would like to make changes to s-tui, you can test your work by running s\_tui.py.
Clone
```
git clone https://github.com/amanusk/s-tui.git
```
s-tui uses psutil and urwid libraries.
These need to be installed to run s-tui.py
```
(sudo) pip install urwid
(sudo) pip install psutil
```
Install stress
```
sudo apt-get install stress
```

Run the .py file
```
(sudo) ./s_tui/s_tui.py
```

## Compatibility
s-tui uses psutil to probe your hardware information. If your hardware is not supported, you might not see all the information.

* On Intel machines:
Running s-tui as root gives access to the maximum Turbo Boost frequency available to your CPU when stressing all cores. (Currently tested on Intel only).  
Running without root will display the Turbo Boost available on a single core. 

* s-tui tested to run on Raspberry-Pi 3

* If the temperature does not show up, your sensor might not be supported. Try opening an issue on github and we can look into it.

