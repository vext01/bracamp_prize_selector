#!/usr/bin/env python

import urwid
from random import *

class uplink_text:

    def make_mask(self):
        m = ""
        for i in range(self.width):
            m = ("%s%c" % (m, chr(self.rng.randrange(33, 122))))
        return m

    def __init__(self, text, width):
        self.rng = Random()
        self.width = width
        self.text = text.center(width)
        self.widget = urwid.Text("", align='center')

    def update(self):
        mask = self.make_mask()
        self.widget.set_text(mask)


# has to be a function not a method
def alarm_handler(loop, selector):
    selector.update()

class barcamp_prize_selector:

    def __init__(self, peep_list):

        self.people = []
        i = 0
        for p in peep_list:
            self.people.append(uplink_text(p, 40))
            i = i + 1
        self.loop = None

    def update(self):
        for p in self.people:
            p.update()
        self.loop.set_alarm_in(.1, alarm_handler, self)

    def render(self):

        widgets = []
        for p in self.people:
            p.update()
            widgets.append(p.widget)
            widgets.append(urwid.Divider())
            
        pile = urwid.Pile(widgets)
        fill = urwid.Filler(pile)
        self.loop = urwid.MainLoop(fill)
        self.update()
        self.loop.run()

if __name__ == "__main__":
    b = barcamp_prize_selector(["edd123", "jim234", "bob-jibble",
        "lalalalalala", "ohnoesohnoesohnoes"])
    b.render()
