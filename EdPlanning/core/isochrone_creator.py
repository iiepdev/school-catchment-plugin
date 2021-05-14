from dataclasses import dataclass
from typing import Optional

from qgis.core import QgsVectorLayer

from ..definitions.constants import Profile, Unit


@dataclass
class IsochroneOpts:
    url: str = ""
    layer: Optional[QgsVectorLayer] = None
    distance: Optional[int] = None
    unit: Optional[Unit] = None
    profile: Optional[Profile] = None

    def check_if_opts_set(self) -> bool:
        if None in [self.layer, self.distance, self.unit, self.profile]:
            return False
        if self.url == "":
            return False
        return True


class IsochroneCreator:
    def __init__(self, opts: IsochroneOpts) -> None:
        self.opts = opts

    def create_isochrone_layer(self) -> QgsVectorLayer:
        """Creates a polygon QgsVectorLayer containing isochrones for points"""
        raise NotImplementedError
