"""Module for getting informations about choaches who are or
were played matches in some way."""

# pyfumbbl/coach/played.py by Adam Szieberth (2013)
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

from match.api import _get_match_date, get_match_ets, \
    DATE_FORMAT, URL

def since(datetime_obj):
    """Generates the IDs of coaches who played at least a match
since the given time."""
    id_s, iterator = set(), get_match_ets(endpage=None)
    match_et = next(iterator)
    while _get_match_date(match_et) >= datetime_obj:
        s = {int(match_et.find(ha).find("coach").attrib["id"])
            for ha in ("home", "away")}
        for id_ in s - id_s:
            yield id_
        id_s |= s
        match_et = next(iterator)

