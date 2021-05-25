import logging
from math import ceil, log
from typing import Optional

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
        self.__update_duration_label()

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

    def _get_duration(self) -> Optional[int]:
        """
        Estimated duration of the calculation in minutes,
        assuming logarithmic scaling
        """
        opts = self.read_isochrone_options()
        if opts.check_if_opts_set():
            count = opts.layer.featureCount()  # type: ignore
            distance_in_minutes_by_foot: int = opts.distance  # type: ignore
            if opts.unit == Unit.METERS:
                # assuming walking speed 5 km/h = 83.3 m/min
                distance_in_minutes_by_foot = opts.distance / 83.3  # type: ignore
            if opts.profile == Profile.CYCLING:
                # assuming biking speed 15 km/h
                distance_in_minutes_by_foot = 3 * distance_in_minutes_by_foot  # type: ignore  # noqa
            elif opts.profile == Profile.DRIVING:
                # assuming driving speed 50 km/h
                distance_in_minutes_by_foot = 10 * distance_in_minutes_by_foot  # type: ignore  # noqa
            if count:
                # 30 minute distance takes ~ 1 minute for 1000 points
                return int(
                    ceil(
                        (float(count) / 1000)
                        * (log(distance_in_minutes_by_foot / 30, 2) + 1)
                    )
                )
        return None

    @staticmethod
    def __get_radiobtn_name(parent: QWidget) -> str:
        for radio_button in parent.findChildren(QRadioButton):
            if radio_button.isChecked():
                return radio_button.objectName()
        raise Exception("No checked radio buttons found")  # TODO: exception

    @pyqtSlot()
    def on_radiobtn_mins_clicked(self) -> None:
        self.__update_unit_selector(Unit.MINUTES)
        self.__update_duration_label()

    @pyqtSlot()
    def on_radiobtn_meters_clicked(self) -> None:
        self.__update_unit_selector(Unit.METERS)
        self.__update_duration_label()

    @pyqtSlot()
    def on_radiobtn_walking_clicked(self) -> None:
        self.__update_duration_label()

    @pyqtSlot()
    def on_radiobtn_cycling_clicked(self) -> None:
        self.__update_duration_label()

    @pyqtSlot()
    def on_radiobtn_driving_clicked(self) -> None:
        self.__update_duration_label()

    @pyqtSlot(int)
    def on_spinbox_distance_valueChanged(self) -> None:
        self.__update_duration_label()

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

    def __update_duration_label(self) -> None:
        """Updates estimated duration based on currently
        selected isochrone options"""

        duration = self._get_duration()
        if duration is not None:
            self.duration_label.setText(f"Estimated time to calculate: {duration} mins")
        else:
            self.duration_label.setText("")
