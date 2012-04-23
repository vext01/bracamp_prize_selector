#!/usr/bin/env python

import urwid
import sys
import time
import sqlite3
import os.path
import os
import readline


from random import *
rng = Random()

class PeopleNumberError(Exception):
    pass

class UplinkText:

    def __init__(self, text, width):
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
                m = m + chr(rng.randrange(33, 122))
        return m

    def update(self):
        mask = self.make_mask()
        self.widget.set_text(mask)

    def resolve_char(self):
        n = rng.randrange(len(self.unresolved_chars))
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

# closure
# this is not pretty, but urwid handler should have the option of passing 
# user data down :(
def make_input_handler(display):
    def input_handler(inp):
        # start resolving
        if (inp == "enter"):
            if not display.started:
                alarm_handler(None, (display, EventType.RESOLVE, 0))
            elif display.finished:
                raise urwid.ExitMainLoop
    return input_handler

class EventType:
    JUMBLE=1
    RESOLVE=2

class SuspenseDisplay:

    UPDATE_RATE = 0.1
    RESOLVE_RATE = 0.2
    START_DELAY = 2
    NEXT_DELAY = 4  # cycles stagger

    def __init__(self, parent, peep_list):

        self.people = []
        self.parent = parent
        i = 0

        max_len = 20
        for i in peep_list:
            if len(i) > max_len:
                max_len = len(i)

        for p in peep_list:
            self.people.append(UplinkText(p, max_len))

        self.loop = None    # main event loop
        self.resolving = -1 # index of which item we are resolving
        self.people_started = []
        self.started = False
        self.finished = False

    def start(self, val):
        if val < len (self.people):
            self.people_started.append(val)
            self.started = True

    def update(self):
        for p in self.people:
            p.update()
        if not self.finished:
            self.loop.set_alarm_in(
                self.UPDATE_RATE, alarm_handler,
                (self, EventType.JUMBLE, None))

    def resolve_char(self, count):
        for val in self.people_started:
            self.people[val].resolve_char()
            if self.people[val].fully_resolved():
                self.people_started.remove(val)
        if self.started and len(self.people_started) == 0:
            self.finished = True

        if (count % self.NEXT_DELAY) == 0:
                self.start(count / self.NEXT_DELAY)
        
        self.loop.set_alarm_in(
            self.RESOLVE_RATE, alarm_handler,
            (self, EventType.RESOLVE, count + 1))

    def render(self):

        widgets = []
        for p in self.people:
            p.update()
            widgets.append(p.widget)
            widgets.append(urwid.Divider())
            
        pile = urwid.Pile(widgets)
        fill = urwid.Filler(pile)
        self.loop = urwid.MainLoop(fill,
                unhandled_input=make_input_handler(self))

        self.update()
        self.loop.run()

