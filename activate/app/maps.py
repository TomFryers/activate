import pyqtlet
from PyQt5.QtCore import Qt
from pyqtlet import L


def get_bounds(*routes):
    """Find the area of the map."""
    return [
        [min(p[0] for r in routes for p in r), min(p[1] for r in routes for p in r)],
        [max(p[0] for r in routes for p in r), max(p[1] for r in routes for p in r)],
    ]


DEFAULT_POS = [53, -1]

ACTIVATE_COLOUR = "#802090"


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
        size_policy = self.sizePolicy()
        size_policy.setRetainSizeWhenHidden(True)
        self.setSizePolicy(size_policy)
        self.setContextMenuPolicy(Qt.NoContextMenu)
        self.map = L.map(self)
        L.tileLayer(
            "http://{s}.tile.osm.org/{z}/{x}/{y}.png",
            {"attribution": "&copy; OpenStreetMap contributors"},
        ).addTo(self.map)

        self.map.runJavaScript(f"{self.map.jsName}.attributionControl.setPrefix('');")


class MapWidget(Map):
    """A map for displaying a route or heatmap"""

    def __init__(self, parent):
        super().__init__(parent)
        self.route_lines = []
        self.start_icon = CircleMarker(DEFAULT_POS, {"radius": 8, "color": "#10b020"})
        self.finish_icon = CircleMarker(DEFAULT_POS, {"radius": 8, "color": "#e00000"})
        self.marker = CircleMarker(DEFAULT_POS, {"radius": 5, "color": ACTIVATE_COLOUR})
        self.highlight_section = self.add_route_line("#ffffff")
        self.mode = None

    def show_route(self, route: list):
        """Display a list of points on the map."""
        self.map.fitBounds(get_bounds(route))
        if self.mode != "route":
            self.clear_route_lines()
            self.route_lines = [self.add_route_line()]
        self.route_lines[0].setLatLngs(route)
        self.start_icon.setLatLng(route[0])
        self.finish_icon.setLatLng(route[-1])
        self.start_icon.addTo(self.map)
        self.finish_icon.addTo(self.map)
        self.mode = "route"

    def show_heatmap(self, routes: list):
        """Display lists of points on the map as a heatmap."""
        if not routes:
            return
        opacity = hex(min(round(1000 / (len(routes) ** 0.5)), 255))[2:]
        self.map.fitBounds(get_bounds(*routes))
        self.start_icon.removeFrom(self.map)
        self.finish_icon.removeFrom(self.map)
        self.clear_route_lines()
        self.route_lines = []
        for route in routes:
            self.route_lines.append(self.add_route_line(f"{ACTIVATE_COLOUR}{opacity}"))
            self.route_lines[-1].setLatLngs(route)
        self.mode = "heatmap"

    def add_route_line(self, colour=ACTIVATE_COLOUR):
        line = Polyline([], {"smoothFactor": 0, "color": colour})
        line.addTo(self.map)
        return line

    def clear_route_lines(self):
        while self.route_lines:
            self.route_lines.pop().removeFrom(self.map)

    def show_marker(self, position):
        if position is None:
            self.remove_marker()
            return
        self.marker.setLatLng(list(position))
        self.marker.addTo(self.map)

    def remove_marker(self):
        self.marker.removeFrom(self.map)

    def show_highlight(self, part):
        self.highlight_section.setLatLngs(part)
        self.highlight_section.addTo(self.map)
        call_js_method(self.highlight_section, "bringToFront")

    def remove_highlight(self):
        self.highlight_section.removeFrom(self.map)
