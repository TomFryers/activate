import pyqtlet
from PyQt5.QtCore import Qt
from pyqtlet import L


def get_bounds(route):
    """Find the area of the map."""
    return [
        [min(p[0] for p in route), min(p[1] for p in route)],
        [max(p[0] for p in route), max(p[1] for p in route)],
    ]


DEFAULT_POS = [51, -1]


def call_js_method(obj, method, *params) -> None:
    """Call obj.method(*params) equivalent in JavaScript."""
    obj.runJavaScript(f"{obj.jsName}.{method}({','.join(str(x) for x in params)});")


class Polyline(L.polyline):
    def setLatLngs(self, coordinates):
        call_js_method(self, "setLatLngs", coordinates)


class CircleMarker(L.circleMarker):
    def setLatLng(self, coordinates):
        call_js_method(self, "setLatLng", coordinates)


class Map(pyqtlet.MapWidget):
    def __init__(self, parent):
        super().__init__()
        parent.addWidget(self)
        self.setContextMenuPolicy(Qt.NoContextMenu)
        self.map = L.map(self, {"attributionControl": False})
        self.map.setView(DEFAULT_POS, 14)
        L.tileLayer("http://{s}.tile.osm.org/{z}/{x}/{y}.png").addTo(self.map)


class RouteMap(Map):
    """A map for displaying a route."""

    def __init__(self, parent):
        super().__init__(parent)
        self.route_line = Polyline([], {"smoothFactor": 0, "color": "#802090"})
        self.start_icon = CircleMarker(DEFAULT_POS, {"radius": 8, "color": "#10b020"})
        self.finish_icon = CircleMarker(DEFAULT_POS, {"radius": 8, "color": "#e00000"})
        self.start_icon.addTo(self.map)
        self.finish_icon.addTo(self.map)
        self.route_line.addTo(self.map)

    def show(self, route: list):
        """Display a list of points on the map."""
        self.map.fitBounds(get_bounds(route))
        self.route_line.setLatLngs(route)
        self.start_icon.setLatLng(route[0])
        self.finish_icon.setLatLng(route[-1])
