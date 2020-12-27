import hashlib
import json
from base64 import b64decode, b64encode
from glob import glob
from pathlib import Path

from flask import Flask, abort, request

from activate.core import activity, serialise

DATA_DIR = Path("/var/lib/activate")

USERS_FILE = DATA_DIR / "users.json"
ACTIVITIES_DIR = DATA_DIR / "activities"

app = Flask(__name__)

ACTIVITIES_DIR.mkdir(parents=True, exist_ok=True)


def load_activity(activity_id):
    return activity.Activity(
        **serialise.load(str(ACTIVITIES_DIR / f"{activity_id}.json.gz"))
    )


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
    new_activity.save(f"{ACTIVITIES_DIR}/")
    return "DONE"


@app.route("/delete_activity/<string:activity_id>")
@requires_auth
def delete_activity(activity_id):
    (ACTIVITIES_DIR / f"{activity_id}.json.gz").unlink()


@app.route("/get_activities")
@requires_auth
def get_list():
    return serialise.dump_bytes(
        [Path(p).stem.replace(".json", "") for p in glob(f"{ACTIVITIES_DIR}/*")]
    )


@app.route("/get_activity/<string:activity_id>")
@requires_auth
def get_activity(activity_id):
    try:
        activity_ = load_activity(activity_id)
    except FileNotFoundError:
        abort(404)
    return serialise.dump_bytes(activity_.save_data)


users = get_users()
