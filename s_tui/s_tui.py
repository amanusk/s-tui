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

from __future__ import absolute_import
from __future__ import print_function

import argparse
import ctypes
import logging
import os
import subprocess
import time
import psutil
import urwid
import signal
import itertools

from sys import exit
from collections import OrderedDict
from distutils.spawn import find_executable
from s_tui.AboutMenu import AboutMenu
from s_tui.ComplexBarGraphs import LabeledBarGraph
from s_tui.ComplexBarGraphs import ScalableBarGraph
from s_tui.HelpMenu import HelpMenu
from s_tui.HelpMenu import HELP_MESSAGE
from s_tui.StressMenu import StressMenu
from s_tui.HelperFunctions import DEFAULT_PALETTE
from s_tui.HelperFunctions import __version__
from s_tui.HelperFunctions import get_processor_name
from s_tui.HelperFunctions import kill_child_processes
from s_tui.HelperFunctions import output_to_csv
from s_tui.HelperFunctions import output_to_terminal
from s_tui.HelperFunctions import output_to_json
from s_tui.HelperFunctions import get_user_config_path
from s_tui.HelperFunctions import make_user_config_dir
from s_tui.HelperFunctions import user_config_dir_exists
from s_tui.UiElements import ViListBox
from s_tui.UiElements import radio_button
from s_tui.UiElements import button
from s_tui.TempSensorsMenu import TempSensorsMenu
from s_tui.StuiBarGraph import StuiBarGraph
from s_tui.SummaryTextList import SummaryTextList
from s_tui.Sources.Source import MockSource as MockSource
from s_tui.Sources.UtilSource import UtilSource as UtilSource
from s_tui.Sources.FreqSource import FreqSource as FreqSource
from s_tui.Sources.TemperatureSource import TemperatureSource as TemperatureSource
from s_tui.Sources.RaplPowerSource import RaplPowerSource as RaplPowerSource
from s_tui.Sources.FanSource import FanSource as FanSource
from s_tui.GlobalData import GlobalData
from s_tui.Sources.Hook import Hook
from s_tui.Sources.ScriptHook import ScriptHook
from s_tui.Sources.ScriptHookLoader import ScriptHookLoader

UPDATE_INTERVAL = 1
DEGREE_SIGN = u'\N{DEGREE SIGN}'

log_file = os.devnull
DEFAULT_LOG_FILE = "_s-tui.log"
# TODO: Add timestamp

DEFAULT_CSV_FILE = "stui_log_" + time.strftime("%Y-%m-%d_%H_%M_%S") + ".csv"

VERSION_MESSAGE = \
"s-tui " + __version__ +\
" - (C) 2017 Alex Manuskin, Gil Tsuker\n\
Released under GNU GPLv2"

fire_starter = None

# globals
is_admin = None
stress_installed = False
graph_controller = None
stress_program = None

INTRO_MESSAGE = HELP_MESSAGE




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

            global fire_starter
            if os.path.isfile('./FIRESTARTER/FIRESTARTER'):
                fire_starter = os.path.join(os.getcwd(), 'FIRESTARTER', 'FIRESTARTER')
            elif find_executable('FIRESTARTER') is not None:
                fire_starter = 'FIRESTARTER'

            if fire_starter is not None:
                self.modes.append('FIRESTARTER')

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
    def signal_handler(signal, frame):
        """singnal handler for properly exiting Ctrl+C"""
        logging.debug(graph_controller.mode.get_stress_process())
        kill_child_processes(graph_controller.mode.get_stress_process())
        raise urwid.ExitMainLoop()

    """ Inherit urwid Mainloop to catch special charachter inputs"""
    def unhandled_input(self, input):
        logging.debug('Caught ' + str(input))
        if input == 'q':
            logging.debug(graph_controller.mode.get_stress_process())
            kill_child_processes(graph_controller.mode.get_stress_process())
            raise urwid.ExitMainLoop()

        if input == 'esc':
            graph_controller.view.on_menu_close()

    signal.signal(signal.SIGINT, signal_handler)


