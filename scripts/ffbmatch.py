"""Module for parsing FFB match data of FUMBBL."""

# ffbmatch.py by Adam Szieberth (2013)
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

from socket import socket as socket_, timeout, AF_INET, \
    SOCK_STREAM

BUFFER_SIZE = 10
RECV_SIZE = 1452
TCP_IP = "h89n19-aars-gr100.ias.bredband.telia.com"
TCP_PORT = 2223
TIMEOUT = 2

def get_match_data(matchid):
    """Retrieves the raw data of an FFB match from the FUMBBL
server based on its match id.

Unfortunately the server is not sending an empty message to
sign the end of the stream. However this function supports it.
However, usually we have to wait for timeout to know we got all
data of the match."""
    result = b""
    hexmessage = "002f00100001{:0>16x}0000".format(matchid)
    message = bytearray.fromhex(hexmessage)
    with socket_(AF_INET, SOCK_STREAM) as s:
        s.connect((TCP_IP, TCP_PORT))
        s.settimeout(TIMEOUT)
        s.send(message)
        while True:
            try:
                msg = s.recv(RECV_SIZE)
            except timeout:
                break
            else:
                if len(msg) == 0:
                    break
            result += msg
    return result

