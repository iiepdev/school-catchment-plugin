# type: ignore
# flake8: noqa ANN201
"""
This class contains fixtures and common helper function to keep the test files shorter
"""
import os
from typing import Callable, Dict, Optional

import pytest
from qgis.core import QgsFeature, QgsGeometry, QgsPointXY, QgsVectorLayer

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
    """Initializes new QGIS project by removing layers and relations etc."""  # noqa E501
    yield IFACE.newProject()


@pytest.fixture(scope="function")
def mock_fetch(mocker, request) -> None:
    """Makes fetch return JSON for a specified URL, exception otherwise.
    Use by calling mock_fetch(desired_url) in a test.
    """

    def _mock_fetch(url: str) -> Callable:
        def mocked_fetch(
            incoming_url: str, params: Optional[Dict[str, str]] = None
        ) -> str:
            if incoming_url == url:
                with open(
                    os.path.join(request.fspath.dirname, "fixtures", "isochrones.json")
                ) as f:
                    return f.read()
            raise QgsPluginNetworkException(tr("Request failed"))

        mocker.patch("EdPlanning.core.isochrone_creator.fetch", new=mocked_fetch)

    yield _mock_fetch


@pytest.fixture(scope="function")
def point() -> None:
    yield QgsPointXY(1.0, 1.0)


@pytest.fixture(scope="function")
def point_feature(point) -> None:
    feature = QgsFeature()
    feature.setGeometry(QgsGeometry.fromPointXY(point))
    yield feature


@pytest.fixture(scope="function")
def vector_layer(point_feature) -> None:
    layer = QgsVectorLayer("Point?crs=epsg:4326&index=yes", "test_points", "memory")
    provider = layer.dataProvider()
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
