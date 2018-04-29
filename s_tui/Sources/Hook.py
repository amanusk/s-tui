#!/usr/bin/env python
#
# Copyright (C) 2017-2018 Alex Manuskin, Gil Tsuker
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

from datetime import datetime, timedelta


class Hook:
    """
    Event handler that invokes an arbitrary callback when invoked.
    If the timeoutMilliseconds argument is greater than 0,
    the hook will be suspended for n milliseconds after it's being invoked.
    """

    def __init__(self, callback, timeoutMilliseconds=0, *callback_args):
        self.callback = callback
        self.callback_args = callback_args
        self.timeoutMilliseconds = timeoutMilliseconds
        self.ready_time = datetime.now()

    def is_ready(self):
        """
        Returns whether the hook is ready to invoke its callback or not
        """

        return datetime.now() >= self.ready_time

    def invoke(self):
        """
        Run callback, optionally passing a variable number
        of arguments `callback_args`
        """

        # Don't sleep a hook if it has never run
        if (self.timeoutMilliseconds > 0):
            self.ready_time = self._get_ready_time(self.timeoutMilliseconds)

        self._run(self.callback_args)

    def _get_ready_time(self, timeoutMilliseconds):
        return datetime.now() + timedelta(milliseconds=timeoutMilliseconds)

    def _run(self, *args):
        self.callback(*args)
