import hashlib
import json
from base64 import b64decode, b64encode
from pathlib import Path
from uuid import UUID

from flask import Flask, abort, request

from activate.core import activity, activity_list, serialise

DATA_DIR = Path("/var/lib/activate")

USERS_FILE = DATA_DIR / "users.json"

app = Flask(__name__)

(DATA_DIR / activity_list.ACTIVITIES_DIR_NAME).mkdir(parents=True, exist_ok=True)


def get_users():
    try:
        with open(USERS_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(f, users)


def password_hash(password: str, salt):
    return b64encode(
        hashlib.scrypt(
            password.encode("utf-8"), salt=b64decode(salt), n=16384, r=8, p=1
        )
    ).decode("utf-8")


def verify_request():
    """Check username and password against the database."""
    if request.authorization is None:
        return False
    username = request.authorization["username"]
    if username not in users:
        return False
    password = request.authorization["password"]
    return (
        password_hash(password, users[username]["salt"])
        == users[username]["password_hash"]
    )


def requires_auth(function):
    def new_function(*args, **kwargs):
        if not verify_request():
            abort(403)
        return function(*args, **kwargs)

    new_function.__name__ = function.__name__
    return new_function


@app.route("/")
def index():
    return "This is an Activate server."


@app.route("/send_activity", methods=["POST"])
@requires_auth
def upload():
    data = serialise.loads(request.form["activity"])
    data["username"] = request.authorization["username"]
    new_activity = activity.Activity(**data)
    activities.add_activity(new_activity)
    activities.save()
    return "DONE"


@app.route("/delete_activity/<string:activity_id>")
@requires_auth
def delete_activity(activity_id):
    try:
        username = activities.by_id(activity_id).username
    except KeyError:
        return "DONE"
    if username != request.authorization["username"]:
        abort(403)
    activities.remove(UUID(activity_id))
    activities.save()
    return "DONE"


@app.route("/get_activities")
@requires_auth
def get_list():
    return serialise.dump_bytes(activities.serialised())


@app.route("/get_activity/<string:activity_id>")
@requires_auth
def get_activity(activity_id):
    try:
        activity_ = activities.get_activity(UUID(activity_id))
    except KeyError:
        abort(404)
    return serialise.dump_bytes(activity_.save_data)


users = get_users()
activities = activity_list.from_disk(DATA_DIR)
