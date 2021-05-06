from typing import Optional

from qgis.core import QgsVectorLayer

from ..definitions.constants import Profile, Unit


class IsochroneOpts:
    def __init__(self) -> None:
        self.url: str = ""
        self.layer: Optional[QgsVectorLayer] = None
        self.distance: Optional[int] = None
        self.unit: Optional[Unit] = None
        self.profile: Optional[Profile] = None

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
