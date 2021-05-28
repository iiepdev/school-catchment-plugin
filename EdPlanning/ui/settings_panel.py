import logging
import webbrowser

from PyQt5.QtWidgets import QDialog
from qgis.gui import QgsFileWidget

from ..definitions.gui import Panels
from ..qgis_plugin_tools.tools.custom_logging import (
    LogTarget,
    get_log_level_key,
    get_log_level_name,
)
from ..qgis_plugin_tools.tools.resources import plugin_name, plugin_path
from ..qgis_plugin_tools.tools.settings import set_setting
from .base_panel import BasePanel

LOGGER = logging.getLogger(plugin_name())

LOGGING_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class SettingsPanel(BasePanel):
    def __init__(self, dialog: QDialog) -> None:
        super().__init__(dialog)
        self.panel = Panels.Settings

    def setup_panel(self) -> None:
        # connect the signals, since pyqt slot decorator cannot be used
        self.dlg.checkbox_file.clicked.connect(self.on_checkbox_file_clicked)

        self.dlg.file_widget.setStorageMode(QgsFileWidget.StorageMode.GetDirectory)

        self.dlg.combo_box_log_level_file.clear()
        self.dlg.combo_box_log_level_console.clear()

        self.dlg.combo_box_log_level_file.addItems(LOGGING_LEVELS)
        self.dlg.combo_box_log_level_console.addItems(LOGGING_LEVELS)
        self.dlg.combo_box_log_level_file.setCurrentText(
            get_log_level_name(LogTarget.FILE)
        )
        self.dlg.combo_box_log_level_console.setCurrentText(
            get_log_level_name(LogTarget.STREAM)
        )

        self.dlg.combo_box_log_level_file.currentTextChanged.connect(
            lambda level: set_setting(get_log_level_key(LogTarget.FILE), level)
        )

        self.dlg.combo_box_log_level_console.currentTextChanged.connect(
            lambda level: set_setting(get_log_level_key(LogTarget.STREAM), level)
        )

        self.dlg.btn_open_log.clicked.connect(
            lambda _: webbrowser.open(plugin_path("logs", f"{plugin_name()}.log"))
        )

    def on_checkbox_file_clicked(self) -> None:
        self.dlg.file_widget.setEnabled(self.dlg.checkbox_file.isChecked())
