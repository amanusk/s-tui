# A make file for creating a s-tui executable.
# This requires pandoc and pyinstaller

all: stui del readme

# Create s-tui executable
stui:
	pyinstaller s_tui.py -F -n s-tui

# Convert the markdown file to .rst file. Markdown for github, rst for PyPi
readme:
	pandoc --from markdown --to rst README.md > README.rst

# Remove files created by pyinstaller
del:
	rm -rf ./s_tui/dist/ ./s_tui/build/ ./s_tui/s*.spec ./s_tui/*.pyc ./s_tui/*.log s-tui.spec

# Clear pyinstall cache and delete file
clean:
	pyinstaller --clean s-tui
	rm -rf ./s_tui/dist/ ./s_tui/build/ ./s_tui/s*.spec ./s_tui/*.pyc ./s_tui/*.log s-tui.spec
