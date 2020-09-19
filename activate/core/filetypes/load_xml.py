import pathlib
import xml.etree.ElementTree

from activate.core import files


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
    tree = xml.etree.ElementTree.iterparse(open(filename, "r"))
    for _, element in tree:
        _, _, element.tag = element.tag.rpartition("}")
    return tree.root


def default_name(filename):
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