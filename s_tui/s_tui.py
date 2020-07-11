#!/usr/bin/python

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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA
#
# This implementation was inspired by Ian Ward
# Urwid web site: http://excess.org/urwid/

"""CPU stress and monitoring utility"""

from __future__ import absolute_import

import argparse
import signal
import itertools
import logging
import os
import subprocess
import time
import timeit
from collections import OrderedDict
from collections import defaultdict
import sys

import psutil
import urwid

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

# Menues
from s_tui.about_menu import AboutMenu
from s_tui.help_menu import HelpMenu
from s_tui.help_menu import HELP_MESSAGE
from s_tui.stress_menu import StressMenu
from s_tui.sensors_menu import SensorsMenu
# Helpers
from s_tui.helper_functions import __version__
from s_tui.helper_functions import get_processor_name
from s_tui.helper_functions import kill_child_processes
from s_tui.helper_functions import output_to_csv
from s_tui.helper_functions import output_to_terminal
from s_tui.helper_functions import output_to_json
from s_tui.helper_functions import get_user_config_dir
from s_tui.helper_functions import get_user_config_file
from s_tui.helper_functions import make_user_config_dir
from s_tui.helper_functions import user_config_dir_exists
from s_tui.helper_functions import user_config_file_exists
from s_tui.helper_functions import seconds_to_text
from s_tui.helper_functions import str_to_bool
from s_tui.helper_functions import which
# Ui Elements
from s_tui.sturwid.ui_elements import ViListBox
from s_tui.sturwid.ui_elements import radio_button
from s_tui.sturwid.ui_elements import button
from s_tui.sturwid.ui_elements import DEFAULT_PALETTE
from s_tui.sturwid.bar_graph_vector import BarGraphVector
from s_tui.sturwid.summary_text_list import SummaryTextList
# Sources
from s_tui.sources.util_source import UtilSource
from s_tui.sources.freq_source import FreqSource
from s_tui.sources.temp_source import TempSource
from s_tui.sources.rapl_power_source import RaplPowerSource
from s_tui.sources.fan_source import FanSource
from s_tui.sources.script_hook_loader import ScriptHookLoader

UPDATE_INTERVAL = 1
HOOK_INTERVAL = 30 * 1000
DEGREE_SIGN = u'\N{DEGREE SIGN}'
ZERO_TIME = seconds_to_text(0)

DEFAULT_LOG_FILE = "_s-tui.log"

DEFAULT_CSV_FILE = "s-tui_log_" + time.strftime("%Y-%m-%d_%H_%M_%S") + ".csv"

VERSION_MESSAGE = \
    "s-tui " + __version__ +\
    " - (C) 2017-2020 Alex Manuskin, Gil Tsuker\n\
    Released under GNU GPLv2"

ERROR_MESSAGE = "\n\
        Oops! s-tui has encountered a fatal error\n\
        Please report this bug here: https://github.com/amanusk/s-tui"

graph_controller = None


class MainLoop(urwid.MainLoop):
    """ Inherit urwid Mainloop to catch special character inputs"""
    def signal_handler(self, frame):
        """signal handler for properly exiting Ctrl+C"""
        graph_controller.stress_conroller.kill_stress_process()
        raise urwid.ExitMainLoop()

    def unhandled_input(self, uinput):
        logging.debug('Caught %s', uinput)
        if uinput == 'q':
            graph_controller.stress_conroller.kill_stress_process()
            raise urwid.ExitMainLoop()

        if uinput == 'f1':
            graph_controller.view.on_help_menu_open(
                graph_controller.view.main_window_w)

        if uinput == 'esc':
            graph_controller.view.on_menu_close()

    signal.signal(signal.SIGINT, signal_handler)


