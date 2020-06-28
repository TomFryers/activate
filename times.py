import datetime

ONE_DAY = datetime.timedelta(days=1)
ONE_HOUR = datetime.timedelta(hours=1)
ONE_MINUTE = datetime.timedelta(minutes=1)


def from_GPX(string):
    if string is None:
        return None
    return datetime.datetime.fromisoformat(string.rstrip("Z"))


def to_string(time):
    result = []
    if time.days:
        result += [str(time.days), " d "]
        time %= ONE_DAY
    if time >= ONE_HOUR:
        result += [f"{time // ONE_HOUR:0>2d}", ":"]
        time %= ONE_HOUR
    if time >= ONE_MINUTE:
        result += [f"{time // ONE_MINUTE:0>2d}", ":"]
        time %= ONE_MINUTE
    secs = time.total_seconds()
    if int(secs) == secs:
        secs = int(secs)
        result.append(f"{secs:0>2d}")
    else:
        result.append(f"{secs:0>.2f}")
    return "".join(result)

def nice(time):
    return time.strftime("%A %d %B %Y\n%H:%M")
