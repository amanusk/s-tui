#!/usr/bin/env python
#
# Copyright (C) 2017-2025 Alex Manuskin, Gil Tsuker
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA
"""Helper functions module with common useful functions"""

from __future__ import annotations

import contextlib
import csv
import json
import logging
import os
import platform
import re
import signal
import subprocess
import sys
import time
from typing import IO, TYPE_CHECKING, Any, Literal, overload

if TYPE_CHECKING:
    import psutil

from collections import OrderedDict

__version__ = "1.3.0"

_DEFAULT = object()
POSIX = os.name == "posix"
ENCODING = sys.getfilesystemencoding()
try:
    ENCODING_ERRS = sys.getfilesystemencodeerrors()
except AttributeError:
    ENCODING_ERRS = "surrogateescape" if POSIX else "replace"


def get_processor_name() -> str:
    """Returns the processor name in the system"""
    if platform.system() == "Linux":
        with open("/proc/cpuinfo") as cpuinfo:
            for line in cpuinfo:
                if "model name" in line:
                    return re.sub(r".*model name.*:", "", line, count=1)
    elif platform.system() == "FreeBSD":
        return subprocess.check_output(["sysctl", "-n", "hw.model"], text=True).strip()
    elif platform.system() == "Darwin":
        return subprocess.check_output(
            ["sysctl", "-n", "machdep.cpu.brand_string"], text=True
        ).strip()

    return platform.processor()


def kill_child_processes(parent_proc: psutil.Process | None, timeout: int = 3) -> None:
    """Kills a process and all its children gracefully.

    Attempts SIGTERM via process group first, falls back to per-process
    terminate, then SIGKILL after timeout.
    """
    import psutil

    if parent_proc is None:
        logging.debug("No stress process to kill")
        return

    logging.debug("Killing stress process %s", parent_proc)

    # Try process-group SIGTERM first (covers the whole tree)
    try:
        pgid = os.getpgid(parent_proc.pid)
        os.killpg(pgid, signal.SIGTERM)
        logging.debug("Sent SIGTERM to process group %s", pgid)
    except (OSError, ProcessLookupError, AttributeError):
        # Process group kill failed — fall back to per-process terminate
        logging.debug("Process group kill failed, falling back to per-process")
        try:
            for proc in parent_proc.children(recursive=True):
                with contextlib.suppress(psutil.NoSuchProcess, ProcessLookupError):
                    proc.terminate()
            parent_proc.terminate()
        except (psutil.NoSuchProcess, AttributeError):
            logging.debug("Process already gone during terminate")
            return

    # Wait for graceful exit, then SIGKILL stragglers
    try:
        _, alive = psutil.wait_procs(
            [parent_proc, *parent_proc.children(recursive=True)],
            timeout=timeout,
        )
        for proc in alive:
            logging.debug("Sending SIGKILL to straggler %s", proc)
            with contextlib.suppress(psutil.NoSuchProcess, ProcessLookupError):
                proc.kill()
    except (psutil.NoSuchProcess, AttributeError):
        logging.debug("Process already gone during wait")


def output_to_csv(sources: dict, csv_writeable_file: str) -> None:
    """Print statistics to csv file"""
    file_exists = os.path.isfile(csv_writeable_file)

    with open(csv_writeable_file, "a") as csvfile:
        csv_dict = OrderedDict()
        csv_dict.update({"Time": time.strftime("%Y-%m-%d_%H:%M:%S")})
        summaries = [val for key, val in sources.items()]
        for summarie in summaries:
            update_dict = {}
            for prob, val in summarie.source.get_sensors_summary().items():
                prob = summarie.source.get_source_name() + ":" + prob
                update_dict[prob] = val
            csv_dict.update(update_dict)

        fieldnames = [key for key, val in csv_dict.items()]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()  # file doesn't exist yet, write a header
        writer.writerow(csv_dict)


