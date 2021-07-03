import hashlib
import json
import sqlite3
from base64 import b64decode, b64encode
from datetime import timedelta
from functools import wraps
from pathlib import Path
from uuid import UUID

import pkg_resources
from flask import Flask, abort, g, request

from activate import activity, serialise

DATA_DIR = Path("/var/lib/activate")

USERS_FILE = DATA_DIR / "users.json"

app = Flask(__name__)

ACTIVITIES_DIR = DATA_DIR / "activities"
ACTIVITIES_DIR.mkdir(parents=True, exist_ok=True)

ACTIVITIES_DATABASE_PATH = DATA_DIR / "activities.sqlite"

sqlite3.register_converter("DICT", serialise.loads)
sqlite3.register_adapter(dict, serialise.dumps)

sqlite3.register_converter(
    "TIMEDELTA", lambda d: timedelta(seconds=float(d) if b"." in d else int(d))
)
sqlite3.register_adapter(timedelta, lambda d: d.total_seconds())

sqlite3.register_converter("UUID", lambda u: UUID(u.decode("utf-8")))
sqlite3.register_adapter(UUID, str)


def add_row(database, table: str, values: dict):
    """Add a row to an SQLite database."""
    database.execute(
        f"INSERT INTO {table} ({', '.join(values)})"
        f" VALUES ({', '.join(f':{v}' for v in values)})",
        values,
    )


def get_row(database, table: str, values: dict):
    """Find a row in an SQLite database."""
    return database.execute(
        f"SELECT * FROM {table} WHERE {' AND '.join(f'{v} = :{v}' for v in values)}",
        values,
    ).fetchone()


def delete_by_id(activities, activity_id):
    """Delete a row with a given activity_id."""
    activities.execute(
        "DELETE FROM activities WHERE activity_id = ?", [str(activity_id)]
    )


def reset_activities():
    """Generate a blank activities database."""
    db = load_database()
    db.executescript(
        pkg_resources.resource_string("activate.resources", "init.sql").decode("utf-8")
    )
    db.commit()


def load_database():
    db = sqlite3.connect(
        ACTIVITIES_DATABASE_PATH,
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
    )
    db.row_factory = sqlite3.Row
    return db


def get_activities():
    if "db" not in g:
        g.db = load_database()

    return g.db


@app.teardown_appcontext
def close_activities(e=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()


def get_users():
    try:
        with open(USERS_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_users():
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
    @wraps(function)
    def new_function(*args, **kwargs):
        if not verify_request():
            abort(403)
        return function(*args, **kwargs)

    return new_function


@app.route("/")
def index():
    return "This is an Activate server."


@app.route("/api/send_activity", methods=["POST"])
@requires_auth
def upload():
    data = serialise.loads(request.form["activity"])
    data["username"] = request.authorization["username"]
    new_activity = activity.Activity(**data)
    activities = get_activities()
    delete_by_id(activities, new_activity.activity_id)
    add_row(
        activities,
        "activities",
        {
            "name": new_activity.name,
            "sport": new_activity.sport,
            "flags": new_activity.flags,
            "effort_level": new_activity.effort_level,
            "start_time": new_activity.start_time,
            "distance": new_activity.distance,
            "duration": new_activity.track.elapsed_time,
            "climb": new_activity.track.ascent,
            "activity_id": new_activity.activity_id,
            "username": new_activity.username,
        },
    )
    new_activity.save(ACTIVITIES_DIR)
    activities.commit()
    return "DONE"


@app.route("/api/delete_activity/<string:activity_id>")
@requires_auth
def delete_activity(activity_id):
    activity_id = UUID(activity_id)
    activities = get_activities()
    row = get_row(activities, "activities", {"activity_id": activity_id})
    if row["username"] != request.authorization["username"]:
        abort(403)
    delete_by_id(activities, activity_id)
    activities.commit()
    return "DONE"


@app.route("/api/get_activities")
@requires_auth
def get_list():
    activities = get_activities()
    activities = activities.execute("SELECT * FROM activities").fetchall()
    return serialise.dump_bytes([{k: a[k] for k in a.keys()} for a in activities])


@app.route("/api/get_activity/<string:activity_id>")
@requires_auth
def get_activity(activity_id):
    activity_id = UUID(activity_id)
    activities = get_activities()
    try:
        get_row(activities, "activities", {"activity_id": activity_id})
    except FileNotFoundError:
        abort(404)
    with open(ACTIVITIES_DIR / f"{activity_id}.json.gz", "rb") as f:
        return f.read()


users = get_users()
if not ACTIVITIES_DATABASE_PATH.exists():
    reset_activities()
