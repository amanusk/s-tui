#!/usr/bin/python

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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA
#
# This implementation was inspired by Ian Ward
# Urwid web site: http://excess.org/urwid/

"""An urwid program to stress and monitor you computer"""

from __future__ import absolute_import

import argparse
import ctypes
import logging
import os
import subprocess
import time
import timeit
import psutil
import urwid
import signal
import itertools

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

from sys import exit
from collections import OrderedDict
from collections import defaultdict
from distutils.spawn import find_executable
from s_tui.AboutMenu import AboutMenu
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
from s_tui.HelperFunctions import get_user_config_dir
from s_tui.HelperFunctions import get_user_config_file
from s_tui.HelperFunctions import make_user_config_dir
from s_tui.HelperFunctions import user_config_dir_exists
from s_tui.HelperFunctions import user_config_file_exists
from s_tui.HelperFunctions import seconds_to_text
from s_tui.HelperFunctions import str_to_bool
from s_tui.UiElements import ViListBox
from s_tui.UiElements import radio_button
from s_tui.UiElements import button
# from s_tui.TempSensorsMenu import TempSensorsMenu
from s_tui.SensorsMenu import SensorsMenu
from s_tui.StuiBarGraphVector import StuiBarGraphVector
from s_tui.SummaryTextList import SummaryTextList
from s_tui.Sources.UtilSource import UtilSource as UtilSource
from s_tui.Sources.FreqSource import FreqSource as FreqSource
from s_tui.Sources.TemperatureSource import TemperatureSource as TempSource
from s_tui.Sources.RaplPowerSource import RaplPowerSource as RaplPowerSource
from s_tui.Sources.FanSource import FanSource as FanSource
from s_tui.GlobalData import GlobalData
from s_tui.Sources.ScriptHookLoader import ScriptHookLoader

UPDATE_INTERVAL = 1
DEGREE_SIGN = u'\N{DEGREE SIGN}'

log_file = os.devnull
DEFAULT_LOG_FILE = "_s-tui.log"
# TODO: Add timestamp

DEFAULT_CSV_FILE = "s-tui_log_" + time.strftime("%Y-%m-%d_%H_%M_%S") + ".csv"

VERSION_MESSAGE = \
    "s-tui " + __version__ +\
    " - (C) 2017-2019 Alex Manuskin, Gil Tsuker\n\
    Released under GNU GPLv2"

fire_starter = None

# globals
is_admin = None
stress_installed = False
graph_controller = None
stress_program = ''
debug_run_counter = 0

INTRO_MESSAGE = HELP_MESSAGE

ERROR_MESSAGE = "\n\
        Ooop! s-tui has encountered a fatal error\n\
        Plase report this bug here: https://github.com/amanusk/s-tui"


class GraphMode:
    """
    A class responsible for storing the data related to
    the current mode of operation
    """

    def __init__(self):
        self.modes = ['Monitor']
        global stress_installed
        global stress_program
        with open(os.devnull, 'w') as DEVNULL:
            # Try if stress installed
            try:
                p = subprocess.Popen("stress", stdout=DEVNULL,
                                     stderr=DEVNULL, shell=False)
                p.kill()
            except OSError:
                logging.debug("stress is not installed")
            else:
                stress_installed = True
                stress_program = 'stress'

            # Try if stress-ng installed
            try:
                p = subprocess.Popen("stress-ng", stdout=DEVNULL,
                                     stderr=DEVNULL, shell=False)
                p.kill()
            except OSError:
                logging.debug("stress-ng is not installed")
            else:
                stress_installed = True
                stress_program = 'stress-ng'

            if stress_installed:
                self.modes.append('Stress')

            global fire_starter
            if os.path.isfile('./FIRESTARTER/FIRESTARTER'):
                fire_starter = os.path.join(os.getcwd(), 'FIRESTARTER',
                                            'FIRESTARTER')
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

    def signal_handler(self, frame):
        """signal handler for properly exiting Ctrl+C"""
        logging.debug(graph_controller.mode.get_stress_process())
        kill_child_processes(graph_controller.mode.get_stress_process())
        raise urwid.ExitMainLoop()

    """ Inherit urwid Mainloop to catch special character inputs"""
    def unhandled_input(self, stui_input):
        logging.debug('Caught ' + str(stui_input))
        if stui_input == 'q':
            logging.debug(graph_controller.mode.get_stress_process())
            kill_child_processes(graph_controller.mode.get_stress_process())
            raise urwid.ExitMainLoop()

        if stui_input == 'esc':
            graph_controller.view.on_menu_close()

    signal.signal(signal.SIGINT, signal_handler)


