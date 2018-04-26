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


class Source:
    def __init__(self):
        self.edge_hooks = []

    def get_reading(self):
        raise NotImplementedError("Get reading is not implemented")

    def update(self):
        self.eval_hooks()

    def get_maximum(self):
        raise NotImplementedError("Get maximum is not implemented")

    def get_is_available(self):
        raise NotImplementedError("Get is available is not implemented")

    def reset(self):
        raise NotImplementedError("Reset max information")

    def get_summary(self):
        raise NotImplementedError("Get summary is not implemented")

    def get_source_name(self):
        raise NotImplementedError("Get source name is not implemented")

    def get_edge_triggered(self):
        raise NotImplementedError("Get Edge triggered not implemented")

    def get_max_triggered(self):
        raise NotImplementedError("Get Edge triggered not implemented")

    def get_measurement_unit(self):
        raise NotImplementedError("Get measurement unit is not implemented")

    def add_edge_hook(self, hook):
        """
        Add hook to be triggered when the threshold of this Source is surpassed
        """
        if hook is None:
            return

        self.edge_hooks.append(hook)

    def eval_hooks(self):
        """
        Evaluate the current state of this Source and
        invoke any attached hooks if they've been triggered
        """
        if self.get_edge_triggered():
            for hook in [h for h in self.edge_hooks if h.is_ready()]:
                hook.invoke()


class MockSource(Source):
    """
    Mock class for testing
    """
    def get_reading(self):
        return 5

    def get_maximum(self):
        return 20

    def get_is_available(self):
        return True

    def get_summary(self):
        return {'MockValue': 5, 'Tahat': 34}

    def get_source_name(self):
        return 'Mock Source'

    def get_measurement_unit(self):
        return 'K'
