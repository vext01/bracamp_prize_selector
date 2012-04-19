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
        self.mask = self.make_mask()

    def update(self):
        self.widget = urwid.Text(self.mask, align='center')



class barcamp_prize_selector:

    def __init__(self, peep_list):

        self.people = []
        i = 0
        for p in peep_list:
            self.people.append(uplink_text(p, 40))
            i = i + 1

    def render(self):

        widgets = []
        for p in self.people:
            p.update()
            widgets.append(p.widget)
            widgets.append(urwid.Divider())
            
        pile = urwid.Pile(widgets)
        fill = urwid.Filler(pile)
        loop = urwid.MainLoop(fill)
        loop.run()

if __name__ == "__main__":
    b = barcamp_prize_selector(["edd123", "jim234"])
    b.render()
