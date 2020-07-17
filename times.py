import datetime

ONE_DAY = datetime.timedelta(days=1)
ONE_HOUR = datetime.timedelta(hours=1)
ONE_MINUTE = datetime.timedelta(minutes=1)


def from_GPX(string) -> datetime.datetime:
    """Load a time from a string in GPX format."""
    if string is None:
        return None
    return datetime.datetime.fromisoformat(string.rstrip("Z"))


def to_string(time: datetime.timedelta, exact=False):
    """Convert a time to a nicely formatted string."""
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
    if int(secs) == secs or not exact:
        secs = int(secs)
        result.append(f"{secs:0>2d}")
    else:
        result.append(f"{secs:0>.2f}")
    return "".join(result).lstrip("0")


def nice(time: datetime.datetime):
    """Format a time on two lines neatly."""
    return time.strftime("%A %d %B %Y\n%H:%M")


def round_time(time: datetime.datetime) -> datetime.datetime:
    """Round a time to the nearest second."""
    return time.replace(
        microsecond=0, second=round(time.second + time.microsecond / 1000000)
    )


def to_number(value):
    """Convert a timedelta to seconds, leaving other values untouched."""
    if isinstance(value, datetime.timedelta):
        return value.total_seconds()
    return value


def is_in_period(compare, original, /, period: str, number=0):
    if period == "year":
        return original.year - compare.year == number
    if period == "month":
        return (
            original.month - compare.month + (original.year - compare.year) * 12
            == number
        )
    if period == "week":
        value = (original.date() - compare.date()).days // 7
        if compare.weekday() > original.weekday():
            value += 1
        return value == number
