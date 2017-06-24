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
#
# This implementation was inspired by Ian Ward
# Urwid web site: http://excess.org/urwid/

"""An urwid program to stress and monitor you computer"""

from __future__ import print_function

import urwid
from ComplexBarGraphs import ScalableBarGraph
from ComplexBarGraphs import LabeledBarGraph
from StressMenu import StressMenu
from HelpMenu import HelpMenu
from AboutMenu import AboutMenu

import psutil
import time
import subprocess
import ctypes
import os
import argparse
import logging
import platform
from aux import read_msr
from aux import kill_child_processes
from aux import get_processor_name
from aux import __version__


# Constants
UPDATE_INTERVAL = 1
DEGREE_SIGN = u'\N{DEGREE SIGN}'
TURBO_MSR = 429
WAIT_SAMPLES = 5

log_file = os.devnull

VERSION_MESSAGE = " s-tui " + __version__ +\
                  " - (C) 2017 Alex Manuskin, Gil Tsuker\n\
                  Relased under GNU GPLv2"

fire_starter = "FIRESTARTER/FIRESTARTER"

# globals
is_admin = None
graph_controller = None

INTRO_MESSAGE = "\
********s-tui manual********\n\
-Alex Manuskin      \n\
-Gil Tsuker         \n\
April 2017\n\
\n\
s-tui is a terminal UI add-on for stress. The software uses stress to run CPU\
hogs, while monitoring the CPU usage, temperature and frequency.\n\
The software was conceived with the vision of being able to stress test your\
computer without the need for a GUI\n\
"


class ViListBox(urwid.ListBox):
    # Catch key presses in box and pass them as arrow keys
    def keypress(self, size, key):
        if key == 'j':
            key = 'down'
        elif key == 'k':
            key = 'up'
        return super(ViListBox, self).keypress(size, key)


class GraphMode:
    """
    A class responsible for storing the data related to
    the current mode of operation
    """

    def __init__(self):
        self.modes = [
            'Regular Operation',
            'Stress Operation',
            # 'FIRESTARTER'
            ]
        self.data = {}

        self.current_mode = self.modes[0]
        self.stress_process = None

    def get_modes(self):
        return self.modes

    def get_current_mode(self):
        return self.current_mode

    def set_mode(self, m):
        self.current_mode = m
        return True

    def get_stress_process(self):
        return self.stress_process

    def set_stress_process(self, proc):
        self.stress_process = proc
        return True


class MainLoop(urwid.MainLoop):
    def unhandled_input(self, input):
        logging.debug('Caught ' + str(input))

        if input == 'q':
            logging.debug(graph_controller.mode.get_stress_process())
            kill_child_processes(graph_controller.mode)
            raise urwid.ExitMainLoop()

        if input == 'esc':
            graph_controller.view.on_stress_menu_close()


