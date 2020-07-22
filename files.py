"""Functions for manipulating files."""
def has_extension(filename, extension) -> bool:
    """Determine if a file path has a given extension."""
    return filename.casefold().endswith("." + extension)


def encode_name(filename, current_filenames, directory):
    """
    Rename a file to avoid name collisions.

    Renames foo.gpx to _0_foo.gpx if foo.gpx already exists. If that
    exists tries _1_foo.gpx, _2_foo.gpx... until a free name is found.
    If the name already starts with an underscore, it is replaced with a
    double underscore, so _foo_bar.gpx becomes __foo_bar.gpx,
    _0___foo_bar.gpx etc.
    """
    if filename[0] == "_":
        filename = "_" + filename
    full_name = f"{directory}/{filename}"
    i = 0
    while full_name in current_filenames:
        full_name = f"{directory}/_{i}_{filename}"
        i += 1
    return full_name


def decode_name(filename):
    """Get a file's original name from its encoded one."""
    if filename[0] != "_":
        return filename
    filename = filename[filename[1:].index("_") + 2 :]
    if filename.startswith("__"):
        return filename[2:]
    return filename
