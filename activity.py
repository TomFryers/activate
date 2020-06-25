import times


class Activity:
    def __init__(self, name, start_time, track=None):
        self.name = name
        self.start_time = start_time
        self.track = track

    @property
    def stats(self):
        return {
            "Distance": f"{self.track.length / 1000:.2f}",
            "Elapsed Time": times.to_string(self.track.elapsed_time),
            "Ascent": self.track.ascent if "ele" in self.track.fields else "None",
            "Average Speed": f"{self.track.average_speed * 3.6:.2f}",
        }

    @property
    def list_row(self):
        return [self.name, str(self.start_time), f"{self.track.length / 1000:.2f}"]
