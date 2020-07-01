import times


def as_int(value):
    """Format a value as an integer, ready to display."""
    return str(round(value))


def info_format(value, entry: str) -> str:
    """Format an value for the info box."""
    if value == "None":
        return value
    if entry == "Elapsed Time":
        return times.to_string(value)
    if entry in {"Ascent", "Descent", "Highest Point"}:
        return as_int(value)
    if entry == "Average Speed":
        return f"{value:.2f}"
    if entry == "Distance":
        return f"{value:.2f}"
    if entry == "Max. Speed":
        return f"{value:.1f}"
    if entry == "Pace":
        return times.to_string(value)
    raise ValueError(f"Unknown entry: {entry}")


def split_format(value, entry: str) -> str:
    """Format a value for the splits table."""
    if value == "None":
        return value
    if entry == "Number":
        return as_int(value)
    if entry in {"Time", "Split"}:
        return times.to_string(value)
    if entry in {"Net Climb", "Ascent"}:
        return as_int(value)
    if entry == "Speed":
        return f"{value:.2f}"
    raise ValueError(f"Unknown entry: {entry}")


def list_format(value, entry: str) -> str:
    """Format a value for the splits table."""
    if value == "None":
        return value
    if entry == "Name":
        return value
    if entry == "Distance":
        return f"{value:.2f}"
    if entry == "Start Time":
        return str(times.round_time(value))
    raise ValueError(f"Unknown entry: {entry}")
