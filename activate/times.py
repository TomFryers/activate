"""Functions for dealing with datetimes and timedeltas."""
from datetime import datetime, timedelta

ONE_WEEK = timedelta(days=7)
ONE_DAY = timedelta(days=1)
ONE_HOUR = timedelta(hours=1)
ONE_MINUTE = timedelta(minutes=1)

EPOCH = datetime.fromtimestamp(0) + timedelta(365 * 3 + 1)

MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def from_GPX(string):
    """Load a time from a string in GPX format."""
    if string is None:
        return None
    return datetime.fromisoformat(string.rstrip("Z"))


def to_string(time: timedelta, exact=False):
    """Convert a time to a nicely formatted string."""
    result = []
    started = False
    if time.days:
        result += [str(time.days), " d "]
        time %= ONE_DAY
        started = True
    if time >= ONE_HOUR or started:
        result += [f"{time // ONE_HOUR:0>2d}", ":"]
        time %= ONE_HOUR
        started = True
    if time >= ONE_MINUTE or started:
        result += [f"{time // ONE_MINUTE:0>2d}", ":"]
        time %= ONE_MINUTE
    secs = time.total_seconds()
    if int(secs) == secs or not exact:
        secs = int(secs)
        result.append(f"{secs:0>2d}")
    else:
        result.append(f"{secs:0>.2f}")
    # Only seconds
    if len(result) == 1:
        result.append(" s")

    return "".join(result).lstrip("0").strip()


def nice(time: datetime):
    """Format a time on two lines neatly."""
    return time.strftime("%A %d %B %Y\n%H:%M")


def round_time(time: datetime) -> datetime:
    """Round a time to the nearest second."""
    new = time - timedelta(microseconds=time.microsecond)
    return new + timedelta(seconds=1) if time.microsecond >= 500000 else new


def to_number(value):
    """Convert a timedelta to seconds, leaving other values untouched."""
    if isinstance(value, timedelta):
        return value.total_seconds()
    return value


def back_name(base, period: str, number=0):
    """Get the name of a year, month or week number back."""
    if period == "year":
        return str(base.year - number)
    if period == "month":
        return MONTHS[(base.month - number - 1) % 12]
    if period == "week":
        date = base.date() - number * ONE_WEEK - timedelta(days=base.weekday())
        return f"w/c {date:%d %b}"
    if period == "day":
        return str((base - ONE_DAY * number).day)
    if period == "weekday":
        return f"{base - ONE_DAY * number:%A}"
    raise ValueError('period must be "year", "month" or "week"')


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
    if "day" in period:
        return (base.date() - other.date()).days
    raise ValueError('period must be "year", "month" or "week"')


def since_start(base, period: str) -> timedelta:
    """Return the time since the start of the current period."""
    return base - start_of(base, period)


def start_of(base, period: str) -> datetime:
    """Get the start of the current period."""
    if period == "year":
        return datetime(year=base.year, month=1, day=1)
    if period == "month":
        return datetime(year=base.year, month=base.month, day=1)
    if period == "week":
        return (
            datetime(year=base.year, month=base.month, day=base.day)
            - base.weekday() * ONE_DAY
        )
    if "day" in period:
        return datetime(year=base.year, month=base.month, day=base.day)
    raise ValueError('period must be "year", "month", "week" or "day"')


def end_of(base, period: str) -> datetime:
    """Get the end of the current period."""
    if period == "year":
        return start_of(base.replace(year=base.year + 1), period)
    if period == "month":
        if base.month == 12:
            return start_of(base.replace(year=base.year + 1, month=1), period)
        return start_of(base.replace(month=base.month + 1), period)

    if period == "week":
        return start_of(base + ONE_WEEK, period)
    if "day" in period:
        return start_of(base + ONE_DAY, period)

    raise ValueError('period must be "year", "month" or "week"')


def hours_minutes_seconds(time: timedelta) -> tuple:
    hours, seconds = divmod(time.total_seconds(), 3600)
    return (hours, *divmod(seconds, 60))


def get_periods(minimum, maximum, period: str) -> list:
    """
    Get the periods between minimum and maximum (exclusive).

    Returns a list of (end datetime, name) tuples.
    """
    current = end_of(minimum, period)
    periods = [(current, back_name(current, period, 1))]
    while current <= end_of(maximum, period):
        current = end_of(current, period)
        periods.append((current, back_name(current, period, 1)))
    return periods