class GraphView(urwid.WidgetPlaceholder):
    """
    A class responsible for providing the application's interface and
    graph display.
    """
    def __init__(self, controller, args):

        self.controller = controller
        self.custom_temp = args.custom_temp
        self.custom_fan = args.custom_fan
        self.args = args
        self.hline = urwid.AttrWrap(urwid.SolidFill(u'_'), 'line')
        self.mode_buttons = []
        self.refresh_rate_ctrl = urwid.Edit(('bold text', u'Refresh[s]:'), self.controller.refresh_rate)


        self.visible_graphs = {}
        self.graph_place_holder = urwid.WidgetPlaceholder(urwid.Pile([]))

        self.main_window_w = []

        self.stress_menu = StressMenu(self.on_menu_close)
        self.help_menu = HelpMenu(self.on_menu_close)
        self.about_menu = AboutMenu(self.on_menu_close)
        self.temp_sensors_menu = TempSensorsMenu(self.on_sensors_menu_close)
        self.global_data = GlobalData(is_admin)

        self.stress_menu.sqrt_workers = str(self.global_data.num_cpus)
        self.left_margin = 0
        self.top_margin = 0
        self.v_relative = 50
        self.h_relative = 50

        urwid.WidgetPlaceholder.__init__(self, self.main_window())
        urwid.connect_signal(self.refresh_rate_ctrl, 'change', self.update_refresh_rate)


    def update_refresh_rate(self, edit, new_refresh_rate):
        try:
            if float(new_refresh_rate) <= 0.001:
                pass
            else:
                self.controller.refresh_rate = new_refresh_rate
        except:
            self.controller.refresh_rate = '1.0'

    def update_displayed_information(self):
        """ Update all the graphs that are being displayed """

        for key,val in self.summaries.items():
            val.source.update()

        for g in self.visible_graphs.values():
            g.update_displayed_graph_data()

        for s in self.available_summaries.values():
            s.update()


    def on_reset_button(self, w):
        """Reset graph data and display empty graph"""
        for g in self.visible_graphs.values():
            g.reset()
        for g in self.graphs.values():
            try:
                g.source.reset()
            except NotImplementedError:
                pass
        self.update_displayed_information()

    def on_menu_close(self):
        """Return to main screen"""
        self.original_widget = self.main_window_w

    def on_sensors_menu_close(self):
        """Return to main screen and update sensor"""
        if self.temp_sensors_menu.current_active_mode:
            logging.info("State is not None")
            self.args.custom_temp = self.temp_sensors_menu.current_active_mode
            self.__init__(self.controller, self.args)
            logging.info("Temp sensor updated to " + self.args.custom_temp)
        else:
            logging.info("Temp sensor is None")

        self.original_widget = self.main_window_w


    def on_stress_menu_open(self, w):
        """Open stress options"""
        self.original_widget = urwid.Overlay(self.stress_menu.main_window,
                                             self.original_widget,
                                             ('relative', self.left_margin),
                                             self.stress_menu.get_size()[1],
                                             ('relative', self.top_margin),
                                             self.stress_menu.get_size()[0])

    def on_help_menu_open(self, w):
        """Open Help menu"""
        self.original_widget = urwid.Overlay(self.help_menu.main_window,
                                             self.original_widget,
                                             ('relative', self.left_margin),
                                             self.help_menu.get_size()[1],
                                             ('relative', self.top_margin),
                                             self.help_menu.get_size()[0])

    def on_about_menu_open(self, w):
        """Open About menu"""
        self.original_widget = urwid.Overlay(self.about_menu.main_window,
                                             self.original_widget,
                                             ('relative', self.left_margin),
                                             self.about_menu.get_size()[1],
                                             ('relative', self.top_margin),
                                             self.about_menu.get_size()[0])

    def on_temp_sensors_menu_open(self, w):
        """Open About menu"""
        self.original_widget = urwid.Overlay(self.temp_sensors_menu.main_window,
                                             self.original_widget,
                                             ('relative', self.left_margin),
                                             self.temp_sensors_menu.get_size()[1],
                                             ('relative', self.top_margin),
                                             self.temp_sensors_menu.get_size()[0])

    def on_mode_button(self, button, state):
        """Notify the controller of a new mode setting."""
        if state:
            # The new mode is the label of the button
            self.controller.set_mode(button.get_label())
            self.controller.start_stress()


    def on_mode_change(self, m):
        """Handle external mode change by updating radio buttons."""
        for rb in self.mode_buttons:
            if rb.get_label() == m:
                rb.set_state(True, do_callback=False)
                break

    def on_unicode_checkbox(self, w, state):
        """Enable smooth edges if utf-8 is supported"""
        logging.debug("unicode State is " + str(state))
        if state:
            self.hline = urwid.AttrWrap(urwid.SolidFill(u'\N{LOWER ONE QUARTER BLOCK}'), 'line')
        else:
            self.hline = urwid.AttrWrap(urwid.SolidFill(u'_'), 'line')

        for g_name,g in self.graphs.items():
            g.set_smooth_colors(state)

        self.show_graphs()


    def exit_program(self, w=None):
        """ Kill all stress operations upon exit"""
        try:
            kill_child_processes(self.controller.mode.get_stress_process())
        except:
            logging.debug('Could not kill process')
        raise urwid.ExitMainLoop()

    def graph_controls(self):
        """ Dislplay sidebar controls. i.e. buttons, and controls"""
        modes = self.controller.get_modes()
        # setup mode radio buttons
        group = []
        for m in modes:
            rb = radio_button(group, m, self.on_mode_button)
            self.mode_buttons.append(rb)

        # Create list of buttons
        control_options = [button("Reset", self.on_reset_button)]
        if stress_installed:
            control_options.append(button('Stress Options', self.on_stress_menu_open))
        control_options.append(button('Temp Sensors', self.on_temp_sensors_menu_open))
        control_options.append(button('Help', self.on_help_menu_open))
        control_options.append(button('About', self.on_about_menu_open))

        # Create the menu
        animate_controls = urwid.GridFlow(control_options, 18, 2, 0, 'center')


        if urwid.get_encoding_mode() == "utf8":
            unicode_checkbox = urwid.CheckBox(
                "Smooth Graph", state=False,
                on_state_change=self.on_unicode_checkbox)
        else:
            unicode_checkbox = urwid.Text(
                "UTF-8 encoding not detected")


        install_stress_message = urwid.Text("")
        if not stress_installed:
            install_stress_message = urwid.Text(('button normal', u"(N/A) install stress"))


        graph_checkboxes = [urwid.CheckBox(x.get_graph_name(), state=True,
                            on_state_change=lambda w, state, x=x:  self.change_checkbox_state(x, state))
                            for x in self.available_graphs.values()]
        unavalable_graphs = [urwid.Text(( "[N/A] " + x.get_graph_name()) ) for x in self.graphs.values() if x.source.get_is_available() == False]
        graph_checkboxes += unavalable_graphs

        buttons = [urwid.Text(('bold text', u"Modes"), align="center"),
                   ] +  self.mode_buttons + [
            install_stress_message,
            urwid.Divider(),
            urwid.Text(('bold text', u"Control Options"), align="center"),
            animate_controls,
            urwid.Divider(),
            self.refresh_rate_ctrl,
            urwid.Divider(),
            urwid.LineBox(urwid.Pile(graph_checkboxes)),
            urwid.LineBox(unicode_checkbox),
            urwid.Divider(),
            button("Quit", self.exit_program),
            ]

        return buttons

    def change_checkbox_state(self, x, state):

        if state:
            self.visible_graphs[x.get_graph_name()] = x
        else:
            del self.visible_graphs[x.get_graph_name()]
        self.show_graphs()


    def show_graphs(self):
        """Show a pile of the graph selected for dislpay"""
        elements = itertools.chain.from_iterable(([graph, ('fixed', 1, self.hline)]
                                            for graph in self.visible_graphs.values()))
        self.graph_place_holder.original_widget = urwid.Pile(elements)

    def cpu_stats(self):
           """Read and display processor name """
           cpu_name = urwid.Text("CPU Name N/A", align="center")
           try:
               cpu_name = urwid.Text(get_processor_name().strip(), align="center")
           except:
               logging.info("CPU name not available")
           cpu_stats = [cpu_name, urwid.Divider()]
           return cpu_stats

    def graph_stats(self):

        fixed_stats = []
        for key, val in self.available_summaries.items():
            fixed_stats += val.get_text_item_list()

        return fixed_stats

    def main_window(self):

        user_config_path = None
        if not user_config_dir_exists():
            user_config_path = make_user_config_dir()
        else:
            user_config_path = get_user_config_path()

        script_hooks_enabled = True
        if user_config_path is None:
            logging.warn('Failed to find or create scripts directory, proceeding without scripting support')
            script_hooks_enabled = False
        else:
            self.script_loader = ScriptHookLoader(user_config_path)

        # initiating the graphs
        self.graphs = OrderedDict()
        self.summaries = OrderedDict()

        # TODO: Update to find sensors automatically


        freq_source = FreqSource(is_admin)
        self.graphs[freq_source.get_source_name()] = StuiBarGraph(freq_source, 'freq light', 'freq dark', 'freq light smooth', 'freq dark smooth')
        self.summaries[freq_source.get_source_name()] = SummaryTextList(freq_source)

        util_source = UtilSource()
        self.graphs[util_source.get_source_name()] = StuiBarGraph(util_source, 'util light', 'util dark', 'util light smooth', 'util dark smooth')
        self.summaries[util_source.get_source_name()] = SummaryTextList(util_source)

        temp_source = TemperatureSource(self.custom_temp)

        if script_hooks_enabled:
            temp_source.add_edge_hook(self.script_loader.load_script(temp_source.__class__.__name__, 30000)) # Invoke threshold script every 30s while threshold is exceeded.

        alert_colors = ['high temp light', 'high temp dark', 'high temp light smooth', 'high temp dark smooth']
        self.graphs[temp_source.get_source_name()] = StuiBarGraph(temp_source, 'temp light', 'temp dark', 'temp light smooth', 'temp dark smooth', alert_colors=alert_colors)
        self.summaries[temp_source.get_source_name()] = SummaryTextList(temp_source, 'high temp txt')

        rapl_power_source = RaplPowerSource()
        self.graphs[rapl_power_source.get_source_name()] = StuiBarGraph(rapl_power_source, 'power dark', 'power light', 'power dark smooth', 'power light smooth')
        self.summaries[rapl_power_source.get_source_name()] = SummaryTextList(rapl_power_source)

        fan_source = FanSource(self.custom_fan)
        self.summaries[fan_source.get_source_name()] = SummaryTextList(fan_source)

        # only interested in available graph
        self.available_graphs = OrderedDict((key, val) for key, val in self.graphs.items() if val.get_is_available())
        self.available_summaries = OrderedDict((key, val) for key, val in self.summaries.items() if val.get_is_available())

        self.visible_graphs = self.available_graphs.copy()
        self.show_graphs()

        cpu_stats = self.cpu_stats()
        graph_controls = self.graph_controls()
        graph_stats = self.graph_stats()

        text_col = ViListBox(urwid.SimpleListWalker(cpu_stats + graph_controls + [urwid.Divider()] + graph_stats))

        vline = urwid.AttrWrap(urwid.SolidFill(u'\u2502'), 'line')
        w = urwid.Columns([
                           ('fixed',  20, text_col),
                           ('fixed',  1, vline),
                           ('weight', 2, self.graph_place_holder),
                           ],
                          dividechars=1, focus_column=0)

        w = urwid.Padding(w, ('fixed left', 1), ('fixed right', 0))
        w = urwid.AttrWrap(w, 'body')
        w = urwid.LineBox(w)
        w = urwid.AttrWrap(w, 'line')
        self.main_window_w = w
        return self.main_window_w


