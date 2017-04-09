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

import urwid
import random

import math
import time

UPDATE_INTERVAL = 0.2

def update_value_2(self):
    last_value = random.randint(0, 50)
    self.rand_data.append(last_value)
    self.rand_data = self.rand_data[1:]

def sin100( x ):
    """
    A sin function that returns values between 0 and 100 and repeats
    after x == 100.
    """
    return 50 + 50 * math.sin( x * math.pi / 50 )

class GraphModel:
    """
    A class responsible for storing the data that will be displayed
    on the graph, and keeping track of which mode is enabled.
    """

    data_max_value = 100

    def __init__(self):
        data = [ ('Saw', range(0,100,2)*2),
            ('Rand', [random.randint(0, 10)
                        for x in range(100)]),
            ]
        self.modes = []
        self.data = {}
        for m, d in data:
            self.modes.append(m)
            self.data[m] = d

    def get_modes(self):
        return self.modes

    def set_mode(self, m):
        self.current_mode = m

    def get_data(self, offset, r):
        """
        Return the data in [offset:offset+r], the maximum value
        for items returned, and the offset at which the data
        repeats.
        """
        l = []
        d = self.data[self.current_mode]
        while r:
            offset = offset % len(d)
            segment = d[offset:offset+r]
            r -= len(segment)
            offset += len(segment)
            l += segment
        return l, self.data_max_value, len(d)


