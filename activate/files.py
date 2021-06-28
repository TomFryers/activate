"""Functions for manipulating files."""
import shutil
from pathlib import Path


def has_extension(filename: Path, extension: str) -> bool:
    """Determine if a file path has a given extension."""
    return filename.suffix.casefold() == "." + extension


def encode_name(filename: str, directory: Path) -> Path:
    """
    Rename a file to avoid name collisions.

    Renames foo.gpx to _0_foo.gpx if foo.gpx already exists. If that
    exists tries _1_foo.gpx, _2_foo.gpx... until a free name is found.
    If the name already starts with an underscore, the bare name cannot
    be used, _foo_bar.gpx becomes _0__foo_bar.gpx, _1__foo_bar.gpx etc.
    """
    current_filenames = set(directory.glob("*"))
    # No-underscore, unique filename
    if filename[0] != "_":
        full_name = directory / filename
        if full_name not in current_filenames:
            return full_name

    # Others
    i = 0
    while True:
        full_name = directory / f"_{i}_{filename}"
        i += 1
        if full_name not in current_filenames:
            return full_name


def decode_name(filename: str) -> str:
    """Get a file's original name from its encoded one."""
    if filename[0] != "_":
        return filename
    filename = filename[filename[1:].index("_") + 2 :]
    return filename


def copy_to_location_renamed(filename: Path, copy_to: Path) -> Path:
    """
    Copy a file to a location, renaming it if necessary.

    Returns the new filename.
    """
    out_name = encode_name(filename.name, copy_to)
    shutil.copy2(filename, out_name)
    return out_name
