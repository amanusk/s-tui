# A make file for creating a s-tui executable.
# This requires pandoc and pyinstaller

all: stui del

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

debug:
	python -m s_tui.s_tui

# ---- Test targets ----

# Run all CI-compatible tests (mocked, no hardware required)
test:
	python -m pytest tests/ -m "not hardware" -v --tb=short

# Run only hardware integration tests (requires real sensors)
test-hw:
	python -m pytest tests/ -m hardware -v --tb=short

# Run the full suite (CI + hardware)
test-all:
	python -m pytest tests/ -v --tb=short

# Run tests matching a keyword (usage: make test-k K=pattern)
test-k:
	python -m pytest tests/ -k "$(K)" -v --tb=short

# Run only expected-to-fail (xfail) tests
test-xfail:
	python -m pytest tests/test_psutil_failures.py::TestTempSourceFailures tests/test_runtime_disruption.py -v --tb=short
