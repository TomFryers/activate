import gzip
from typing import Optional
from xml.etree import ElementTree


def try_multi(point, locations) -> Optional[str]:
    """Try to search for a value in several positions."""
    for location in locations:
        try:
            return point.find(location).text
        except AttributeError:
            continue
    return None


def get_tree(filename):
    """Load the tree, getting rid of namespaces."""
    with (gzip.open if filename.suffix == ".gz" else open)(filename) as f:
        text = f.read().lstrip()
    tree = ElementTree.ElementTree(ElementTree.fromstring(text))
    for element in tree.iter():
        _, _, element.tag = element.tag.rpartition("}")
    return tree.getroot()


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
