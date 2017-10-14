#!/usr/bin/env python
#
# Copyright (C) 2017 Alex Manuskin, Gil Tsuker
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

import subprocess
from s_tui.Sources.Hook import Hook

class ScriptHook:
    """Runs an arbitrary shell script stored in the filesystem when invoked
    """

    def __init__(self, path, timeout = 0):
        self.path = path
        self.hook = self._make_script_hook(path, timeout)

    def is_ready(self):
        return self.hook.is_ready()

    def invoke(self):
        self.hook.invoke()

    def _run_script(self, *args):
        # Run script in a shell subprocess asynchronously so as to not block main thread (graphs)
        # if the script is a long-running task
        subprocess.Popen(
                [ "sh", args[0][0] ],
                # TODO -- Could redirect this to a separate log file but not a priority just now
                # Silence hook scripts so that they don't interfere with the application's tui
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
        )

    def _make_script_hook(self, path, timeout):
        return Hook(self._run_script, timeout, path)