class StressController:
    """
    Responsible for storing the data related to stress test options
    and operation
    """

    def __init__(self, stress_installed, firestarter_installed):
        self.stress_modes = ['Monitor']

        if stress_installed:
            self.stress_modes.append('Stress')

        if firestarter_installed:
            self.stress_modes.append('FIRESTARTER')

        self.current_mode = self.stress_modes[0]
        self.stress_process = None

    def get_modes(self):
        """ Returns all possible stress_modes for stress operations """
        return self.stress_modes

    def get_current_mode(self):
        """ Returns the current stress test mode, monitor/stress/other """
        return self.current_mode

    def set_mode(self, mode):
        """ Sets a stress test mode monitor/stress/other """
        self.current_mode = mode

    def get_stress_process(self):
        """ Returns the current external stress process running """
        return self.stress_process

    def set_stress_process(self, proc):
        """ Sets the current stress process running """
        self.stress_process = proc

    def kill_stress_process(self):
        """ Kills the current running stress process """
        try:
            kill_child_processes(self.stress_process)
        except psutil.NoSuchProcess:
            logging.debug("Stress process no longer exists")
        self.stress_process = None

    def start_stress(self, stress_cmd):
        """ Starts a new stress process with a given cmd """
        with open(os.devnull, 'w') as dev_null:
            try:
                stress_proc = subprocess.Popen(stress_cmd, stdout=dev_null,
                                               stderr=dev_null)
                self.set_stress_process(psutil.Process(stress_proc.pid))
            except OSError:
                logging.debug("Unable to start stress")


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
        self.clock_view = urwid.Text(ZERO_TIME, align="center")
        self.refresh_rate_ctrl = urwid.Edit((u'Refresh[s]:'),
                                            self.controller.refresh_rate)
        self.hline = urwid.AttrWrap(urwid.SolidFill(u' '), 'line')

        self.mode_buttons = []

        self.summary_widget_index = None

        # Visible graphs are the graphs currently displayed, this is a
        # subset of the available graphs for display
        self.graph_place_holder = urwid.WidgetPlaceholder(urwid.Pile([]))

        # construct the various menus during init phase
        self.stress_menu = StressMenu(self.on_menu_close,
                                      self.controller.stress_exe)
        self.help_menu = HelpMenu(self.on_menu_close)
        self.about_menu = AboutMenu(self.on_menu_close)
        self.graphs_menu = SensorsMenu(self.on_graphs_menu_close,
                                       self.controller.sources,
                                       self.controller.graphs_default_conf)
        self.summary_menu = SensorsMenu(self.on_summary_menu_close,
                                        self.controller.sources,
                                        self.controller.summary_default_conf)

        # call super
        urwid.WidgetPlaceholder.__init__(self, self.main_window())
        urwid.connect_signal(self.refresh_rate_ctrl, 'change',
                             self.update_refresh_rate)

    def update_refresh_rate(self, _, new_refresh_rate):
        # Special case of 'q' in refresh rate
        if 'q' in new_refresh_rate:
            self.on_exit_program()

        try:
            if float(new_refresh_rate) <= 0.001:
                pass
            else:
                self.controller.refresh_rate = new_refresh_rate
        except ValueError:
            self.controller.refresh_rate = '2.0'

    def update_displayed_information(self):
        """ Update all the graphs that are being displayed """

        for source in self.controller.sources:
            source_name = source.get_source_name()
            if (any(self.graphs_menu.active_sensors[source_name]) or
                    any(self.summary_menu.active_sensors[source_name])):
                source.update()

        for graph in self.visible_graphs.values():
            try:
                graph.update()
            except IndexError:
                logging.debug("Graph update failed")
                pass

        # update graph summery
        for summary in self.visible_summaries.values():
            try:
                summary.update()
            except IndexError:
                logging.debug("Summary update failed")
                pass

        # Only update clock if not is stress mode
        if self.controller.stress_conroller.get_current_mode() != 'Monitor':
            self.clock_view.set_text(seconds_to_text(
                (timeit.default_timer() - self.controller.stress_start_time)))

    def on_reset_button(self, _):
        """Reset graph data and display empty graph"""
        for graph in self.visible_graphs.values():
            graph.reset()
        for graph in self.graphs.values():
            try:
                graph.source.reset()
            except NotImplementedError:
                pass
        # Reset clock
        self.clock_view.set_text(ZERO_TIME)

        self.update_displayed_information()

    def on_menu_close(self):
        """Return to main screen"""
        self.original_widget = self.main_window_w

    def on_graphs_menu_close(self, update):
        """Return to main screen and update sensor that
        are active in the view"""
        logging.info("closing sensor menu, update=%s", update)
        if update:
            for sensor, visible_sensors in \
                    self.graphs_menu.active_sensors.items():
                self.graphs[sensor].set_visible_graphs(visible_sensors)
                # If not sensor is selected, do not display the graph
                if sensor in self.visible_graphs and not any(visible_sensors):
                    del self.visible_graphs[sensor]
                elif not any(visible_sensors):
                    pass
                # Update visible graphs if a sensor was selected
                else:
                    self.visible_graphs[sensor] = self.graphs[sensor]
            self.show_graphs()

        self.original_widget = self.main_window_w

    def on_summary_menu_close(self, update):
        """Return to main screen and update sensor that
        are active in the view"""
        logging.info("closing summary_menu menu, update=%s", update)
        if update:
            for sensor, visible_sensors in \
                    self.summary_menu.active_sensors.items():
                self.visible_summaries[sensor].update_visibility(
                    visible_sensors)

        self.main_window_w.base_widget[0].body[self.summary_widget_index] =\
            self._generate_summaries()

        self.original_widget = self.main_window_w

    def on_stress_menu_open(self, widget):
        """Open stress options"""
        self.original_widget = urwid.Overlay(self.stress_menu.main_window,
                                             self.original_widget,
                                             ('relative', self.left_margin),
                                             self.stress_menu.get_size()[1],
                                             ('relative', self.top_margin),
                                             self.stress_menu.get_size()[0])

    def on_help_menu_open(self, widget):
        """Open Help menu"""
        self.original_widget = urwid.Overlay(self.help_menu.main_window,
                                             self.original_widget,
                                             ('relative', self.left_margin),
                                             self.help_menu.get_size()[1],
                                             ('relative', self.top_margin),
                                             self.help_menu.get_size()[0])

    def on_about_menu_open(self, widget):
        """Open About menu"""
        self.original_widget = urwid.Overlay(self.about_menu.main_window,
                                             self.original_widget,
                                             ('relative', self.left_margin),
                                             self.about_menu.get_size()[1],
                                             ('relative', self.top_margin),
                                             self.about_menu.get_size()[0])

    def on_graphs_menu_open(self, widget):
        """Open Sensor menu on top of existing frame"""
        self.original_widget = urwid.Overlay(
            self.graphs_menu.main_window,
            self.original_widget,
            ('relative', self.left_margin),
            self.graphs_menu.get_size()[1],
            ('relative', self.top_margin),
            self.graphs_menu.get_size()[0])

    def on_summary_menu_open(self, widget):
        """Open Sensor menu on top of existing frame"""
        self.original_widget = urwid.Overlay(
            self.summary_menu.main_window,
            self.original_widget,
            ('relative', self.left_margin),
            self.summary_menu.get_size()[1],
            ('relative', self.top_margin),
            self.summary_menu.get_size()[0])

    def on_mode_button(self, my_button, state):
        """Notify the controller of a new mode setting."""
        if state:
            # The new mode is the label of the button
            self.controller.set_mode(my_button.get_label())

    def on_unicode_checkbox(self, w=None, state=False):
        """Enable smooth edges if utf-8 is supported"""
        logging.debug("unicode State is %s", state)

        # Update the controller to the state of the checkbox
        self.controller.smooth_graph_mode = state
        if state:
            self.hline = urwid.AttrWrap(
                urwid.SolidFill(u'\N{LOWER ONE QUARTER BLOCK}'), 'line')
        else:
            self.hline = urwid.AttrWrap(urwid.SolidFill(u' '), 'line')

        for graph in self.graphs.values():
            graph.set_smooth_colors(state)

        self.show_graphs()

    def on_save_settings(self, w=None):
        """ Calls controller save settings method """
        self.controller.save_settings()

    def on_exit_program(self, w=None):
        """ Calls controller exit_program method """
        self.controller.exit_program()

    def _generate_graph_controls(self):
        """ Display sidebar controls. i.e. buttons, and controls"""
        # setup mode radio buttons
        stress_modes = self.controller.stress_conroller.get_modes()
        group = []
        for mode in stress_modes:
            self.mode_buttons.append(radio_button(group, mode,
                                                  self.on_mode_button))

        # Set default radio button to "Monitor" mode
        self.mode_buttons[0].set_state(True, do_callback=False)

        # Create list of buttons
        control_options = list()
        control_options.append(button('Graphs',
                                      self.on_graphs_menu_open))
        control_options.append(button('Summaries',
                                      self.on_summary_menu_open))
        if self.controller.stress_exe:
            control_options.append(button('Stress Options',
                                          self.on_stress_menu_open))
        control_options.append(button("Reset", self.on_reset_button))
        control_options.append(button('Help', self.on_help_menu_open))
        control_options.append(button('About', self.on_about_menu_open))
        control_options.append(button("Save Settings",
                                      self.on_save_settings))
        control_options.append(button("Quit", self.on_exit_program))

        # Create the menu
        animate_controls = urwid.GridFlow(control_options, 18, 2, 0, 'center')

        # Create smooth graph selection button
        default_smooth = self.controller.smooth_graph_mode
        if urwid.get_encoding_mode() == "utf8":
            unicode_checkbox = urwid.CheckBox(
                "UTF-8", state=default_smooth,
                on_state_change=self.on_unicode_checkbox)
            # Init the state of the graph accoding to the selected mode
            self.on_unicode_checkbox(state=default_smooth)
        else:
            unicode_checkbox = urwid.Text(
                "[N/A] UTF-8")

        install_stress_message = urwid.Text("")
        if not self.controller.firestarter and not self.controller.stress_exe:
            install_stress_message = urwid.Text(
                ('button normal', u"(N/A) install stress"))

        clock_widget = []
        # if self.controller.stress_exe or self.controller.firestarter:
        if self.controller.stress_exe or self.controller.firestarter:
            clock_widget = [
                urwid.Text(('bold text', u"Stress Timer"), align="center"),
                self.clock_view
                ]

        controls = [urwid.Text(('bold text', u"Modes"), align="center")]
        controls += self.mode_buttons
        controls += [install_stress_message]
        controls += clock_widget
        controls += [
            urwid.Divider(),
            urwid.Text(('bold text', u"Control Options"), align="center"),
            animate_controls,
            urwid.Divider(),
            urwid.Text(('bold text', u"Visual Options"), align="center"),
            unicode_checkbox,
            self.refresh_rate_ctrl,
            urwid.Divider(),
            urwid.Text(('bold text', u"Summaries"), align="center"),
        ]

        return controls

    @staticmethod
    def _generate_cpu_stats():
        """Read and display processor name """
        cpu_name = urwid.Text("CPU Name N/A", align="center")
        try:
            cpu_name = urwid.Text(get_processor_name().strip(), align="center")
        except OSError:
            logging.info("CPU name not available")
        return [urwid.Text(('bold text', "CPU Detected"),
                           align="center"), cpu_name, urwid.Divider()]

    def _generate_summaries(self):

        fixed_stats = []
        for summary in self.visible_summaries.values():
            fixed_stats += summary.get_text_item_list()
            fixed_stats += [urwid.Text('')]

        # return fixed_stats pile widget
        return urwid.Pile(fixed_stats)

    def show_graphs(self):
        """Show a pile of the graph selected for dislpay"""
        elements = itertools.chain.from_iterable(
            ([graph]
             for graph in self.visible_graphs.values()))
        self.graph_place_holder.original_widget = urwid.Pile(elements)

    def main_window(self):
        # initiating the graphs
        self.graphs = OrderedDict()
        self.summaries = OrderedDict()

        for source in self.controller.sources:
            source_name = source.get_source_name()
            color_pallet = source.get_pallet()
            alert_pallet = source.get_alert_pallet()
            self.graphs[source_name] = BarGraphVector(
                source, color_pallet,
                len(source.get_sensor_list()),
                self.graphs_menu.active_sensors[source_name],
                alert_colors=alert_pallet
            )
            if self.controller.script_hooks_enabled:
                source.add_edge_hook(
                    self.controller.script_loader.load_script(
                        source.__class__.__name__, HOOK_INTERVAL)
                )  # Invoke threshold script every 30s

            self.summaries[source_name] = SummaryTextList(
                self.graphs[source_name].source,
                self.summary_menu.active_sensors[source_name],
            )

        # Check if source is available and add it to a dict of visible graphs
        # and summaries.
        # All available summaries are always visible
        self.visible_graphs = OrderedDict(
            (key, val) for key, val in self.graphs.items() if
            val.get_is_available())

        # Do not show the graph if there is no selected sensors
        for key in self.graphs.keys():
            if not any(self.graphs_menu.active_sensors[key]):
                del self.visible_graphs[key]

        self.visible_summaries = OrderedDict(
            (key, val) for key, val in self.summaries.items() if
            val.get_is_available())

        cpu_stats = self._generate_cpu_stats()
        graph_controls = self._generate_graph_controls()
        summaries = self._generate_summaries()

        text_col = ViListBox(urwid.SimpleListWalker(cpu_stats +
                                                    graph_controls +
                                                    [summaries]))

        vline = urwid.AttrWrap(urwid.SolidFill(u'|'), 'line')
        widget = urwid.Columns([('fixed', 20, text_col),
                                ('fixed', 1, vline),
                                ('weight', 2, self.graph_place_holder)],
                               dividechars=0, focus_column=0)

        widget = urwid.Padding(widget, ('fixed left', 1), ('fixed right', 1))
        self.main_window_w = widget

        base = self.main_window_w.base_widget[0].body
        self.summary_widget_index = len(base) - 1
        logging.debug("Pile index: %s", self.summary_widget_index)

        return self.main_window_w


