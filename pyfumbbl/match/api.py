"""Module for parsing API match result sheets of FUMBBL."""

# pyfumbbl/match/api.py by Adam Szieberth (2013)
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

import xml.etree.ElementTree as ET
from datetime import datetime
from time import strptime
from urllib import parse, request

from const import DIVISIONS

## > Constants

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
URL = "http://fumbbl.com/xml:matches"

def _get_match_info(match_et_element):
    e, result = match_et_element, {}
    result["match_id"] = int(e.attrib["id"])
    result["date"] = _get_match_date(e)
    result["gate"] = int(e.find("gate").text)
    result["division"] = DIVISIONS[int(e.find("division").text)]
    result["home"] = _get_team_performance_dict(e.find("home"))
    result["away"] = _get_team_performance_dict(e.find("away"))
    return result

def _get_match_date(match_et_element):
    _datestring = match_et_element.find("date").text
    _parsed_date = strptime(_datestring, DATE_FORMAT)
    return datetime(*_parsed_date[:6])

def _get_team_performance_dict(team_et_element):
    e, result = team_et_element, {}
    result["team_id"] = int(e.attrib["id"])
    result["coach_id"] = int(e.find("coach").attrib["id"])
    result["team_name"] = e.find("name").text
    result["TV"] =  int(e.find("teamValue").text) // 1000
    result["TW"] =  int(e.find("tournamentWeight").text) // 1000
    result["touchdowns"] = int(e.find("touchdowns").text)
    result["casualties"], _cas_e = {}, e.find("casualties")
    result["casualties"]["bh"] = int(_cas_e.find("bh").text)
    result["casualties"]["si"] = int(_cas_e.find("si").text)
    result["casualties"]["kill"] = int(_cas_e.find("kill").text)
    result["fan_factor"] = int(e.find("fanfactor").text)
    result["winnings"] = int(e.find("winnings").text)
    result["players"] = _get_player_performances_dict(
        e.find("performances"))
    return result

def _get_player_performances_dict(performances_et_element):
    e, result = performances_et_element, {}
    for p in e.iter("performance"):
        p_id = int(p.attrib["player"])
        p_dict = {k : int(v) for k, v in p.attrib.items()
            if k != "player"}
        result[p_id] = p_dict
    return result

def get_match_ets(
    match_id = None,
    coach_id = None,
    startpage = 1,
    endpage = 1,
    ):
    """
    Generator which yields match ElementTree (XML) objects
    provided by the FUMBBL API.
    """
    parse_data = {}
    if match_id:
        parse_data["m"] = match_id
    elif coach_id:
        parse_data["c"] = coach_id
    while True:
        parse_data["p"] = startpage
        url = URL + '?' + parse.urlencode(parse_data)
        response = request.urlopen(url)
        page = response.read().decode("utf-8")
        matches = iter(ET.fromstring(page))
        # I try to yield one Match() object. If it fails, then
        # the while loop breaks immediately.
        yield next(matches)
        # Now I yield the reamining objects of the page.
        for match in matches:
            yield match
        if startpage == endpage:
            break
        startpage += 1

def get_match_info(
    match_id = None,
    coach_id = None,
    startpage = 1,
    endpage = 1,
    ):
    iterator = get_match_ets(
        match_id = match_id,
        coach_id = coach_id,
        startpage = startpage,
        endpage = endpage,
        )
    for match_et in iterator:
        yield _get_match_info(match_et)

