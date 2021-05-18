import json
import logging
from dataclasses import dataclass
from typing import Optional

from qgis.core import QgsFeature, QgsGeometry, QgsPointXY, QgsVectorLayer

from ..definitions.constants import Profile, Unit
from ..qgis_plugin_tools.tools.exceptions import QgsPluginNetworkException
from ..qgis_plugin_tools.tools.network import fetch
from ..qgis_plugin_tools.tools.resources import plugin_name

LOGGER = logging.getLogger(plugin_name())


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
        # no type checking needed, since we check if options are set
        if self.opts.check_if_opts_set():
            self.base_url = self.opts.url
            if not self.base_url[-1] == "/":
                self.base_url += "/"
            self.base_url += "isochrone"
            self.params = {
                "profile": self.opts.profile.value,  # type: ignore
                "buckets": 1,
            }
            if self.opts.unit == Unit.METERS:
                self.params["distance_limit"] = self.opts.distance
                self.params["time_limit"] = -1
            else:
                self.params["time_limit"] = 60 * self.opts.distance  # type: ignore

    def create_isochrone_layer(self) -> QgsVectorLayer:
        """Creates a polygon QgsVectorLayer containing isochrones for points"""
        layer_name = f"{self.opts.distance} {self.opts.unit.value} by {self.opts.profile.value}"  # type: ignore  # noqa
        isochrone_layer = QgsVectorLayer(
            "Polygon?crs=epsg:4326&index=yes", layer_name, "memory"
        )
        isochrone_layer.renderer().symbol().setOpacity(0.25)
        for idx, point in enumerate(self.opts.layer.getFeatures()):  # type: ignore
            point = point.geometry().asPoint()
            isochrone_params = self.params
            isochrone_params["point"] = f"{point.y()},{point.x()}"
            try:
                isochrone_json = fetch(self.base_url, params=isochrone_params)
            except QgsPluginNetworkException as e:
                LOGGER.warn(f"Request failed for point {point}: {e}")
            bucketed_isochrones = json.loads(isochrone_json)["polygons"]
            for polygon_in_bucket in bucketed_isochrones:
                feature = QgsFeature()
                feature.setGeometry(
                    QgsGeometry.fromPolygonXY(
                        [
                            [
                                QgsPointXY(pt[0], pt[1])
                                for pt in polygon_in_bucket["geometry"]["coordinates"][
                                    0
                                ]
                            ]
                        ]
                    )
                )
                isochrone_layer.dataProvider().addFeature(feature)
            # update layer's extent when new features have been added
            if idx and idx % 10 == 0:
                LOGGER.info(
                    f"{idx} out of {self.opts.layer.featureCount()} objects fetched"  # type: ignore  # noqa
                )
        isochrone_layer.updateExtents()
        return isochrone_layer
