import re
import shutil
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from activate import serialise
from activate.app import files, load_activity, paths
from activate.app.sync import strava

FILENAME = re.compile(r'filename="(.*)"')


def download_response(response, path):
    try:
        filename = next(
            FILENAME.finditer(response.headers["Content-Disposition"])
        ).group(1)
    except KeyError:
        filename = response.url.split("/")[-1]
    filename = files.encode_name(filename, path)
    with open(filename, "wb") as f:
        response.raw.decode_content = True
        shutil.copyfileobj(response.raw, f)
    return filename


def add_photo_from_response(response, activity):
    filename = download_response(response, paths.PHOTOS)
    activity.photos.append(filename)


def import_from_response(response):
    filename = download_response(response, paths.TRACKS)
    activity = load_activity.load(filename)
    activity["filename"] = filename
    return activity


@dataclass
class SyncState:
    state: Optional[defaultdict] = None

    def ensure_loaded(self):
        if self.state is not None:
            return
        try:
            self.state = defaultdict(
                dict, {UUID(k): v for k, v in serialise.load(paths.SYNC_STATE).items()}
            )
        except FileNotFoundError:
            self.state = defaultdict(dict)

    def write(self):
        serialise.dump(
            {str(k): v for k, v in self.state.items()}, paths.SYNC_STATE, gz=True
        )

    def add(self, service, activity_id, service_activity_id):
        self.state[activity_id] = {service: service_activity_id}

    def get(self, service, activity_id):
        return self.state[activity_id].get(service)

    def sync(self, cookies, activities):
        """
        Download new activities.

        Returns a generator. The first value is the number of items after
        it. The other items are Activities.
        """
        yield from strava.sync_new(cookies["Strava"], activities, self)


sync_state = SyncState()
