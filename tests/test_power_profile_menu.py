"""Tests for PowerProfileMenu: UI construction, apply logic, and error handling."""

from unittest.mock import MagicMock, patch

import pytest

from s_tui.power_profile_menu import (
    _EPP_TO_PROFILE,
    PowerProfileMenu,
    _read_current,
    _set_epp_via_powerprofilesctl,
    _write_all_cores,
    read_available,
)

GOVERNORS = ["performance", "powersave"]
EPP_VALUES = ["default", "performance", "balance_performance", "balance_power", "power"]


@pytest.fixture
def menu_full():
    """Menu with both governor and EPP controllable (root + powerprofilesctl)."""
    with patch("s_tui.power_profile_menu._read_current", return_value="powersave"):
        return PowerProfileMenu(
            return_fn=MagicMock(),
            powerprofilesctl_exe="/usr/bin/powerprofilesctl",
            can_write_governor=True,
            can_write_epp=True,
            available_governors=GOVERNORS,
            available_epp=EPP_VALUES,
        )


@pytest.fixture
def menu_epp_only():
    """Menu with only EPP controllable via powerprofilesctl (non-root)."""
    with patch("s_tui.power_profile_menu._read_current", return_value="powersave"):
        return PowerProfileMenu(
            return_fn=MagicMock(),
            powerprofilesctl_exe="/usr/bin/powerprofilesctl",
            can_write_governor=False,
            can_write_epp=False,
            available_governors=GOVERNORS,
            available_epp=EPP_VALUES,
        )


@pytest.fixture
def menu_nothing():
    """Menu with nothing controllable (no root, no powerprofilesctl)."""
    with patch("s_tui.power_profile_menu._read_current", return_value="powersave"):
        return PowerProfileMenu(
            return_fn=MagicMock(),
            powerprofilesctl_exe=None,
            can_write_governor=False,
            can_write_epp=False,
            available_governors=GOVERNORS,
            available_epp=EPP_VALUES,
        )


# =====================================================================
# Construction and is_controllable
# =====================================================================


class TestConstruction:
    def test_full_control(self, menu_full):
        assert menu_full.is_controllable()
        assert menu_full.governor_controllable
        assert menu_full.epp_controllable
        assert len(menu_full.governor_buttons) == 2
        assert len(menu_full.epp_buttons) == 5

    def test_epp_only(self, menu_epp_only):
        assert menu_epp_only.is_controllable()
        assert not menu_epp_only.governor_controllable
        assert menu_epp_only.epp_controllable
        # Governor shown as read-only text, no radio buttons
        assert len(menu_epp_only.governor_buttons) == 0
        assert len(menu_epp_only.epp_buttons) == 5

    def test_nothing_controllable(self, menu_nothing):
        assert not menu_nothing.is_controllable()

    def test_single_governor_hides_section(self):
        """If only one governor, section is not controllable."""
        with patch("s_tui.power_profile_menu._read_current", return_value="powersave"):
            m = PowerProfileMenu(
                return_fn=MagicMock(),
                powerprofilesctl_exe=None,
                can_write_governor=True,
                can_write_epp=False,
                available_governors=["powersave"],
                available_epp=[],
            )
        assert not m.governor_controllable
        assert not m.is_controllable()

    def test_no_epp_hides_section(self):
        """If no EPP values, section is not controllable."""
        with patch(
            "s_tui.power_profile_menu._read_current", return_value="performance"
        ):
            m = PowerProfileMenu(
                return_fn=MagicMock(),
                powerprofilesctl_exe="/usr/bin/powerprofilesctl",
                can_write_governor=True,
                can_write_epp=False,
                available_governors=GOVERNORS,
                available_epp=[],
            )
        assert m.governor_controllable
        assert not m.epp_controllable
        assert m.is_controllable()


# =====================================================================
# get_size
# =====================================================================


class TestGetSize:
    def test_returns_tuple(self, menu_full):
        size = menu_full.get_size()
        assert isinstance(size, tuple)
        assert len(size) == 2
        assert size[1] == PowerProfileMenu.MAX_TITLE_LEN


# =====================================================================
# Apply governor
# =====================================================================


class TestApplyGovernor:
    def test_apply_governor_writes_all_cores(self, menu_full):
        # Select "performance"
        for rb in menu_full.governor_group:
            rb.set_state(rb.label == "performance", do_callback=False)

        with (
            patch("s_tui.power_profile_menu._write_all_cores") as mock_write,
            patch("s_tui.power_profile_menu._set_epp_via_powerprofilesctl"),
        ):
            menu_full.on_apply(None)

        mock_write.assert_any_call(
            "/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor", "performance"
        )

    def test_apply_governor_error_shows_status(self, menu_full):
        for rb in menu_full.governor_group:
            rb.set_state(rb.label == "performance", do_callback=False)

        with patch(
            "s_tui.power_profile_menu._write_all_cores",
            side_effect=OSError("permission denied"),
        ):
            menu_full.on_apply(None)

        status = menu_full.status_text.get_text()[0]
        assert "permission denied" in status
        # return_fn should NOT be called on error
        menu_full.return_fn.assert_not_called()


