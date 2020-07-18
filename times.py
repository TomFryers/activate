import datetime

ONE_DAY = datetime.timedelta(days=1)
ONE_HOUR = datetime.timedelta(hours=1)
ONE_MINUTE = datetime.timedelta(minutes=1)


def from_GPX(string):
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


def period_difference(base, other, period: str) -> int:
    """
    Determine the number of years/months/weeks between other and base.

    Returns 0 if they are in the same week, 1 if other is in the
    previous week etc.
    """
    if period == "year":
        return base.year - other.year
    if period == "month":
        return base.month - other.month + (base.year - other.year) * 12
    if period == "week":
        value = (base.date() - other.date()).days // 7
        if other.weekday() > base.weekday():
            value += 1
        return value
    raise ValueError('period must be "year", "month" or "week"')


def to_this_period(base, other, period: str):
    if period == "year":
        return other.replace(year=base.year)
    if period == "month":
        return other.replace(year=base.year, month=base.month)
    if period == "week":
        return other.replace(year=base.year, month=base.month, day=base.day) + (
            other.weekday() - base.weekday()
        ) * datetime.timedelta(days=1)
