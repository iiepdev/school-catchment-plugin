# type: ignore
# flake8: noqa ANN201
"""
This class contains fixtures and common helper function to keep the test files shorter
"""
import pytest
from qgis.core import QgsVectorLayer

from EdPlanning.core.isochrone_creator import IsochroneOpts
from EdPlanning.definitions.constants import Profile, Unit

from ..qgis_plugin_tools.testing.utilities import get_qgis_app

QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()


@pytest.fixture(autouse=True)
def new_project() -> None:
    """Initializes new QGIS project by removing layers and relations etc."""  # noqa E501
    yield IFACE.newProject()


@pytest.fixture(scope="function")
def vector_layer() -> None:
    yield QgsVectorLayer()


@pytest.fixture(scope="function")
def isochrone_opts(vector_layer) -> None:
    opts = IsochroneOpts(
        url="http://mock.url",
        layer=vector_layer,
        distance=30,
        unit=Unit.MINUTES,
        profile=Profile.HIKING,
    )
    yield opts
