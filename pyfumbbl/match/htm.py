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

## > Constants

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

TEAM_SUBDICT = {
    "casualties": {},
    "inducements": [],
    "team_performance": {},
    "players": {},
    }

## > Stated HTML Parser Class
##
## To parse the match pages first I create a special subclass of
## html.parser.HTMLParser(). Why? Well, that class is intended
## to be subclassed by default. However, it still provides
## limited tools to parse a complex page, since it has only
## common handler methods to be overridden.
##
## I want to enhance the class to support states, and when I
## change state, I want another method to be called for let's
## say a starttag than before.
##
## The name of the state-specific handlers are bound. Let's say
## the state is "team_id". Now the handling of all starttags
## are redirected to the self._handle_team_id_starttag() method.
## Data blocks are redirected to self._handle_team_id_data().
## Same with end tags. However, if no private method in the
## required name is present, the parser goes towards.

class StatedHTMLParser(HTMLParser):
    """
    Subclass of html.parser.HTMLParser() which supports states.

    The regular handlers does nothing here than redirect the
    handling to the state-specific handler methods. These
    methods have to be properly named, eg. for the state of
    "test", a data handler should be _handle_test_data().
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state = ""

    # TODO: Since I needed starttag, endtag, and data handling,
    # handle_startendtag, handle_entityref, handle_charref,
    # handle_comment, handle_decl, and handle_pi are missing.
    # A proper stated parser class should support these handlers
    # aswell.

    def handle_starttag(self, tag, attrs):
        func_name = "_handle_{}_starttag".format(self.state)
        try:
            func = getattr(self, func_name)
        except AttributeError:
            pass
        else:
            func(tag, dict(attrs))

    def handle_data(self, data):
        if data == "\n":
            return
        func_name = "_handle_{}_data".format(self.state)
        try:
            func = getattr(self, func_name)
        except AttributeError:
            pass
        else:
            func(data)

    def handle_endtag(self, tag):
        func_name = "_handle_{}_endtag".format(self.state)
        try:
            func = getattr(self, func_name)
        except AttributeError:
            pass
        else:
            func(tag)

## > Match Page Parser
##
## Despite I made the stated parser class to make my life
## easier, there are still some obstacles around. Besides the
## state variable which I initially set to "team_id", I need a
## variable to store which team I actually parsing, home or
## away. This is necessary since team page have two columns, one
## for home team stats, and another for the away team. The
## process of parsing is done by rows so I have to constantly
## swich between teams.

class MatchPageParser(StatedHTMLParser):
    """
    Parses a FUMBBL match result page and returns a Match()
    object.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dict = {
            "home": dict(TEAM_SUBDICT),
            "away": dict(TEAM_SUBDICT),
            }
        self.state, self._team = "team_id", "home"
        self._perfrow, self._player_perf_i = {}, None
        self._total_iv = 0

## > Team ID
##
## The first relevant data I face on the report page is a team
## link enclosing the team name. I am looking for this:
##  ...<a href="/p/team?op=view&amp;team_id=752380" style="
##      font-size: 1.4em;">Tiny Toon Terrors</a>...
##
## I get the ID from the href link and set the state to
## "team_name" at the end.

    def _handle_team_id_starttag(self, tag, a_dict):
        if tag == "a" and a_dict["href"].startswith(TEAM_LINK):
            parsed_link = parse.parse_qs(a_dict["href"])
            team_id = int(parsed_link["team_id"].pop())
            self._dict[self._team]["team_id"] = team_id
            self.state = "team_name"

## > Team Name
##
## Since the link tag which redirected me to the team name
## state encloses the team name itself, it comes
## immediately. After team name comes the small sized text
## containing the TV plus the bought inducements and the race.

    def _handle_team_name_data(self, data):
        self._dict[self._team]["team_name"] = data
        self.state = "team_value_and_race"

## > TV, Inducement Value, and Race
##
## This is a bit trickier, since the data has different formats
## in the HTML code:
##  ...>TV 1270k Dwarf<...
##  ...>TV 950+50k Chaos Pact<...
##
## I use re to parse the string. If I am doing this with the
## home team, then the next to parse is the replay_link.
## Otherwise, date.

    def _handle_team_value_and_race_data(self, data):
        s = re.search("^TV (\d*)\+?(\d*)k (.+)$", data)
        self._dict[self._team]["TV"] = int(s.group(1))
        self._dict[self._team]["race"] = s.group(3)
        if s.group(2):
            iv = int(s.group(2))
        else:
            iv = 0
        self._dict[self._team]["inducement_value"] = iv
        self._total_iv += iv
        if self._team == "home":
            self.state = "replay_link"
        else:
            self.state = "date"

