#!/usr/bin/python
#
# Urwid graphics example program
#    Copyright (C) 2004-2011  Ian Ward
#
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 2.1 of the License, or (at your option) any later version.
#
#    This library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with this library; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Urwid web site: http://excess.org/urwid/

"""
Urwid example demonstrating use of the BarGraph widget and creating a
floating-window appearance.  Also shows use of alarms to create timed
animation.
"""
from __future__ import print_function

import urwid
from ComplexBarGraphs import ScalableBarGraph
from ComplexBarGraphs import LabeledBarGraph

import psutil
import time
import subprocess

UPDATE_INTERVAL = 1
DEGREE_SIGN = u'\N{DEGREE SIGN}'


class GraphMode:
    """
    A class responsible for storing the data related to 
    the current mode of operation
    """

    data_max_value = 100

    def __init__(self):
        self.modes = [
            'Regular Operation',
            'Stress Operation',
            ]
        self.data = {}

        self.current_mode = self.modes[0]
        self.stress_process = None

    def get_modes(self):
        return self.modes

    def set_mode(self, m):
        if m == 'Regular Operation':
            pass  # TODO stop stress
        elif m == 'Stress Operation':
            pass  # TODO open stress options (new window?)

        self.current_mode = m
        # Start stress here?
        if m == 'Stress Operation':
            self.stress_process = subprocess.Popen(['stress', '-c', '4'], shell=False)
            self.stress_process = psutil.Process(self.stress_process.pid)
        else:
            try:
                # Kill all the subprocess of stress
                for proc in self.stress_process.children(recursive=True):
                    proc.kill()
            except:
                print('Could not kill process')
        return True


class GraphData:
    def __init__(self, graph_num_bars):
        self.graph_num_bars = graph_num_bars
        self.cpu_util = [0] * graph_num_bars
        self.cpu_temp = [0] * graph_num_bars
        self.max_temp = 0
        self.cur_temp = 0

    def update_util(self):
        last_value = psutil.cpu_percent(interval=None)
        self.cpu_util = self.update_graph_val(self.cpu_util, last_value)

    def update_temp(self):
        # TODO make this more robust
        # TODO change color according to last recorded temp
        last_value = psutil.sensors_temperatures()['acpitz'][0].current
        self.cpu_temp = self.update_graph_val(self.cpu_temp, last_value)
        # Update max temp
        if last_value > int(self.max_temp):
            self.max_temp = last_value
        # Update currnt temp
        self.cur_temp = last_value

    def update_graph_val(self, values, new_val):
        values_num = len(values)

        if values_num > self.graph_num_bars:
            values = values[values_num - self.graph_num_bars - 1:]
        elif values_num < self.graph_num_bars:
            zero_pad = [0] * (self.graph_num_bars - values_num)
            values = zero_pad + values

        values.append(new_val)
        return values[1:]


