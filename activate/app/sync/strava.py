"""Sync activities with other services."""

import json
from datetime import datetime

import requests

import activate.activity
from activate.app import load_activity, sync


def strava_url(page: str) -> str:
    return f"https://www.strava.com/{page}"


def list_activities(cookie: str) -> dict:
    response = requests.get(
        strava_url("athlete/training?page=1"),
        headers={"X-Requested-With": "XMLHttpRequest"},
        cookies={"_strava4_session": cookie},
    )
    return {a["id"]: a for a in json.loads(response.text)["models"]}


def get_activity_data(strava_activity_id: int, cookie: str) -> requests.models.Response:
    page = f"activities/{strava_activity_id}"

    activity_file = requests.get(
        strava_url(f"{page}/export_original"),
        cookies={"_strava4_session": cookie},
        stream=True,
    )
    return activity_file


def sport(data):
    return load_activity.convert_activity_type(data["type"], data["name"])


def update_local(activity, data):
    activity.name = data["name"]
    activity.sport = sport(data)
    activity.description = (
        data["description"] if data["description"] is not None else ""
    )


def matches(activity, data):
    return all(
        (
            datetime.fromisoformat(data["start_time"][:-5]) == activity.start_time,
            sport(data) == activity.sport,
        )
    )


def sync_new(cookie, activities, sync_list):
    """
    Download new activities from Strava.

    Returns a generator. The first value is the number of items after
    it. The other items are Activities.
    """
    remote_activities = list_activities(cookie)
    for activity in activities:
        strava_id = sync_list.get("Strava", activity.activity_id)
        if strava_id is None:
            for remote_id, data in remote_activities.items():
                if matches(activity, data):
                    sync_list.add("Strava", activity.activity_id, remote_id)
                    strava_id = remote_id
                    break
            else:
                continue

        elif strava_id not in remote_activities:
            continue
        update_local(activity, remote_activities[strava_id])
        del remote_activities[strava_id]

    yield len(remote_activities)

    for strava_activity_id, data in remote_activities.items():
        activity = activate.activity.from_track(
            **sync.import_from_response(get_activity_data(strava_activity_id, cookie))
        )
        update_local(activity, data)
        sync_list.add("Strava", activity.activity_id, strava_activity_id)
        yield activity
