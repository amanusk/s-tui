#!/usr/bin/env python

# Copyright (C) 2017-2018 Alex Manuskin, Maor Veitsman
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
""" This module reads intel power measurements"""

from __future__ import absolute_import

import time
import glob
import os
import sys
from collections import namedtuple

import logging
LOGGER = logging.getLogger(__name__)

INTER_RAPL_DIR = '/sys/class/powercap/intel-rapl/'
MICRO_JOULE_IN_JOULE = 1000000.0
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

RaplStats = namedtuple('rapl', ['label', 'current', 'max'])


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


def rapl_read():
    """ Read power stats and return dictionary"""
    basenames = glob.glob('/sys/class/powercap/intel-rapl:*/')
    basenames = sorted(set({x for x in basenames}))

    pjoin = os.path.join
    ret = list()
    for path in basenames:
        name = None
        try:
            name = cat(pjoin(path, 'name'), fallback=None, binary=False)
        except (IOError, OSError, ValueError) as err:
            logging.warning("ignoring %r for file %r",
                            (err, path), RuntimeWarning)
            continue
        if name:
            try:
                current = cat(pjoin(path, 'energy_uj'))
                max_reading = 0.0
                ret.append(RaplStats(name, float(current), max_reading))
            except (IOError, OSError, ValueError) as err:
                logging.warning("ignoring %r for file %r",
                                (err, path), RuntimeWarning)
    return ret


if __name__ == '__main__':
    while True:
        RESULT = rapl_read()
        print(RESULT)
        time.sleep(2)
