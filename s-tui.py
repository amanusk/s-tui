#!/usr/bin/python

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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

"""An urwid program to stress and monitor you computer"""

from __future__ import print_function

import urwid
from ComplexBarGraphs import ScalableBarGraph
from ComplexBarGraphs import LabeledBarGraph
from StressMenu import StressMenu

import psutil
import time
import subprocess
import ctypes
import os
import argparse
import logging
from aux import readmsr

# Constants
UPDATE_INTERVAL = 1
DEGREE_SIGN = u'\N{DEGREE SIGN}'
FNULL = open(os.devnull, 'w')
TURBO_MSR = 429
WAIT_SAMPLES = 5

log_file = "_s-tui.log"

VERSION = 0.1
VERSION_MESSAGE = " s-tui " + str(VERSION) +\
" - (C) 2017 Alex Manuskin, Gil Tsuker\n\
Relased under GNU GPLv2"

# globals
is_admin = None

INTRO_MESSAGE = "\
********s-tui manual********\n\
-Alex Manuskin      alex.manuskin@gmail.com\n\
-Gil Tsuker         \n\
April 2017\n\
\n\
s-tui is a terminal UI add-on for stress. The software uses stress to run CPU\n\
hogs, while monitoring the CPU usage, temperature and frequency.\n\
The software was conceived with the vision of being able to stress test your\n\
computer without the need for a GUI\n\
\n\
Usage:\n\
* Toggle between stressed and regular operation using the radio buttons.\n\
* If you wish to alternate stress defaults, you can do it in 'stress options\n\
* If your system supports it, you can use the utf8 button to get a smoother graph\n\
* Reset buttons resets the graph and the max statistics\n\
* Use the quit button to quit the software\n\
"

class GraphMode:
    """
    A class responsible for storing the data related to 
    the current mode of operation
    """

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
        self.current_mode = m
        return True


class GraphData:
    def __init__(self, graph_num_bars):
        self.temp_max_value = 100
        self.util_max_value = 100
        self.graph_num_bars = graph_num_bars
        # Data for graphs
        self.cpu_util = [0] * graph_num_bars
        self.cpu_temp = [0] * graph_num_bars
        self.cpu_freq = [0] * graph_num_bars
        # Constants data
        self.max_temp = 0
        self.cur_temp = 0
        self.cur_freq = 0
        self.perf_lost = 0
        self.max_perf_lost = 0
        self.samples_taken = 0

        self.core_num = psutil.cpu_count()
        if is_admin:
            self.top_freq = readmsr(TURBO_MSR, 0)
            if self.top_freq is None:
                self.top_freq = psutil.cpu_freq().max
        else:
            self.top_freq = psutil.cpu_freq().max

    def update_util(self):
        last_value = psutil.cpu_percent(interval=None)
        self.cpu_util = self.update_graph_val(self.cpu_util, last_value)

    def update_freq(self):
        self.samples_taken += 1
        self.cur_freq = int(psutil.cpu_freq().current)

        self.cpu_freq = self.update_graph_val(self.cpu_freq, self.cur_freq)

        if is_admin and self.samples_taken > WAIT_SAMPLES:
            self.perf_lost = int(self.top_freq) - int(self.cur_freq)
            self.perf_lost = round(float(self.perf_lost) / float(self.top_freq) * 100, 1)
            if self.perf_lost > self.max_perf_lost:
                self.max_perf_lost = self.perf_lost
        elif not is_admin:
            self.max_perf_lost = "N/A (no root)"

    def reset(self):
        self.cpu_util = [0] * self.graph_num_bars
        self.cpu_temp = [0] * self.graph_num_bars
        self.cpu_freq = [0] * self.graph_num_bars
        self.max_temp = 0
        self.cur_temp = 0
        self.cur_freq = 0
        self.perf_lost = 0
        self.max_perf_lost = 0
        self.samples_taken = 0

    def update_temp(self):
        # TODO make this more robust
        # TODO change color according to last recorded temp
        last_value = psutil.sensors_temperatures()['acpitz'][0].current
        self.cpu_temp = self.update_graph_val(self.cpu_temp, last_value)
        # Update max temp
        if last_value > int(self.max_temp):
            self.max_temp = last_value
        # Update currnet temp
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