class GraphController:
    """
    A class responsible for setting up the model and view and running
    the application.
    """
    def __init__(self, args):
        self.animate_alarm = None
        self.save_csv = args.csv
        self.terminal = args.terminal
        self.json = args.json
        self.mode = GraphMode()
        self.handle_mouse = not(args.no_mouse)
        self.refresh_rate = '1.0'
        self.view = GraphView(self, args)
        # use the first mode as the default
        mode = self.get_modes()[0]
        self.mode.set_mode(mode)
        # update the view
        self.view.on_mode_change(mode)
        self.view.update_displayed_information()

    def get_modes(self):
        """Allow our view access to the list of modes."""
        return self.mode.get_modes()

    def set_mode(self, m):
        """Allow our view to set the mode."""
        rval = self.mode.set_mode(m)
        self.view.update_displayed_information()
        return rval

    def main(self):
        self.loop = MainLoop(self.view, DEFAULT_PALETTE, handle_mouse = self.handle_mouse)
        self.animate_graph()
        try:
            self.loop.run()
        except ZeroDivisionError:
            logging.debug("Some stat caused divide by zero exception. Exiting")
            self.exit_program()


    def animate_graph(self, loop=None, user_data=None):
        """update the graph and schedule the next update"""
        if self.save_csv:
            output_to_csv(self.view.summaries, DEFAULT_CSV_FILE)
        self.view.update_displayed_information()
        self.animate_alarm = self.loop.set_alarm_in(
            float(self.refresh_rate), self.animate_graph)

    def start_stress(self):
        mode = self.mode
        if mode.get_current_mode() == 'Stress Operation':
            try:
                kill_child_processes(mode.get_stress_process())
            except:
                logging.debug('Could not kill process')
            # This is not pretty, but this is how we know stress started
            self.view.graphs['Frequency'].source.set_stress_started()
            stress_cmd = [stress_program]
            if int(self.view.stress_menu.sqrt_workers) > 0:
                stress_cmd.append('-c')
                stress_cmd.append(self.view.stress_menu.sqrt_workers)

            if int(self.view.stress_menu.sync_workers) > 0:
                stress_cmd.append('-i')
                stress_cmd.append(self.view.stress_menu.sync_workers)

            if int(self.view.stress_menu.memory_workers) > 0:
                stress_cmd.append('--vm')
                stress_cmd.append(self.view.stress_menu.memory_workers)
                stress_cmd.append('--vm-bytes')
                stress_cmd.append(self.view.stress_menu.malloc_byte)
                stress_cmd.append('--vm-stride')
                stress_cmd.append(self.view.stress_menu.byte_touch_cnt)

            if self.view.stress_menu.no_malloc:
                stress_cmd.append('--vm-keep')

            if int(self.view.stress_menu.write_workers) > 0:
                stress_cmd.append('--hdd')
                stress_cmd.append(self.view.stress_menu.write_workers)
                stress_cmd.append('--hdd-bytes')
                stress_cmd.append(self.view.stress_menu.write_bytes)

            if self.view.stress_menu.time_out != 'none':
                stress_cmd.append('-t')
                stress_cmd.append(self.view.stress_menu.time_out)

            with open(os.devnull, 'w') as DEVNULL:
                try:
                    stress_proc = subprocess.Popen(stress_cmd, stdout=DEVNULL, stderr=DEVNULL, shell=False)
                    mode.set_stress_process(psutil.Process(stress_proc.pid))
                except:
                    logging.debug("Unable to start stress")

            #self.data.max_perf_lost = 0
            #self.data.samples_taken = 0

        elif mode.get_current_mode() == 'FIRESTARTER':
            logging.debug('Started FIRESTARTER mode')
            try:
                kill_child_processes(mode.get_stress_process())
            except:
                logging.debug('Could not kill process')

            stress_cmd = fire_starter
            self.view.graphs['Frequency'].source.set_stress_started()
            logging.debug("Firestarter " + str(fire_starter))
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
                self.view.graphs['Frequency'].source.set_stress_stopped()
            except:
                try:
                    logging.debug('Could not kill process' + str(mode.get_stress_process()))
                except:
                    logging.debug('Could not kill process FIRESTARTER')


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
        log_file = DEFAULT_LOG_FILE
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
        logging.info("Started without root permissions")

    if args.csv:
        logging.info("Printing output to csv " + DEFAULT_CSV_FILE)

    if args.terminal or args.json:
        logging.info("Printing single line to terminal")
        sources = [FreqSource(is_admin), TemperatureSource(args.custom_temp), UtilSource(), RaplPowerSource(), FanSource(args.custom_fan)]
        if args.terminal:
            output_to_terminal(sources)
        elif args.json:
            output_to_json(sources)



    global graph_controller
    graph_controller = GraphController(args)
    graph_controller.main()


