# The Stress Terminal UI: s-tui

s-tui is a terminal UI for monitoring your computer. s-tui allows to monitor CPU temperature, frequency and utilization in a graphical way from the terminal. 

## Screenshot
![](./ScreenShots/Screen_3.png?raw=true "Full Screen")

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

## Simplest installation with pip
```
sudo pip install s-tui
```
Or if you cannot use sudo:
```
pip install s-tui --user
```

## Run local executable:
* Download the latest release version from https://github.com/amanusk/s-tui/releases
* Change s-tui to executable `chmod +x s-tui`
* Run `(sudo) ./s-tui`



## Dependencies
s-tui is a great tool for monitoring. If you would like to stress your computer, install stress
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
If would like to make changes to s-tui, you can test your work by running s\_tui.py.
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

Running s-tui as root gives access to the maximum Turbo Boost frequency available to your CPU when stressing all cores. (Currently tested on Intel only).  
Running without root will display the Turbo Boost available on a single core. 


