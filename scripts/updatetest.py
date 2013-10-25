from apimatch import played_since
from coachcsv import csv_lastid, generate_coach_csv, update_coach_csv
from datetime import datetime

# First I update the CSV file with new registered coaches
generate_coach_csv("coaches.csv", csv_lastid("coaches.csv") + 1, 1000000)

print(datetime.now())

# Then I update it with new data
update_coach_csv("coaches.csv", played_since(
    datetime(2013, 10, 22)))

