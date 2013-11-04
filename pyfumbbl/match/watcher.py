"""
This module helps watching finished games.
"""

from queue import Queue
from time import sleep
from threading import Thread

from match.api import get_match_info

class MatchWatcher(Thread):
    """
    Sends all new matches to the given coroutine until it
    reaches the
    """
    def __init__(self,
        coroutine,
        check_interval=10):
        super().__init__()
        self.coroutine = coroutine
        self.running = True
        self.check_interval = check_interval
        most_recent = next(get_match_info())
        self.reference_match_id = most_recent["match_id"]
        self.last_match_id = most_recent["match_id"]

    def run(self):
        while self.running:
            match_iterator = get_match_info(endpage=1000000)
            m = next(match_iterator)
            new_last_id = m["match_id"]
            while m["match_id"] != self.last_match_id:
                self.coroutine.send(m)
                m = next(match_iterator)
            self.last_match_id = new_last_id
            sleep(self.check_interval)