class GraphView(urwid.WidgetWrap):
    """
    A class responsible for providing the application's interface and
    graph display.
    """

    palette = [
        ('body',          'black',      'light gray',   'standout'),
        ('header',        'white',      'dark red',     'bold'),
        ('screen edge',   'light blue', 'dark cyan'),
        ('main shadow',   'dark gray',  'black'),
        ('line',          'black',      'light gray',   'standout'),
        ('bg background', 'light gray', 'black'),
        ('bg 1',          'black',      'dark green',   'standout'),
        ('bg 1 smooth',   'dark blue',  'black'),
        ('bg 2',          'dark red',    'light green', 'standout'),
        ('bg 2 smooth',   'dark cyan',  'black'),
        ('bg 3', 'light red', 'dark red', 'standout'),
        ('bg 4', 'dark red', 'light red', 'standout'),
        ('button normal', 'light gray', 'dark blue',    'standout'),
        ('button select', 'white',      'dark green'),
        ('line',          'black',      'light gray',   'standout'),
        ('pg normal',     'white',      'black',        'standout'),
        ('pg complete',   'white',      'dark magenta'),
        ('pg smooth',     'dark magenta', 'black')
        ]

    graph_samples_per_bar = 10
    graph_offset_per_second = 5

    def __init__(self, controller):

        self.controller = controller
        self.started = True
        self.start_time = None
        self.offset = 0
        self.last_offset = None
        self.graph_data = GraphData(0)
        self.mode_buttons = []
        self.animate_button = []
        self.graph_util = []
        self.graph_temp = []
        self.max_temp = None
        self.cur_temp = None
        self.animate_progress = []
        self.animate_progress_wrap = []

        urwid.WidgetWrap.__init__(self, self.main_window())

    def get_offset_now(self):
        if self.start_time is None:
            return 0
        if not self.started:
            return self.offset
        tdelta = time.time() - self.start_time
        return int(self.offset + (tdelta*self.graph_offset_per_second))

    def update_stats(self):
        self.max_temp.set_text(str(self.graph_data.max_temp) + DEGREE_SIGN + 'c')
        self.cur_temp.set_text(str(self.graph_data.cur_temp) + DEGREE_SIGN + 'c')

    def update_graph(self, force_update=False):

        self.graph_data.graph_num_bars = self.graph_util.bar_graph.get_size()[1]

        o = self.get_offset_now()
        if o == self.last_offset and not force_update:
            return False
        self.last_offset = o
        # gspb = self.graph_samples_per_bar
        # r = gspb * self.graph_data.graph_num_bars

        # TODO set maximum value dynamically and per graph
        max_value = 100
        l = []

        self.graph_data.update_temp()
        self.graph_data.update_util()

        # Updating CPU utilization
        for n in range(self.graph_data.graph_num_bars):
            value = self.graph_data.cpu_util[n]
            # toggle between two bar types
            if n & 1:
                l.append([0, value])
            else:
                l.append([value, 0])
        self.graph_util.bar_graph.set_data(l, max_value)

        # Updating CPU temperature
        l = []
        for n in range(self.graph_data.graph_num_bars):
            value = self.graph_data.cpu_temp[n]
            # toggle between two bar types
            if n & 1:
                l.append([0, value])
            else:
                l.append([value, 0])
        self.graph_temp.bar_graph.set_data(l, max_value)

        self.update_stats()

    def on_animate_button(self, button):
        """Toggle started state and button text."""
        if self.started:  # stop animation
            button.set_label("Start")
            self.offset = self.get_offset_now()
            self.started = False
            self.controller.stop_animation()
        else:
            button.set_label("Stop")
            self.started = True
            self.start_time = time.time()
            self.controller.animate_graph()

    def on_reset_button(self, w):
        self.offset = 0
        self.start_time = time.time()
        self.update_graph(True)

    def on_mode_button(self, button, state):
        """Notify the controller of a new mode setting."""
        if state:
            # The new mode is the label of the button
            self.controller.set_mode(button.get_label())

        self.last_offset = None

    def on_mode_change(self, m):
        """Handle external mode change by updating radio buttons."""
        for rb in self.mode_buttons:
            if rb.get_label() == m:
                rb.set_state(True, do_callback=False)
                break
        self.last_offset = None

    # TODO is this needed?
    def on_unicode_checkbox(self, w, state):
        self.graph_util = self.bar_graph('bg 1 smooth', 'bg 2 smooth', state)
        self.update_graph(True)

    def main_shadow(self, w):
        """Wrap a shadow and background around widget w."""
        bg = urwid.AttrWrap(urwid.SolidFill(u"\u2592"), 'screen edge')
        shadow = urwid.AttrWrap(urwid.SolidFill(u" "), 'main shadow')

        bg = urwid.Overlay(shadow, bg,
                           ('fixed left', 3), ('fixed right', 1),
                           ('fixed top', 2), ('fixed bottom', 1))
        w = urwid.Overlay(w, bg,
                          ('fixed left', 2), ('fixed right', 3),
                          ('fixed top', 1), ('fixed bottom', 2))
        return w

    def bar_graph(self, color_a, color_b, title, x_label, y_label, smooth=False):
        satt = None
        if smooth:
            satt = {(1, 0): 'bg 1 smooth', (2, 0): 'bg 2 smooth'}
        w = ScalableBarGraph(['bg background', color_a, color_b], satt=satt)
        bg = LabeledBarGraph([w, x_label, y_label, title])

        return bg

    def button(self, t, fn):
        w = urwid.Button(t, fn)
        w = urwid.AttrWrap(w, 'button normal', 'button select')
        return w

    def radio_button(self, g, l, fn):
        w = urwid.RadioButton(g, l, False, on_state_change=fn)
        w = urwid.AttrWrap(w, 'button normal', 'button select')
        return w

    def progress_bar(self, smooth=False):
        if smooth:
            return urwid.ProgressBar('pg normal', 'pg complete',
                                     0, 1, 'pg smooth')
        else:
            return urwid.ProgressBar('pg normal', 'pg complete',
                                     0, 1)

    def exit_program(self, w):
        raise urwid.ExitMainLoop()

    def graph_controls(self):
        modes = self.controller.get_modes()
        # setup mode radio buttons
        group = []
        for m in modes:
            rb = self.radio_button(group, m, self.on_mode_button)
            self.mode_buttons.append(rb)
        # setup animate button
        self.animate_button = self.button("", self.on_animate_button)
        self.on_animate_button(self.animate_button)
        self.offset = 0
        self.animate_progress = self.progress_bar()
        animate_controls = urwid.GridFlow([
            self.animate_button,
            self.button("Reset", self.on_reset_button),
        ], 9, 2, 0, 'center')

        if urwid.get_encoding_mode() == "utf8":
            unicode_checkbox = urwid.CheckBox(
                "Enable Unicode Graphics",
                on_state_change=self.on_unicode_checkbox)
        else:
            unicode_checkbox = urwid.Text(
                "UTF-8 encoding not detected")

        buttons = [urwid.Text("Mode", align="center"),
             ] + self.mode_buttons + [
            urwid.Divider(),
            urwid.Text("Animation", align="center"),
            animate_controls,
            urwid.Divider(),
            urwid.LineBox(unicode_checkbox),
            urwid.Divider(),
            self.button("Quit", self.exit_program),
            ]
        # w = urwid.ListBox(urwid.SimpleListWalker(buttons))
        return buttons

    def graph_stats(self):
        fixed_stats = [urwid.Divider(), urwid.Text("Max Temp", align="left"),
                       self.max_temp] + \
                      [urwid.Divider(), urwid.Text("Current Temp", align="left"),
                       self.cur_temp]
        return fixed_stats

    def main_window(self):
        # Initiating the data
        self.graph_util = self.bar_graph('bg 1', 'bg 2', 'util[%]', [], [0, 50, 100])
        self.graph_temp = self.bar_graph('bg 3', 'bg 4', 'temp[C]', [], [0, 25, 50, 75, 100])
        self.max_temp = urwid.Text(str(self.graph_data.max_temp) + DEGREE_SIGN + 'c', align="right")
        self.cur_temp = urwid.Text(str(self.graph_data.cur_temp) + DEGREE_SIGN + 'c', align="right")

        self.graph_data.graph_num_bars = self.graph_util.bar_graph.get_size()[1]

        # TODO: Optional if graph could be stretched
        self.graph_util.bar_graph.set_bar_width(1)
        self.graph_temp.bar_graph.set_bar_width(1)
        vline = urwid.AttrWrap(urwid.SolidFill(u'\u2502'), 'line')
        hline = urwid.AttrWrap(urwid.SolidFill(u'\N{LOWER ONE QUARTER BLOCK}'), 'line')

        graph_controls = self.graph_controls()
        graph_stats = self.graph_stats()
        text_col = urwid.ListBox(urwid.SimpleListWalker(graph_controls + [urwid.Divider()] + graph_stats))
        l = [('weight', 2, self.graph_util),
             ('fixed',  1, hline),
             ('weight', 2, self.graph_temp)]

        r = urwid.Pile(l, focus_item=None)

        w = urwid.Columns([('weight', 2, r),
                           ('fixed',  1, vline),
                           ('fixed',  20, text_col)],
                          dividechars=1, focus_column=2)
        w = urwid.Padding(w, ('fixed left', 1), ('fixed right', 0))
        w = urwid.AttrWrap(w, 'body')
        w = urwid.LineBox(w)
        w = urwid.AttrWrap(w, 'line')
        w = self.main_shadow(w)
        return w