## > Replay Link
##
## The replay link looks like this in the HTML code:
##  ...(<a href="/ffb.jnlp?replay=441264">Replay</a>)...
##
## After this comes the team name/TV/race info of the away team,
## so I change state and team when I am done here.

    def _handle_replay_link_starttag(self, tag, a_dict):
        if tag == "a":
            parsed_link = parse.parse_qs(a_dict["href"])
            # For some reason "replay" is not enough here.
            replay_id = parsed_link["/ffb.jnlp?replay"].pop()
            self._dict["replay_id"] = int(replay_id)
            self.state, self._team = "team_id", "away"

## > Date
##
## Date info looks like this in the HTML code:
##  ...>Date: 2013-10-30 12:29:58<...
##
## I parse the date and convert it to datetime() object.
## The next thing to parse is gate.

    def _handle_date_data(self, data):
        if data.startswith("Date:"):
            _handled_date = strptime(data, DATE_FORMAT)
            self._dict["date"] = datetime(*_handled_date[:6])
            self.state = "gate"

## > Gate
##
## Gate info is easy to get as it looks like this in the
## HTML code:
##  ...>Gate: 23000<...
##
## When I am done, I switch to home team, and set state to
## score.

    def _handle_gate_data(self, data):
        if data.startswith("Gate:"):
            self._dict["gate"] = int(data.split()[1])
            self.state, self._team = "score", "home"

## > Special Parser Method for Center Formatted Data
##
## Starting from score there is some trickyness in getting the
## main match infos from the HTML, since they are separated
## by a label, like here (2 Score 1):
##  ...<td align="right">2</td><td width="1" style="text-align:
##      center; font-size: 1.2em;">Score </td><td align="left">1
##      </td>...
##
## So what I am gonna do is to switch team when I face the
## label. I change state when I got the score value of
## the away team, and I switch back to home team too.
##
## This method is the prototype for the following states. It
## requires some extra parameters by them:
##     key: for the Match() object
##     label: explained later
##     next_state: obvious
##     data_type: str for string (default: int -- integer)

    def _specparse_centered(self, data,
        key, label, next_state, data_type=int):
        if data == label:
            self._team = "away"
        else:
            self._dict[self._team][key] = data_type(data)
            if self._team == "away":
                self.state, self._team = next_state, "home"

## > Score and Coach Name

    def _handle_score_data(self, data):
        self._specparse_centered(data, "touchdowns", "Score",
            "coach_name")

    def _handle_coach_name_data(self, data):
        self._specparse_centered(data, "coach_name", "Coach",
            "coach_ranking", data_type=str)

## > Coach Ranking
##
## To getting coach rankings I have to deal different
## formats for home and away cases:
##     home: ...>(171.91) Legend<...
##     away: ...>Star (155.74)<...
##
## The next state is spectators.

    def _handle_coach_ranking_data(self, data):
        if data == "Ranking":
            self._team = "away"
        else:
            if self._team == "home":
                s = re.search("^\((.+)\)\s(.+)$", data)
                cr, rank = s.groups()
            else:
                s = re.search("^(.+)\s\((.+)\)$", data)
                rank, cr = s.groups()
            self._dict[self._team]["coach_rank"] = rank
            self._dict[self._team]["coach_cr"] = float(cr)
            if self._team == "away":
                self.state, self._team = "spectators", "home"

## > Spectators, FAME, Winnings

    def _handle_spectators_data(self, data):
        self._specparse_centered(data, "spectators",
            "Spectators", "fame")

    def _handle_fame_data(self, data):
        self._specparse_centered(data, "FAME", "FAME",
            "winnings")

    def _handle_winnings_data(self, data):
        self._specparse_centered(data, "winnings", "Winnings",
            "spiralling_expenses")

