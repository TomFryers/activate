"""Contains classes and for handling units and some predefined units."""
import math
from dataclasses import dataclass
from datetime import timedelta
from functools import wraps
from typing import Union


class DimensionError(Exception):
    pass


def compatible_dimensions(function):
    @wraps(function)
    def wrapper(var1, var2, **kwargs):
        if var1.dimension != var2.dimension:
            raise DimensionError(
                f"incompatible dimensions: {var1.dimension} and {var2.dimension}"
            )
        return function(var1, var2, **kwargs)

    return wrapper


@dataclass(frozen=True)
class DimensionValue:
    """A value with a dimension attached."""

    value: Union[float, timedelta]
    dimension: str

    def format(self, unit_system):
        return unit_system.format(self.value, self.dimension)

    def encode(self, unit_system):
        return unit_system.encode(self.value, self.dimension)

    @compatible_dimensions
    def __lt__(self, other):
        return self.value < other.value

    @compatible_dimensions
    def __gt__(self, other):
        return self.value > other.value

    @compatible_dimensions
    def __eq__(self, other):
        return self.value == other.value

    @compatible_dimensions
    def __ne__(self, other):
        return self.value != other.value

    @compatible_dimensions
    def __le__(self, other):
        return self.value <= other.value

    @compatible_dimensions
    def __ge__(self, other):
        return self.value >= other.value

    @compatible_dimensions
    def __add__(self, other):
        return DimensionValue(self.value + other.value, self.dimension)

    @compatible_dimensions
    def __sub__(self, other):
        return DimensionValue(self.value - other.value, self.dimension)

    def __neg__(self):
        return DimensionValue(-self.value, self.dimension)


@dataclass
class Unit:
    name: str
    symbol: str
    size: float

    def encode(self, value):
        return value / self.size

    def decode(self, value):
        return value * self.size

    def format(self, value):
        return (self.encode(value), self.symbol)

    def __truediv__(self, other):
        return Unit(
            f"{self.name} per {other.name}",
            f"{self.symbol} ∕ {other.symbol}",
            self.size / other.size,
        )

    def __mul__(self, other):
        return Unit(
            f"{self.name} {other.name}",
            f"{self.symbol} {other.symbol}",
            self.size * other.size,
        )


@dataclass
class UnitConfig:
    """The current preferred unit system."""

    units: dict

    def encode(self, value, dimension):
        return self.units[dimension].encode(value)

    def decode(self, value, dimension):
        return self.units[dimension].decode(value)

    def format(self, value, dimension):
        return self.units[dimension].format(value)

    def format_name_unit(self, dimension, symbol=None, name=None) -> str:
        """
        Get 'Distance (m)' or similar string.

        Returns the dimension if it isn't recognised.
        """
        if symbol is None:
            if dimension not in self.units:
                return dimension
            symbol = self.units[dimension].symbol
        if symbol:
            return f"{dimension.title() if name is None else name} ({symbol})"
        return dimension.title()


class PaceUnit(Unit):
    """A unit of pace (1 / speed), such as 4:00 kilometres."""

    def __init__(self, distance: Unit):
        self.distance = distance
        self.name = f"minutes per {distance.name}"
        self.size = 1 / distance.size
        self.symbol = "∕ " + distance.symbol

    def encode(self, value) -> timedelta:
        return timedelta(seconds=super().encode(value))

    def __repr__(self):
        return f"{self.__class__.__qualname__}({self.distance!r})"


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
SECOND = Unit("second", "s", 1)
MINUTE = Unit("minute", "min", 60)
HOUR = Unit("hour", "h", 3600)
METRE_PER_SECOND = METRE / SECOND
KM_PER_HOUR = KM / HOUR
MILE_PER_HOUR = MILE / HOUR
MILE_PER_HOUR.symbol = "mph"
FOOT_PER_MINUTE = FOOT / MINUTE
METRE_PER_MINUTE = METRE / MINUTE
TIME = Unit("minutes and seconds", "", 1)
MIN_PER_KM = PaceUnit(KM)
MIN_PER_MILE = PaceUnit(MILE)
BEAT_PER_MINUTE = Unit("beat per minute", "bpm", 1 / 60)
CYCLES_PER_MINUTE = Unit("cycles per minute", "rpm", 1 / 60)
HERTZ = Unit("hertz", "Hz", 1)
WATT = Unit("watt", "W", 1)
HORSE_POWER = Unit("horsepower", "hp", 745.6998715822702)
DEGREE = Unit("degree", "°", math.tau / 360)
RADIAN = Unit("radian", "", 1)
UNITLESS = Unit("", "", 1)
DATE = DateUnit()
ALL = {
    "distance": (METRE, FOOT, YARD, KM, MILE),
    "altitude": (METRE, FOOT),
    "speed": (METRE_PER_SECOND, KM_PER_HOUR, MILE_PER_HOUR, METRE_PER_MINUTE),
    "vertical_speed": (METRE_PER_SECOND, METRE_PER_MINUTE, FOOT_PER_MINUTE),
    "real_time": (SECOND, MINUTE, HOUR),
    "time": (TIME,),
    "pace": (MIN_PER_KM, MIN_PER_MILE),
    "date": (DATE,),
    "heartrate": (BEAT_PER_MINUTE,),
    "cadence": (CYCLES_PER_MINUTE,),
    "power": (WATT,),
    "angle": (DEGREE,),
    None: (UNITLESS,),
}

METRIC = {
    "distance": KM,
    "altitude": METRE,
    "speed": KM_PER_HOUR,
    "vertical_speed": METRE_PER_MINUTE,
    "real_time": MINUTE,
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
    "real_time": MINUTE,
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

UNIT_NAMES = {
    u.name: u
    for u in (
        KM,
        MILE,
        METRE,
        FOOT,
        YARD,
        SECOND,
        MINUTE,
        HOUR,
        METRE_PER_SECOND,
        KM_PER_HOUR,
        MILE_PER_HOUR,
        FOOT_PER_MINUTE,
        METRE_PER_MINUTE,
        TIME,
        MIN_PER_KM,
        MIN_PER_MILE,
        BEAT_PER_MINUTE,
        CYCLES_PER_MINUTE,
        HERTZ,
        WATT,
        HORSE_POWER,
        DEGREE,
        RADIAN,
        UNITLESS,
        DATE,
    )
}
