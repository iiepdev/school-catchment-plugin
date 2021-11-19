import json
import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

import qgis.processing
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransformContext,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsLayerTreeLayer,
    QgsPointXY,
    QgsProcessing,
    QgsProject,
    QgsTask,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtNetwork import QNetworkReply

from ..definitions.constants import Profile, Unit
from ..qgis_plugin_tools.tools.exceptions import QgsPluginNetworkException
from ..qgis_plugin_tools.tools.network import fetch
from ..qgis_plugin_tools.tools.resources import plugin_name

# from qgis.PyQt.QtCore import QCoreApplication

MAIN_LOGGER = logging.getLogger(plugin_name())
TASK_LOGGER = logging.getLogger(f"{plugin_name()}_task")


@dataclass
class IsochroneOpts:
    url: str = ""
    api_key: str = ""
    layer: Optional[QgsVectorLayer] = None
    polygon_layer: Optional[QgsVectorLayer] = None
    selected_only: bool = False
    distance: Optional[int] = None
    unit: Optional[Unit] = None
    buckets: int = 1
    profile: Optional[Profile] = None
    write_to_directory: bool = False
    directory: str = ""

    def check_if_opts_set(self) -> bool:
        if None in [self.layer, self.distance, self.unit, self.profile]:
            return False
        if self.url == "":
            return False
        return True


