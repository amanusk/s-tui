#!/bin/bash
cd ./s_tui
pyinstaller s_tui.py -F -n s-tui &&
mv dist/s-tui ..
cd ../
./clean_build.sh