class GraphView(urwid.WidgetPlaceholder):
    """
    A class responsible for providing the application's interface and
    graph display.
    The GraphView can change the state of the graph, since it provides the UI
    The change is state should be reflected in the GraphController
    """
    def __init__(self, controller):
        # constants
        self.left_margin = 0
        self.top_margin = 0

        # main control
        self.controller = controller
        self.main_window_w = []

        # general urwid items
        clock_text = seconds_to_text(self.controller.stress_time)
        self.clock_view = urwid.Text(('bold text', clock_text), align="center")
        self.refresh_rate_ctrl = urwid.Edit(('bold text', u'Refresh[s]:'),
                                            self.controller.refresh_rate)
        self.hline = urwid.AttrWrap(urwid.SolidFill(u'_'), 'line')

        self.mode_buttons = []

        # Visible graphs are the graphs currently displayed, this is a
        # subset of the available graphs for display
        self.graph_place_holder = urwid.WidgetPlaceholder(urwid.Pile([]))

        # construct sources
        possible_source = [TempSource(self.controller.temp_thresh),
                           FreqSource(),
                           UtilSource(),
                           RaplPowerSource()]
        self.source_list = [s for s in possible_source if s.get_is_available()]

        # construct the variouse menus during init phase
        self.stress_menu = StressMenu(self.on_menu_close)
        self.help_menu = HelpMenu(self.on_menu_close)
        self.about_menu = AboutMenu(self.on_menu_close)
        self.sensors_menu = SensorsMenu(self.on_sensors_menu_close,
                                        self.source_list,
                                        self.controller.source_default_conf)
        self.global_data = GlobalData(is_admin)
        self.stress_menu.sqrt_workers = str(self.global_data.num_cpus)

        # call super
        urwid.WidgetPlaceholder.__init__(self, self.main_window())
        urwid.connect_signal(self.refresh_rate_ctrl, 'change',
                             self.update_refresh_rate)

    def update_refresh_rate(self, edit, new_refresh_rate):
        try:
            if float(new_refresh_rate) <= 0.001:
                pass
            else:
                self.controller.refresh_rate = new_refresh_rate
        except ValueError:
            self.controller.refresh_rate = '2.0'

    def update_displayed_information(self):
        """ Update all the graphs that are being displayed """

        for key, val in self.available_summaries.items():
            val.source.update()

        for g in self.visible_graphs.values():
            g.update_displayed_graph_data()
        # update graph summery

        for s in self.available_summaries.values():
            s.update()

        # Only update clock if not is stress mode
        if self.controller.mode.get_current_mode() != 'Monitor':
            self.controller.stress_time = (timeit.default_timer() -
                                           self.controller.stress_start_time)
        self.clock_view.set_text(('bold text', seconds_to_text(
            int(self.controller.stress_time))))

    def on_reset_button(self, w):
        """Reset graph data and display empty graph"""
        for g in self.visible_graphs.values():
            g.reset()
        for g in self.graphs.values():
            try:
                g.source.reset()
            except NotImplementedError:
                pass
        # Reset clock
        self.controller.stress_time = 0

        self.update_displayed_information()

    def on_menu_close(self):
        """Return to main screen"""
        self.original_widget = self.main_window_w

    def on_sensors_menu_close(self, update):
        """Return to main screen and update sensor that
        are active in the view"""
        logging.info("closing sensor menu, update=" + str(update))
        if update:
            for sensor, visible_sensors in \
                    self.sensors_menu.sensor_current_active_dict.items():
                self.graphs[sensor].set_visible_graphs(visible_sensors)
                # If not sensor is selected, do not display the graph
                if not any(visible_sensors):
                    del self.visible_graphs[sensor]
                # Update visible graphs if a sensor was selected
                else:
                    self.visible_graphs[sensor] = self.graphs[sensor]
            self.show_graphs()

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

    def on_sensors_menu_open(self, w):
        """Open Sensor menu on top of existing frame"""
        self.original_widget = urwid.Overlay(
            self.sensors_menu.main_window,
            self.original_widget,
            ('relative', self.left_margin),
            self.sensors_menu.get_size()[1],
            ('relative', self.top_margin),
            self.sensors_menu.get_size()[0])

    def on_mode_button(self, my_button, state):
        """Notify the controller of a new mode setting."""
        if state:
            # The new mode is the label of the button
            self.controller.set_mode(my_button.get_label())
            self.controller.start_stress()

    def on_mode_change(self, m):
        """Handle external mode change by updating radio buttons."""
        for rb in self.mode_buttons:
            if rb.get_label() == m:
                rb.set_state(True, do_callback=False)
                break

    def on_unicode_checkbox(self, w=None, state=False):
        """Enable smooth edges if utf-8 is supported"""
        logging.debug("unicode State is " + str(state))

        # Update the controller to the state of the checkbox
        self.controller.smooth_graph_mode = state
        if state:
            self.hline = urwid.AttrWrap(
                urwid.SolidFill(u'\N{LOWER ONE QUARTER BLOCK}'), 'line')
        else:
            self.hline = urwid.AttrWrap(urwid.SolidFill(u'_'), 'line')

        for g_name, g in self.graphs.items():
            g.set_smooth_colors(state)

        self.show_graphs()

    def exit_program(self, w=None):
        """ Kill all stress operations upon exit"""
        kill_child_processes(self.controller.mode.get_stress_process())
        raise urwid.ExitMainLoop()

    def save_settings(self, w=None):
        """ Save the current configuration to a user config file """

        if not user_config_dir_exists():
            make_user_config_dir()

        conf = configparser.ConfigParser()
        config_file = get_user_config_file()
        with open(config_file, 'w') as cfgfile:
            conf.add_section('GraphControll')
            conf.set('GraphControll', 'refresh', str(
                self.controller.refresh_rate))
            conf.set('GraphControll', 'UTF8', str(
                self.controller.smooth_graph_mode))

            # Save settings for sensors menu
            for source, visible_sensors in \
                    self.sensors_menu.sensor_current_active_dict.items():
                conf.add_section(source)

                source_list = self.source_list
                # TODO: consider changing sensors_list to dict
                curr_sensor = [x for x in source_list if
                               x.get_source_name() == source][0]
                logging.debug("Saving settings for" + str(curr_sensor))
                sensor_list = curr_sensor.get_sensor_list()
                for sensor_id, sensor in enumerate(sensor_list):
                    conf.set(source, sensor, str(visible_sensors[sensor_id]))
            conf.write(cfgfile)

    def graph_controls(self):
        """ Display sidebar controls. i.e. buttons, and controls"""
        modes = self.controller.get_modes()
        # setup mode radio buttons
        group = []
        for m in modes:
            rb = radio_button(group, m, self.on_mode_button)
            self.mode_buttons.append(rb)

        # Create list of buttons
        control_options = [button("Reset", self.on_reset_button)]
        if stress_installed:
            control_options.append(button('Stress Options',
                                          self.on_stress_menu_open))
        control_options.append(button('Sensors',
                                      self.on_sensors_menu_open))
        control_options.append(button('Help', self.on_help_menu_open))
        control_options.append(button('About', self.on_about_menu_open))

        # Create the menu
        animate_controls = urwid.GridFlow(control_options, 18, 2, 0, 'center')

        # Create smooth graph selection button
        default_smooth = self.controller.smooth_graph_mode
        if urwid.get_encoding_mode() == "utf8":
            unicode_checkbox = urwid.CheckBox(
                "Smooth Graph", state=default_smooth,
                on_state_change=self.on_unicode_checkbox)
            # Init the state of the graph accoding to the selected mode
            self.on_unicode_checkbox(state=default_smooth)
        else:
            unicode_checkbox = urwid.Text(
                "UTF-8 encoding not detected")

        install_stress_message = urwid.Text("")
        if not stress_installed:
            install_stress_message = urwid.Text(
                ('button normal', u"(N/A) install stress"))

        buttons = [urwid.Text(('bold text', u"Modes"), align="center"),
                   ] + self.mode_buttons + [
            install_stress_message,
            urwid.LineBox(self.clock_view),
            urwid.Divider(),
            urwid.Text(('bold text', u"Control Options"), align="center"),
            animate_controls,
            urwid.Divider(),
            self.refresh_rate_ctrl,
            urwid.Divider(),
            urwid.LineBox(unicode_checkbox),
            urwid.Divider(),
            button("Save Settings", self.save_settings),
            urwid.Divider(),
            button("Quit", self.exit_program),
        ]

        return buttons

    def show_graphs(self):
        """Show a pile of the graph selected for dislpay"""
        elements = itertools.chain.from_iterable(
            ([graph, ('fixed', 1, self.hline)]
                for graph in self.visible_graphs.values()))
        self.graph_place_holder.original_widget = urwid.Pile(elements)

    @staticmethod
    def cpu_stats():
        """Read and display processor name """
        cpu_name = urwid.Text("CPU Name N/A", align="center")
        try:
            cpu_name = urwid.Text(get_processor_name().strip(), align="center")
        except OSError:
            logging.info("CPU name not available")
        cpu_stats = [cpu_name, urwid.Divider()]
        return cpu_stats

    def graph_stats(self):

        fixed_stats = []
        for key, val in self.available_summaries.items():
            fixed_stats += val.get_text_item_list()
            fixed_stats += [urwid.Text('')]

        # return fixed_stats pile widget
        return urwid.Pile(fixed_stats)

    def main_window(self):
        # initiating the graphs
        self.graphs = OrderedDict()
        self.summaries = OrderedDict()

        for source in self.source_list:
            source_name = source.get_source_name()
            color_pallet = source.get_pallet()
            alert_pallet = source.get_alert_pallet()
            self.graphs[source_name] = StuiBarGraphVector(
                source, color_pallet[0], color_pallet[1],
                color_pallet[2], color_pallet[3],
                len(source.get_sensor_list()),
                self.sensors_menu.sensor_current_active_dict[source_name],
                alert_colors=alert_pallet
            )

            self.summaries[source_name] = SummaryTextList(
                self.graphs[source_name].source
            )

        fan_source = FanSource()
        if fan_source.get_is_available():
            self.summaries[fan_source.get_source_name()] = SummaryTextList(
                fan_source)

        # Check if source is available and add it to a dict of visible graphs
        # and summaryies.
        # All available summaries are always visible
        self.visible_graphs = OrderedDict(
            (key, val) for key, val in self.graphs.items()
            if val.get_is_available())

        # Do not show the graph if there is no selected sensors
        for key in self.graphs.keys():
            if not any(self.sensors_menu.sensor_current_active_dict[key]):
                del self.visible_graphs[key]

        self.available_summaries = OrderedDict(
            (key, val) for key, val in self.summaries.items() if
            val.get_is_available())

        self.show_graphs()

        cpu_stats = self.cpu_stats()
        graph_controls = self.graph_controls()
        graph_stats = self.graph_stats()

        text_col = ViListBox(urwid.SimpleListWalker(cpu_stats +
                                                    graph_controls +
                                                    [urwid.Divider()] +
                                                    [graph_stats]))

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
    The GraphController holds the state of the graph, this includes the current
    * Operation mode (stress/no-stress)
    * Current selected graphs for display,
    * The state of the radio and selector buttons
    * The current graphs refresh rate

    The controller is generated once, and is updated according to inputs
    """
    def __init__(self, args):

        # Load and configure user config dir when controller starts
        if not user_config_dir_exists():
            user_config_dir = make_user_config_dir()
        else:
            user_config_dir = get_user_config_dir()

        self.script_hooks_enabled = True
        if user_config_dir is None:
            logging.warning("Failed to find or create scripts directory,\
                             proceeding without scripting support")
            self.script_hooks_enabled = False
        else:
            self.script_loader = ScriptHookLoader(user_config_dir)

        # Use user config file if one was saved before
        self.conf = None
        if user_config_file_exists():
            self.conf = configparser.ConfigParser()
            self.conf.read(get_user_config_file())
        else:
            logging.debug("Config file not found")

        # Set refresh rate accorrding to user config
        self.refresh_rate = '2.0'
        try:
            self.refresh_rate = str(self.conf.getfloat(
                'GraphControll', 'refresh'))
            logging.debug("User refresh rate: " + str(self.refresh_rate))
        except (AttributeError, ValueError, configparser.NoOptionError,
                configparser.NoSectionError):
            logging.debug("No refresh rate configed")

        # Set initial smooth graph state according to user config
        self.smooth_graph_mode = False
        try:
            if self.conf.getboolean('GraphControll', 'UTF8'):
                self.smooth_graph_mode = True
            else:
                logging.debug("UTF8 selected as " +
                              self.conf.get('GraphControll', 'UTF8'))
        except (AttributeError, ValueError, configparser.NoOptionError,
                configparser.NoSectionError):
            logging.debug("No user config for utf8")

        self.temp_thresh = args.t_thresh

        # Try to load high temperature threshold if configured
        if args.t_thresh is None:
            try:
                self.temp_thresh = self.conf.get('TempControll', 'threshold')
                logging.debug("Temperature threshold set to " +
                              str(self.temp_thresh))
            except (AttributeError, ValueError, configparser.NoOptionError,
                    configparser.NoSectionError):
                logging.debug("No user config for temp threshold")

        # Load sensors config if available
        sources = ['Temp', 'Frequency', 'Util', 'Power']
        self.source_default_conf = defaultdict(list)
        for source in sources:
            options = list(self.conf.items(source))
            for option in options:
                # Returns tuples of values in order
                self.source_default_conf[source].append(str_to_bool(option[1]))

        # Needed for use in view
        self.args = args

        self.animate_alarm = None
        self.terminal = args.terminal
        self.json = args.json
        self.mode = GraphMode()

        self.handle_mouse = not args.no_mouse

        self.stress_start_time = 0
        self.stress_time = 0

        self.view = GraphView(self)
        # use the first mode (no stress) as the default
        mode = self.get_modes()[0]
        self.mode.set_mode(mode)
        # update the view
        self.view.on_mode_change(mode)
        self.view.update_displayed_information()

        # Update csv file to save
        self.csv_file = None
        self.save_csv = args.csv
        if args.csv_file is not None:
            self.csv_file = args.csv_file
            logging.info("Printing output to csv " + self.csv_file)
        elif args.csv_file is None and args.csv:
            self.csv_file = DEFAULT_CSV_FILE

    def get_modes(self):
        """Allow our view access to the list of modes."""
        return self.mode.get_modes()

    def set_mode(self, m):
        """Allow our view to set the mode."""
        rval = self.mode.set_mode(m)
        self.view.update_displayed_information()
        return rval

    def main(self):
        self.loop = MainLoop(self.view, DEFAULT_PALETTE,
                             handle_mouse=self.handle_mouse)
        self.animate_graph()
        try:
            self.loop.run()
        except (ZeroDivisionError) as e:
            logging.debug("Some stat caused divide by zero exception. Exiting")
            logging.error(e, exc_info=True)
            print(ERROR_MESSAGE)
        except (AttributeError) as e:
            logging.error("Catch attribute Error in urwid and restart")
            logging.error(e, exc_info=True)
            print(ERROR_MESSAGE)
        except (psutil.NoSuchProcess) as e:
            logging.error("No such proccess error")
            logging.error(e, exc_info=True)
            print(ERROR_MESSAGE)

    def animate_graph(self, loop=None, user_data=None):
        """update the graph and schedule the next update"""
        if self.save_csv or self.csv_file is not None:
            output_to_csv(self.view.summaries, self.csv_file)

        self.view.update_displayed_information()
        self.animate_alarm = self.loop.set_alarm_in(
            float(self.refresh_rate), self.animate_graph)
        # Update
        global debug_run_counter
        if self.args.debug_run:
            debug_run_counter += int(float(self.refresh_rate))
            if debug_run_counter >= 5:
                self.view.exit_program()

    def start_stress(self):
        mode = self.mode
        if mode.get_current_mode() == 'Stress':

            self.stress_start_time = timeit.default_timer()
            self.stress_time = 0

            kill_child_processes(mode.get_stress_process())
            mode.set_stress_process(None)
            # This is not pretty, but this is how we know stress started
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
                    stress_proc = subprocess.Popen(stress_cmd, stdout=DEVNULL,
                                                   stderr=DEVNULL, shell=False)
                    mode.set_stress_process(psutil.Process(stress_proc.pid))
                except OSError:
                    logging.debug("Unable to start stress")

        elif mode.get_current_mode() == 'FIRESTARTER':
            logging.debug('Started FIRESTARTER mode')
            kill_child_processes(mode.get_stress_process())
            mode.set_stress_process(None)

            stress_cmd = fire_starter

            self.stress_start_time = timeit.default_timer()
            self.stress_time = 0

            logging.debug("Firestarter " + str(fire_starter))
            with open(os.devnull, 'w') as DEVNULL:
                try:
                    stress_proc = subprocess.Popen(
                        stress_cmd,
                        stdout=DEVNULL,
                        stderr=DEVNULL,
                        shell=False)
                    mode.set_stress_process(psutil.Process(stress_proc.pid))
                    logging.debug('Started process' +
                                  str(mode.get_stress_process()))
                except OSError:
                    logging.debug("Unable to start stress")

        else:
            logging.debug('Monitoring')
            kill_child_processes(mode.get_stress_process())
            mode.set_stress_process(None)

        # Start a new clock upon starting a new stress test
        self.view.clock_view.set_text(('bold text', seconds_to_text(
            int(self.stress_time))))


def main():
    args = get_args()
    # Print version and exit
    if args.version:
        print(VERSION_MESSAGE)
        exit(0)

    # Setup logging util
    global log_file
    log_file = DEFAULT_LOG_FILE
    if args.debug_run:
        args.debug = True
    if args.debug or args.debug_file is not None:
        level = logging.DEBUG
        if args.debug_file is not None:
            log_file = args.debug_file
        log_formatter = logging.Formatter(
            "%(asctime)s [%(funcName)s()] [%(levelname)-5.5s]  %(message)s")
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

    if args.terminal or args.json:
        logging.info("Printing single line to terminal")
        sources = [FreqSource(), TempSource(),
                   UtilSource(),
                   RaplPowerSource(),
                   FanSource()]
        if args.terminal:
            output_to_terminal(sources)
        elif args.json:
            output_to_json(sources)

    global graph_controller
    graph_controller = GraphController(args)
    graph_controller.main()


def get_args():

    parser = argparse.ArgumentParser(
        description=INTRO_MESSAGE,
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('-d', '--debug',
                        default=False, action='store_true',
                        help="Output debug log to _s-tui.log")
    parser.add_argument('--debug-file',
                        default=None,
                        help="Use a custom debug file. Default: " +
                        "_s-tui.log")
    # This is mainly to be used for testing purposes
    parser.add_argument('-dr', '--debug_run',
                        default=False, action='store_true',
                        help="Run for 5 seconds and quit")
    parser.add_argument('-c', '--csv', action='store_true',
                        default=False, help="Save stats to csv file")
    parser.add_argument('--csv-file',
                        default=None,
                        help="Use a custom CSV file. Default: " +
                        "s-tui_log_<TIME>.csv")
    parser.add_argument('-t', '--terminal', action='store_true',
                        default=False,
                        help="Display a single line of stats without tui")
    parser.add_argument('-j', '--json', action='store_true',
                        default=False,
                        help="Display a single line of stats in JSON format")
    parser.add_argument('-nm', '--no-mouse', action='store_true',
                        default=False, help="Disable Mouse for TTY systems")
    parser.add_argument('-v', '--version',
                        default=False, action='store_true',
                        help="Display version")
    parser.add_argument('-tt', '--t_thresh',
                        default=None,
                        help="High Temperature threshold. Default: 80")
    args = parser.parse_args()
    return args


if '__main__' == __name__:
    main()
