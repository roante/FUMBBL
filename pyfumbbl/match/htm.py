"""Module for parsing the HTML match result pages of FUMBBL."""

# pyfumbbl/match/htm.py by Adam Szieberth (2013)
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

from datetime import datetime
from html.parser import HTMLParser
import re
from time import strptime
from urllib import parse, request

from match import Match

DATE_FORMAT = "Date: %Y-%m-%d %H:%M:%S"

MATCH_URL = "http://fumbbl.com/p/match?id="
MATCHES_URL = "http://fumbbl.com/p/matches"

PLAYER_PERFORMANCE_ORDER = (
    "turns",
    "completions",
    "touchdowns",
    "interceptions",
    "casualties",
    "mvps",
    "spps",
    "passing",
    "rushing",
    "blocks",
    "fouls",
    )

TEAM_LINK = "/p/team"

class MatchPageParser(HTMLParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dict, self._temp = {"home": {}, "away": {}}, {}
        self._state, self._team = "team_id", "home"
        self._player_perf_i = None

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if (self._state == "team_id"
            and tag == "a"
            and d["href"].startswith(TEAM_LINK)):
            parsed_link = parse.parse_qs(d["href"])
            t_id = int(parsed_link["team_id"].pop())
            self._dict[self._team]["team_id"] = t_id
            self._state = "team_name"
        elif self._state == "replay_link" and tag == "a":
            parsed_link = parse.parse_qs(d["href"])
            replay_id = parsed_link["/ffb.jnlp?replay"].pop()
            self._dict["replay_id"] = int(replay_id)
            self._state, self._team = "team_id", "away"
        elif (self._state == "players_t"
            and tag == "tr"
            and d.get("align") == "right"):
            self._state, self._temp = "player_nr", {}
        elif self._state == "player_id":
            parsed_link = parse.parse_qs(d["href"])
            p_id = parsed_link["/p/player?player_id"].pop()
            self._dict[self._team]["players"][p_id] = self._temp

    def handle_data(self, data):
        if not self._state or data == "\n":
            return
        if self._state == "player_perf_":
            self._state = "player_nr"
        if self._state == "team_name":
            self._dict[self._team]["team_name"] = data
            self._state = "team_value_and_race"
        elif self._state == "team_value_and_race":
            s = re.search("^TV (.+?)k (.+)$", data)
            if "+" in s.group(1):
                tv, iv = [int(e) for e in s.group(1).split("+")]
            else:
                tv, iv = int(s.group(1)), 0
            self._dict[self._team]["TV"] = tv
            self._dict[self._team]["inducement_value"] = iv
            self._dict[self._team]["team_race"] = s.group(2)
            if self._team == "home":
                self._state = "replay_link"
            else:
                self._state = "date"
        elif self._state == "date" and data.startswith("Date:"):
            _parsed_date = strptime(data, DATE_FORMAT)
            self._dict["date"] = datetime(*_parsed_date[:6])
            self._state = "gate"
        elif self._state == "gate" and data.startswith("Gate:"):
            self._dict["gate"] = int(data.split()[1])
            self._state, self._team = "score", "home"
        elif self._state == "score":
            self._handle_team_data(data, "touchdowns",
                "Score", "coach", datatype=int)
        elif self._state == "coach":
            self._handle_team_data(data, "coach_name",
                "Coach", "coach_ranking")
        elif self._state == "coach_ranking":
            if data == "Ranking":
                self._team = "away"
                return
            if self._team == "home":
                s = re.search("^\((.+)\)\s(.+)$", data)
                cr, rank = s.groups()
            else:
                s = re.search("^(.+)\s\((.+)\)$", data)
                rank, cr = s.groups()
            self._dict[self._team]["coach_rank"] = rank
            self._dict[self._team]["coach_cr"] = float(cr)
            if self._team == "away":
                self._state, self._team = "spectators", "home"
        elif self._state == "spectators":
            self._handle_team_data(data, "spectators",
                "Spectators", "fame", datatype=int)
        elif self._state == "fame":
            self._handle_team_data(data, "FAME",
                "FAME", "winnings", datatype=int)
        elif self._state == "winnings":
            self._handle_team_data(data, "winnings",
                "Winnings", "spiralling_expenses", datatype=int)
        elif self._state == "spiralling_expenses":
            if data == "Expenses":
                return
            self._handle_team_data(data, "spiralling_expenses",
                "Spiralling",
                "fan_factor_change", datatype=int)
        elif self._state == "fan_factor_change":
            def _ffdata(data):
                if data == "No Change":
                    return 0
                return int(data)
            self._handle_team_data(data, "fan_factor_change",
                "Fanfactor", "casualties", datatype=_ffdata)
        elif self._state == "casualties":
            if data == "Casualties":
                self._team = "away"
                return
            bh, si, kill = (int(s) for s in data.split("/"))
            self._dict[self._team]["casualties"] = {}
            self._dict[self._team]["casualties"]["bh"] = bh
            self._dict[self._team]["casualties"]["si"] = si
            self._dict[self._team]["casualties"]["kill"] = kill
            tot = bh + si + kill
            self._dict[self._team]["casualties"]["total"] = tot
            if self._team == "away":
                self._dict[self._team]["players"] = {}
                self._state, self._team = "players_t", "home"
                self._dict[self._team]["players"] = {}                
        elif self._state == "player_nr":
            if data == "Total":
                if self._team == "home":
                    self._team = "away"
                self._state = "players_t"
                return
            player_nr = int(data.strip().lstrip("#"))
            self._temp["nr"] = player_nr
            self._state = "player_id"
        elif self._state == "player_id":
            self._temp["name"] = data
            self._player_perf_i = 0
            self._state = "player_perf_" + self._p_perf_st()
        elif self._state == "player_perf_" + self._p_perf_st():
            self._temp[self._p_perf_st()] = int(data)
            self._player_perf_i += 1
            self._state = "player_perf_" + self._p_perf_st()

    def _p_perf_st(self):
        _i, _d = self._player_perf_i, PLAYER_PERFORMANCE_ORDER
        if _i is None or _i >= len(_d):
            return ""
        return _d[_i]

    def _handle_team_data(self, data, key, switchdata,
        nextstate, datatype=str):
        if data == switchdata:
            self._team = "away"
            return
        self._dict[self._team][key] = datatype(data)
        if self._team == "away":
            self._state, self._team = nextstate, "home"

def get_match_obj(match_id):
    url = MATCH_URL + str(match_id)
    response = request.urlopen(url)
    page = response.read().decode("utf-8")
    parser = MatchPageParser()
    parser.feed(page)
    match_obj = Match()
    match_obj.update(parser._dict)
    return match_obj