class GraphData:
    THRESHOLD_TEMP = 80

    def __init__(self, graph_num_bars):
        # Constants data
        self.temp_max_value = 100
        self.util_max_value = 100
        self.graph_num_bars = graph_num_bars
        # Data for graphs
        self.cpu_util = [0] * graph_num_bars
        self.cpu_temp = [0] * graph_num_bars
        self.cpu_freq = [0] * graph_num_bars
        # Data for statistics
        self.overheat = False
        self.overheat_detected = False
        self.max_temp = 0
        self.cur_temp = 0
        self.cur_freq = 0
        self.perf_lost = 0
        self.max_perf_lost = 0
        self.samples_taken = 0
        self.core_num = "N/A"
        try:
            self.core_num = psutil.cpu_count()
        except:
            self.core_num = 1
            logging.debug("Num of cores unavailable")
        self.top_freq = 100
        self.turbo_freq = False

        if is_admin:
            try:
                num_cpus = psutil.cpu_count(logical=False)
                available_freq = read_msr(TURBO_MSR, 0)
                logging.debug(available_freq)
                self.top_freq = float(available_freq[num_cpus - 1] * 100)
                self.turbo_freq = True
            except (IOError, OSError) as e:
                logging.debug(e.message)

        if self.top_freq == 100:
            try:
                self.top_freq = psutil.cpu_freq().max
                self.turbo_freq = False
            except:
                logging.debug("Top frequency is not supported")

    def update_util(self):
        try:
            last_value = psutil.cpu_percent(interval=None)
        except:
            last_value = 0
            logging.debug("Cpu Utilization unavailable")

        self.cpu_util = self.update_graph_val(self.cpu_util, last_value)

    def update_freq(self):
        self.samples_taken += 1
        try:
            self.cur_freq = int(psutil.cpu_freq().current)
        except:
            self.cur_freq = 0
            logging.debug("Frequency unavailable")

        self.cpu_freq = self.update_graph_val(self.cpu_freq, self.cur_freq)

        if is_admin and self.samples_taken > WAIT_SAMPLES:
            self.perf_lost = int(self.top_freq) - int(self.cur_freq)
            if self.top_freq != 0:
                self.perf_lost = (round(float(self.perf_lost) / float(self.top_freq) * 100, 1))
            else:
                self.perf_lost = 0
            if self.perf_lost > self.max_perf_lost:
                self.max_perf_lost = self.perf_lost
        elif not is_admin:
            self.max_perf_lost = "N/A (no root)"

    def reset(self):
        self.overheat = False
        self.cpu_util = [0] * self.graph_num_bars
        self.cpu_temp = [0] * self.graph_num_bars
        self.cpu_freq = [0] * self.graph_num_bars
        self.max_temp = 0
        self.cur_temp = 0
        self.cur_freq = 0
        self.perf_lost = 0
        self.max_perf_lost = 0
        self.samples_taken = 0
        self.overheat_detected = False

    def update_temp(self):
        # Reading for temperature might be different between systems
        # Support for additional systems can be added here
        last_value = 0
        # NOTE: Negative values might not be supported
        if last_value <= 0:
            try:
                last_value = psutil.sensors_temperatures()['coretemp'][0].current
            except:
                pass
        if last_value <= 0:
            try:
                last_value = psutil.sensors_temperatures()['it8622'][0].current
            except:
                pass
        if last_value <= 0:
            try:
                last_value = psutil.sensors_temperatures()['bcm2835_thermal'][0].current
            except:
                pass
        # Raspberry pi + raspiban CPU temp
        if last_value <= 0:
            try:
                last_value = os.popen('cat /sys/class/thermal/thermal_zone0/temp').read()
                last_value = int(last_value) / 1000
            except:
                pass



        if last_value <= 0:
                logging.debug("Temperature sensor unavailable")

        self.cpu_temp = self.update_graph_val(self.cpu_temp, last_value)
        # Update max temp
        if last_value > int(self.max_temp):
            self.max_temp = last_value
        # Update current temp
        self.cur_temp = last_value
        if self.cur_temp >= self.THRESHOLD_TEMP:
            self.overheat = True
            self.overheat_detected = True
        else:
            self.overheat = False

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
        ('body',                    'black',          'light gray',   'standout'),
        ('header',                  'white',          'dark red',     'bold'),
        ('screen edge',             'light blue',     'brown'),
        ('main shadow',             'dark gray',      'black'),
        ('line',                    'black',          'light gray',   'standout'),
        ('menu button',             'light gray',     'black'),
        ('bg background',           'light gray',     'black'),
        ('util light',              'black',          'dark green',   'standout'),
        ('util light smooth',       'dark green',     'black'),
        ('util dark',               'dark red',       'light green',  'standout'),
        ('util dark smooth',        'light green',    'black'),
        ('high temp dark',          'light red',      'dark red',     'standout'),
        ('overheat dark',           'black',          'light red',     'standout'),
        ('high temp dark smooth',   'dark red',       'black'),
        ('high temp light',         'dark red',       'light red',    'standout'),
        ('high temp light smooth',  'light red',      'black'),
        ('temp dark',               'black',          'dark cyan',    'standout'),
        ('temp dark smooth',        'dark cyan',      'black'),
        ('temp light',              'dark red',       'light cyan',   'standout'),
        ('temp light smooth',       'light cyan',     'black'),
        ('freq dark',               'dark red',       'dark magenta', 'standout'),
        ('freq dark smooth',        'dark magenta',   'black'),
        ('freq light',              'dark red',       'light magenta', 'standout'),
        ('freq light smooth',       'light magenta',  'black'),
        ('button normal',           'light gray',     'dark blue',    'standout'),
        ('button select',           'white',          'dark green'),
        ('line',                    'black',          'light gray',   'standout'),
        ('pg normal',               'white',          'black',        'standout'),
        ('pg complete',             'white',          'dark magenta'),
        ('high temp txt',           'light red',      'light gray'),
        ('pg smooth',               'dark magenta',   'black')
        ]

    GRAPH_OFFSET_PER_SECOND = 5
    SCALE_DENSITY = 5
    MAX_UTIL = 100
    MAX_TEMP = 100

    def __init__(self, controller):

        self.controller = controller
        self.started = True
        self.start_time = None
        self.offset = 0
        self.last_offset = None
        self.temp_color = (['bg background', 'temp dark', 'temp light'],
                           {(1, 0): 'temp dark smooth', (2, 0): 'temp light smooth'},
                           'line')
        self.mode_buttons = []

        self.graph_data = GraphData(0)
        self.graph_util = []
        self.graph_temp = []
        self.graph_freq = []
        self.visible_graphs = []
        self.graph_place_holder = urwid.WidgetPlaceholder(urwid.Pile([]))

        self.max_temp = None
        self.cur_temp = None
        self.top_freq = None
        self.cur_freq = None
        self.perf_lost = None

        self.main_window_w = []

        self.stress_menu = StressMenu(self.on_stress_menu_close)
        self.help_menu = HelpMenu(self.on_help_menu_close)
        self.about_menu = AboutMenu(self.on_about_menu_close)
        self.stress_menu.sqrt_workers = str(self.graph_data.core_num)

        urwid.WidgetPlaceholder.__init__(self, self.main_window())

    def get_offset_now(self):
        if self.start_time is None:
            return 0
        if not self.started:
            return self.offset
        tdelta = time.time() - self.start_time
        return int(self.offset + (tdelta * self.GRAPH_OFFSET_PER_SECOND))

    def update_stats(self):
        if self.controller.mode.current_mode == 'Regular Operation':
            self.graph_data.max_perf_lost = 0
        if self.graph_data.overheat_detected:
            self.max_temp.set_text(('overheat dark', str(self.graph_data.max_temp) + DEGREE_SIGN + 'c'))
        else:
            self.max_temp.set_text(str(self.graph_data.max_temp) + DEGREE_SIGN + 'c')

        self.cur_temp.set_text((self.temp_color[2], str(self.graph_data.cur_temp) + DEGREE_SIGN + 'c'))

        self.top_freq.set_text(str(self.graph_data.top_freq) + 'MHz')
        self.cur_freq.set_text(str(self.graph_data.cur_freq) + 'MHz')
        self.perf_lost.set_text(str(self.graph_data.max_perf_lost) + '%')

    def update_graph(self, force_update=False):
        self.graph_data.graph_num_bars = self.graph_util.bar_graph.get_size()[1]

        o = self.get_offset_now()
        if o == self.last_offset and not force_update:
            return False
        self.last_offset = o

        self.graph_data.update_temp()
        self.graph_data.update_util()
        self.graph_data.update_freq()

        # Updating CPU utilization
        l = []
        for n in range(self.graph_data.graph_num_bars):
            value = self.graph_data.cpu_util[n]
            # toggle between two bar types
            if n & 1:
                l.append([0, value])
            else:
                l.append([value, 0])
        self.graph_util.bar_graph.set_data(l, self.graph_data.util_max_value)
        y_label_size = self.graph_util.bar_graph.get_size()[0]
        self.graph_util.set_y_label(self.get_label_scale(0, self.MAX_UTIL, y_label_size))

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
        self.set_temp_color()
        y_label_size = self.graph_temp.bar_graph.get_size()[0]
        self.graph_temp.set_y_label(self.get_label_scale(0, self.MAX_TEMP, y_label_size))

        # Updating CPU frequency
        l = []
        for n in range(self.graph_data.graph_num_bars):
            value = self.graph_data.cpu_freq[n]
            # toggle between two bar types
            if n & 1:
                l.append([0, value])
            else:
                l.append([value, 0])
        self.graph_freq.bar_graph.set_data(l, self.graph_data.top_freq)
        y_label_size = self.graph_freq.bar_graph.get_size()[0]
        self.graph_freq.set_y_label(self.get_label_scale(0, self.graph_data.top_freq, y_label_size))

        self.update_stats()

    def set_temp_color(self, smooth=None):
        if self.graph_data.overheat:
            new_color = (['bg background', 'high temp dark', 'high temp light'],
                         {(1, 0): 'high temp dark smooth', (2, 0): 'high temp light smooth'},
                         'high temp txt')
        else:
            new_color = (['bg background', 'temp dark', 'temp light'],
                         {(1, 0): 'temp dark smooth', (2, 0): 'temp light smooth'},
                         'line')

        if new_color[2] == self.temp_color[2] and smooth is None:
            return

        if smooth is None:
            if self.temp_color[1] is None:
                self.temp_color = (new_color[0], None, new_color[2])
            else:
                self.temp_color = new_color
        elif smooth:
            self.temp_color = new_color
        else:
            self.temp_color = (new_color[0], None, new_color[2])

        self.graph_temp.bar_graph.set_segment_attributes(self.temp_color[0], satt=self.temp_color[1])

    def get_label_scale(self, min_val, max_val, size):

        if size < self.SCALE_DENSITY:
            label_cnt = 1
        else:
            label_cnt = (size / self.SCALE_DENSITY)
        try:
            label = [int(min_val + i * (int(max_val) - int(min_val)) / label_cnt)
                     for i in range(label_cnt + 1)]
        except:
            pass
        return label

    def toggle_animation(self):
        if self.started:  # stop animation
            self.offset = self.get_offset_now()
            self.started = False
            self.controller.stop_animation()
        else:
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

    def on_help_menu_close(self):
        self.original_widget = self.main_window_w

    def on_about_menu_close(self):
        self.original_widget = self.main_window_w

    def on_stress_menu_open(self, w):
        self.original_widget = urwid.Overlay(self.stress_menu.main_window,
                                             self.original_widget,
                                             ('fixed left', 3),
                                             self.stress_menu.get_size()[1],
                                             ('fixed top', 2),
                                             self.stress_menu.get_size()[0])

    def on_help_menu_open(self, w):
        self.original_widget = urwid.Overlay(self.help_menu.main_window,
                                             self.original_widget,
                                             ('fixed left', 3),
                                             self.help_menu.get_size()[1],
                                             ('fixed top', 2),
                                             self.help_menu.get_size()[0])

    def on_about_menu_open(self, w):
        self.original_widget = urwid.Overlay(self.about_menu.main_window,
                                             self.original_widget,
                                             ('fixed left', 3),
                                             self.about_menu.get_size()[1],
                                             ('fixed top', 2),
                                             self.about_menu.get_size()[0])

    def on_mode_button(self, button, state):
        """Notify the controller of a new mode setting."""

        def start_stress(mode):
            if mode.get_current_mode() == 'Stress Operation':

                try:
                    kill_child_processes(mode.get_stress_process())
                except:
                    logging.debug('Could not kill process')

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

                with open(os.devnull, 'w') as DEVNULL:
                    try:
                        stress_proc = subprocess.Popen(stress_cmd, stdout=DEVNULL, stderr=DEVNULL, shell=False)
                        mode.set_stress_process(psutil.Process(stress_proc.pid))
                    except:
                        logging.debug("Unable to start stress")

                self.graph_data.max_perf_lost = 0
                self.graph_data.samples_taken = 0

            elif mode.get_current_mode() == 'FIRESTARTER':
                logging.debug('Started FIRESTARTER mode')
                try:
                    kill_child_processes(mode.get_stress_process())
                except:
                    logging.debug('Could not kill process')

                stress_cmd = [os.path.join(os.getcwd(), fire_starter)]
                with open(os.devnull, 'w') as DEVNULL:
                    try:
                        stress_proc = subprocess.Popen(stress_cmd, stdout=DEVNULL, stderr=DEVNULL, shell=False)
                        mode.set_stress_process(psutil.Process(stress_proc.pid))
                        logging.debug('Started process' + str(mode.get_stress_process()))
                    except:
                        logging.debug("Unable to start stress")

            else:
                logging.debug('Regular operation mode')
                try:
                    kill_child_processes(mode.get_stress_process())
                except:
                    try:
                        logging.debug('Could not kill process' + str(mode.get_stress_process()))
                    except:
                        logging.debug('Could not kill process FIRESTARTER')

        if state:
            # The new mode is the label of the button
            self.controller.set_mode(button.get_label())
            start_stress(self.controller.mode)

        self.last_offset = None

    def on_mode_change(self, m):
        """Handle external mode change by updating radio buttons."""
        for rb in self.mode_buttons:
            if rb.get_label() == m:
                rb.set_state(True, do_callback=False)
                break
        self.last_offset = None

    def on_unicode_checkbox(self, w, state):

        if state:
            satt = {(1, 0): 'util light smooth', (2, 0): 'util dark smooth'}
        else:
            satt = None
        self.graph_util.bar_graph.set_segment_attributes(['bg background', 'util light', 'util dark'], satt=satt)

        self.set_temp_color(smooth=state)

        if state:
            satt = {(1, 0): 'freq dark smooth', (2, 0): 'freq light smooth'}
        else:
            satt = None
        self.graph_freq.bar_graph.set_segment_attributes(['bg background', 'freq dark', 'freq light'], satt=satt)

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

    def exit_program(self, w):
        try:
            kill_child_processes(self.controller.mode.get_stress_process())
        except:
            logging.debug('Could not kill process')
        raise urwid.ExitMainLoop()

    def graph_controls(self):
        modes = self.controller.get_modes()
        # setup mode radio buttons
        group = []
        for m in modes:
            rb = self.radio_button(group, m, self.on_mode_button)
            self.mode_buttons.append(rb)
        self.offset = 0
        animate_controls = urwid.GridFlow([
            self.button("Reset", self.on_reset_button),
            self.button('Stress Options', self.on_stress_menu_open),
            self.button('Help', self.on_help_menu_open),
            self.button('About', self.on_about_menu_open),
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
                urwid.CheckBox('Frequency', state=True, on_state_change=self.show_frequency),
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

    def cpu_stats(self):
        cpu_stats = [ urwid.Text(get_processor_name().strip(), align="center"), urwid.Divider()]
        return cpu_stats


    def graph_stats(self):
        top_freq_string = "Top Freq"
        if self.graph_data.turbo_freq:
            top_freq_string += " " + str(self.graph_data.core_num) + " Cores"
        else:
            top_freq_string += " 1 Core"
        fixed_stats = [urwid.Divider(), urwid.Text("Max Temp", align="left"),
                       self.max_temp] + \
                      [urwid.Divider(), urwid.Text("Cur Temp", align="left"),
                       self.cur_temp] + \
                      [urwid.Divider(), urwid.Text(top_freq_string, align="left"),
                       self.top_freq] + \
                      [urwid.Divider(), urwid.Text("Cur Freq", align="left"),
                       self.cur_freq] + \
                      [urwid.Divider(), urwid.Text("Max Perf Lost", align="left"),
                       self.perf_lost]
        return fixed_stats

    def main_window(self):
        # Initiating the data
        self.graph_util = self.bar_graph('util light', 'util dark', 'Utilization[%]', [], [0, 50, 100])
        self.graph_temp = self.bar_graph('temp dark', 'temp light', 'Temperature[C]', [], [0, 25, 50, 75, 100])
        top_freq = self.graph_data.top_freq
        one_third = 0
        two_third = 0
        try:
            one_third = int(top_freq / 3)
            two_third = int(2 * top_freq / 3)
        except:
            one_third = 0
            two_third = 0
            top_freq = 0
        self.graph_freq = self.bar_graph('freq dark', 'freq light', 'Frequency[MHz]', [],
                                         [0, one_third, two_third, top_freq])
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

        self.visible_graphs = [self.graph_freq, self.graph_util, self.graph_temp]
        self.show_graphs()

        cpu_stats = self.cpu_stats()
        graph_controls = self.graph_controls()
        graph_stats = self.graph_stats()

        text_col = ViListBox(urwid.SimpleListWalker(cpu_stats + graph_controls + [urwid.Divider()] + graph_stats))

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
        self.loop = MainLoop(self.view, self.view.palette)

        self.view.started = False  # simulate pressing to start button
        self.view.toggle_animation()

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
    global log_file
    level = ""
    if args.debug:
        level = logging.DEBUG
        log_file = "_s-tui.log"
        log_formatter = logging.Formatter("%(asctime)s [%(funcName)s()] [%(levelname)-5.5s]  %(message)s")
        root_logger = logging.getLogger()
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(log_formatter)
        root_logger.addHandler(file_handler)
        root_logger.setLevel(level)

    global is_admin
    try:
        is_admin = os.getuid() == 0
    except AttributeError:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    if not is_admin:
        print ("You are running without root permissions. Run as root for best results")
        logging.info("Started without root permissions")
        time.sleep(2)

    global graph_controller
    graph_controller = GraphController()
    graph_controller.main()


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
