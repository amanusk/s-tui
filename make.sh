#!/bin/bash
pyinstaller s-tui.py -F -n s-tui &&
cp dist/s-tui . &&
./clean_build.sh
