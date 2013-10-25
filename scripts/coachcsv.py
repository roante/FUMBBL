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
from os import remove, rename
from os.path import exists
from time import strftime, strptime
from urllib import request

URL = "http://fumbbl.com/FUMBBL.php?page=coachinfo&coach="

CoachInfo = namedtuple("CoachInfo", ("coachid", "nickname",
    "joined", "realname", "location", "record"))

def profile_info(profile_page):
    """Returns a dictionary of a FUMBBL coach's profile data."""
    d = {}
    p = {
        "nickname": "<div style=\"text-align: center; " +
            "font-size: 2em;\">\s*(.*?)\s*</div>",
        "realname": "<b>Real Name:</b>\s*(.+?)\s*<br />",
        "location": "<b>Location:</b>\s*(.+?)\s*<br />",
        "joined": "<b>Member since:</b>\s*(.+?)\s*<br />",
        }
    for key, pat in p.items():
        try:
            s = re.search(pat, profile_page).group(1)
        except AttributeError:
            s = ""
        else:
            # I make it CSV compatible
            s = s.replace(";", "\semicol")
        d[key] = s
    # All profile page should have data of "Member since"
    if not d["joined"].strip():
        return
    for s in {"st", "nd", "rd", "th"}:
        d["joined"] = d["joined"].replace(s + ",", "").strip()
    d["joined"] = strptime(d["joined"], "%B %d %Y")
    d["joined"] = strftime("%Y-%m-%d", d["joined"])
    record_pat = re.compile(r"""
        <b>Total&nbsp;Record:</b></td><td\salign="right">
        (?P<w>\d+?)&nbsp;/&nbsp;
        (?P<d>\d+?)&nbsp;/&nbsp;
        (?P<l>\d+?)</td></tr>
        """, re.X)
    try:
        d["record"] = "{}/{}/{}".format(
            *record_pat.search(profile_page).groups())
    except AttributeError:
        d["record"] = "0/0/0"
    return d

def get_coachinfo(coachid):
    """Returns the CoachInfo namedtuple of a given coachid in
the following format:
    (coachid, nickname, joined, realname, location, record)"""
    url = URL + str(coachid)
    response = request.urlopen(url)
    page = response.read().decode("utf-8")
    profile_info_dict = profile_info(page)
    profile_info_dict["coachid"] = str(coachid)
    return CoachInfo(**profile_info_dict)

def generate_coach_csv(csv_file_path, startid, endid,
    ignore=100, verbose=True):
    """Appends FUMBBL coaches' data in CSV format to the given
csv file, according to the given FUMBBL coach ID range.

The function excludes IDs without an actual coach record and the
loop stops after <ignore> amount of such IDs.

If verbose is set, the function prints the CSV data lines to the
screen."""
    with open(csv_file_path, "a", encoding="utf-8") as f:
        i, ignore_ = startid, ignore
        while ignore_ and (startid <= i <= endid):
            try:
                coachinfo = get_coachinfo(i)
            except TypeError:
                coachinfo = None, None
            if not coachinfo[1]:
                i += 1
                ignore_ -=1
                continue
            ignore_, csv_string = ignore, ";".join(coachinfo)
            if verbose:
                print(csv_string.encode("utf-8", "ignore"))
            f.write(csv_string + "\n")
            i += 1

def update_coach_csv(csv_file_path, coach_id_seq, verbose=True):
    """Updates the given coaches' data in a coach CSV file."""
    # First I rename the CSV file to a BAK file.
    bak_file = csv_file_path + ".bak"
    rename(csv_file_path, bak_file)
    with open(csv_file_path, "a", encoding="utf-8") as f:
        for coachinfo in csv_coachinfo_iterator(bak_file):
            if int(coachinfo.coachid) in coach_id_seq:
                coachinfo = get_coachinfo(coachinfo.coachid)
                csv_string = ";".join(coachinfo)
                if verbose:
                    print(csv_string.encode("utf-8", "ignore"))
            csv_string = ";".join(coachinfo)
            f.write(csv_string + "\n")
    remove(bak_file)

def csv_lastid(csv_file_path):
    """Returns the last coach ID of a coach CSV file."""
    with open(csv_file_path, 'r', encoding="utf-8") as f:
        for line in f:
            i = line[:line.find(";")]
    return int(i)

def csv_coachinfo_by_nickname(csv_file_path, nickname):
    """Returns the coach ID of a coach nickname."""
    iterator = coachinfos(csv_file_path)
    for c in iterator:
        if c.nickname == nickname:
            return c

def csv_coachinfo_iterator(csv_file_path):
    """Generates CoachInfo namedtuples of the given CSV file."""
    with open(csv_file_path, 'r', encoding="utf-8") as f:
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
    csv_file_path, options = sys.argv[1], {}
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
    if exists(csv_file_path) and not "s" in options:
        options["s"] = csv_lastid(csv_file_path) + 1
    generate_coach_csv(
        csv_file_path = csv_file_path,
        startid = options.get("s", 1),
        endid = options.get("e", 1000000),
        ignore = options.get("i", 100),
        verbose = options.get("v", False),
        )

