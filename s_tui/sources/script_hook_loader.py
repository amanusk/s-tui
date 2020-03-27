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

import os
from s_tui.sources.hook_script import ScriptHook


class ScriptHookLoader:
    """
    Loads shell scripts from a directory into ScriptHooks for a given Source
    """

    def __init__(self, dir_path):
        self.scripts_dir_path = os.path.join(dir_path, 'hooks.d')

    def load_script(self, source_name, timeoutMilliseconds=0):
        """
        Return ScriptHook for source_name Source and with a ready timeout
        of timeoutMilliseconds
        """

        script_path = os.path.join(self.scripts_dir_path,
                                   self._source_to_script_name(source_name))

        if os.path.isfile(script_path):
            return ScriptHook(script_path, timeoutMilliseconds)
        return None

    def _source_to_script_name(self, source_name):
        return source_name.lower() + '.sh'