def output_to_terminal(sources: list) -> None:
    """Print statistics to the terminal"""
    results = OrderedDict()
    for source in sources:
        if source.get_is_available():
            source.update()
            source_name = source.get_source_name()
            results[source_name] = source.get_sensors_summary()
    for key, value in results.items():
        sys.stdout.write(str(key) + ": ")
        for skey, svalue in value.items():
            sys.stdout.write(str(skey) + ": " + str(svalue) + ", ")
    sys.stdout.write("\n")
    sys.exit()


def output_to_json(sources: list) -> None:
    """Print statistics to the terminal in Json format"""
    results = OrderedDict()
    for source in sources:
        if source.get_is_available():
            source.update()
            source_name = source.get_source_name()
            results[source_name] = source.get_sensors_summary()
    print(json.dumps(results, indent=4))
    sys.exit()


def _get_xdg_config_home() -> str:
    """Return the XDG config home directory, with fallback to ~/.config"""
    user_home = os.getenv("XDG_CONFIG_HOME")
    if user_home:
        return user_home
    return os.path.expanduser(os.path.join("~", ".config"))


def get_config_dir() -> str:
    """
    Return the path to the user home config directory
    """
    return _get_xdg_config_home()


def get_user_config_dir() -> str:
    """
    Return the path to the user s-tui config directory
    """
    return os.path.join(_get_xdg_config_home(), "s-tui")


def get_user_config_file() -> str:
    """
    Return the path to the user s-tui config file
    """
    return os.path.join(get_user_config_dir(), "s-tui.conf")


def user_config_dir_exists() -> bool:
    """
    Check whether the user s-tui config dir exists or not
    """
    return os.path.isdir(get_user_config_dir())


def config_dir_exists() -> bool:
    """
    Check whether the home config dir exists or not
    """
    return os.path.isdir(get_config_dir())


def user_config_file_exists() -> bool:
    """
    Check whether the user s-tui config file exists or not
    """
    return os.path.isfile(get_user_config_file())


def make_user_config_dir() -> str | None:
    """
    Create the user s-tui config directory if it doesn't exist
    """
    config_dir = get_config_dir()
    config_path = get_user_config_dir()

    if not config_dir_exists():
        try:
            os.mkdir(config_dir)
        except OSError:
            return None

    if not user_config_dir_exists():
        try:
            os.mkdir(config_path)
            os.mkdir(os.path.join(config_path, "hooks.d"))
        except OSError:
            return None

    return config_path


def seconds_to_text(secs: float) -> str:
    """Converts seconds to a string of hours:minutes:seconds"""
    hours = (secs) // 3600
    minutes = (secs - hours * 3600) // 60
    seconds = secs - hours * 3600 - minutes * 60
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"


def str_to_bool(string: str) -> bool:
    """Converts a string to a boolean"""
    if string == "True":
        return True
    if string == "False":
        return False
    raise ValueError


def which(program: str) -> str | None:
    """Find the path of an executable"""

    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, _ = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None


def _open_binary(fname: str, **kwargs: Any) -> IO[bytes]:
    return open(fname, "rb", **kwargs)


def _open_text(fname: str, **kwargs: Any) -> IO[str]:
    """Opens a file in text mode by using fs encoding and
    a proper en/decoding errors handler.
    """
    kwargs.setdefault("encoding", ENCODING)
    kwargs.setdefault("errors", ENCODING_ERRS)
    return open(fname, **kwargs)


@overload
def cat(fname: str, fallback: object = ..., *, binary: Literal[True]) -> bytes: ...
@overload
def cat(fname: str, fallback: object = ..., *, binary: Literal[False]) -> str: ...
@overload
def cat(fname: str, fallback: object = ..., binary: bool = ...) -> bytes | str: ...


def cat(fname, fallback=_DEFAULT, binary=True):
    """Return file content.
    fallback: the value returned in case the file does not exist or
              cannot be read
    binary: whether to open the file in binary or text mode.
    """
    try:
        with _open_binary(fname) if binary else _open_text(fname) as f_d:
            return f_d.read().strip()
    except OSError:
        if fallback is not _DEFAULT:
            return fallback
        raise
