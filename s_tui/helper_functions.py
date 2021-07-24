#!/usr/bin/env python
#
# Copyright (C) 2017-2020 Alex Manuskin, Gil Tsuker
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
""" Helper functions module with common useful functions """


import os
import logging
import platform
import subprocess
import re
import csv
import sys
import json
import time

from collections import OrderedDict

__version__ = "1.1.3"

_DEFAULT = object()
PY3 = sys.version_info[0] == 3
POSIX = os.name == "posix"
ENCODING = sys.getfilesystemencoding()
if not PY3:
    ENCODING_ERRS = "replace"
else:
    try:
        ENCODING_ERRS = sys.getfilesystemencodeerrors()  # py 3.6
    except AttributeError:
        ENCODING_ERRS = "surrogateescape" if POSIX else "replace"


def get_processor_name():
    """ Returns the processor name in the system """
    if platform.system() == "Linux":
        with open("/proc/cpuinfo", "rb") as cpuinfo:
            all_info = cpuinfo.readlines()
            for line in all_info:
                if b'model name' in line:
                    return re.sub(b'.*model name.*:', b'', line, 1)
    elif platform.system() == "FreeBSD":
        cmd = ["sysctl", "-n", "hw.model"]
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        str_value = process.stdout.read()
        return str_value
    elif platform.system() == "Darwin":
        cmd = ['sysctl', '-n', 'machdep.cpu.brand_string']
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        str_value = process.stdout.read()
        return str_value

    return platform.processor()


def kill_child_processes(parent_proc):
    """ Kills a process and all its children """
    logging.debug("Killing stress process")
    try:
        for proc in parent_proc.children(recursive=True):
            logging.debug('Killing %s', proc)
            proc.kill()
        parent_proc.kill()
    except AttributeError:
        logging.debug('No such process')
        logging.debug('Could not kill process')


def output_to_csv(sources, csv_writeable_file):
    """Print statistics to csv file"""
    file_exists = os.path.isfile(csv_writeable_file)

    with open(csv_writeable_file, 'a') as csvfile:
        csv_dict = OrderedDict()
        csv_dict.update({'Time': time.strftime("%Y-%m-%d_%H:%M:%S")})
        summaries = [val for key, val in sources.items()]
        for summarie in summaries:
            update_dict = dict()
            for prob, val in summarie.source.get_sensors_summary().items():
                prob = summarie.source.get_source_name() + ":" + prob
                update_dict[prob] = val
            csv_dict.update(update_dict)

        fieldnames = [key for key, val in csv_dict.items()]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()  # file doesn't exist yet, write a header
        writer.writerow(csv_dict)


def output_to_terminal(sources):
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


def output_to_json(sources):
    """Print statistics to the terminal in Json format"""
    results = OrderedDict()
    for source in sources:
        if source.get_is_available():
            source.update()
            source_name = source.get_source_name()
            results[source_name] = source.get_sensors_summary()
    print(json.dumps(results, indent=4))
    sys.exit()


def get_user_config_dir():
    """
    Return the path to the user s-tui config directory
    """
    user_home = os.getenv('XDG_CONFIG_HOME')
    if user_home is None or not user_home:
        config_path = os.path.expanduser(os.path.join('~', '.config', 's-tui'))
    else:
        config_path = os.path.join(user_home, 's-tui')

    return config_path


def get_config_dir():
    """
    Return the path to the user home config directory
    """
    user_home = os.getenv('XDG_CONFIG_HOME')
    if user_home is None or not user_home:
        config_path = os.path.expanduser(os.path.join('~', '.config'))
    else:
        config_path = user_home

    return config_path


def get_user_config_file():
    """
    Return the path to the user s-tui config directory
    """
    user_home = os.getenv('XDG_CONFIG_HOME')
    if user_home is None or not user_home:
        config_path = os.path.expanduser(os.path.join('~', '.config',
                                                      's-tui', 's-tui.conf'))
    else:
        config_path = os.path.join(user_home, 's-tui', 's-tui.conf')

    return config_path


def user_config_dir_exists():
    """
    Check whether the user s-tui config dir exists or not
    """
    return os.path.isdir(get_user_config_dir())


def config_dir_exists():
    """
    Check whether the home config dir exists or not
    """
    return os.path.isdir(get_config_dir())


def user_config_file_exists():
    """
    Check whether the user s-tui config file exists or not
    """
    return os.path.isfile(get_user_config_file())


def make_user_config_dir():
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
            os.mkdir(os.path.join(config_path, 'hooks.d'))
        except OSError:
            return None

    return config_path


def seconds_to_text(secs):
    """ Converts seconds to a string of hours:minutes:seconds """
    hours = (secs)//3600
    minutes = (secs - hours*3600)//60
    seconds = secs - hours*3600 - minutes*60
    return "%02d:%02d:%02d" % (hours, minutes, seconds)


def str_to_bool(string):
    """ Converts a string to a boolean """
    if string == 'True':
        return True
    if string == 'False':
        return False
    raise ValueError


def which(program):
    """ Find the path of an executable """
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


def _open_binary(fname, **kwargs):
    return open(fname, "rb", **kwargs)


def _open_text(fname, **kwargs):
    """On Python 3 opens a file in text mode by using fs encoding and
    a proper en/decoding errors handler.
    On Python 2 this is just an alias for open(name, 'rt').
    """
    if PY3:
        kwargs.setdefault('encoding', ENCODING)
        kwargs.setdefault('errors', ENCODING_ERRS)
    return open(fname, "rt", **kwargs)


def cat(fname, fallback=_DEFAULT, binary=True):
    """Return file content.
    fallback: the value returned in case the file does not exist or
              cannot be read
    binary: whether to open the file in binary or text mode.
    """
    try:
        with _open_binary(fname) if binary else _open_text(fname) as f_d:
            return f_d.read().strip()
    except (IOError, OSError):
        if fallback is not _DEFAULT:
            return fallback
        raise
