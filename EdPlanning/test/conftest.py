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
    QgsPointXY,
    QgsVectorLayer,
)

from EdPlanning.core.isochrone_creator import IsochroneOpts
from EdPlanning.definitions.constants import Profile, Unit
from EdPlanning.plugin import Plugin

from ..qgis_plugin_tools.testing.utilities import get_qgis_app
from ..qgis_plugin_tools.tools.exceptions import QgsPluginNetworkException
from ..qgis_plugin_tools.tools.i18n import tr

QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()
MOCK_URL = "http://mock.url"


@pytest.fixture(autouse=True)
def new_project() -> None:
    """Initializes the QGIS project by removing layers and relations etc."""  # noqa E501
    # yields nothing
    yield IFACE.newProject()


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

        mocker.patch("EdPlanning.core.isochrone_creator.fetch", new=mocked_fetch)

    yield _mock_fetch


@pytest.fixture(scope="function")
def point() -> None:
    yield QgsPointXY(1.0, 1.0)


@pytest.fixture(scope="function")
def fields() -> None:
    fields = QgsFields()
    fields.append(QgsField("id", QVariant.Int))
    fields.append(QgsField("name", QVariant.String))
    yield fields


@pytest.fixture(scope="function")
def point_feature(fields, point) -> None:
    feature = QgsFeature(fields)
    feature.setGeometry(QgsGeometry.fromPointXY(point))
    feature.setAttribute("id", 1)
    feature.setAttribute("name", "school")
    yield feature


@pytest.fixture(scope="function")
def vector_layer(fields, point_feature) -> None:
    layer = QgsVectorLayer("Point?crs=epsg:4326&index=yes", "test_points", "memory")
    provider = layer.dataProvider()
    provider.addAttributes(fields)
    layer.updateFields()
    provider.addFeature(point_feature)
    layer.updateExtents()
    yield layer


@pytest.fixture(scope="function")
def isochrone_opts(vector_layer) -> None:
    opts = IsochroneOpts(
        url=MOCK_URL,
        layer=vector_layer,
        distance=30,
        unit=Unit.MINUTES,
        profile=Profile.WALKING,
    )
    yield opts


@pytest.fixture(scope="function")
def new_plugin(isochrone_opts) -> None:
    plugin = Plugin(IFACE)
    plugin.initGui()
    # mock options, since mock QgisInterface does not support QgsMapLayerComboBox
    plugin.dlg.read_isochrone_options = lambda: isochrone_opts
    yield plugin