# =====================================================================
# Apply EPP
# =====================================================================


class TestApplyEpp:
    def test_apply_epp_via_powerprofilesctl(self, menu_full):
        """EPP values with a mapping should use powerprofilesctl."""
        for rb in menu_full.epp_group:
            rb.set_state(rb.label == "balance_performance", do_callback=False)

        with (
            patch("s_tui.power_profile_menu._write_all_cores"),
            patch(
                "s_tui.power_profile_menu._set_epp_via_powerprofilesctl"
            ) as mock_pctl,
        ):
            menu_full.on_apply(None)

        mock_pctl.assert_called_once_with(
            "/usr/bin/powerprofilesctl", "balance_performance"
        )

    def test_apply_epp_unmapped_falls_to_sysfs(self):
        """EPP values without powerprofilesctl mapping fall back to sysfs."""
        with patch(
            "s_tui.power_profile_menu._read_current", return_value="balance_power"
        ):
            m = PowerProfileMenu(
                return_fn=MagicMock(),
                powerprofilesctl_exe="/usr/bin/powerprofilesctl",
                can_write_governor=False,
                can_write_epp=True,
                available_governors=["powersave"],
                available_epp=EPP_VALUES,
            )

        for rb in m.epp_group:
            rb.set_state(rb.label == "balance_power", do_callback=False)

        with (
            patch(
                "s_tui.power_profile_menu._set_epp_via_powerprofilesctl",
            ) as mock_pctl,
            patch("s_tui.power_profile_menu._write_all_cores") as mock_sysfs,
        ):
            m.on_apply(None)

        mock_pctl.assert_not_called()
        mock_sysfs.assert_any_call(
            "/sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference",
            "balance_power",
        )

    def test_apply_epp_no_method_shows_error(self, menu_epp_only):
        """If powerprofilesctl fails on unmapped value and no sysfs write, show error."""
        for rb in menu_epp_only.epp_group:
            rb.set_state(rb.label == "default", do_callback=False)

        menu_epp_only.on_apply(None)
        status = menu_epp_only.status_text.get_text()[0]
        assert "EPP" in status

    def test_apply_epp_powerprofilesctl_busy_falls_back_to_sysfs(self):
        """When powerprofilesctl returns 'busy', fall back to sysfs if writable."""
        with patch(
            "s_tui.power_profile_menu._read_current", return_value="performance"
        ):
            m = PowerProfileMenu(
                return_fn=MagicMock(),
                powerprofilesctl_exe="/usr/bin/powerprofilesctl",
                can_write_governor=True,
                can_write_epp=True,
                available_governors=GOVERNORS,
                available_epp=EPP_VALUES,
            )

        for rb in m.epp_group:
            rb.set_state(rb.label == "performance", do_callback=False)

        with (
            patch(
                "s_tui.power_profile_menu._set_epp_via_powerprofilesctl",
                side_effect=OSError("Device busy"),
            ),
            patch("s_tui.power_profile_menu._write_all_cores") as mock_sysfs,
        ):
            m.on_apply(None)

        mock_sysfs.assert_any_call(
            "/sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference",
            "performance",
        )
        assert m.return_fn.call_count == 1  # type: ignore[union-attr]

    def test_apply_epp_busy_no_sysfs_shows_short_error(self, menu_epp_only):
        """When powerprofilesctl returns 'busy' and no sysfs, show a short error."""
        for rb in menu_epp_only.epp_group:
            rb.set_state(rb.label == "power", do_callback=False)

        with patch(
            "s_tui.power_profile_menu._set_epp_via_powerprofilesctl",
            side_effect=OSError("Cannot change EPP (governor: performance)"),
        ):
            menu_epp_only.on_apply(None)

        status = menu_epp_only.status_text.get_text()[0]
        assert "Cannot change EPP" in status
        menu_epp_only.return_fn.assert_not_called()


# =====================================================================
# Cancel
# =====================================================================


class TestCancel:
    def test_cancel_calls_return_fn(self, menu_full):
        with patch.object(menu_full, "refresh_state"):
            menu_full.on_cancel(None)
        menu_full.return_fn.assert_called_once()

    def test_cancel_refreshes_state(self, menu_full):
        with patch.object(menu_full, "refresh_state") as mock_refresh:
            menu_full.on_cancel(None)
        mock_refresh.assert_called_once()


