"""Named warehouse locations: map coordinates <-> Korean/English names."""

from pathlib import Path
import math

import yaml
from ament_index_python.packages import get_package_share_directory


class Locations:
    def __init__(self, path=None):
        file = Path(path) if path else Path(get_package_share_directory("warehouse_lecture")) / "worlds/locations.yaml"
        data = yaml.safe_load(file.read_text())
        self.locations = data["locations"]
        self.patrol = data.get("patrol", {}).get("waypoints", [])
        self._alias = {}
        for name, loc in self.locations.items():
            self._alias[name.lower()] = name
            for alias in loc.get("aliases", []):
                self._alias[str(alias).lower().replace(" ", "")] = name

    def names(self):
        return list(self.locations)

    def resolve(self, text):
        """Location key for a name/alias (case- and space-insensitive), or None."""
        if not text:
            return None
        key = str(text).lower().replace(" ", "")
        if key in self._alias:
            return self._alias[key]
        for alias, name in self._alias.items():
            if alias in key or key in alias:
                return name
        return None

    def goal(self, name):
        return list(self.locations[name]["base_goal"])

    def station(self, name):
        return self.locations[name].get("station")

    def nearest(self, x, y):
        """(name, distance_m) of the closest location centre; name is None if outside every radius."""
        best, best_d = None, math.inf
        for name, loc in self.locations.items():
            cx, cy = loc["center"]
            d = math.hypot(x - cx, y - cy)
            if d < best_d:
                best, best_d = name, d
        if best is not None and best_d > self.locations[best].get("radius", 2.0):
            return None, best_d
        return best, best_d

    def describe(self, x, y, language="ko"):
        name, d = self.nearest(x, y)
        if name is None:
            return f"({x:.1f}, {y:.1f}) 지점" if language == "ko" else f"at ({x:.1f}, {y:.1f})"
        label = self.locations[name]["aliases"][0] if self.locations[name].get("aliases") else name
        if language == "ko":
            return f"{label} 근처" if d > 0.6 else f"{label} 바로 앞"
        return f"near {name}" if d > 0.6 else f"at {name}"

    def prompt_table(self):
        """Compact text for LLM system prompts."""
        rows = []
        for name, loc in self.locations.items():
            aliases = ", ".join(map(str, loc.get("aliases", [])))
            rows.append(f"- {name}: ({loc['center'][0]}, {loc['center'][1]}) [{aliases}]")
        return "\n".join(rows)
