"""Tests for StressController: mode management and process lifecycle."""

from unittest.mock import MagicMock

from s_tui.s_tui import StressController


class TestStressControllerInit:
    def test_monitor_and_builtin_always_available(self):
        """Monitor and Built-in modes are always available."""
        sc = StressController(stress_installed=False)
        assert sc.get_modes() == ["Monitor", "s-tui stress"]
        assert sc.get_current_mode() == "Monitor"

    def test_stress_installed(self):
        """With stress installed, Monitor, s-tui stress, and Stress (ext) are available."""
        sc = StressController(stress_installed=True)
        modes = sc.get_modes()
        assert "Monitor" in modes
        assert "s-tui stress" in modes
        assert "Stress (ext)" in modes

    def test_builtin_stresser_lazy_init(self):
        """BuiltinStresser is not created until first access."""
        sc = StressController(stress_installed=False)
        assert sc._builtin_stresser is None
        # Accessing the property triggers creation
        stresser = sc.builtin_stresser
        assert stresser is not None
        assert sc._builtin_stresser is stresser


class TestStressControllerModes:
    def test_set_mode(self):
        """set_mode changes current_mode."""
        sc = StressController(True)
        sc.set_mode("Stress (ext)")
        assert sc.get_current_mode() == "Stress (ext)"

    def test_set_mode_builtin(self):
        """Can switch to Built-in mode."""
        sc = StressController(False)
        sc.set_mode("s-tui stress")
        assert sc.get_current_mode() == "s-tui stress"

    def test_set_mode_back_to_monitor(self):
        """Can switch back to Monitor."""
        sc = StressController(True)
        sc.set_mode("Stress (ext)")
        sc.set_mode("Monitor")
        assert sc.get_current_mode() == "Monitor"


class TestStressControllerProcess:
    def test_stress_process_initially_none(self):
        """No stress process running initially."""
        sc = StressController(True)
        assert sc.get_stress_process() is None

    def test_set_stress_process(self):
        """set_stress_process stores the process."""
        sc = StressController(True)
        mock_proc = MagicMock()
        sc.set_stress_process(mock_proc)
        assert sc.get_stress_process() is mock_proc

    def test_kill_stress_process(self, mocker):
        """kill_stress_process calls kill_child_processes and resets to None."""
        mocker.patch("s_tui.s_tui.kill_child_processes")
        sc = StressController(True)
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
        sc = StressController(True)
        sc.set_stress_process(MagicMock())
        sc.kill_stress_process()
        assert sc.get_stress_process() is None

    def test_kill_stress_process_stops_builtin(self, mocker):
        """kill_stress_process also stops the builtin stresser if initialized."""
        mocker.patch("s_tui.s_tui.kill_child_processes")
        sc = StressController(True)
        sc._builtin_stresser = MagicMock()
        sc.kill_stress_process()
        sc._builtin_stresser.stop.assert_called_once()

    def test_kill_stress_process_skips_builtin_if_not_initialized(self, mocker):
        """kill_stress_process does not create builtin stresser just to stop it."""
        mocker.patch("s_tui.s_tui.kill_child_processes")
        sc = StressController(True)
        sc.kill_stress_process()
        assert sc._builtin_stresser is None

    def test_start_stress(self, mocker):
        """start_stress launches subprocess and stores psutil.Process."""
        mock_popen = mocker.patch("subprocess.Popen")
        mock_popen.return_value.pid = 99999
        mock_psutil_proc = MagicMock()
        mocker.patch("psutil.Process", return_value=mock_psutil_proc)

        sc = StressController(True)
        sc.start_stress(["stress", "-c", "4"])
        assert sc.get_stress_process() is mock_psutil_proc

    def test_start_stress_uses_new_session(self, mocker):
        """start_stress passes start_new_session=True for process group isolation."""
        mock_popen = mocker.patch("subprocess.Popen")
        mock_popen.return_value.pid = 99999
        mocker.patch("psutil.Process", return_value=MagicMock())

        sc = StressController(True)
        sc.start_stress(["stress", "-c", "4"])
        _, kwargs = mock_popen.call_args
        assert kwargs.get("start_new_session") is True

    def test_start_stress_oserror(self, mocker):
        """start_stress handles OSError gracefully."""
        mocker.patch("subprocess.Popen", side_effect=OSError("not found"))
        sc = StressController(True)
        sc.start_stress(["stress", "-c", "4"])
        # Should not crash; process remains None
        assert sc.get_stress_process() is None

    def test_start_builtin_stress(self):
        """start_builtin_stress delegates to builtin_stresser.start."""
        sc = StressController(False)
        sc._builtin_stresser = MagicMock()
        sc.start_builtin_stress(4)
        sc._builtin_stresser.start.assert_called_once_with(4, strategy=None)

    def test_start_builtin_stress_with_strategy(self):
        """start_builtin_stress passes strategy to builtin_stresser."""
        sc = StressController(False)
        sc._builtin_stresser = MagicMock()
        sc.start_builtin_stress(2, strategy="hashlib")
        sc._builtin_stresser.start.assert_called_once_with(2, strategy="hashlib")

    def test_start_builtin_stress_oserror_falls_back_to_monitor(self):
        """start_builtin_stress falls back to Monitor on OSError (e.g. no /dev/shm)."""
        sc = StressController(False)
        sc.set_mode("s-tui stress")
        sc._builtin_stresser = MagicMock()
        sc._builtin_stresser.start.side_effect = PermissionError("Permission denied")
        sc.start_builtin_stress(4)
        assert sc.get_current_mode() == "Monitor"
