from flask import Flask, request

from activate.core import activity, serialise

app = Flask(__name__)

activities = {}


@app.route("/")
def index():
    return "This is an Activate server."


@app.route("/send_activity", methods=["POST"])
def upload():
    new_activity = activity.Activity(*serialise.loads(request.form["activity"]))
    activities[new_activity.activity_id] = new_activity
    return "DONE"


@app.route("/get_activities")
def get_list():
    return serialise.dump_bytes(list(activities.keys()))


@app.route("/get_activity/<int:activity_id>")
def get_activity(activity_id):
    try:
        return serialise.dump_bytes(activities[activity_id].save_data)
    except KeyError:
        return "NOT FOUND"
