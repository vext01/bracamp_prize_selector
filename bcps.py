#!/usr/bin/env python

import urwid
import sys
import time
import sqlite3
import os.path
import os

from random import *

class UplinkText:

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

    if event == EventType.JUMBLE:
        selector.update()
    elif event == EventType.RESOLVE:
        selector.resolve_char(val)

class EventType:
    JUMBLE=1
    RESOLVE=2

class SuspenseDisplay:

    UPDATE_RATE = 0.1
    RESOLVE_RATE = 0.5
    START_DELAY = 2
    NEXT_DELAY = 4  # cycles stagger

    def __init__(self, peep_list):

        self.people = []
        i = 0
        for p in peep_list:
            self.people.append(UplinkText(p, 20))
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
        self.loop.set_alarm_in(self.UPDATE_RATE, alarm_handler, (self, EventType.JUMBLE, None))

    def resolve_char(self, count):
        for val in self.started:
            self.people[val].resolve_char()
            if self.people[val].fully_resolved():
                self.started.remove(val)
        if self.s and len(self.started) == 0:
            raise urwid.ExitMainLoop

        if (count % self.NEXT_DELAY) == 0:
                self.start (count / self.NEXT_DELAY)
        
        self.loop.set_alarm_in(self.RESOLVE_RATE, alarm_handler, (self, EventType.RESOLVE, count + 1))

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
        self.loop.set_alarm_in(self.START_DELAY, alarm_handler, (self, EventType.RESOLVE, 0))

        self.update()
        self.loop.run()

class PrizeSelector:

    DBNAME = "barcamp.db"

    def __init__(self):
        self.init_sql()

    def init_sql(self):

        if os.path.isfile(self.DBNAME):
            print("Using existing database\n")
        else:
            print("Creating new database\n")

        self.db = sqlite3.connect(self.DBNAME)
        self.curs = c = self.db.cursor()

        # make schema (if we need to)
        c.execute('''CREATE TABLE IF NOT EXISTS names
            (name_id INTEGER PRIMARY KEY, name TEXT, prize_allocated INT);''');
        c.execute('''CREATE TABLE IF NOT EXISTS prizes
                (prize_id INTEGER PRIMARY KEY, descr TEXT, quantity INT,
                quantity_allocated INT);''');

    def prompt(self):

        cmds = {
                "names-import" :    { "func" : self.cmd_names_import,
                                      "msg" : "names-import <file>"},
                "names-list" :      { "func" : self.cmd_names_list,
                                      "msg" : "names-list"},
                "prizes-import" :   { "func" : self.cmd_prizes_import,
                                      "msg" : "prizes-import <file>"},
                "prizes-list" :     { "func" : self.cmd_prizes_list,
                                      "msg" : "prizes-list"},
        };

        print("Type 'help' for usage instructions.")

        while (True):
            sys.stdout.write("> ")
            sys.stdout.flush()

            try:
                line = raw_input().strip()
            except EOFError:
                break

            elems = line.split(" ")

            if (elems[0] == "quit"):
                break

            try:
               func = cmds[elems[0]]["func"]
            except KeyError:
                # bogus command
                print("parse error")
                continue

            # user gave a useful command, execute it 
            func(elems[1:])

    def cmd_prizes_list(self, args):
        self.curs.execute(
                "SELECT prize_id, descr, quantity, quantity_allocated FROM prizes", ())
        res = self.curs.fetchall()
        print(res)

        for rec in res:
            print("  %03d: (%-d/%-d) %s" % (rec[0], rec[3], rec[2], rec[1]))

    def close_sql(self):
        self.db.close()

    def cmd_prizes_import(self, args):

        try:
            f = open(args[0], "r")
        except IOError:
            print("File not found")
            return

        prizes = []
        for line in f:
            if line.startswith("#") or len(line.strip()) == 0:
                continue
            elems = line.split(",")

            if len(elems) != 2:
                print("malformed line ignored: '%s'" % (line))
                continue

            try:
                qty = int(elems[1])
            except:
                print("malformed line ignored: '%s'" % (line))
                continue

            prizes.append((elems[0], qty))
        f.close()

        self.curs.executemany(
            "INSERT INTO prizes (descr, quantity, quantity_allocated) " + \
                    "VALUES (?, ?, 0)", prizes)
        self.db.commit()

        print("Imported %d prize descriptions from %s" % (len(prizes), args[0]))

    def cmd_names_import(self, args):

        try:
            f = open(args[0], "r")
        except IOError:
            print("File not found")
            return

        names = []
        for line in f:
            if line.startswith("#") or len(line.strip()) == 0:
                continue
            names.append((line.strip(),))
        f.close()

        self.curs.executemany(
            "INSERT INTO names (name, prize_allocated) VALUES (?, -1)", names)
        self.db.commit()

        print("Imported %d names from %s" % (len(names), args[0]))

    def cmd_names_list(self, args):
        self.curs.execute("SELECT * FROM names WHERE prize_allocated = -1", ())
        res = self.curs.fetchall()

        print("Names with no prizes allocated:")
        for rec in res:
            print("  %3s: %s" % (rec[0], rec[1]))

        print("")

        self.curs.execute("SELECT * FROM names WHERE prize_allocated > -1", ())
        res = self.curs.fetchall()

        print("Names with prizes allocated:")
        for rec in res:
            print("  %3s: %s" % (rec[0], rec[1]))

    def close_sql(self):
        self.db.close()

if __name__ == "__main__":
    names = [
            "Edd Barrett", "Matt Mole", "Han Greer", "Tris Linell", "Gunther Pleasureman"
            ]
    #b = SuspenseDisplay(names)
    #b.render()
    ps = PrizeSelector()
    ps.prompt()
    ps.close_sql()