## > Spiralling Expenses
##
## Much like getting the rest of center labelled data.
## However, the label here has two parts:
##  ...>Spiralling<br />Expenses<...
##
## I have to swich at one and skip the another. The next
## state is fanfactor_change.

    def _handle_spiralling_expenses_data(self, data):
        if data == "Expenses":
            return
        self._specparse_centered(data, "spiralling_expenses",
            "Spiralling", "fan_factor_change")

## > Fan factor Change
##
## The fan factor change can have data of the following formats:
##  ...>+1<... == 1
##  ...>No Change<... == 0
##  ...>-1<... == -1
##
## I have to define a custom function to convert them to the
## respective integers and to serve as a datatype.

    def _handle_fan_factor_change_data(self, data):
        def _ffdata(data):
            if data == "No Change":
                return 0
            return int(data)
        self._specparse_centered(data, "fan_factor_change",
            "Fanfactor", "casualties", data_type=_ffdata)

## > Casualties
##
## These data are containing three values (BH/SI/KILL):
##  ...>2/0/0<...
##
## I have to separate them and put them to the dictionary
## one-by-one.
##
## If any team have positive inducement value, then the
## next state is inducements, else it is players_table.

    def _handle_casualties_data(self, data):
        if data == "Casualties":
            self._team = "away"
        else:
            bh, si, kill = (int(s) for s in data.split("/"))
            self._dict[self._team]["casualties"]["bh"] = bh
            self._dict[self._team]["casualties"]["si"] = si
            self._dict[self._team]["casualties"]["kill"] = kill
            if self._team == "away":
                self._team = "home"
                if self._total_iv:
                    self.state = "inducements"
                else:
                    self.state = "players_table_row"

## > Inducements
##
## Inducements are also center labelled. However, a team can
## have a list of inducements, like:
##  ...>1 wizard<...
##  ...>\n2 bloodweiser babes<...
##  ...>\nMercenary Merc Lineman 1<...
##  ...>\nStar player Wilhelm Chaney<...
##
## I am gonna put them into a list in the team's subdictionary
## named "inducements". Those which have count value greater
## than one will be appended more than one times. I will use the
## following re:
##     "^\n?(\d*)\s?(.+?)\s*\d*$"
##
## It trims the unnecessary newlines from the front of the data,
## and results the following tuples respectively:
##     ('1', 'wizard')
##     ('2', 'bloodweiser babes')
##     ('', 'Mercenary Merc Lineman')
##     ('', 'Star player Wilhelm Chaney')
##
## What I need is to convert the count part to integer and
## treat empties as ones. Plus I want to trim "s" from the
## right part if count is greater than 1.
##
## I only know I am done with away team inducements is when I
## face with a "tr" tag. This is managed by the private method
## self._handle_inducements_starttag().

    def _handle_inducements_data(self, data):
        # TODO: Inducements given and remained by kick-off
        # results appear in the match reports which is a bug in
        # the reports page. However these suspicious inducements
        # can happen normally by using of petty cash. Some logic
        # handle them would be nice here.

        # TODO: Replace "()" named players with
        # "Mercenary Lineman"-like names.
        if data == "Inducements":
            self._team = "away"
            return
        s = re.search("^\n?(\d*)\s?(.+?)\s*\d*$", data)
        if not s.group(1):
            count = 1
        else:
            count = int(s.group(1))
        if count > 1:
            name = s.group(2).title().rstrip("s")
            name = name.replace("ies", "y")
        else:
            name = s.group(2).title()
        name = name.replace(" Merc ", " ")
        for n in range(count):
            self._dict[self._team]["inducements"].append(name)

    def _handle_inducements_starttag(self, tag, a_dict):
        if self._team == "away" and tag == "tr":
            self.state = "players_table_row"

## > A New Row in the Player Performance Table
##
## A row of player performance starts with a "tr" tag aligned to
## right, and it has class="odd" or class="even", like here:
##  ...<tr align="right" class="odd"><td align="left">#2 <...
##
## If I face that I set state to player_nr, since that is the
## first data of such a row.
##
## A line of Total has a style attribute instead:
##  ...<tr align="right" style="color: white; background: b
##      lack;"><td colspan="2"><b>Total</b>...
##
## If I face this I set state to total_performance. In both
## cases I reset the player performance index since from now on
## they will come in a predefined order
## (PLAYER_PERFORMANCE_ORDER). I will use a private dictionary
## alias ("self._perfrow") to put data into, and I redefine it
## when I get to a new row. It is easyer than keeping track of
## the current player's performance dictionary location.

    def _handle_players_table_row_starttag(self, tag, a_dict):
        if tag != "tr" or a_dict.get("align") != "right":
            return
        self._perfrow, self._player_perf_i = {}, 0
        if "class" in a_dict:
            self.state  = "player_nr"
        elif "style" in a_dict:
            self.state  = "total_performance"

