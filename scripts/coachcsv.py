"""Module for getting CSV data of FUMBBL coaches."""

# coachcsv.py by Adam Szieberth (2013)
# Python 3.3

# Full license text:
# --------------------------------------------------------------
# DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
# Version 2, December 2004
#
# Copyright (C) 2004 Sam Hocevar <sam@hocevar.net>
#
# Everyone is permitted to copy and distribute verbatim or
# modified copiesof this license document, and changing it is
# allowed as long as the name is changed.
#
# DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
# TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND
# MODIFICATION
#
# 0. You just DO WHAT THE FUCK YOU WANT TO.
# --------------------------------------------------------------

import re
import sys
from collections import namedtuple
from os.path import exists
from time import strftime, strptime
from urllib import request

URL = "http://fumbbl.com/FUMBBL.php?page=coachinfo&coach="

CoachInfo = namedtuple("CoachInfo", ("id", "nickname", "joined",
    "realname", "location", "record"))

def profile(page):
    d = {}
    p = {
        "nick_name": "<div style=\"text-align: center; " +
            "font-size: 2em;\">\s*(.*?)\s*</div>",
        "real_name": "<b>Real Name:</b>\s*(.+?)\s*<br />",
        "location": "<b>Location:</b>\s*(.+?)\s*<br />",
        "joined": "<b>Member since:</b>\s*(.+?)\s*<br />",
        }
    order = ("nick_name", "joined", "real_name", "location")
    for key, pat in p.items():
        try:
            s = re.search(pat, page).group(1).replace(";", ",")
        except AttributeError:
            s = ""
        d[key] = s
    if not d["joined"].strip():
        return
    for s in {"st", "nd", "rd", "th"}:
        d["joined"] = d["joined"].replace(s + ",", "").strip()
    d["joined"] = strptime(d["joined"], "%B %d %Y")
    d["joined"] = strftime("%Y-%m-%d", d["joined"])
    return [d[k] for k in order]

def record(page):
    pattern = re.compile(r"""
        <b>Total&nbsp;Record:</b></td><td\salign="right">
        (?P<w>\d+?)&nbsp;/&nbsp;
        (?P<d>\d+?)&nbsp;/&nbsp;
        (?P<l>\d+?)</td></tr>
        """, re.X)
    result = pattern.search(page)
    try:
        return "{}/{}/{}".format(*result.groups())
    except AttributeError:
        return "0/0/0"

def coachdata(coachid):
    url = URL + str(coachid)
    response = request.urlopen(url)
    page = response.read().decode("utf-8")
    return profile(page), record(page)

def generate_coach_csv(filepath, startid, endid, ignore=100,
    verbose=True):
    with open(filepath, "a", encoding="utf-8") as f:
        i, profile_, ignore_ = startid, "INITIAL", ignore
        while ignore_ and (startid <= i <= endid):
            profile_, record_ = coachdata(i)
            i += 1
            if not profile_ or not profile_[0]:
                ignore_ -=1
                continue
            ignore_ = ignore
            nick, joined, real_name, location = profile_
            s = ";".join((str(i-1), nick, joined, real_name,
                location, record_))
            if verbose:
                print(s.encode("utf-8", "ignore"))
            f.write(s+ "\n")

def lastid(filepath):
    with open(filepath, 'r', encoding="utf-8") as f:
        for line in f:
            i = line[:line.find(";")]
    return int(i)

def coachinfo(filepath, nickname):
    iterator = coachinfos(filepath)
    for c in iterator:
        if c.nickname == nickname:
            return c

def coachinfos(filepath):
    with open(filepath, 'r', encoding="utf-8") as f:
        for line in f:
            yield CoachInfo(*line[:-1].split(";"))


if __name__ == '__main__':
    print("FUMBBL Coach CSV generator v0.1 by Szieberth Ádám\n")
    if len(sys.argv) == 1:
        print("Fetches coach data to a CSV file\n")
        print("""Usage: python coachcsv.py file <options>
Options:
    /s=n    startid (default=1 for new CSV file; an existing CSV
                file is going to be updated by default)
    /e=n    endid (default=1000000)
    /i=n    number of allowed empty coach pages before exit
                (default=100)
    /v      verbose mode""")
        sys.exit()
    filepath, options = sys.argv[1], {}
    if len(sys.argv) > 2:
        for o in sys.argv[2:]:
            if not o.startswith("/"):
                raise ValueError("Options should start with "
                    "'/'.")
            if "=" in o:
                key, value = o.lstrip("/").split("=")
                options[key] = int(value)
            else:
                options[o.lstrip("/")] = True
    # If the CSV file exsists at the given location and no
    # startid was given, then I set startid to the last id + 1
    # of the CSV file.
    if exists(filepath) and not "s" in options:
        options["s"] = lastid(filepath)
    generate_coach_csv(
        filepath = filepath,
        startid = options.get("s", 1),
        endid = options.get("e", 1000000),
        ignore = options.get("i", 100),
        verbose = options.get("v", False),
        )

