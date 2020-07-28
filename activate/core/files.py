"""Functions for manipulating files."""


def has_extension(filename, extension) -> bool:
    """Determine if a file path has a given extension."""
    return filename.casefold().endswith("." + extension)


def encode_name(filename, current_filenames, directory):
    """
    Rename a file to avoid name collisions.

    Renames foo.gpx to _0_foo.gpx if foo.gpx already exists. If that
    exists tries _1_foo.gpx, _2_foo.gpx... until a free name is found.
    If the name already starts with an underscore, the bare name cannot
    be used, _foo_bar.gpx becomes _0__foo_bar.gpx, _1__foo_bar.gpx etc.
    """
    # No-underscore, unique filename
    if filename[0] != "_":
        full_name = f"{directory}{filename}"
        if full_name not in current_filenames:
            return full_name

    # Others
    i = 0
    while True:
        full_name = f"{directory}_{i}_{filename}"
        i += 1
        if full_name not in current_filenames:
            return full_name


def decode_name(filename):
    """Get a file's original name from its encoded one."""
    if filename[0] != "_":
        return filename
    filename = filename[filename[1:].index("_") + 2 :]
    return filename