## > Player Nr.
##
## Player number data looks like this in the HTML code:
##  ...>#7 <...
##
## I only need the integer "7" from this. The player number is
## going to be the key of the players subdictionary of a team.
## Whit this information I attach the self._perfrow() dictionary
## to the team's player_performances subdictionary. As I
## mentioned earlier, I do not need to keep track of this
## location anymore, I only have to put data into
## self._perfrow() and make a new self._perfrow() for next line.
##
## The next state is player_id.

    def _handle_player_nr_data(self, data):
        _dict = self._dict[self._team]["players"]
        _dict[int(data.strip().lstrip("#"))] = self._perfrow
        self.state = "player_id"

## > Player ID.
##
## After the player number comes the link to the player
## which encloses his or her name and includes the ID too:
##  ...<a href="/p/player?player_id=9671127">Lúthien</a>...
##
## The next state is player_name.

    def _handle_player_id_starttag(self, tag, a_dict):
        parsed_link = parse.parse_qs(a_dict["href"])
        p_id = int(parsed_link["/p/player?player_id"].pop())
        self._perfrow["player_id"] = p_id
        self.state = "player_name"

## > Player Name
##
## I just need the plain data now.

    def _handle_player_name_data(self, data):
        self._perfrow["name"] = data
        self.state = "players"

## > Player Performance Data
##
## I parse the performance data of the actual player according
## to the order defined in PLAYER_PERFORMANCE_ORDER. All data
## has integer type. After I am done I increment the performance
## index by one, and I check if I am done with the line, in
## which case I reset it to zero and I switch state to
## players_table_row.

    def _handle_players_data(self, data):
        _name = PLAYER_PERFORMANCE_ORDER[self._player_perf_i]
        self._perfrow[_name] = int(data)
        self._player_perf_i += 1
        if self._player_perf_i >= len(PLAYER_PERFORMANCE_ORDER):
            self._player_perf_i = 0
            self.state = "players_table_row"

## > Total Team Performance
##
## Quite the same as a player performance row without turns
## stat. However the "Total" label uses colspan of two, so it
## would be treated as turns value. To avoid this I am gonna put
## stats to the dictionary only from performance index of 2.
## When I am done with the line, I switch to permanent_injuries.

    def _handle_total_performance_data(self, data):
        _name = PLAYER_PERFORMANCE_ORDER[self._player_perf_i]
        if self._player_perf_i > 0:
            _dict = self._dict[self._team]["team_performance"]
            _dict[_name] = int(data)
        self._player_perf_i += 1
        if self._player_perf_i >= len(PLAYER_PERFORMANCE_ORDER):
            self.state = "permanent_injuries"

## > Permanent Injuries
##
## The injuries are looking like this in the HTML code:
##  ...<div align="center"><br />#2 Lúthien (Broken Ribs (MNG))<
##      br />#9 Indis (Dead (RIP))</div>...
##
## Since a player can have more than one injuries I use a list
## to store injuries data inside the "players" subdictionary of
## a team under the key "permanent_injury".
##
## I only know I am done with permanent injuries when I face
## with a "div" endtag. That's what
## self._handle_permanent_injuries_endtag() manages.

    def _handle_permanent_injuries_data(self, data):
        s = re.search("^#(\d+) (.+?) \((.+)\)$", data)
        player_nr = int(s.group(1))
        _dict = self._dict[self._team]["players"][player_nr]
        if not "permanent_injury" in _dict:
            _dict["permanent_injury"] = []
        _dict["permanent_injury"].append(s.group(3))

    def _handle_permanent_injuries_endtag(self, tag):
        if tag != "div":
            return
        if self._team == "home":
            self._team = "away"
            self.state = "players_table_row"
        else:
            self.state = "done"

def get_match_info(match_id):
    url = MATCH_URL + str(match_id)
    response = request.urlopen(url)
    page = response.read().decode("utf-8")
    parser = MatchPageParser()
    parser.feed(page)
    return parser._dict

