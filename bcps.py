#!/usr/bin/env python

import urwid
import sys
import time
from random import *

class uplink_text:

    def __init__(self, text, width):
        self.rng = Random()
        self.width = width
        self.text = text.center(width)
        self.widget = urwid.Text("", align='center')
        self.resolved_chars = []

    def make_mask(self):
        m = ""
        for i in range(self.width):
            if i in self.resolved_chars:
                m = m + self.text[i]
            else:
                m = m + chr(self.rng.randrange(33, 122))
        return m

    def update(self):
        mask = self.make_mask()
        self.widget.set_text(mask)

    def resolve_char(self):
        ok = False;

        while not ok:
            n = self.rng.randrange(self.width)
            if not n in self.resolved_chars:
                ok = True
        self.resolved_chars.append(n)

    def fully_resolved(self):
        if len(self.resolved_chars) == len(self.text):
            return True
        return False

# has to be a function not a method
def alarm_handler(loop, data):
    (selector, event) = data;

    if event == event_type.JUMBLE:
        selector.update()
    elif event == event_type.RESOLVE:
        selector.resolve_char()

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

    def update(self):
        for p in self.people:
            p.update()
        self.loop.set_alarm_in(.1, alarm_handler, (self, event_type.JUMBLE))

    def resolve_char(self):

        # done?
        if self.resolving >= len(self.people):
            time.sleep(5)
            sys.exit(1)

        # -1 while intro is running
        if self.resolving == -1:
            self.resolving = 0
        else:
            self.people[self.resolving].resolve_char()
            if self.people[self.resolving].fully_resolved():
                self.resolving = self.resolving + 1

        self.loop.set_alarm_in(.2, alarm_handler, (self, event_type.RESOLVE))

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
        self.loop.set_alarm_in(2, alarm_handler, (self, event_type.RESOLVE))

        self.update()
        self.loop.run()

if __name__ == "__main__":
    names = [
            "Edd Barrett", "Matt Mole", "Han Greer", "Tris Linell", "Gunther Pleasureman"
            ]
    b = barcamp_prize_selector(names)
    b.render()