class GraphView(urwid.WidgetWrap):
    """
    A class responsible for providing the application's interface and
    graph display.
    """

    palette = [
        ('body',         'black',      'light gray', 'standout'),
        ('header',       'white',      'dark red',   'bold'),
        ('screen edge',  'light blue', 'dark cyan'),
        ('main shadow',  'dark gray',  'black'),
        ('line',         'black',      'light gray', 'standout'),
        ('bg background','light gray', 'black'),
        ('bg 1',         'black',      'dark blue', 'standout'),
        ('bg 1 smooth',  'dark blue',  'black'),
        ('bg 2',         'black',      'dark cyan', 'standout'),
        ('bg 2 smooth',  'dark cyan',  'black'),
        ('button normal','light gray', 'dark blue', 'standout'),
        ('button select','white',      'dark green'),
        ('line',         'black',      'light gray', 'standout'),
        ('pg normal',    'white',      'black', 'standout'),
        ('pg complete',  'white',      'dark magenta'),
        ('pg smooth',     'dark magenta','black')
        ]

    graph_samples_per_bar = 10
    graph_num_bars = 5
    graph_offset_per_second = 5

    def __init__(self, controller):
        self.controller = controller
        self.started = True
        self.start_time = None
        self.offset = 0
        self.last_offset = None
        self.rand_data = [0] * self.graph_num_bars

        urwid.WidgetWrap.__init__(self, self.main_window())

    def get_offset_now(self):
        if self.start_time is None:
            return 0
        if not self.started:
            return self.offset
        tdelta = time.time() - self.start_time
        return int(self.offset + (tdelta*self.graph_offset_per_second))

    def update_value(self):
        last_value = random.randint(0,100)
        self.rand_data.append(last_value)
        self.rand_data = self.rand_data[1:]

    def update_graph(self, force_update=False):
        o = self.get_offset_now()
        if o == self.last_offset and not force_update:
            return False
        self.last_offset = o
        gspb = self.graph_samples_per_bar
        r = gspb * self.graph_num_bars
        d, max_value, repeat = self.controller.get_data( o, r )
        l = []
        self.update_value()

        for n in range(self.graph_num_bars):
            value = self.rand_data[n]
            # toggle between two bar types
            if n & 1:
                l.append([0,value])
            else:
                l.append([value,0])
        self.graph.set_data(l,max_value)

        # also update progress
        if (o//repeat)&1:
            # show 100% for first half, 0 for second half
            if o%repeat > repeat//2:
                prog = 0
            else:
                prog = 1
        else:
            prog = float(o%repeat) / repeat
        self.animate_progress.set_completion( prog )
        return True

    def on_animate_button(self, button):
        """Toggle started state and button text."""
        if self.started: # stop animation
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
            self.controller.set_mode( button.get_label() )
        self.last_offset = None

    def on_mode_change(self, m):
        """Handle external mode change by updating radio buttons."""
        for rb in self.mode_buttons:
            if rb.get_label() == m:
                rb.set_state(True, do_callback=False)
                break
        self.last_offset = None

    def on_unicode_checkbox(self, w, state):
        self.graph = self.bar_graph( state )
        self.graph_wrap._w = self.graph
        self.animate_progress = self.progress_bar( state )
        self.animate_progress_wrap._w = self.animate_progress
        self.update_graph( True )


    def main_shadow(self, w):
        """Wrap a shadow and background around widget w."""
        bg = urwid.AttrWrap(urwid.SolidFill(u"\u2592"), 'screen edge')
        shadow = urwid.AttrWrap(urwid.SolidFill(u" "), 'main shadow')

        bg = urwid.Overlay( shadow, bg,
            ('fixed left', 3), ('fixed right', 1),
            ('fixed top', 2), ('fixed bottom', 1))
        w = urwid.Overlay( w, bg,
            ('fixed left', 2), ('fixed right', 3),
            ('fixed top', 1), ('fixed bottom', 2))
        return w

    def bar_graph(self, smooth=False):
        satt = None
        if smooth:
            satt = {(1,0): 'bg 1 smooth', (2,0): 'bg 2 smooth'}
        w = urwid.BarGraph(['bg background','bg 1','bg 2'], satt=satt)
        return w

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
        self.mode_buttons = []
        group = []
        for m in modes:
            rb = self.radio_button( group, m, self.on_mode_button )
            self.mode_buttons.append( rb )
        # setup animate button
        self.animate_button = self.button( "", self.on_animate_button)
        self.on_animate_button( self.animate_button )
        self.offset = 0
        self.animate_progress = self.progress_bar()
        animate_controls = urwid.GridFlow( [
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

        self.animate_progress_wrap = urwid.WidgetWrap(
            self.animate_progress)

        l = [    urwid.Text("Mode",align="center"),
            ] + self.mode_buttons + [
            urwid.Divider(),
            urwid.Text("Animation",align="center"),
            animate_controls,
            self.animate_progress_wrap,
            urwid.Divider(),
            urwid.LineBox( unicode_checkbox ),
            urwid.Divider(),
            self.button("Quit", self.exit_program ),
            ]
        w = urwid.ListBox(urwid.SimpleListWalker(l))
        return w

    def main_window(self):
        self.graph = self.bar_graph()
        self.graph_wrap = urwid.WidgetWrap( self.graph )
        vline = urwid.AttrWrap( urwid.SolidFill(u'\u2502'), 'line')
        hline = urwid.AttrWrap(urwid.SolidFill(u'\N{LOWER ONE QUARTER BLOCK}'), 'line')

        c = self.graph_controls()
        l = [('weight',2,self.graph_wrap), ('fixed',1,hline), ('weight',2,self.graph_wrap)]

        r = urwid.Pile(l, focus_item=None)

        w = urwid.Columns([('weight',2,r),
            ('fixed',1,vline), c],
            dividechars=1, focus_column=2)
        w = urwid.Padding(w,('fixed left',1),('fixed right',0))
        w = urwid.AttrWrap(w,'body')
        w = urwid.LineBox(w)
        w = urwid.AttrWrap(w,'line')
        w = self.main_shadow(w)
        return w


class GraphController:
    """
    A class responsible for setting up the model and view and running
    the application.
    """
    def __init__(self):
        self.animate_alarm = None
        self.model = GraphModel()
        self.view = GraphView( self )
        # use the first mode as the default
        mode = self.get_modes()[0]
        self.model.set_mode( mode )
        # update the view
        self.view.on_mode_change( mode )
        self.view.update_graph(True)

    def get_modes(self):
        """Allow our view access to the list of modes."""
        return self.model.get_modes()

    def set_mode(self, m):
        """Allow our view to set the mode."""
        rval = self.model.set_mode( m )
        self.view.update_graph(True)
        return rval

    def get_data(self, offset, range):
        """Provide data to our view for the graph."""
        return self.model.get_data( offset, range )


    def main(self):
        self.loop = urwid.MainLoop(self.view, self.view.palette)
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

if '__main__'==__name__:
    main()