def get_args():
    custom_temp_help= """Custom temperature sensors.
The format is: <sensors>,<number>
As it appears in 'sensors'
e.g
> sensors
it8792-isa-0a60,
temp1: +47.0C
temp2: +35.0C
temp3: +37.0C

use: -ct it8792,0 for temp 1
    """

    custom_fan_help= """Similar to custom temp
e.g
>sensors
thinkpad-isa-0000
Adapter: ISA adapter
fan1:        1975 RPM

use: -cf thinkpad,0 for fan1
    """

    parser = argparse.ArgumentParser(
        description=INTRO_MESSAGE,
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('-d', '--debug',
                        default=False, action='store_true', help="Output debug log to _s-tui.log")
    parser.add_argument('-c', '--csv', action='store_true',
                        default=False, help="Save stats to csv file")
    parser.add_argument('-t', '--terminal', action='store_true',
                        default=False, help="Display a single line of stats without tui")
    parser.add_argument('-j', '--json', action='store_true',
                        default=False, help="Display a single line of stats in JSON format")
    parser.add_argument('-nm', '--no-mouse', action='store_true',
                        default=False, help="Disable Mouse for TTY systems")
    parser.add_argument('-v', '--version',
                        default=False, action='store_true', help="Display version")
    parser.add_argument('-ct', '--custom_temp',
                        default=None,
                        help= custom_temp_help)
    parser.add_argument('-cf', '--custom_fan',
                        default=None,
                        help= custom_fan_help)
    args = parser.parse_args()
    return args


if '__main__' == __name__:
        main()
