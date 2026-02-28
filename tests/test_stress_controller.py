"""Tests for StressController: mode management and process lifecycle."""

import pytest
from unittest.mock import MagicMock, patch

from s_tui.s_tui import StressController


class TestStressControllerInit:
    def test_monitor_only(self):
        """With no stress tools, only Monitor mode is available."""
        sc = StressController(stress_installed=False, firestarter_installed=False)
        assert sc.get_modes() == ["Monitor"]
        assert sc.get_current_mode() == "Monitor"

    def test_stress_installed(self):
        """With stress installed, Monitor and Stress are available."""
        sc = StressController(stress_installed=True, firestarter_installed=False)
        modes = sc.get_modes()
        assert "Monitor" in modes
        assert "Stress" in modes

    def test_firestarter_installed(self):
        """With FIRESTARTER installed, it appears in modes."""
        sc = StressController(stress_installed=False, firestarter_installed=True)
        modes = sc.get_modes()
        assert "FIRESTARTER" in modes

    def test_both_installed(self):
        """With both installed, all three modes are available."""
        sc = StressController(stress_installed=True, firestarter_installed=True)
        modes = sc.get_modes()
        assert len(modes) == 3


class TestStressControllerModes:
    def test_set_mode(self):
        """set_mode changes current_mode."""
        sc = StressController(True, False)
        sc.set_mode("Stress")
        assert sc.get_current_mode() == "Stress"

    def test_set_mode_back_to_monitor(self):
        """Can switch back to Monitor."""
        sc = StressController(True, False)
        sc.set_mode("Stress")
        sc.set_mode("Monitor")
        assert sc.get_current_mode() == "Monitor"


class TestStressControllerProcess:
    def test_stress_process_initially_none(self):
        """No stress process running initially."""
        sc = StressController(True, False)
        assert sc.get_stress_process() is None

    def test_set_stress_process(self):
        """set_stress_process stores the process."""
        sc = StressController(True, False)
        mock_proc = MagicMock()
        sc.set_stress_process(mock_proc)
        assert sc.get_stress_process() is mock_proc

    def test_kill_stress_process(self, mocker):
        """kill_stress_process calls kill_child_processes and resets to None."""
        mocker.patch("s_tui.s_tui.kill_child_processes")
        sc = StressController(True, False)
        mock_proc = MagicMock()
        sc.set_stress_process(mock_proc)
        sc.kill_stress_process()
        assert sc.get_stress_process() is None

    def test_kill_stress_process_no_such_process(self, mocker):
        """kill_stress_process handles NoSuchProcess gracefully."""
        import psutil

        mocker.patch(
            "s_tui.s_tui.kill_child_processes",
            side_effect=psutil.NoSuchProcess(pid=12345),
        )
        sc = StressController(True, False)
        sc.set_stress_process(MagicMock())
        sc.kill_stress_process()
        assert sc.get_stress_process() is None

    def test_start_stress(self, mocker):
        """start_stress launches subprocess and stores psutil.Process."""
        mock_popen = mocker.patch("subprocess.Popen")
        mock_popen.return_value.pid = 99999
        mock_psutil_proc = MagicMock()
        mocker.patch("psutil.Process", return_value=mock_psutil_proc)

        sc = StressController(True, False)
        sc.start_stress(["stress", "-c", "4"])
        assert sc.get_stress_process() is mock_psutil_proc

    def test_start_stress_oserror(self, mocker):
        """start_stress handles OSError gracefully."""
        mocker.patch("subprocess.Popen", side_effect=OSError("not found"))
        sc = StressController(True, False)
        sc.start_stress(["stress", "-c", "4"])
        # Should not crash; process remains None
        assert sc.get_stress_process() is None