class GraphController:
    """
    The GraphController holds the state of the graph, this includes the current
    * Operation mode (stress/no-stress)
    * Current selected graphs for display,
    * The state of the radio and selector buttons
    * The current graphs refresh rate

    The controller is generated once, and is updated according to inputs

    GraphController and GraphView are closely intertwined, there is a reference
    to each in the other.
    This is not perfect, but changes in the View reflect on the graph state and
    visa versa
    """

    def _load_config(self, t_thresh):
        """
        Uses configurations defined by user to configure sources for display.
        This should be the only place where sources are initiated

        This returns a list of sources after configurations are applied
        """
        # Load and configure user config dir when controller starts
        if not user_config_dir_exists():
            user_config_dir = make_user_config_dir()
        else:
            user_config_dir = get_user_config_dir()

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

        # Load refresh refresh rate from config
        try:
            self.refresh_rate = str(self.conf.getfloat(
                'GraphControll', 'refresh'))
            logging.debug("User refresh rate: %s", self.refresh_rate)
        except (AttributeError, ValueError, configparser.NoOptionError,
                configparser.NoSectionError):
            logging.debug("No refresh rate configed")

        # Change UTF8 setting from config
        try:
            if self.conf.getboolean('GraphControll', 'UTF8'):
                self.smooth_graph_mode = True
            else:
                logging.debug("UTF8 selected as %s",
                              self.conf.get('GraphControll', 'UTF8'))
        except (AttributeError, ValueError, configparser.NoOptionError,
                configparser.NoSectionError):
            logging.debug("No user config for utf8")

        # Try to load high temperature threshold if configured
        if t_thresh is None:
            try:
                self.temp_thresh = self.conf.get('GraphControll', 'TTHRESH')
                logging.debug("Temperature threshold set to %s",
                              self.temp_thresh)
            except (AttributeError, ValueError, configparser.NoOptionError,
                    configparser.NoSectionError):
                logging.debug("No user config for temp threshold")
        else:
            self.temp_thresh = t_thresh

        # This should be the only place where sources are configured
        possible_sources = [TempSource(self.temp_thresh),
                            FreqSource(),
                            UtilSource(),
                            RaplPowerSource(),
                            FanSource()]

        # Load sensors config if available
        sources = [x.get_source_name() for x in possible_sources
                   if x.get_is_available()]
        for source in sources:
            try:
                options = list(self.conf.items(source + ",Graphs"))
                for option in options:
                    # Returns tuples of values in order
                    self.graphs_default_conf[source].append(
                        str_to_bool(option[1]))
                options = list(self.conf.items(source + ",Summaries"))
                for option in options:
                    # Returns tuples of values in order
                    self.summary_default_conf[source].append(
                        str_to_bool(option[1]))
            except (AttributeError, ValueError, configparser.NoOptionError,
                    configparser.NoSectionError):
                logging.debug("Error reading sensors config")

        return possible_sources

    def _config_stress(self):
        """ Configures the possible stress processes and modes """
        # Configure stress_process
        self.stress_exe = None
        stress_installed = False
        self.stress_exe = which('stress')
        if self.stress_exe:
            stress_installed = True
        else:
            self.stress_exe = which('stress-ng')
            if self.stress_exe:
                stress_installed = True

        self.firestarter = None
        firestarter_installed = False
        if os.path.isfile('./FIRESTARTER/FIRESTARTER'):
            self.firestarter = os.path.join(os.getcwd(),
                                            'FIRESTARTER', 'FIRESTARTER')
            firestarter_installed = True
        else:
            firestarter_exe = which('FIRESTARTER')
            if firestarter_exe is not None:
                self.firestarter = firestarter_exe
                firestarter_installed = True

        return StressController(stress_installed, firestarter_installed)

    def __init__(self, args):
        self.conf = None
        self.script_hooks_enabled = True
        self.script_loader = None

        self.refresh_rate = '2.0'

        self.smooth_graph_mode = False

        self.summary_default_conf = defaultdict(list)
        self.graphs_default_conf = defaultdict(list)

        self.temp_thresh = None

        possible_sources = self._load_config(args.t_thresh)

        # Needed for use in view
        self.args = args

        self.stress_conroller = self._config_stress()

        self.handle_mouse = not args.no_mouse

        self.stress_start_time = 0

        # construct sources
        self.sources = [s for s in possible_sources if s.get_is_available()]

        # The view has a reference to the controller and visa versa
        self.view = GraphView(self)

        # Update csv file to save
        self.csv_file = None
        self.save_csv = args.csv
        if args.csv_file is not None:
            self.csv_file = args.csv_file
            logging.info("Printing output to csv %s", self.csv_file)
        elif args.csv_file is None and args.csv:
            self.csv_file = DEFAULT_CSV_FILE
        # Debug counter
        self.debug_run_counter = 0

    def set_mode(self, mode):
        """Allow our view to set the mode."""
        self.stress_conroller.set_mode(mode)
        self.update_stress_mode()

    def main(self):
        """ Starts the main loop and graph animation """
        loop = MainLoop(self.view, DEFAULT_PALETTE,
                        handle_mouse=self.handle_mouse)
        self.view.show_graphs()
        self.animate_graph(loop)
        try:
            loop.run()
        except (ZeroDivisionError) as err:
            # In case of Zero division, we want an error to return, and
            # get a clue where this happens
            logging.debug("Some stat caused divide by zero exception. Exiting")
            logging.error(err, exc_info=True)
            print(ERROR_MESSAGE)
        except (AttributeError) as err:
            # In this case we restart the loop, to address bug #50, where
            # urwid crashes on multiple presses on 'esc'
            logging.debug("Catch attribute Error in urwid and restart")
            logging.debug(err, exc_info=True)
            self.main()
        except (psutil.NoSuchProcess) as err:
            # This might happen if the stress process is not found, in this
            # case, we want to know why
            logging.error("No such process error")
            logging.error(err, exc_info=True)
            print(ERROR_MESSAGE)

    def update_stress_mode(self):
        """ Updates stress mode according to radio buttons state """

        self.stress_conroller.kill_stress_process()

        # Start a new clock upon starting a new stress test
        self.view.clock_view.set_text(ZERO_TIME)
        self.stress_start_time = timeit.default_timer()

        if self.stress_conroller.get_current_mode() == 'Stress':
            stress_cmd = self.view.stress_menu.get_stress_cmd()
            self.stress_conroller.start_stress(stress_cmd)

        elif self.stress_conroller.get_current_mode() == 'FIRESTARTER':
            stress_cmd = [self.firestarter]
            self.stress_conroller.start_stress(stress_cmd)

    def save_settings(self):
        """ Save the current configuration to a user config file """
        def _save_displayed_setting(conf, submenu):
            items = []
            if (submenu == "Graphs"):
                items = self.view.graphs_menu.active_sensors.items()
            elif (submenu == "Summaries"):
                items = self.view.summary_menu.active_sensors.items()

            for source, visible_sensors in items:
                section = source + "," + submenu
                conf.add_section(section)

                sources = self.sources
                logging.debug("Saving settings for %s", source)
                logging.debug("Visible sensors %s", visible_sensors)
                # TODO: consider changing sensors_list to dict
                curr_sensor = [x for x in sources if
                               x.get_source_name() == source][0]
                sensor_list = curr_sensor.get_sensor_list()
                for sensor_id, sensor in enumerate(sensor_list):
                    try:
                        conf.set(section, sensor, str(
                            visible_sensors[sensor_id]))
                    except IndexError:
                        conf.set(section, sensor, str(True))

        if not user_config_dir_exists():
            make_user_config_dir()

        conf = configparser.ConfigParser()
        config_file = get_user_config_file()
        with open(config_file, 'w') as cfgfile:
            conf.add_section('GraphControll')
            # Save the configured refresh rete
            conf.set('GraphControll', 'refresh', str(
                self.refresh_rate))
            # Save the configured UTF8 setting
            conf.set('GraphControll', 'UTF8', str(
                self.smooth_graph_mode))
            # Save the configured t_thresh
            if self.temp_thresh:
                conf.set('GraphControll', 'TTHRESH', str(
                    self.temp_thresh))

            _save_displayed_setting(conf, "Graphs")
            _save_displayed_setting(conf, "Summaries")
            conf.write(cfgfile)

    def exit_program(self):
        """ Kill all stress operations upon exit"""
        self.stress_conroller.kill_stress_process()
        raise urwid.ExitMainLoop()

    def animate_graph(self, loop, user_data=None):
        """
        Update the graph and schedule the next update
        This is where the magic happens
        """
        self.view.update_displayed_information()

        # Save to CSV if configured
        if self.save_csv or self.csv_file is not None:
            output_to_csv(self.view.summaries, self.csv_file)

        # Set next update
        self.animate_alarm = loop.set_alarm_in(
            float(self.refresh_rate), self.animate_graph)

        if self.args.debug_run:
            # refresh rate is a string in float format
            self.debug_run_counter += int(float(self.refresh_rate))
            if self.debug_run_counter >= 8:
                self.exit_program()


def main():
    args = get_args()
    # Print version and exit
    if args.version:
        print(VERSION_MESSAGE)
        sys.exit(0)

    # Setup logging util
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
        description=HELP_MESSAGE,
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


if __name__ == '__main__':
    main()
