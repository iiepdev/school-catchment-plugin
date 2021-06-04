# type: ignore
import pytest
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QDialogButtonBox
from qgis.core import QgsProject, QgsWkbTypes

from EdPlanning.plugin import Plugin
from EdPlanning.qgis_plugin_tools.tools.settings import get_setting

from .conftest import MOCK_URL, QGIS_APP


def test_plugin(new_plugin, mock_fetch, qtbot):
    mock_fetch(MOCK_URL + "/isochrone")
    new_plugin.run()
    dialog = new_plugin.dlg
    buttonbox = dialog.buttonbox_main
    for button in buttonbox.buttons():
        if buttonbox.buttonRole(button) == QDialogButtonBox.AcceptRole:
            qtbot.mouseClick(button, Qt.LeftButton)
    action = QGIS_APP.taskManager().activeTasks()[0]
    blocker = qtbot.waitSignal(action.taskCompleted, timeout=10000)
    blocker.wait()
    # check result layer
    assert QgsProject.instance().count() == 1
    for layer in QgsProject.instance().mapLayers().values():
        assert layer.geometryType() == QgsWkbTypes.PolygonGeometry
        assert layer.featureCount() == 1


def test_plugin_fail(new_plugin, mock_fetch, qtbot):
    mock_fetch(MOCK_URL + "/isochrone", "error.json", error=True)
    new_plugin.run()
    dialog = new_plugin.dlg
    buttonbox = dialog.buttonbox_main
    for button in buttonbox.buttons():
        if buttonbox.buttonRole(button) == QDialogButtonBox.AcceptRole:
            qtbot.mouseClick(button, Qt.LeftButton)
    action = QGIS_APP.taskManager().activeTasks()[0]
    # check that the task is *not* completed
    blocker = qtbot.waitSignal(action.taskTerminated, timeout=10000)
    blocker.wait()
    # check that empty layer is not added
    assert QgsProject.instance().count() == 0