class IsochroneCreator(QgsTask):
    def __init__(self, opts: IsochroneOpts) -> None:
        self.opts = opts
        self.result_layer: Optional[QgsVectorLayer] = None
        self.points: list[QgsFeature] = []
        self.limiting_polygons: list[QgsFeature] = []
        # no type checking needed, since we check if options are set
        if self.opts.check_if_opts_set():
            self.base_url = self.opts.url
            if not self.base_url.startswith("http://") and not self.base_url.startswith(
                "https://"
            ):
                # our instance does not support https out of the box
                self.base_url = "http://" + self.base_url
            if not self.base_url[-1] == "/":
                self.base_url += "/"
            self.base_url += "isochrone"
            self.params = {
                "profile": self.opts.profile.value,  # type: ignore
                "buckets": self.opts.buckets,
                "reverse_flow": True,
            }
            if self.opts.api_key:
                self.params["key"] = self.opts.api_key
            if self.opts.unit == Unit.METERS:
                self.params["distance_limit"] = self.opts.distance
                self.params["time_limit"] = -1
            else:
                self.params["time_limit"] = 60 * self.opts.distance  # type: ignore

            # reproject layers if needed
            layer: QgsVectorLayer = self.opts.layer
            polygon_layer: Optional[QgsVectorLayer] = self.opts.polygon_layer
            wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
            if layer.crs() != wgs84:
                selected_ids = [
                    feature.attribute("fid") for feature in layer.getSelectedFeatures()
                ]
                MAIN_LOGGER.info(
                    f"Layer in {layer.crs().authid()}, reprojecting to WGS 84 first."
                )
                alg_params = {
                    "INPUT": layer,
                    "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
                    "TARGET_CRS": wgs84,
                }
                layer = qgis.processing.run("native:reprojectlayer", alg_params)[
                    "OUTPUT"
                ]
                layer.select(selected_ids)
            if polygon_layer and polygon_layer.crs() != wgs84:
                MAIN_LOGGER.info(
                    (f"Limit polygon layer in {polygon_layer.crs().authid()},"
                     f" reprojecting to WGS 84 first.")
                )
                alg_params = {
                    "INPUT": polygon_layer,
                    "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
                    "TARGET_CRS": wgs84,
                }
                polygon_layer = qgis.processing.run(
                    "native:reprojectlayer", alg_params)["OUTPUT"]

            # QgsVectorLayer from main thread may not be used in other threads?
            # How about the QgsFeatures we list here, seems to work fine?
            self.points = (
                list(layer.getSelectedFeatures())
                if self.opts.selected_only
                else list(layer.getFeatures())
            )
            if polygon_layer:
                # Store one boundary polygon per point. Store all original polygon ids.
                fields = QgsFields(polygon_layer.fields())
                boundary_fid_field = QgsField(
                    name="fids", type=QVariant.String, typeName="varchar"
                )
                fields.append(boundary_fid_field)
                for point in self.points:
                    # - In case a point is located inside multiple polygons, consider
                    #   all of them, i.e. their intersection.
                    # - In case a point has no boundary polygon, do not limit it.
                    boundary_polygon = None
                    for polygon in polygon_layer.getFeatures():
                        if point.geometry().intersects(polygon.geometry()):
                            if not boundary_polygon:
                                # Here the boundary polygon will get all other fields
                                # from the *first* polygon. Doesn't matter as long as
                                # we only save the ids in the end
                                boundary_polygon = QgsFeature(polygon)
                                boundary_polygon.setFields(fields)
                                boundary_polygon['fids'] = str(polygon['fid'])
                            else:
                                intersection_parts = boundary_polygon.geometry().\
                                    intersection(polygon.geometry()).\
                                    asGeometryCollection()
                                intersection_geometry = QgsGeometry.fromMultiPolygonXY(
                                    [geometry.asPolygon()
                                        for geometry in intersection_parts
                                        if geometry.wkbType() == QgsWkbTypes.Polygon]
                                )
                                boundary_polygon.setGeometry(intersection_geometry)
                                boundary_polygon['fids'] += f",{polygon['fid']}"
                    self.limiting_polygons.append(boundary_polygon)
            else:
                # no limiting polygons for any of the points
                self.limiting_polygons = len(self.points)*[None]

        profile_string = (
            f" by {self.opts.profile.value}" if self.opts.unit == Unit.MINUTES else ""  # type: ignore  # noqa
        )
        direction_string = "to" if self.params["reverse_flow"] else "from"
        selected_string = "selected " if self.opts.selected_only else ""
        limited_string = f" limited by {self.opts.polygon_layer.name()}" if \
            self.opts.polygon_layer else ""
        self.name = (f"{self.opts.distance} {self.opts.unit.value} {direction_string}"
            f" {selected_string}{self.opts.layer.name()}{profile_string}{limited_string}")  # type: ignore  # noqa

        super().__init__(description=f"Fetching GraphHopper isochrones: {self.name}")
        self.setProgress(0.0)

    def run(self) -> bool:
        """
        This method MUST return True or False.

        Raising exceptions will crash QGIS, so we handle them
        internally and raise them in self.finished

        Any resulting QObjects must be manually moved to the main thread
        when finished with them.
        """
        try:
            self.result_layer = self.create_isochrone_layer()
        except QgsPluginNetworkException as e:
            TASK_LOGGER.error(
                f"Network request failed, aborting run. Error: {e.message}"  # noqa
            )
            return False
        count = self.result_layer.featureCount()
        TASK_LOGGER.info(f"Total of {count} isochrones generated.")
        TASK_LOGGER.info(
            f"{self.opts.buckets*len(self.points)-count} isochrones could not be generated."  # noqa
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
        if not result:
            if not self.result_layer:
                MAIN_LOGGER.error(
                    f"Graphhopper request to {self.base_url} failed",
                    extra={
                        "details": "Please check your Graphhopper url and your Internet connection."  # noqa
                    },
                )
            elif len(self.points):
                MAIN_LOGGER.error(
                    "No results, no roads found close to any of the points",
                    extra={
                        "details": "Please make sure that Graphhopper contains the roads in your region."  # noqa
                    },
                )
            else:
                MAIN_LOGGER.error(
                    "Starting layer was empty, no isochrones generated",
                    extra={
                        "details": "Please check that your starting layer contains at least one point."  # noqa
                    },
                )
        else:
            QgsProject.instance().addMapLayer(self.result_layer, False)
            root = QgsProject.instance().layerTreeRoot()
            root.insertChildNode(1, QgsLayerTreeLayer(self.result_layer))

    def __fetch_bucketed_isochrones(self, point: QgsFeature) -> List[Dict]:
        # the API may return multiple isochrones for a single point (buckets)
        geometry = point.geometry()
        isochrones = []
        # the geometry may be multipoint, handle each point
        for point in geometry.parts():
            isochrone_params = self.params
            isochrone_params["point"] = f"{point.y()},{point.x()}"
            try:
                isochrone_json = fetch(self.base_url, params=isochrone_params)
            except QgsPluginNetworkException as e:
                # In case we have a bad request, it is usually due to missing roads.
                # Inform the user and continue.
                if e.error == QNetworkReply.ProtocolInvalidOperationError:
                    error_message = e.message  # noqa
                    try:
                        # Graphhopper will return json error message. However,
                        # error content will be empty in older QGIS versions:
                        # https://github.com/qgis/QGIS/issues/42442
                        # In this case, the error message will be the default string.
                        error_message = json.loads(error_message)["message"]
                    except json.decoder.JSONDecodeError:
                        pass
                    TASK_LOGGER.warning(
                        f"Request failed for point {point.y()},{point.x()}: {error_message}. "  # noqa
                    )
                    return []
                # All other network exceptions should be raised
                raise e
            isochrones.extend(json.loads(isochrone_json)["polygons"])
        return isochrones

    def __add_isochrones_to_layer(self, layer: QgsVectorLayer) -> None:
        TASK_LOGGER.info("Starting isochrone fetch...")
        for idx, (point, boundary) in enumerate(
                zip(self.points, self.limiting_polygons)):
            bucketed_isochrones = self.__fetch_bucketed_isochrones(point)
            for polygon_in_bucket in bucketed_isochrones:
                feature = QgsFeature(layer.fields())
                # save the original feature id separately
                # setAttributes cannot be used, will destroy any extra fields!!
                for index, attribute in enumerate(point.attributes()):
                    feature.setAttribute(index, attribute)
                # set the added distance field separately
                bucket = polygon_in_bucket["properties"]["bucket"]
                distance = (bucket + 1) * (
                    self.opts.distance / self.opts.buckets  # type: ignore
                )
                feature["isochrone_distance"] = distance

                isochrone = QgsGeometry.fromMultiPolygonXY(
                        [[[QgsPointXY(pt[0], pt[1])
                          for pt in polygon_in_bucket["geometry"]["coordinates"][0]
                           ]]]
                    )
                if boundary:
                    feature["boundary_fids"] = boundary["fids"]
                    isochrone_parts = boundary.geometry().\
                        intersection(isochrone).asGeometryCollection()
                    # After intersecting with the boundary, the isochrone may be a
                    # GeometryCollection of Polygons, LineStrings and Points. We are
                    # only interested in 2D areas, so collect all the Polygons to a
                    # MultiPolygon.
                    isochrone = QgsGeometry.fromMultiPolygonXY(
                        [geometry.asPolygon()
                            for geometry in isochrone_parts
                            if geometry.wkbType() == QgsWkbTypes.Polygon
                         ]
                    )
                else:
                    feature["boundary_fids"] = ""

                feature.setGeometry(isochrone)
                layer.dataProvider().addFeature(feature)
            if idx and idx % 10 == 0:
                TASK_LOGGER.info(
                    f"{idx} out of {len(self.points)} objects fetched"  # type: ignore  # noqa
                )
            if self.isCanceled():
                TASK_LOGGER.warning(
                    f"Task cancelled, only {idx} out of {len(self.points)} isochrones calculated"  # type: ignore  # noqa
                )
                break
            self.setProgress(100 * (idx / len(self.points)))

    def create_isochrone_layer(self) -> QgsVectorLayer:
        """Creates a polygon QgsVectorLayer containing isochrones for points"""
        isochrone_layer = QgsVectorLayer(
            "Polygon?crs=epsg:4326&index=yes", self.name, "memory"
        )

        # add all the required fields to the new layer
        fields = QgsFields(self.opts.layer.fields())  # type: ignore
        # save original feature id separate from new feature id
        fields.rename(0, "original_fid")
        distance_field = QgsField(
            name="isochrone_distance", type=QVariant.Double, typeName="double"
        )
        boundary_fid_field = QgsField(
            name="boundary_fids", type=QVariant.String, typeName="varchar"
        )
        fields.append(distance_field)
        fields.append(boundary_fid_field)
        provider = isochrone_layer.dataProvider()
        provider.addAttributes(fields)
        isochrone_layer.updateFields()

        self.__add_isochrones_to_layer(isochrone_layer)
        # update layer's extent when new features have been added
        isochrone_layer.updateExtents()

        # in case a directory was specified, save the layer to geopackage
        geopackage_file = None
        if (
            isochrone_layer.featureCount()
            and self.opts.write_to_directory
            and self.opts.directory
        ):
            geopackage_file = os.path.join(self.opts.directory, f"{self.name}.gpkg")
            save_options = QgsVectorFileWriter.SaveVectorOptions()
            error = QgsVectorFileWriter.writeAsVectorFormatV2(
                isochrone_layer,
                geopackage_file,
                QgsCoordinateTransformContext(),
                save_options,
            )
            if error[0]:
                TASK_LOGGER.error(
                    f"Could not save file: {error}",
                )
            else:
                # in case the layer was saved, return the saved layer instead
                TASK_LOGGER.info(f"Saved to file {geopackage_file}")
                isochrone_layer = QgsVectorLayer(geopackage_file, self.name, "ogr")

        isochrone_layer.renderer().symbol().setOpacity(0.15)
        return isochrone_layer
