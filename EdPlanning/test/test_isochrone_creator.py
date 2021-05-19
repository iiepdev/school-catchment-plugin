from EdPlanning.core.isochrone_creator import IsochroneCreator


def test_isochrone_layer(new_project, isochrone_opts):
    isochrone_layer = IsochroneCreator(isochrone_opts).create_isochrone_layer()
    assert isochrone_layer
