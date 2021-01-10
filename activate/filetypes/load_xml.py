import pathlib
import gzip
import xml.etree.ElementTree

from activate import files


def try_multi(point, locations):
    """Try to search for a value in several positions."""
    for location in locations:
        try:
            return point.find(location).text
        except AttributeError:
            continue
    return None


def get_tree(filename):
    """Load the tree, getting rid of namespaces"""
    tree = xml.etree.ElementTree.iterparse(
        (gzip.open if filename.suffix == ".gz" else open)(filename)
    )
    for _, element in tree:
        _, _, element.tag = element.tag.rpartition("}")
    return tree.root


def default_name(filename):
    """Generate a default activity name from a file name."""
    return files.decode_name(pathlib.Path(filename).stem)


def load_fields(points, fields):
    """Extract the fields from a list of points activity file."""
    result = {field: [] for field in fields}
    for point in points:
        for field in fields:
            value = None
            try:
                value = fields[field](point)
            except Exception:
                value = None
            result[field].append(value)
    return {field: result[field] for field in result if set(result[field]) != {None}}
