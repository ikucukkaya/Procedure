from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
                          QDialogButtonBox, QGroupBox)
from PyQt5.QtCore import Qt

class StartupOptionsDialog(QDialog):
    """Dialog to select both airspace folder and GeoJSON map file."""
    def __init__(self, airspace_folders, geojson_files, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Data Sources")
        self.setMinimumWidth(450)
        
        # Remove the context help button flag
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.layout = QVBoxLayout(self)
        self.selected_airspace_folder = None
        self.selected_geojson_file = None

        # --- Airspace Folder Selection --- 
        airspace_group = QGroupBox("Airspace Data")
        airspace_layout = QHBoxLayout()
        airspace_layout.addWidget(QLabel("Select Airspace Folder:"))
        self.airspace_combo = QComboBox()
        if airspace_folders: # Check if the list is not empty
            self.airspace_combo.addItems(airspace_folders)
        else:
            # Optionally disable the combo box or add a placeholder
            self.airspace_combo.addItem("No airspace folders found")
            self.airspace_combo.setEnabled(False)
        airspace_layout.addWidget(self.airspace_combo)
        airspace_group.setLayout(airspace_layout)
        self.layout.addWidget(airspace_group)

        # --- GeoJSON File Selection --- 
        geojson_group = QGroupBox("Map Data")
        geojson_layout = QHBoxLayout()
        geojson_layout.addWidget(QLabel("Select GeoJSON Map File:"))
        self.geojson_combo = QComboBox()
        if geojson_files: # Check if the list is not empty
            self.geojson_combo.addItems(geojson_files)
            # Select map.geojson by default if it exists
            if "map.geojson" in geojson_files:
                self.geojson_combo.setCurrentText("map.geojson")
        else:
            # Optionally disable or add placeholder
            self.geojson_combo.addItem("No GeoJSON files found")
            self.geojson_combo.setEnabled(False)
        geojson_layout.addWidget(self.geojson_combo)
        geojson_group.setLayout(geojson_layout)
        self.layout.addWidget(geojson_group)

        # --- OK and Cancel buttons --- 
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        # Disable OK if critical data is missing
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(bool(airspace_folders)) 
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonBox)

    def accept(self):
        """Store selected values before accepting."""
        # Only store if combo boxes are enabled (meaning data was found)
        if self.airspace_combo.isEnabled():
             self.selected_airspace_folder = self.airspace_combo.currentText()
        if self.geojson_combo.isEnabled():
             self.selected_geojson_file = self.geojson_combo.currentText()
        super().accept()

    def get_selected_paths(self):
        """Return the selected folder and file names."""
        return self.selected_airspace_folder, self.selected_geojson_file 