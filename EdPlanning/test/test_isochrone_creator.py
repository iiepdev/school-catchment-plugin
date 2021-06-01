import pytest
from qgis.core import QgsWkbTypes

from EdPlanning.core.isochrone_creator import IsochroneCreator


def test_isochrone_layer_isochrone_created(isochrone_opts, mock_fetch):
    mock_fetch(isochrone_opts.url + "/isochrone")
    assert isochrone_opts.layer.featureCount() == 1
    assert isochrone_opts.check_if_opts_set()
    isochrone_layer = IsochroneCreator(isochrone_opts).create_isochrone_layer()
    assert isochrone_layer.featureCount() == 1
    assert isochrone_layer.geometryType() == QgsWkbTypes.PolygonGeometry
    for feature in isochrone_layer.getFeatures():
        assert feature.attribute("id") == 1
        assert feature.attribute("name") == "school"


def test_isochrone_layer_request_failed(isochrone_opts, mock_fetch):
    mock_fetch("another.url")
    assert isochrone_opts.layer.featureCount() == 1
    assert isochrone_opts.check_if_opts_set()
    isochrone_layer = IsochroneCreator(isochrone_opts).create_isochrone_layer()
    assert isochrone_layer.featureCount() == 0