class PrizeSelector:

    DBNAME = "barcamp.db"

    def __init__(self):

        self.cmds = {
                "names_import" :    { "func" : self.cmd_names_import,
                                      "msg" : "names_import <file>"},
                "names_list" :      { "func" : self.cmd_names_list,
                                      "msg" : "names_list"},
                "prizes_import" :   { "func" : self.cmd_prizes_import,
                                      "msg" : "prizes_import <file>"},
                "prizes_list" :     { "func" : self.cmd_prizes_list,
                                      "msg" : "prizes_list"},
                "prizes_issue" :    { "func" : self.cmd_prizes_issue,
                                      "msg" : "prizes_issue <prizes-id> <qty>"},
                "help" :            { "func" : self.cmd_help,
                                      "msg" : "help" }
        };
        self.init_sql()
        readline.set_completer(SimpleCompleter(
            [a[0] for a in self.cmds.items()]).complete)
        readline.parse_and_bind('tab: complete')

    def init_sql(self):

        if os.path.isfile(self.DBNAME):
            print("Using existing database\n")
        else:
            print("Creating new database\n")

        self.db = sqlite3.connect(self.DBNAME)
        self.curs = c = self.db.cursor()

        # make schema (if we need to)
        c.execute('''CREATE TABLE IF NOT EXISTS names
            (name_id INTEGER PRIMARY KEY, fname TEXT, lname TEXT, role TEXT,
            company TEXT, prize_allocated INT);''');
        c.execute('''CREATE TABLE IF NOT EXISTS prizes
                (prize_id INTEGER PRIMARY KEY, descr TEXT, quantity INT,
                quantity_allocated INT);''');

    def prompt(self):

        print("Type 'help' for usage instructions.")

        while (True):
            try:
                line = raw_input('> ')
            except EOFError:
                break

            elems = line.strip().split(" ")
            if (elems[0] == "quit"):
                break

            try:
               cmd = self.cmds[elems[0]]
            except KeyError:
                # bogus command
                print("parse error")
                continue

            # check args are right
            if len(elems) != len(cmd["msg"].split(" ")):
                print("incorrect usage")
                continue

            # user gave a useful command, execute it 
            cmd["func"](elems[1:])

    def cmd_help(self, args):
        for (k, v) in self.cmds.items():
            print("  " + v["msg"])

    def cmd_prizes_list(self, args):
        self.curs.execute(
                "SELECT prize_id, descr, quantity, quantity_allocated " + \
                "FROM prizes", ())
        res = self.curs.fetchall()

        for rec in res:
            print("  %03d: (%d/%d) %s" % (rec[0], rec[3], rec[2], rec[1]))

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

        print("Imported %d prize descriptions from %s" % \
            (len(prizes), args[0]))

    def cmd_names_import(self, args):

        try:
            f = open(args[0], "r")
        except IOError:
            print("File not found")
            return

        recs = []
        for line in f:
            if line.startswith("#") or len(line.strip()) == 0:
                continue
            rec = (fname, lname, role, company) = line.strip().split(",")

            if role not in ("AT", "ST", "SP"):
                print("Bad role code: %s" % (role))
                print("Aborting")
                sys.exit(1)

            recs.append(rec)
        f.close()

        self.curs.executemany(
            "INSERT INTO names " + \
            "(fname, lname, role, company, prize_allocated) " + \
            "VALUES (?, ?, ?, ?, -1)", recs)
        self.db.commit()

        print("Imported %d names from %s" % (len(recs), args[0]))

    def cmd_names_list(self, args):
        self.curs.execute("SELECT name_id, fname, lname, role, company " + \
                "FROM names WHERE prize_allocated = -1", ())
        res = self.curs.fetchall()

        print("Names with no prizes allocated:")
        for rec in res:
            print("  %3s %s: %s %s (%s)" % \
                (rec[0], rec[3], rec[1], rec[2], rec[4]))

        print("")

        self.curs.execute("SELECT names.name_id, names.fname, names.lname, " + \
            "names.role, names.company, prizes.prize_id, prizes.descr " + \
            "FROM names,prizes WHERE names.prize_allocated = prizes.prize_id " + \
            "AND prize_allocated > -1", ())
        res = self.curs.fetchall()

        print("Names with prizes allocated:")
        for rec in res:
            print("  %3s %s: %s %s (%s)" % \
                (rec[0], rec[3], rec[1], rec[2], rec[4]))
            print("        %3d: %s" % (rec[5], rec[6]))

    def cmd_prizes_issue(self, args):

        try:
            pid = int(args[0])
            qty_going = int(args[1])
        except ValueError:
            print("bad argument")
            return

        self.curs.execute(
                "SELECT prize_id, descr, quantity, quantity_allocated FROM" + \
                " prizes WHERE prize_id = ?", (pid,))
        res = self.curs.fetchall()

        if len(res) != 1:
            print("Unknown prizes id")
            return

        if res[0][2] - res[0][3] < qty_going:
            print("Not enough prizes left")
            return

        try:
            lucky_people = self.choose_x_random_names(qty_going)
        except PeopleNumberError:
            print("Too few people left (who are not staff)")
            return

        names_only = [x[1] + " " + x[2] for x in lucky_people]

        sd = SuspenseDisplay(self, names_only)
        self.suspense_display = sd
        sd.render()
        self.suspense_display = None

        # update db
        updates = [(pid, x[0]) for x in lucky_people]
        self.curs.executemany("UPDATE names SET prize_allocated=? WHERE " + \
            "name_id=?", updates)

        self.curs.execute("UPDATE prizes SET " + \
            "quantity_allocated=quantity_allocated + ? WHERE " + \
            "prize_id=?", (qty_going, pid))
        self.db.commit()

    """ Choose random names that have not yet had a prize """
    def choose_x_random_names(self, x):

        self.curs.execute(
                "SELECT name_id, fname, lname FROM names WHERE " + \
                "prize_allocated=-1 AND role != 'ST';")
        res = self.curs.fetchall()

        if len(res) < x:
            raise PeopleNumberError

        selected = []
        for unused in range(x):
            chosen = rng.randint(0, len(res) - 1)
            selected.append(res[chosen])
            del(res[chosen])

        return selected

    def close_sql(self):
        self.db.close()

class SimpleCompleter(object):
    
    def __init__(self, options):
        self.options = sorted(options)
        return

    def complete(self, text, state):
        response = None
        if state == 0:
            # This is the first time for this text, so build a match list.
            if text:
                self.matches = [s 
                    for s in self.options if s and s.startswith(text)]
            else:
                self.matches = self.options[:]

        # Return the state'th item from the match list,
        # if we have that many.
        try:
            response = self.matches[state]
        except IndexError:
            response = None

        return response


if __name__ == "__main__":
    ps = PrizeSelector()
    ps.prompt()
    ps.close_sql()

"""
TODO:
    * backup db
"""
