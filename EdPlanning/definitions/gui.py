"""Definitions for GUI concepts."""
import enum

from PyQt5.QtGui import QIcon
from qgis.core import QgsApplication

from ..qgis_plugin_tools.tools.resources import resources_path


class Panels(enum.Enum):
    """Panels in the Dialog"""

    CatchmentAreas = {"icon": "/mIconPolygonLayer.svg"}
    Settings = {"icon": "/mActionMapSettings.svg"}
    About = {"icon": "/mActionHelpContents.svg"}

    @property
    def icon(self) -> QIcon:
        _icon: str = self.value["icon"]

        # QGIS icons
        # https://github.com/qgis/QGIS/tree/master/images/themes/default
        if _icon.startswith("/"):
            return QgsApplication.getThemeIcon(_icon)
        else:
            # Internal icons
            return QIcon(resources_path("icons", _icon))
