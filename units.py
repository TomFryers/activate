import datetime


class Unit:
    def __init__(self, name, symbol, size):
        self.name = name
        self.symbol = symbol
        self.size = size

    def encode(self, value):
        return value / self.size

    def decode(self, value):
        return value * self.size

    def format(self, value):
        return (self.encode(value), self.symbol)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}({self.name!r}, {self.symbol!r}, {self.size!r})"
        )


class UnitConfig:
    """The current preferred unit system."""

    def __init__(self, units: dict):
        self.units = units

    def encode(self, value, dimension):
        return self.units[dimension].encode(value)

    def decode(self, value, dimension):
        return self.units[dimension].decode(value)

    def format(self, value, dimension):
        return self.units[dimension].format(value)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.units!r})"


class PaceUnit(Unit):
    """A unit of pace (1 / speed), such as 4:00 kilometres."""

    def __init__(self, distance: Unit):
        self.distance = distance
        self.name = f"minutes per {distance.name}"
        self.size = 1 / distance.size
        self.symbol = "∕ " + distance.symbol

    def encode(self, value):
        return datetime.timedelta(seconds=super().encode(value))

    def __repr__(self):
        return f"{self.__class__.__name__}({self.distance!r})"


class DateUnit(Unit):
    """A unit giving a date."""

    def __init__(self):
        super().__init__("date", "", 1)

    def encode(self, value):
        return value.timestamp()

    def format(self, value):
        return str(value)


KM = Unit("kilometre", "km", 1000)
MILE = Unit("mile", "mi", 1609.344)
METRE = Unit("metre", "m", 1)
FOOT = Unit("foot", "ft", 0.3048)
YARD = Unit("yard", "yd", 0.9144)
METRE_PER_SECOND = Unit("metre per second", "m ∕ s", 1)
KM_PER_HOUR = Unit("kilometre per hour", "km ∕ h", 1 / 3.6)
MILE_PER_HOUR = Unit("mile per hour", "mph", 1609.344 / 3600)
TIME = Unit("minutes and seconds", "", 1)
SECOND = Unit("second", "s", 1)
MINUTE = Unit("minute", "min", 60)
MIN_PER_KM = PaceUnit(KM)
MIN_PER_MILE = PaceUnit(MILE)
UNITLESS = Unit("", "", 1)
DATE = DateUnit()
ALL = {
    "distance": (METRE, FOOT, YARD, KM, MILE),
    "altitude": (METRE, FOOT),
    "speed": (METRE_PER_SECOND, KM_PER_HOUR, MILE_PER_HOUR),
    "time": (TIME,),
    "pace": (MIN_PER_KM, MIN_PER_MILE),
    "date": (DATE,),
    None: UNITLESS,
}

METRIC = {
    "distance": KM,
    "altitude": METRE,
    "speed": KM_PER_HOUR,
    "time": TIME,
    "pace": MIN_PER_KM,
    "date": DATE,
    None: UNITLESS,
}

IMPERIAL = {
    "distance": MILE,
    "altitude": FOOT,
    "speed": MILE_PER_HOUR,
    "time": TIME,
    "pace": MIN_PER_MILE,
    "date": DATE,
    None: UNITLESS,
}


DEFAULT = "Metric"

UNIT_SYSTEMS = {"Metric": UnitConfig(METRIC), "Imperial": UnitConfig(IMPERIAL)}
