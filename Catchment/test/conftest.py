# type: ignore
# flake8: noqa ANN201
"""
This class contains fixtures and common helper function to keep the test files shorter
"""
import os
from typing import Callable, Dict, Optional

import pytest
from PyQt5.QtCore import QVariant

# from PyQt5.QtNetwork import QNetworkReply
from qgis.core import (
    QgsFeature,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsLineString,
    QgsPointXY,
    QgsPolygon,
    QgsVectorLayer,
)

from Catchment.core.isochrone_creator import IsochroneOpts
from Catchment.definitions.constants import Profile, Unit
from Catchment.plugin import Plugin

from ..qgis_plugin_tools.tools.exceptions import QgsPluginNetworkException
from ..qgis_plugin_tools.tools.i18n import tr

MOCK_URL = "http://mock.url"


@pytest.fixture(scope="function")
def mock_fetch(mocker, request) -> None:
    """Makes fetch return JSON for a specified URL, exception otherwise.
    Use by calling mock_fetch(desired_url, json_file_name, error_desired) in a test.
    """

    def _mock_fetch(
        url: str,
        json_to_return: str = "isochrones.json",
        error: bool = False,
    ) -> Callable:
        def mocked_fetch(
            incoming_url: str,
            params: Optional[Dict[str, str]] = None,
        ) -> str:
            if incoming_url == url:
                with open(
                    os.path.join(request.fspath.dirname, "fixtures", json_to_return)
                ) as f:
                    # mock error if desired
                    if error:
                        raise QgsPluginNetworkException(f.read(), error=302)
                    return f.read()
            raise QgsPluginNetworkException(tr("Request failed"))

        mocker.patch("Catchment.core.isochrone_creator.fetch", new=mocked_fetch)

    yield _mock_fetch


@pytest.fixture(scope="function")
def point() -> None:
    yield QgsGeometry.fromPointXY(QgsPointXY(1.0, 1.0))


@pytest.fixture(scope="function")
def square() -> None:
    yield QgsGeometry.fromPolygonXY(
        [[QgsPointXY(0.0, 0.0), QgsPointXY(2.0, 0.0), QgsPointXY(2.0, 2.0), QgsPointXY(0.0, 2.0)]]
    )


@pytest.fixture(scope="function")
def multipolygon() -> None:
    yield QgsGeometry.fromMultiPolygonXY(
        [[[QgsPointXY(0.0, 0.0), QgsPointXY(2.0, 0.0), QgsPointXY(2.0, 2.0), QgsPointXY(0.0, 2.0)]],
        [[QgsPointXY(4.0, 4.0), QgsPointXY(6.0, 4.0), QgsPointXY(6.0, 6.0), QgsPointXY(4.0, 6.0)]]]
    )


@pytest.fixture(scope="function")
def triangle() -> None:
    yield QgsGeometry.fromPolygonXY(
        [[QgsPointXY(-1.0, -1.0), QgsPointXY(3.0, -1.0), QgsPointXY(1.0, 2.0)]]
    )


@pytest.fixture(scope="function")
def fields() -> None:
    fields = QgsFields()
    fields.append(QgsField("fid", QVariant.Int))
    fields.append(QgsField("name", QVariant.String))
    yield fields


@pytest.fixture(scope="function")
def point_feature(fields, point) -> None:
    feature = QgsFeature(fields)
    feature.setGeometry(point)
    feature.setAttribute("fid", 1)
    feature.setAttribute("name", "school")
    yield feature


@pytest.fixture(scope="function")
def square_feature(fields, square) -> None:
    feature = QgsFeature(fields)
    feature.setGeometry(square)
    feature.setAttribute("fid", 1)
    feature.setAttribute("name", "square_school_area_boundary")
    yield feature


@pytest.fixture(scope="function")
def multipolygon_feature(fields, multipolygon) -> None:
    feature = QgsFeature(fields)
    feature.setGeometry(multipolygon)
    feature.setAttribute("fid", 1)
    feature.setAttribute("name", "multipolygon_school_area_boundary")
    yield feature


@pytest.fixture(scope="function")
def triangle_feature(fields, triangle) -> None:
    feature = QgsFeature(fields)
    feature.setGeometry(triangle)
    feature.setAttribute("fid", 1)
    feature.setAttribute("name", "triangular_school_area_boundary")
    yield feature


@pytest.fixture(scope="function")
def point_layer(fields, point_feature) -> None:
    layer = QgsVectorLayer("Point?crs=epsg:4326&index=yes", "test_points", "memory")
    provider = layer.dataProvider()
    provider.addAttributes(fields)
    layer.updateFields()
    provider.addFeature(point_feature)
    layer.updateExtents()
    yield layer


@pytest.fixture(scope="function")
def square_layer(fields, square_feature) -> None:
    layer = QgsVectorLayer("Polygon?crs=epsg:4326&index=yes", "test_boundaries", "memory")
    provider = layer.dataProvider()
    provider.addAttributes(fields)
    layer.updateFields()
    provider.addFeature(square_feature)
    layer.updateExtents()
    yield layer


@pytest.fixture(scope="function")
def multipolygon_layer(fields, multipolygon_feature) -> None:
    layer = QgsVectorLayer("Polygon?crs=epsg:4326&index=yes", "test_boundaries", "memory")
    provider = layer.dataProvider()
    provider.addAttributes(fields)
    layer.updateFields()
    provider.addFeature(multipolygon_feature)
    layer.updateExtents()
    yield layer


@pytest.fixture(scope="function")
def triangle_layer(fields, triangle_feature) -> None:
    layer = QgsVectorLayer("Polygon?crs=epsg:4326&index=yes", "test_boundaries", "memory")
    provider = layer.dataProvider()
    provider.addAttributes(fields)
    layer.updateFields()
    provider.addFeature(triangle_feature)
    layer.updateExtents()
    yield layer


@pytest.fixture(scope="function")
def square_plus_triangle_layer(fields, square_feature, triangle_feature) -> None:
    layer = QgsVectorLayer("Polygon?crs=epsg:4326&index=yes", "test_boundaries", "memory")
    provider = layer.dataProvider()
    provider.addAttributes(fields)
    layer.updateFields()
    provider.addFeature(square_feature)
    provider.addFeature(triangle_feature)
    layer.updateExtents()
    yield layer


@pytest.fixture(scope="function")
def isochrone_opts(point_layer, request) -> None:
    opts = IsochroneOpts(
        url=MOCK_URL,
        layer=point_layer,
        distance=30,
        unit=Unit.MINUTES,
        profile=Profile.WALKING,
    )
    yield opts


@pytest.fixture(scope="function")
def new_plugin(isochrone_opts) -> None:
    plugin = Plugin()
    plugin.initGui()
    # mock options, since mock QgisInterface does not support QgsMapLayerComboBox
    plugin.dlg.read_isochrone_options = lambda: isochrone_opts
    yield plugin
