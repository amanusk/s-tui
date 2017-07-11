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

import argparse
import ctypes
import logging
import os
import subprocess
import time

import psutil
import urwid

from AboutMenu import AboutMenu
from ComplexBarGraphs import LabeledBarGraph
from ComplexBarGraphs import ScalableBarGraph
from GraphData import GraphData
from HelpMenu import HelpMenu
from StressMenu import StressMenu
from HelperFunctions import PALETTE
from HelperFunctions import __version__
from HelperFunctions import get_processor_name
from HelperFunctions import kill_child_processes

UPDATE_INTERVAL = 1
DEGREE_SIGN = u'\N{DEGREE SIGN}'

log_file = os.devnull

VERSION_MESSAGE = " s-tui " + __version__ +\
                  " - (C) 2017 Alex Manuskin, Gil Tsuker\n\
                  Released under GNU GPLv2"

fire_starter = "FIRESTARTER/FIRESTARTER"

# globals
is_admin = None
stress_installed = False
graph_controller = None
stress_program = None

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
        self.modes = ['Regular Operation']
        global stress_installed
        global stress_program
        with open(os.devnull, 'w') as DEVNULL:
            # Try if stress installed
            try:
                subprocess.Popen("stress", stdout=DEVNULL, stderr=DEVNULL, shell=False)
            except OSError:
                logging.debug("stress is not installed")
            else:
                stress_installed = True
                stress_program = 'stress'

            # Try if stress-ng installed
            try:
                subprocess.Popen("stress-ng", stdout=DEVNULL, stderr=DEVNULL, shell=False)
            except OSError:
                logging.debug("stress-ng is not installed")
            else:
                stress_installed = True
                stress_program = 'stress-ng'

            if stress_installed:
                self.modes.append('Stress Operation')

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
            kill_child_processes(graph_controller.mode.get_stress_process())
            raise urwid.ExitMainLoop()

        if input == 'esc':
            graph_controller.view.on_stress_menu_close()


class GraphView(urwid.WidgetPlaceholder):
    """
    A class responsible for providing the application's interface and
    graph display.
    """

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

        self.graph_data = GraphData(is_admin=is_admin)
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
            return label
        except:
            return ""

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

                stress_cmd = [stress_program]

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
        #shadow = urwid.AttrWrap(urwid.SolidFill(u" "), 'main shadow')

        #bg = urwid.Overlay(shadow, bg,
        #                   ('fixed left', 3), ('fixed right', 1),
        #                   ('fixed top', 2), ('fixed bottom', 1))
        #w = urwid.Overlay(w, bg,
        #                  ('fixed left', 2), ('fixed right', 3),
        #                  ('fixed top', 1), ('fixed bottom', 2))
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

        # Create list of buttons
        control_options = [self.button("Reset", self.on_reset_button)]
        if stress_installed:
            control_options.append(self.button('Stress Options', self.on_stress_menu_open))
        control_options.append(self.button('Help', self.on_help_menu_open))
        control_options.append(self.button('About', self.on_about_menu_open))

        # Create the menu
        animate_controls = urwid.GridFlow(control_options, 18, 2, 0, 'center')

        if urwid.get_encoding_mode() == "utf8":
            unicode_checkbox = urwid.CheckBox(
                "Smooth Graph",
                on_state_change=self.on_unicode_checkbox)
        else:
            unicode_checkbox = urwid.Text(
                "UTF-8 encoding not detected")

        install_stress_message = urwid.Text("")
        if not stress_installed:
            install_stress_message = urwid.Text("\nstress not installed")
        buttons = [urwid.Text("Mode", align="center"),
                   ] + self.mode_buttons + [
            urwid.Divider(),
            urwid.Text("Control Options", align="center"),
            animate_controls,
            install_stress_message,
            urwid.Divider(),
            urwid.LineBox(unicode_checkbox),
            urwid.Divider(),
            urwid.LineBox(urwid.Pile([
                urwid.CheckBox('Frequency', state=True, on_state_change=self.show_frequency),
                urwid.CheckBox('Temperature', state=True, on_state_change=self.show_temperature),
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

    def show_temperature(self, w, state):
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
        cpu_stats = [urwid.Text(get_processor_name().strip(), align="center"), urwid.Divider()]
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
        self.loop = MainLoop(self.view, PALETTE)

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

    global graph_controller
    graph_controller = GraphController()
    graph_controller.main()


def get_args():
    parser = argparse.ArgumentParser(
        description=INTRO_MESSAGE,
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('-d', '--debug',
                        default=False, action='store_true', help="Output debug log to " + log_file)
    parser.add_argument('-c', '--csv',
                        default=None, help="CSV file to save information")
    parser.add_argument('-v', '--version',
                        default=False, action='store_true', help="Display version")
    args = parser.parse_args()
    return args


if '__main__' == __name__:
    main()