class GraphController:
    """
    A class responsible for setting up the model and view and running
    the application.
    """
    def __init__(self):
        self.loop = []
        self.animate_alarm = None
        self.mode = GraphMode()
        self.view = GraphView(self)
        # use the first mode as the default
        mode = self.get_modes()[0]
        self.mode.set_mode(mode)
        # update the view
        self.view.on_mode_change(mode)
        self.view.update_graph(True)

    def get_modes(self):
        """Allow our view access to the list of modes."""
        return self.mode.get_modes()

    def set_mode(self, m):
        """Allow our view to set the mode."""
        rval = self.mode.set_mode(m)
        self.view.update_graph(True)
        return rval

    # def get_data(self, offset, range):
    #     """Provide data to our view for the graph."""
    #     return self.model.get_data(offset, range)

    def main(self):
        self.loop = urwid.MainLoop(self.view, self.view.palette)

        self.view.started = False  # simulate pressing to start button
        self.view.on_animate_button(self.view.animate_button)

        self.loop.run()

    def animate_graph(self, loop=None, user_data=None):
        """update the graph and schedule the next update"""
        self.view.update_graph()
        self.animate_alarm = self.loop.set_alarm_in(
            UPDATE_INTERVAL, self.animate_graph)

    def stop_animation(self):
        """stop animating the graph"""
        if self.animate_alarm:
            self.loop.remove_alarm(self.animate_alarm)
        self.animate_alarm = None


def main():
    GraphController().main()

if '__main__' == __name__:
    main()