class GraphView(urwid.WidgetPlaceholder):
    """
    A class responsible for providing the application's interface and
    graph display.
    """

    palette = [
        ('body',          'black',      'light gray',   'standout'),
        ('header',        'white',      'dark red',     'bold'),
        ('screen edge',   'light blue', 'brown'),
        ('main shadow',   'dark gray',  'black'),
        ('line',          'black',      'light gray',   'standout'),
        ('menu button',   'light gray', 'black'),
        ('bg background', 'light gray', 'black'),
        ('bg 1',          'black',      'dark green',   'standout'),
        ('bg 1 smooth',   'dark green', 'black'),
        ('bg 2',          'dark red',   'light green',  'standout'),
        ('bg 2 smooth',   'light green','black'),
        ('bg 3',          'light red',  'dark red',     'standout'),
        ('bg 3 smooth',   'dark red',   'black'),
        ('bg 4',          'dark red',   'light red',    'standout'),
        ('bg 4 smooth',   'light red',  'black'),
        ('bg 5',          'black',      'dark cyan', 'standout'),
        ('bg 5 smooth',   'dark cyan',  'black'),
        ('bg 6',          'dark red',   'light cyan', 'standout'),
        ('bg 6 smooth',   'light cyan', 'black'),
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
        self.graph_freq = []

        self.graph_place_holder = urwid.WidgetPlaceholder(urwid.Pile([]))
        self.visible_graphs = []

        self.max_temp = None
        self.cur_temp = None
        self.top_freq = None
        self.cur_freq = None
        self.perf_lost = None
        self.main_window_w = []
        self.stress_menu = StressMenu(self.on_stress_menu_close)

        self.stress_menu.sqrt_workers = str(self.graph_data.core_num)

        self.animate_progress = []
        self.animate_progress_wrap = []

        urwid.WidgetPlaceholder.__init__(self, self.main_window())

    def get_offset_now(self):
        if self.start_time is None:
            return 0
        if not self.started:
            return self.offset
        tdelta = time.time() - self.start_time
        return int(self.offset + (tdelta*self.graph_offset_per_second))

    def update_stats(self):
        if self.controller.mode.current_mode == 'Regular Operation':
            self.graph_data.max_perf_lost = 0
        self.max_temp.set_text(str(self.graph_data.max_temp) + DEGREE_SIGN + 'c')
        self.cur_temp.set_text(str(self.graph_data.cur_temp) + DEGREE_SIGN + 'c')
        self.top_freq.set_text(str(self.graph_data.top_freq) + 'MHz')
        self.cur_freq.set_text(str(self.graph_data.cur_freq) + 'MHz')
        self.perf_lost.set_text(str(self.graph_data.max_perf_lost) + '%')

    def update_graph(self, force_update=False):
        self.graph_data.graph_num_bars = self.graph_util.bar_graph.get_size()[1]

        o = self.get_offset_now()
        if o == self.last_offset and not force_update:
            return False
        self.last_offset = o

        # TODO set maximum value dynamically and per graph
        l = []

        self.graph_data.update_temp()
        self.graph_data.update_util()
        self.graph_data.update_freq()

        # Updating CPU utilization
        for n in range(self.graph_data.graph_num_bars):
            value = self.graph_data.cpu_util[n]
            # toggle between two bar types
            if n & 1:
                l.append([0, value])
            else:
                l.append([value, 0])
        self.graph_util.bar_graph.set_data(l, self.graph_data.util_max_value)

        # Updating CPU temperature
        l = []
        for n in range(self.graph_data.graph_num_bars):
            value = self.graph_data.cpu_temp[n]
            # toggle between two bar types
            if n & 1:
                l.append([0, value])
            else:
                l.append([value, 0])
        self.graph_temp.bar_graph.set_data(l, self.graph_data.temp_max_value)

        # Updating CPU frequancy
        l = []
        for n in range(self.graph_data.graph_num_bars):
            value = self.graph_data.cpu_freq[n]
            # toggle between two bar types
            if n & 1:
                l.append([0, value])
            else:
                l.append([value, 0])
        self.graph_freq.bar_graph.set_data(l, self.graph_data.top_freq)


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
        self.graph_data.reset()
        self.update_graph(True)

    def on_stress_menu_close(self):
        self.original_widget = self.main_window_w

    def on_stress_menu_open(self, w):
        self.original_widget = urwid.Overlay(self.stress_menu.main_window, self.original_widget,
                                             ('fixed left', 3), self.stress_menu.get_size()[1],
                                             ('fixed top', 2), self.stress_menu.get_size()[0])

    def on_mode_button(self, button, state):
        """Notify the controller of a new mode setting."""

        def start_stress(mode):
            # Start stress here?
            if mode == 'Stress Operation':

                stress_cmd = ['stress']

                if int(self.stress_menu.sqrt_workers) > 0:
                    stress_cmd.append('-c')
                    stress_cmd.append(self.stress_menu.sqrt_workers)

                if int(self.stress_menu.sync_workers) > 0:
                    stress_cmd.append('-i')
                    stress_cmd.append(self.stress_menu.sync_workers)

                if int(self.stress_menu.memory_workers) > 0:
                    stress_cmd.append('--vm')
                    stress_cmd.append(self.stress_menu.memory_workers)
                    stress_cmd.append('--vm-bytes')
                    stress_cmd.append(self.stress_menu.malloc_byte)
                    stress_cmd.append('--vm-stride')
                    stress_cmd.append(self.stress_menu.byte_touch_cnt)

                if self.stress_menu.no_malloc:
                    stress_cmd.append('--vm-keep')

                if int(self.stress_menu.write_workers) > 0:
                    stress_cmd.append('--hdd')
                    stress_cmd.append(self.stress_menu.write_workers)
                    stress_cmd.append('--hdd-bytes')
                    stress_cmd.append(self.stress_menu.write_bytes)

                if self.stress_menu.time_out != 'none':
                    stress_cmd.append('-t')
                    stress_cmd.append(self.stress_menu.time_out)

                self.stress_process = subprocess.Popen(stress_cmd,
                                                       stdout=FNULL, stderr=FNULL, shell=False)
                self.stress_process = psutil.Process(self.stress_process.pid)

                self.graph_data.max_perf_lost = 0
                self.graph_data.samples_taken = 0
            else:
                try:
                    # Kill all the subprocess of stress
                    for proc in self.stress_process.children(recursive=True):
                        proc.kill()
                except:
                    print('Could not kill process')

        if state:
            # The new mode is the label of the button
            self.controller.set_mode(button.get_label())
            start_stress(self.controller.mode.current_mode)

        self.last_offset = None

    def on_mode_change(self, m):
        """Handle external mode change by updating radio buttons."""
        for rb in self.mode_buttons:
            if rb.get_label() == m:
                rb.set_state(True, do_callback=False)
                break
        self.last_offset = None

    def on_unicode_checkbox(self, w, state):

        if state: satt = {(1, 0): 'bg 1 smooth', (2, 0): 'bg 2 smooth'}
        else: satt = None
        self.graph_util.bar_graph.set_segment_attributes(['bg background', 'bg 1', 'bg 2'], satt=satt)

        if state: satt = {(1, 0): 'bg 3 smooth', (2, 0): 'bg 4 smooth'}
        else: satt = None
        self.graph_temp.bar_graph.set_segment_attributes(['bg background', 'bg 3', 'bg 4'], satt=satt)

        if state: satt = {(1, 0): 'bg 5 smooth', (2, 0): 'bg 6 smooth'}
        else: satt = None
        self.graph_freq.bar_graph.set_segment_attributes(['bg background', 'bg 5', 'bg 6'], satt=satt)

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

    def bar_graph(self, color_a, color_b, title, x_label, y_label):

        w = ScalableBarGraph(['bg background', color_a, color_b])
        bg = LabeledBarGraph([w, x_label, y_label, title])

        return bg

    def button(self, t, fn, data=None):
        w = urwid.Button(t, fn, data)
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
        try:
            # Kill all the subprocess of stress
            for proc in self.stress_process.children(recursive=True):
                proc.kill()
        except:
            print('Could not kill process')
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
            self.button('Stress Options', self.on_stress_menu_open),
        ], 18, 2, 0, 'center')

        if urwid.get_encoding_mode() == "utf8":
            unicode_checkbox = urwid.CheckBox(
                "Smooth Graph (Unicode Graphics)",
                on_state_change=self.on_unicode_checkbox)
        else:
            unicode_checkbox = urwid.Text(
                "UTF-8 encoding not detected")

        buttons = [urwid.Text("Mode", align="center"),
             ] + self.mode_buttons + [
            urwid.Divider(),
            urwid.Text("Control Options", align="center"),
            animate_controls,
            urwid.Divider(),
            urwid.LineBox(unicode_checkbox),
            urwid.Divider(),
            urwid.LineBox(urwid.Pile([
                urwid.CheckBox('Frequency', on_state_change=self.show_frequency),
                urwid.CheckBox('Temperature', state=True, on_state_change=self.show_temprature),
                urwid.CheckBox('Utilization', state=True, on_state_change=self.show_utilization)])),
            urwid.Divider(),
            self.button("Quit", self.exit_program),
            ]

        return buttons

    def show_frequency(self, w, state):
        if state:
            self.visible_graphs[0] = self.graph_freq
        else:
            self.visible_graphs[0] = None
        self.show_graphs()

    def show_utilization(self, w, state):
        if state:
            self.visible_graphs[1] = self.graph_util
        else:
            self.visible_graphs[1] = None
        self.show_graphs()

    def show_temprature(self, w, state):
        if state:
            self.visible_graphs[2] = self.graph_temp
        else:
            self.visible_graphs[2] = None
        self.show_graphs()

    def show_graphs(self):

        graph_list = []
        hline = urwid.AttrWrap(urwid.SolidFill(u'\N{LOWER ONE QUARTER BLOCK}'), 'line')

        for g in self.visible_graphs:
            if g is not None:
                graph_list.append(g)
                graph_list.append(('fixed',  1, hline))

        self.graph_place_holder.original_widget = urwid.Pile(graph_list)

    def graph_stats(self):
        fixed_stats = [urwid.Divider(), urwid.Text("Max Temp", align="left"),
                       self.max_temp] + \
                      [urwid.Divider(), urwid.Text("Current Temp", align="left"),
                       self.cur_temp] + \
                      [urwid.Divider(), urwid.Text("Top Freq", align="left"),
                       self.top_freq] + \
                      [urwid.Divider(), urwid.Text("Cur Freq", align="left"),
                       self.cur_freq] + \
                      [urwid.Divider(), urwid.Text("Max Perf Lost", align="left"),
                       self.perf_lost]
        return fixed_stats

    def main_window(self):
        # Initiating the data
        self.graph_util = self.bar_graph('bg 1', 'bg 2', 'Utilization[%]', [], [0, 50, 100])
        self.graph_temp = self.bar_graph('bg 3', 'bg 4', 'Temperature[C]', [], [0, 25, 50, 75, 100])
        top_freq = self.graph_data.top_freq
        self.graph_freq = self.bar_graph('bg 5', 'bg 6', 'Frequency[MHz]', [], [0, int(top_freq / 3), int(2 * top_freq / 3), int(top_freq)])
        self.max_temp = urwid.Text(str(self.graph_data.max_temp) + DEGREE_SIGN + 'c', align="right")
        self.cur_temp = urwid.Text(str(self.graph_data.cur_temp) + DEGREE_SIGN + 'c', align="right")
        self.top_freq = urwid.Text(str(self.graph_data.top_freq) + 'MHz', align="right")
        self.cur_freq = urwid.Text(str(self.graph_data.cur_freq) + 'MHz', align="right")
        self.perf_lost = urwid.Text(str(self.graph_data.max_perf_lost) + '%', align="right")

        self.graph_data.graph_num_bars = self.graph_util.bar_graph.get_size()[1]

        self.graph_util.bar_graph.set_bar_width(1)
        self.graph_temp.bar_graph.set_bar_width(1)
        self.graph_freq.bar_graph.set_bar_width(1)

        vline = urwid.AttrWrap(urwid.SolidFill(u'\u2502'), 'line')

        self.visible_graphs = [None, self.graph_util, self.graph_temp]
        self.show_graphs()

        graph_controls = self.graph_controls()
        graph_stats = self.graph_stats()

        text_col = urwid.ListBox(urwid.SimpleListWalker(graph_controls + [urwid.Divider()] + graph_stats))

        w = urwid.Columns([('weight', 2, self.graph_place_holder),
                           ('fixed',  1, vline),
                           ('fixed',  20, text_col)],
                          dividechars=1, focus_column=2)

        w = urwid.Padding(w, ('fixed left', 1), ('fixed right', 0))
        w = urwid.AttrWrap(w, 'body')
        w = urwid.LineBox(w)
        w = urwid.AttrWrap(w, 'line')
        self.main_window_w = self.main_shadow(w)
        return self.main_window_w


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
    args = get_args()
    # Print version and exit
    if args.version:
        print (VERSION_MESSAGE)
        exit(0)

    # Setup logging util
    log_file
    level = ""
    if args.debug:
        level=logging.DEBUG
        logFormatter = logging.Formatter("%(asctime)s [%(funcName)s()] [%(levelname)-5.5s]  %(message)s")
        rootLogger = logging.getLogger()
        fileHandler = logging.FileHandler(log_file)
        fileHandler.setFormatter(logFormatter)
        rootLogger.addHandler(fileHandler)
        rootLogger.setLevel(level)


    global is_admin
    try:
        is_admin = os.getuid() == 0
    except AttributeError:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    if not is_admin:
        print ("You are running without root permissions. Run as root for best results")
        logging.info("Started without root permissions")
        time.sleep(2)

    GraphController().main()

def get_args():
    parser = argparse.ArgumentParser(
        description=INTRO_MESSAGE,
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('-d', '--debug',
                        default=False, action='store_true', help="Output debug log to " + log_file)
    parser.add_argument('-v', '--version',
                        default=False, action='store_true', help="Display version")
    args = parser.parse_args()
    return args

if '__main__' == __name__:
    main()

