"""Module for fetching and parsing of FUMBBL matches."""

# pyfumbbl/match/__init__.py by Adam Szieberth (2013)
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

from copy import deepcopy

PLAYER_PERFORMANCE = {
    "completions": None,
    "touchdowns": None,
    "interceptions": None,
    "casualties": None,
    "mvps": None,
    "passing": None,
    "rushing": None,
    "blocks": None,
    "fouls": None,
    "turns": None,
    }

CASUALTIES_DICT = {
    "total": None,
    "bh": None,
    "si": None,
    "kill": None,
    }

TEAM_DICT = {
    "casualties": dict(CASUALTIES_DICT),
    "coach_cr": None,
    "coach_id": None,
    "coach_name": None,
    "coach_rank": None,
    "FAME": None,
    "fan_factor": None,
    "fan_factor_change": None,
    "inducement_value": None,
    "players": {},
    "spectators": None,
    "spiralling_expenses": None,
    "team_id": None,
    "team_name": None,
    "team_race": None,
    "touchdowns": None,
    "TV": None,
    "TW": None,
    "winnings": None,
    }

INITIAL_DICT = {
    "away": deepcopy(TEAM_DICT),
    "date": None,
    "division": None,
    "gate": None,
    "home": deepcopy(TEAM_DICT),
    "match_id": None,
    "replay_id": None,
    }

_DIFF_ERR_MSG = "Match dictionaries differ!"

class Match:
    def __init__(self):
        self._dict = deepcopy(INITIAL_DICT)

    def update(self, match_dict, orig_dict=None):
        if orig_dict is None:
            orig_dict = self._dict
        for k, v in match_dict.items():
            if v is None:
                continue
            elif isinstance(v, dict):
                if k == "players":
                    self._players_update(v, orig_dict[k])
                else:
                    self.update(v, orig_dict=orig_dict[k])
            elif orig_dict[k] is None:
                orig_dict[k] = v
            elif orig_dict[k] != v:
                raise ValueError(_DIFF_ERR_MSG)

    def _players_update(self, new_perf_dict, orig_perf_dict):
        for player_id, player_data in new_perf_dict.items():
            if player_id in orig_perf_dict:
                orig_perf = orig_perf_dict[player_id]
                for k, v in player_data.items():
                    if orig_perf.get(k) is None:
                        orig_perf[k] = v
                    elif orig_perf[k] != v:
                        raise ValueError(_DIFF_ERR_MSG)
            else:
                orig_perf_dict[player_id] = player_data

