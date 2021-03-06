import json
from flask import Flask, request
from db import db, Time
import requests
from threading import Timer
from constants import *
from datetime import datetime as dt, date, timedelta
import calendar

db_filename = "todo.db"
app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///%s' % db_filename
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True


db.init_app(app)
with app.app_context():
    db.create_all()

def individual_time_format(individual_time):
  """
  Helper function that takes in split time string and converts it to the proper
  time format
  """
  if ":" in individual_time:
    individual_time = individual_time.replace("pm", " PM")
    individual_time = individual_time.replace("am", " AM")
  else:
    individual_time = individual_time.replace("pm", ":00 PM")
    individual_time = individual_time.replace("am", ":00 AM")
  return individual_time

def make_time_format(time):
  """
  Helper function that takes in time string and converts it to the proper
  time format 4:00 PM - 11:00 PM"
  """
  if "-" in time:
    time_split = time.split('-', 1)
    time_from = time_split[0]
    time_to = time_split[1]
    return individual_time_format(time_from)+"-"+individual_time_format(time_to)
  else:
    return time

def get_all_times(weeks):
  """
  Helper function that takes in weeks from library json and gives array of
  times of 7 days from today
  """
  date_today = date.today()
  upper_date_bound = date_today + timedelta(days=7)
  result = []
  for value in weeks:
    for day in value.keys():
      times_date = dt.strptime(value[day]["date"], "%Y-%m-%d").date()
      if times_date >= date_today and times_date < upper_date_bound:
        result.append(make_time_format(value[day]["rendered"]))
  return result

def update_cafe():
  """
  Updates cafe time
  """
  cafe_names = ["Amit Bhatia Libe Café"]
  cafe_names_libraries = {"Amit Bhatia Libe Café": "Olin Library"}
  jsons = requests.get("https://now.dining.cornell.edu/api/1.0/dining/eateries.json").json()
  for value in jsons["data"]["eateries"]:
    if value["name"] in cafe_names:
      for day in value["operatingHours"]:
        if day["date"] == str(date.today()):
          time = day["events"][0]["start"]+" - "+ day["events"][0]["end"]
          time = time.replace("am", " AM")
          time = time.replace("pm", " PM")
          record = Time.query.filter_by(name=cafe_names_libraries[value["name"]]).first()
          record.information = [record.information[0], record.information[1], record.information[2], record.information[3], time, record.information[5]]
          db.session.commit()

@app.route('/api/hidden/initialize/')
def initial():
  """
  Hardcoding fixed data
  """
  for i in range(len(LIBRARY_NAMES)):
    record = Time(
        name = LIBRARY_NAMES[i],
        json_name = LIBRARY_NAMES_JSON[i],
        image_url = IMAGE_GITHUB_URL + IMAGE_NAMES[i],
        information = LIBRARY_INFORMATION[i],
        location = LIBRARY_LOCATION[i]
    )
    db.session.add(record)
    db.session.commit()
  return get_times()

@app.route('/api/hidden/update/')
def update():
  """
  Update times of all libraries
  """
  times_json = requests.get(CORNELL_LIBRARY_TIMES_URL).json()
  try:
    update_cafe()
    for value in times_json["locations"]:
      if value["name"] == "Manndible": # Updating Maandible Cafe time
          record = Time.query.filter_by(name="Mann Library").first()
          cafe_time = value["weeks"][0][calendar.day_name[date.today().weekday()]]["rendered"]
          record.information = [record.information[0], record.information[1], record.information[2], record.information[3], make_time_format(cafe_time), record.information[5]]
          db.session.commit()
      record = Time.query.filter_by(json_name=value["name"]).first()
      if record is not None:
        record.times = get_all_times(value["weeks"])
        db.session.commit()
    return get_times()
  except Exception as e:
    print('Update failed: ', e)


@app.route('/api/times/')
def get_times():
    """
    Gets all information for all libraries
    """
    return json.dumps({
      'success': True,
      'data': { "libraries": [lib.serialize() for lib in Time.query.all()] }
    }), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
