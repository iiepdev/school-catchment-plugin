import logging
from math import floor, pow
from typing import Optional

from qgis.core import QgsMapLayerProxyModel
from qgis.PyQt.QtWidgets import QDialog

from ..definitions.constants import Profile, Unit
from ..definitions.gui import Panels
from ..qgis_plugin_tools.tools.exceptions import QgsPluginException
from ..qgis_plugin_tools.tools.resources import plugin_name
from .base_panel import BasePanel

LOGGER = logging.getLogger(plugin_name())


class TooHeavyOperationException(QgsPluginException):
    pass


class CatchmentAreaPanel(BasePanel):
    def __init__(self, dialog: QDialog) -> None:
        super().__init__(dialog)
        self.panel = Panels.CatchmentAreas

    def setup_panel(self) -> None:
        self.dlg.combobox_layer.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.dlg.combobox_polygon_layer.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.dlg.combobox_polygon_layer.setEnabled(False)
        self.__update_duration_label()

        # connect the signals, since pyqt slot decorator cannot be used
        self.dlg.radiobtn_mins.clicked.connect(self.on_radiobtn_mins_clicked)
        self.dlg.radiobtn_meters.clicked.connect(self.on_radiobtn_meters_clicked)
        self.dlg.radiobtn_walking.clicked.connect(self.on_radiobtn_walking_clicked)
        self.dlg.radiobtn_cycling.clicked.connect(self.on_radiobtn_cycling_clicked)
        self.dlg.radiobtn_driving.clicked.connect(self.on_radiobtn_driving_clicked)
        self.dlg.combobox_layer.layerChanged.connect(
            self.on_combobox_layer_layerChanged
        )
        self.dlg.combobox_polygon_layer.layerChanged.connect(
            self.on_combobox_polygon_layer_layerChanged
        )
        self.dlg.checkbox_selected_only.clicked.connect(
            self.on_checkbox_selected_only_clicked
        )
        self.dlg.checkbox_limit_to_polygon.clicked.connect(
            self.on_checkbox_limit_to_polygon_clicked
        )
        self.dlg.spinbox_distance.valueChanged.connect(
            self.on_spinbox_distance_valueChanged
        )
        self.dlg.spinbox_buckets.valueChanged.connect(
            self.on_spinbox_buckets_valueChanged
        )

    def _get_duration(self) -> Optional[int]:
        """
        Estimated duration of the calculation in minutes,
        assuming O(2^(5K-1) - 2^(4K-4)) scaling.

        Here K is one step in the graph. Simplifies to
        O(2^(5K)-2^(4K))~=O(2^(5K)) for large K.
        """
        opts = self.dlg.read_isochrone_options()
        if opts.check_if_opts_set():
            buckets = opts.buckets
            count = buckets * (
                opts.layer.selectedFeatureCount()  # type: ignore
                if opts.selected_only
                else opts.layer.featureCount()  # type: ignore
            )
            distance_in_minutes_by_foot: int = opts.distance  # type: ignore
            if opts.unit == Unit.METERS:
                # assuming walking speed 5 km/h = 83.3 m/min
                distance_in_minutes_by_foot = opts.distance / 83.3  # type: ignore
            elif opts.profile == Profile.CYCLING:
                # assuming biking speed 25 km/h
                distance_in_minutes_by_foot = 3 * distance_in_minutes_by_foot  # type: ignore  # noqa
            elif opts.profile == Profile.DRIVING:
                # assuming driving speed 50 km/h
                distance_in_minutes_by_foot = 10 * distance_in_minutes_by_foot  # type: ignore  # noqa
            if count:
                # TODO: improve estimate, larger K and smaller count factor!
                # Normalize, knowing that 60 minute distance by car
                # (equivalent of 600 minutes by foot) takes ~ 10 minute
                # to calculate for 1000 points.
                # No idea why K should be so small here.
                minutes_per_thousand_points = 10 * pow(
                    2, distance_in_minutes_by_foot / 100 - 6
                )
                # Network calls ~ 5 minutes for 1000 pts
                # (on a slow network with large polygons)
                total = float(count / 200) * float(minutes_per_thousand_points + 1)
                if total > 120:
                    raise TooHeavyOperationException()
                return floor(total)
        return None

    def on_radiobtn_mins_clicked(self) -> None:
        self.__update_unit_selector(Unit.MINUTES)
        self.__update_duration_label()

    def on_radiobtn_meters_clicked(self) -> None:
        self.__update_unit_selector(Unit.METERS)
        self.__update_duration_label()

    def on_radiobtn_walking_clicked(self) -> None:
        self.__update_duration_label()

    def on_radiobtn_cycling_clicked(self) -> None:
        self.__update_duration_label()

    def on_radiobtn_driving_clicked(self) -> None:
        self.__update_duration_label()

    def on_combobox_layer_layerChanged(self) -> None:  # noqa
        self.__update_duration_label()

    def on_combobox_polygon_layer_layerChanged(self) -> None:  # noqa
        pass

    def on_checkbox_selected_only_clicked(self) -> None:
        self.__update_duration_label()

    def on_checkbox_limit_to_polygon_clicked(self) -> None:
        self.dlg.combobox_polygon_layer.setEnabled(
            not self.dlg.combobox_polygon_layer.isEnabled()
            )

    def on_spinbox_distance_valueChanged(self) -> None:  # noqa
        self.__update_duration_label()

    def on_spinbox_buckets_valueChanged(self) -> None:  # noqa
        self.__update_duration_label()

    def __update_unit_selector(self, selected_unit: Unit) -> None:
        """Sets unit spinbox min, max, and step values
        based on currently selected unit"""
        if selected_unit == Unit.MINUTES:
            step = 5
            min_ = 5
            max_ = 120
            default = 30
        elif selected_unit == Unit.METERS:
            step = 500
            min_ = 500
            max_ = 10000
            default = 2000

        self.dlg.spinbox_distance.setSingleStep(step)
        self.dlg.spinbox_distance.setMinimum(min_)
        self.dlg.spinbox_distance.setMaximum(max_)
        self.dlg.spinbox_distance.setValue(default)
        self.dlg.spinbox_distance.setClearValue(default)

    def __update_duration_label(self) -> None:
        """Updates estimated duration based on currently
        selected isochrone options"""

        try:
            duration = self._get_duration()
            if duration is not None:
                self.dlg.duration_label.setText(
                    f"Approximate processing time: {duration} mins\nThe amount of "
                    "road data in your area and your internet connection speed\n"
                    "will affect the total processing time."
                )
            else:
                self.dlg.duration_label.setText("")
            self.dlg.duration_label.setStyleSheet("color: black")
        except (OverflowError, TooHeavyOperationException):
            self.dlg.duration_label.setText(
                "Too many points or too large distance selected.\nRunning with these "
                "settings may take several hours or days."
            )
            self.dlg.duration_label.setStyleSheet("color: red")
