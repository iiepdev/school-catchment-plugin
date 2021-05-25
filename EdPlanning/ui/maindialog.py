from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QDialog, QRadioButton, QWidget
from qgis.core import QgsMapLayerProxyModel

from ..core.isochrone_creator import IsochroneOpts
from ..definitions.constants import Profile, Unit
from ..qgis_plugin_tools.tools.resources import load_ui
from ..qgis_plugin_tools.tools.settings import get_setting

FORM_CLASS = load_ui("main.ui")


class MainDialog(QDialog, FORM_CLASS):  # type: ignore
    def __init__(self) -> None:
        super().__init__()
        self.setupUi(self)
        self.combobox_layer.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.lineedit_url.setText(get_setting("gh_url"))

    def read_isochrone_options(self) -> IsochroneOpts:
        opts = IsochroneOpts()
        opts.url = self.lineedit_url.text()
        opts.layer = self.combobox_layer.currentLayer()
        opts.distance = self.spinbox_distance.value()

        unit = self.__get_radiobtn_name(self.groupbox_units)
        if unit == "radiobtn_mins":
            opts.unit = Unit.MINUTES
        elif unit == "radiobtn_meters":
            opts.unit = Unit.METERS

        profile = self.__get_radiobtn_name(self.groupbox_profile)
        if profile == "radiobtn_walking":
            opts.profile = Profile.WALKING
        elif profile == "radiobtn_cycling":
            opts.profile = Profile.CYCLING
        elif profile == "radiobtn_driving":
            opts.profile = Profile.DRIVING

        return opts

    @staticmethod
    def __get_radiobtn_name(parent: QWidget) -> str:
        for radio_button in parent.findChildren(QRadioButton):
            if radio_button.isChecked():
                return radio_button.objectName()
        raise Exception("No checked radio buttons found")  # TODO: exception

    @pyqtSlot()
    def on_radiobtn_mins_clicked(self) -> None:
        self.__update_unit_selector(Unit.MINUTES)

    @pyqtSlot()
    def on_radiobtn_meters_clicked(self) -> None:
        self.__update_unit_selector(Unit.METERS)

    def __update_unit_selector(self, selected_unit: Unit) -> None:
        """Sets unit spinbox min, max, and step values
        based on currently selected unit"""
        if selected_unit == Unit.MINUTES:
            step = 1
            min_ = 1
            max_ = 120
            default = 30
        elif selected_unit == Unit.METERS:
            step = 500
            min_ = 500
            max_ = 5000
            default = 2000

        self.spinbox_distance.setSingleStep(step)
        self.spinbox_distance.setMinimum(min_)
        self.spinbox_distance.setMaximum(max_)
        self.spinbox_distance.setValue(default)
        self.spinbox_distance.setClearValue(default)
