#!/bin/bash
pyinstaller s_tui/s_tui.py -F -n s-tui &&
cp dist/s-tui . &&
./clean_build.sh
