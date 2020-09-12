# A make file for creating a s-tui executable.
# This requires pandoc and pyinstaller

all: stui del readme

# Create s-tui executable
stui:
	pyinstaller s_tui/s_tui.py -F -n s-tui
	mv dist/s-tui .

# Remove files created by pyinstaller
del:
	rm -rf ./s_tui/dist/ ./build/ ./s_tui/s*.spec ./s_tui/*.pyc ./s_tui/*.log s-tui.spec dist/

# Clear pyinstall cache and delete file
clean:
	pyinstaller --clean s-tui
	rm -rf ./s_tui/dist/ ./s_tui/build/ ./s_tui/s*.spec ./s_tui/*.pyc ./s_tui/*.log s-tui.spec dist/
