"""
Updates the coaches.csv file.
"""

from coach.csv import CoachInfo, csv_lastid, \
    generate_coach_csv, get_coachinfo, _update_coach_csv
from match.api import get_match_info
from match.watcher import MatchWatcher

def update_coach_csv(
    csv_file_path,
    from_datetime,
    to_datetime,
    verbose=True):
    if to_datetime < from_datetime:
        raise ValueError("To datetime have to be newer.")

    generate_coach_csv(
        csv_file_path,
        csv_lastid(csv_file_path) + 1,
        1000000,
        )

    def exclude_by_match():
        while True:
            match_obj = yield
            home_coach = m["home"]["coach_id"]
            if home_coach not in excluded_coaches:
                excluded_coaches[home_coach] = [0, 0, 0]
            away_coach = m["away"]["coach_id"]
            if away_coach not in excluded_coaches:
                excluded_coaches[away_coach] = [0, 0, 0]
            home_tds = m["home"]["touchdowns"]
            away_tds = m["away"]["touchdowns"]
            if home_tds > away_tds:
                excluded_coaches[home_coach][0] += 1
                excluded_coaches[away_coach][2] += 1
            elif home_tds < away_tds:
                excluded_coaches[home_coach][2] += 1
                excluded_coaches[away_coach][0] += 1
            else:
                excluded_coaches[home_coach][1] += 1
                excluded_coaches[away_coach][1] += 1
            print(home_coach, excluded_coaches[home_coach])
            print(away_coach, excluded_coaches[away_coach])

    coaches_to_refresh = set()
    excluded_coaches, coroutine = {}, exclude_by_match()
    # I jump to yield in the coroutine.
    next(coroutine)
    watcher = MatchWatcher(coroutine)
    watcher.start()

    match_iterator = get_match_info(endpage=1000000)
    while True:
        m = next(match_iterator)
        print(m["date"])
        if m["date"] >= to_datetime:
            coroutine.send(m)
        elif m["date"] >= from_datetime:
            home_coach = m["home"]["coach_id"]
            away_coach = m["away"]["coach_id"]
            coaches_to_refresh |= {home_coach, away_coach}
        else:
            break

    coachinfos = {}
    for c in coaches_to_refresh:
        base_coachinfo = get_coachinfo(c)
        print(str(base_coachinfo).encode("utf-8", "ignore"))
        record_adj = excluded_coaches.get(c, [0, 0, 0])
        base_record = [int(n) for n in
            base_coachinfo.record.split("/")]
        new_record = [str(base_record[i] - v) for i, v
            in enumerate(record_adj)]
        coachinfo_kargs = base_coachinfo._asdict()
        coachinfo_kargs["record"] = "/".join(new_record)
        new_coachinfo = CoachInfo(**coachinfo_kargs)
        coachinfos[c] = new_coachinfo
        print(str(new_coachinfo).encode("utf-8", "ignore"))
    watcher.running = False

    _update_coach_csv(csv_file_path, coachinfos)

