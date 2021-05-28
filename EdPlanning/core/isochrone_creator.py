import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from qgis.core import (
    QgsFeature,
    QgsGeometry,
    QgsLayerTreeLayer,
    QgsPointXY,
    QgsProject,
    QgsTask,
    QgsVectorLayer,
)

from ..definitions.constants import Profile, Unit
from ..qgis_plugin_tools.tools.exceptions import QgsPluginNetworkException
from ..qgis_plugin_tools.tools.network import fetch
from ..qgis_plugin_tools.tools.resources import plugin_name

# from qgis.PyQt.QtCore import QCoreApplication


LOGGER = logging.getLogger(f"{plugin_name()}_task")


@dataclass
class IsochroneOpts:
    url: str = ""
    api_key: str = ""
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


class IsochroneCreator(QgsTask):
    def __init__(self, opts: IsochroneOpts) -> None:
        super().__init__(description="Fetching GraphHopper isochrones for all points")
        self.opts = opts
        self.result_layer: Optional[QgsVectorLayer] = None
        self.points = []
        self.setProgress(0.0)
        # no type checking needed, since we check if options are set
        if self.opts.check_if_opts_set():
            self.base_url = self.opts.url
            if not self.base_url[-1] == "/":
                self.base_url += "/"
            self.base_url += "isochrone"
            self.params = {
                "profile": self.opts.profile.value,  # type: ignore
                "buckets": 1,
                "reverse_flow": True,
            }
            if self.opts.api_key:
                self.params["key"] = self.opts.api_key
            if self.opts.unit == Unit.METERS:
                self.params["distance_limit"] = self.opts.distance
                self.params["time_limit"] = -1
            else:
                self.params["time_limit"] = 60 * self.opts.distance  # type: ignore

            # QgsVectorLayer from main thread may not be used in other threads?
            # How about the QgsFeatures we list here, seems to work fine?
            self.points = list(self.opts.layer.getFeatures())  # type: ignore

    def run(self) -> bool:
        """
        This method MUST return True or False.

        Raising exceptions will crash QGIS, so we handle them
        internally and raise them in self.finished

        Any resulting QObjects must be manually moved to the main thread
        when finished with them.
        """
        self.result_layer = self.create_isochrone_layer()
        count = self.result_layer.featureCount()
        LOGGER.info(f"Total of {count} isochrones generated.")
        LOGGER.info(
            f"Isochrones could not be generated for {len(self.points)-count} points."
        )
        # don't know if this is really needed or done automatically?
        # finished will run in the main thread anyway
        # self.result_layer.moveToThread(QCoreApplication.instance().thread())
        return bool(count)

    def finished(self, result: bool) -> None:
        """
        This function is automatically called when the task has
        completed (successfully or not).

        finished is always called from the main thread, so it's safe
        to do GUI operations and raise Python exceptions here.
        result is the return value from self.run.
        """
        if result and self.result_layer:
            QgsProject.instance().addMapLayer(self.result_layer, False)
            root = QgsProject.instance().layerTreeRoot()
            root.insertChildNode(1, QgsLayerTreeLayer(self.result_layer))
        elif not len(self.points):
            LOGGER.warning("Point layer empty, no isochrones generated")
        else:
            LOGGER.warning("No isochrones returned for any of the points")

    def __fetch_bucketed_isochrones(self, point: QgsPointXY) -> List[Dict]:
        # the API may return multiple isochrones for a single point
        point = point.geometry().asPoint()
        isochrone_params = self.params
        isochrone_params["point"] = f"{point.y()},{point.x()}"
        try:
            isochrone_json = fetch(self.base_url, params=isochrone_params)
        except QgsPluginNetworkException as e:
            LOGGER.warning(
                f"Request failed for point {point.y()},{point.x()}: {e}. "
                "Most likely isochrone could not be calculated because no roads were "
                "found close to the point."
            )
            return []
        return json.loads(isochrone_json)["polygons"]

    def __add_isochrones_to_layer(self, layer: QgsVectorLayer) -> None:
        for idx, point in enumerate(self.points):
            bucketed_isochrones = self.__fetch_bucketed_isochrones(point)
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
                layer.dataProvider().addFeature(feature)
            if idx and idx % 10 == 0:
                LOGGER.info(
                    f"{idx} out of {len(self.points)} objects fetched"  # type: ignore  # noqa
                )
            if self.isCanceled():
                LOGGER.warning(
                    f"Task cancelled, only {idx} out of {len(self.points)} isochrones calculated"  # type: ignore  # noqa
                )
                break
            self.setProgress(100 * (idx / len(self.points)))

    def create_isochrone_layer(self) -> QgsVectorLayer:
        """Creates a polygon QgsVectorLayer containing isochrones for points"""
        profile = (
            f" by {self.opts.profile.value}" if self.opts.unit == Unit.MINUTES else ""  # type: ignore  # noqa
        )
        direction = "to" if self.params["reverse_flow"] else "from"
        layer_name = f"{self.opts.distance} {self.opts.unit.value} {direction} school{profile}"  # type: ignore  # noqa
        isochrone_layer = QgsVectorLayer(
            "Polygon?crs=epsg:4326&index=yes", layer_name, "memory"
        )
        self.__add_isochrones_to_layer(isochrone_layer)
        # update layer's extent when new features have been added
        isochrone_layer.updateExtents()
        return isochrone_layer
