# s-tui

s-tui is a terminal UI add-on for stress. The software uses stress to run CPU hogs, while monitoring the CPU usage, temperature and frequency.

This software makes it possible to stress and monitor your computer without a need for a GUI. 

You can now monitor your server over ssh.

## Screen Shots
![](./ScreenShots/stui1.png?raw=true "Full Screen")

![](./ScreenShots/stui2.png?raw=true "Overheat detected")

![](./ScreenShots/stui3.png?raw=true "Two Graphs")


## Dependencies
s-tui uses stress. To install stress on Ubuntu run:
```
sudo apt-get install stress
```

## Usage
To run the compiled executable simply run:
```
./s-tui
```

# To run .py file
s-tui uses psutil and urwid libraries.
These need to be installed to run the s-tui.py
For example:
```
(sudo) pip install urwid
(sudo) pip install psutil
```
then run 
```
./s-tui.py
```



