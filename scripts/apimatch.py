"""Module for parsing API match result sheets of FUMBBL."""

# apimatch.py by Adam Szieberth (2013)
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
from collections import namedtuple
from datetime import datetime
from time import strptime
from urllib import parse, request

URL = "http://fumbbl.com/xml:matches"

DIVISIONS = (
    "All",
    "Ranked",
    "N/A",
    "Stunty",
    "N/A",
    "League",
    "Faction",
    "Academy",
    "Unranked",
    "d5",
    "Blackbox",
    )

class XMLElement:
    def __init__(self, match_Element):
        self.e = match_Element

Cas = namedtuple("Cas", "bh si kill")
_PlayerPerformance = namedtuple("PlayerPerformance", (
    "completions",
    "touchdowns",
    "interceptions",
    "casualties",
    "mvps",
    "passing",
    "rushing",
    "blocks",
    "fouls",
    "turns",
    ))

class PlayerPerformance(_PlayerPerformance):
    @property
    def spp(self):
        return (self.completions + 3 * self.touchdowns +
            2 * self.interceptions + 2 * self.casualties +
            self.mvps)

class Match(XMLElement):
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    def matchid(self):
        """Returns the FUMBBL ID of the match."""
        return int(self.e.attrib["id"])

    def date(self):
        """Returns match date in datetime.datetime() format."""
        datestring = self.e.find('date').text
        parsed_date = strptime(datestring, self.DATE_FORMAT)
        return datetime(*parsed_date[:6])

    def gate(self):
        """Returns match gate."""
        return int(self.e.find('gate').text)

    def division(self):
        """Returns the name of the division of the match."""
        return DIVISIONS[int(self.e.find('division').text)]

    def teams(self):
        """Returnes a two element tuple of home/away
TeamPerformance objets."""
        return (TeamPerformance(self.e.find('home')),
            TeamPerformance(self.e.find('away')))

class TeamPerformance(XMLElement):

    def teamid(self):
        """Returns the FUMBBL ID of the team."""
        return int(self.e.attrib["id"])

    def coachid(self):
        """Returns the FUMBBL ID of the coach."""
        return int(self.e.find('coach').attrib["id"])

    def teamname(self):
        """Returns the name of the team."""
        return self.e.find('name').text

    def TV(self):
        """Returns the Team Value of the team."""
        return int(self.e.find('teamValue').text) // 1000

    def TW(self):
        """Returns the Tournament Weight of the team."""
        return int(self.e.find('tournamentWeight').text) // 1000

    def touchdowns(self):
        """Returns the number of touchdowns the team made."""
        return int(self.e.find('touchdowns').text)

    def casualties(self):
        """Returns a three element long namedtuple of the
casualities the team made in format of (bh, si, kill)."""
        cas_element = self.e.find('casualties')
        return Cas(
            int(cas_element.find('bh').text),
            int(cas_element.find('si').text),
            int(cas_element.find('kill').text),
            )

    def fanfactor(self):
        """Returns the fan factor of the team."""
        return int(self.e.find('fanfactor').text)

    def winnings(self):
        """Returns the winnings of the team."""
        return int(self.e.find('winnings').text)

    def performances(self):
        """Returns the player performance dictionary of the
team. The keys of the dictionary are the FUMBBL player IDs.
The values are namedtuples in the following format:
    (completions, touchdowns, interceptions, casualties, mvps,
        passing, rushing, blocks, fouls, turns)"""
        result = {}
        performances_element = self.e.find('performances')
        for p in performances_element.iter('performance'):
            p_dict = {k : int(v) for k, v in p.attrib.items()
                if k != "player"}
            player_id = int(p.attrib["player"])
            result[player_id] = PlayerPerformance(**p_dict)
        return result

def get_matches(startpage=1, endpage=1, coachid=None):
    """Generator which yields Match() objects using the FUMBBL
API."""
    parse_data = {}
    if coachid:
        parse_data["c"] = coachid
    while True:
        parse_data["p"] = startpage
        url = URL + '?' + parse.urlencode(parse_data)
        response = request.urlopen(url)
        page = response.read().decode("utf-8")
        matches = iter(ET.fromstring(page))
        # I try to yield one Match() object. If it fails, then
        # the while loop breaks immediately.
        yield Match(next(matches))
        # Now I yield the reamining objects of the page.
        for match in matches:
            yield Match(match)
        if startpage == endpage:
            break
        startpage += 1

