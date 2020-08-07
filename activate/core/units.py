"""Contains classes and for handling units and some predefined units."""
import datetime
import math


class DimensionValue:
    def __init__(self, value, dimension):
        self.value = value
        self.dimension = dimension

    def format(self, unit_system):
        return unit_system.format(self.value, self.dimension)

    def encode(self, unit_system):
        return unit_system.encode(self.value, self.dimension)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.value!r}, {self.dimension!r})"


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

    def format_name_unit(self, dimension, symbol=None) -> str:
        """
        Get 'Distance (m)' or similar string.

        Returns the dimension if it isn't recognised.
        """
        if symbol is None:
            if dimension not in self.units:
                return dimension
            symbol = self.units[dimension].symbol
        if symbol:
            return f"{dimension.title()} ({symbol})"
        return dimension.title()

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
FOOT_PER_MINUTE = Unit("foot per minute", "ft ∕ min", 0.3048 / 60)
METRE_PER_MINUTE = Unit("metre per minute", "m ∕ min", 1 / 60)
TIME = Unit("minutes and seconds", "", 1)
SECOND = Unit("second", "s", 1)
MINUTE = Unit("minute", "min", 60)
MIN_PER_KM = PaceUnit(KM)
MIN_PER_MILE = PaceUnit(MILE)
BEAT_PER_MINUTE = Unit("beat per minute", "bpm", 1 / 60)
CYCLES_PER_MINUTE = Unit("cycles per minute", "rpm", 1 / 60)
WATT = Unit("watt", "W", 1)
HORSE_POWER = Unit("horsepower", "hp", 745.6998715822702)
DEGREE = Unit("degree", "°", math.tau / 360)
UNITLESS = Unit("", "", 1)
DATE = DateUnit()
ALL = {
    "distance": (METRE, FOOT, YARD, KM, MILE),
    "altitude": (METRE, FOOT),
    "speed": (METRE_PER_SECOND, KM_PER_HOUR, MILE_PER_HOUR, METRE_PER_MINUTE),
    "vertical_speed": (METRE_PER_SECOND, METRE_PER_MINUTE, FOOT_PER_MINUTE),
    "time": (TIME,),
    "pace": (MIN_PER_KM, MIN_PER_MILE),
    "date": (DATE,),
    "heartrate": (BEAT_PER_MINUTE,),
    "cadence": (CYCLES_PER_MINUTE,),
    "power": (WATT,),
    "angle": (DEGREE,),
    None: UNITLESS,
}

METRIC = {
    "distance": KM,
    "altitude": METRE,
    "speed": KM_PER_HOUR,
    "vertical_speed": METRE_PER_MINUTE,
    "time": TIME,
    "pace": MIN_PER_KM,
    "date": DATE,
    "heartrate": BEAT_PER_MINUTE,
    "cadence": CYCLES_PER_MINUTE,
    "power": WATT,
    "angle": DEGREE,
    None: UNITLESS,
}

IMPERIAL = {
    "distance": MILE,
    "altitude": FOOT,
    "speed": MILE_PER_HOUR,
    "vertical_speed": FOOT_PER_MINUTE,
    "time": TIME,
    "pace": MIN_PER_MILE,
    "date": DATE,
    "heartrate": BEAT_PER_MINUTE,
    "cadence": CYCLES_PER_MINUTE,
    "power": HORSE_POWER,
    "angle": DEGREE,
    None: UNITLESS,
}


DEFAULT = "Metric"

UNIT_SYSTEMS = {"Metric": UnitConfig(METRIC), "Imperial": UnitConfig(IMPERIAL)}