# =====================================================================
# refresh_state
# =====================================================================


class TestRefreshState:
    def test_refresh_updates_radio_buttons(self, menu_full):
        with patch(
            "s_tui.power_profile_menu._read_current", return_value="performance"
        ):
            menu_full.refresh_state()

        for rb in menu_full.governor_group:
            if rb.label == "performance":
                assert rb.state is True
            else:
                assert rb.state is False

    def test_refresh_clears_status(self, menu_full):
        menu_full.status_text.set_text("some error")
        with patch("s_tui.power_profile_menu._read_current", return_value="powersave"):
            menu_full.refresh_state()
        assert menu_full.status_text.get_text()[0] == ""


# =====================================================================
# Helper functions
# =====================================================================


class TestHelpers:
    def test_read_available_success(self):
        with patch(
            "s_tui.power_profile_menu.cat",
            return_value="performance powersave",
        ):
            result = read_available("/some/path")
        assert result == ["performance", "powersave"]

    def test_read_available_oserror(self):
        with patch("s_tui.power_profile_menu.cat", side_effect=OSError("no file")):
            result = read_available("/some/path")
        assert result == []

    def test_read_current_success(self):
        with patch("s_tui.power_profile_menu.cat", return_value="powersave"):
            assert _read_current("/some/path") == "powersave"

    def test_read_current_oserror(self):
        with patch("s_tui.power_profile_menu.cat", side_effect=OSError("no file")):
            assert _read_current("/some/path") == ""

    def test_write_all_cores_success(self, tmp_path):
        # Create fake sysfs files
        for i in range(4):
            p = tmp_path / f"cpu{i}"
            p.mkdir()
            (p / "scaling_governor").write_text("powersave")

        _write_all_cores(str(tmp_path / "cpu*/scaling_governor"), "performance")

        for i in range(4):
            assert (
                tmp_path / f"cpu{i}" / "scaling_governor"
            ).read_text() == "performance"

    def test_write_all_cores_no_paths(self):
        with pytest.raises(OSError, match="No sysfs paths found"):
            _write_all_cores("/nonexistent/path/cpu*/gov", "performance")

    def test_write_all_cores_busy_gives_short_error(self, tmp_path):
        """When all cores fail with 'busy', produce a short error message."""
        for i in range(2):
            p = tmp_path / f"cpu{i}"
            p.mkdir()
            f = p / "epp"
            f.write_text("balance_performance")
            f.chmod(0o444)  # read-only to trigger write error

        with pytest.raises(OSError, match=r"(?i)busy|permission"):
            _write_all_cores(str(tmp_path / "cpu*/epp"), "performance")

    def test_set_epp_via_powerprofilesctl_busy(self):
        """Device busy stderr produces a clean short error with governor info."""
        with (
            patch("s_tui.power_profile_menu.subprocess.run") as mock_run,
            patch("s_tui.power_profile_menu._read_current", return_value="performance"),
        ):
            mock_run.return_value = MagicMock(
                returncode=1,
                stderr="Device or resource busy",
            )
            with pytest.raises(
                OSError, match=r"Cannot change EPP.*governor.*performance"
            ):
                _set_epp_via_powerprofilesctl("/usr/bin/powerprofilesctl", "power")

    def test_set_epp_via_powerprofilesctl_success(self):
        with patch("s_tui.power_profile_menu.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            _set_epp_via_powerprofilesctl("/usr/bin/powerprofilesctl", "performance")
        mock_run.assert_called_once_with(
            ["/usr/bin/powerprofilesctl", "set", "performance"],
            capture_output=True,
            text=True,
            timeout=5,
        )

    def test_set_epp_via_powerprofilesctl_unmapped(self):
        with pytest.raises(OSError, match="No powerprofilesctl mapping"):
            _set_epp_via_powerprofilesctl("/usr/bin/powerprofilesctl", "default")

    def test_set_epp_via_powerprofilesctl_failure(self):
        with patch("s_tui.power_profile_menu.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="access denied")
            with pytest.raises(OSError, match="failed"):
                _set_epp_via_powerprofilesctl("/usr/bin/powerprofilesctl", "power")

    def test_epp_to_profile_mapping(self):
        assert _EPP_TO_PROFILE["performance"] == "performance"
        assert _EPP_TO_PROFILE["balance_performance"] == "balanced"
        assert _EPP_TO_PROFILE["power"] == "power-saver"
        assert "default" not in _EPP_TO_PROFILE
        assert "balance_power" not in _EPP_TO_PROFILE
