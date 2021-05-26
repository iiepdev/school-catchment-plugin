import logging

from PyQt5.QtWidgets import QDesktopWidget, QDialog, QRadioButton, QWidget

from ..core.isochrone_creator import IsochroneOpts
from ..definitions.constants import Profile, Unit
from ..definitions.gui import Panels
from ..qgis_plugin_tools.tools.resources import load_ui, plugin_name
from ..qgis_plugin_tools.tools.settings import get_setting
from .about_panel import AboutPanel
from .catchment_area_panel import CatchmentAreaPanel
from .settings_panel import SettingsPanel

FORM_CLASS = load_ui("main.ui")
LOGGER = logging.getLogger(plugin_name())


class MainDialog(QDialog, FORM_CLASS):  # type: ignore
    """
    The structure and idea of the UI is adapted from https://github.com/3liz/QuickOSM
    licenced under GPL version 2
    """

    def __init__(self) -> None:
        super().__init__()
        self.setupUi(self)
        self.lineedit_url.setText(get_setting("gh_url"))

        self._set_window_location()
        self.panels = {
            Panels.CatchmentAreas: CatchmentAreaPanel(self),
            Panels.Settings: SettingsPanel(self),
            Panels.About: AboutPanel(self),
        }
        for i, panel in enumerate(self.panels):
            item = self.menu_widget.item(i)
            item.setIcon(panel.icon)
            self.panels[panel].panel = panel
        # Change panel as menu item is changed
        self.menu_widget.currentRowChanged["int"].connect(
            self.stacked_widget.setCurrentIndex
        )
        # Set up all the panels
        for panel in self.panels.values():
            panel.setup_panel()
        # The first panel is shown initially
        self.menu_widget.setCurrentRow(0)

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

    def _set_window_location(self):
        ag = QDesktopWidget().availableGeometry()
        sg = QDesktopWidget().screenGeometry()

        widget = self.geometry()
        x = (ag.width() - widget.width()) / 1.5
        y = 2 * ag.height() - sg.height() - 1.2 * widget.height()
        self.move(x, y)

    @staticmethod
    def __get_radiobtn_name(parent: QWidget) -> str:
        for radio_button in parent.findChildren(QRadioButton):
            if radio_button.isChecked():
                return radio_button.objectName()
        raise Exception("No checked radio buttons found")  # TODO: exception
