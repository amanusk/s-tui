# The Stress Terminal UI: s-tui

s-tui is a terminal UI add-on for stress. The tool uses stress to run CPU hogs, while monitoring the CPU usage, temperature and frequency of your computer.

This software makes it possible to stress and monitor your computer without a need for a GUI. 

### Pros
* Monitoring your headless server over ssh
* See performance dips caused by thermal throttling 
* Requires minimal resources



## Usage
```
s-tui
```
or  
```
sudo s-tui
```


## Run local executable:
* Download the latest release version from https://github.com/amanusk/s-tui/releases
* Install stress (See dependencies)
```
sudo apt-get install stress
```
* Change s-tui to exectuable `chmod +x s-tui`
* Run `(sudo) ./s-tui`

## Screen Shots
![](./ScreenShots/stui1.png?raw=true "Full Screen")

![](./ScreenShots/stui2.png?raw=true "Overheat detected")

![](./ScreenShots/stui3.png?raw=true "Two Graphs")


## Dependencies
s-tui uses stress. To install stress on Ubuntu run:
```
sudo apt-get install stress
```

## Installation
Installation is available from ppa. Apt does not hold the latest versions of psutil and urwid. Some features will not work.
```
sudo add-apt-repository ppa:amanusk/python-s-tui
sudo apt-get update
sudo apt-get install python-s-tui
```

* Installation with pip coming soon

## Build
If would like to make changes to s-tui, you can test your work by running s-tui.py.
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
(sudo) ./s-tui.py
```

## Compatibility
s-tui uses psutil to probe your hardware information. If your hardware is not supported, you might not see all the information.

Running s-tui as root gives access to the maximum Turbo Boost frequency available to your CPU when stressing all cores. (Currently tested on Intel only).

Running without root will display the Turbo Boost available on a single core. 


