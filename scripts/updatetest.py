from apimatch import played_since
from coachcsv import update_coach_csv
from datetime import datetime

update_coach_csv("coaches.csv", played_since(
    datetime(2013, 10, 22)))

