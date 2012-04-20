#!/usr/bin/env python

import cProfile

import urwid
import sys
import time
from random import *

UPDATE_RATE = 0.1
RESOLVE_RATE = 0.5
START_DELAY = 2
NEXT_DELAY = 4  # cycles stagger

class uplink_text:

    def __init__(self, text, width):
        self.rng = Random()
        self.width = width
        self.text = text.center(width)
        self.widget = urwid.Text("", align='center')
        self.unresolved_chars = range(len(self.text))

    def make_mask(self):
        m = ""
        for i in range(self.width):
            if not i in self.unresolved_chars:
                m = m + self.text[i]
            else:
                m = m + chr(self.rng.randrange(33, 122))
        return m

    def update(self):
        mask = self.make_mask()
        self.widget.set_text(mask)

    def resolve_char(self):
        n = self.rng.randrange(len(self.unresolved_chars))
        del self.unresolved_chars[n]

    def fully_resolved(self):
        return len(self.unresolved_chars) == 0

# has to be a function not a method
def alarm_handler(loop, data):
    (selector, event, val) = data;

    if event == event_type.JUMBLE:
        selector.update()
    elif event == event_type.RESOLVE:
        selector.resolve_char(val)

class event_type:
    JUMBLE=1
    RESOLVE=2

class barcamp_prize_selector:

    def __init__(self, peep_list):

        self.people = []
        i = 0
        for p in peep_list:
            self.people.append(uplink_text(p, 20))
            i = i + 1
        self.loop = None    # main event loop
        self.resolving = -1 # index of which item we are resolving
        self.started = []
        self.s = False

    def start(self, val):
        if val < len (self.people):
            self.started.append(val)
            self.s = True


    def update(self):
        for p in self.people:
            p.update()
        self.loop.set_alarm_in(UPDATE_RATE, alarm_handler, (self, event_type.JUMBLE, None))

    def resolve_char(self, count):
        for val in self.started:
            self.people[val].resolve_char()
            if self.people[val].fully_resolved():
                self.started.remove(val)
        if self.s and len(self.started) == 0:
            raise urwid.ExitMainLoop

        if (count % NEXT_DELAY) == 0:
                self.start (count / NEXT_DELAY)
        
        self.loop.set_alarm_in(RESOLVE_RATE, alarm_handler, (self, event_type.RESOLVE, count + 1))

    def render(self):

        widgets = []
        for p in self.people:
            p.update()
            widgets.append(p.widget)
            widgets.append(urwid.Divider())
            
        pile = urwid.Pile(widgets)
        fill = urwid.Filler(pile)
        self.loop = urwid.MainLoop(fill)

        # start resolving after 10 seconds
        self.loop.set_alarm_in(START_DELAY, alarm_handler, (self, event_type.RESOLVE, 0))

        self.update()
        self.loop.run()

if __name__ == "__main__":
    names = [
            "Edd Barrett", "Matt Mole", "Han Greer", "Tris Linell", "Gunther Pleasureman"
            ]
    b = barcamp_prize_selector(names)
    #cProfile.run('b.render()')
    b.render()
