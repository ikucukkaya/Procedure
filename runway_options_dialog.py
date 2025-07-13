from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, \
                          QHeaderView, QCheckBox, QLineEdit, QComboBox, \
                          QDialogButtonBox, QWidget, QHBoxLayout, QLabel)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDoubleValidator, QIntValidator
from collections import defaultdict # Import defaultdict
import re # Import re if not already there

# Import the specific DMS parser function needed
from utils import parse_dms as utils_parse_dms 

class RunwayOptionsDialog(QDialog):
    """Dialog to configure display options for runway centerlines."""
    def __init__(self, runways, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Runway Display Options")
        # Sort runways before storing them
        self.runways = self._sort_runways(runways) 
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        self.layout = QVBoxLayout(self)
        self.widgets_by_runway = {} # To store widgets for getting values later

        self._setup_table()
        self._populate_table()
        self._setup_buttons()

    def _sort_runways(self, runways):
        """Apply custom sorting logic to the runway list."""
        if not runways: return []
        
        airport_groups = defaultdict(list)
        for runway in runways:
            try:
                 airport_id = runway['id'].split()[0]
                 airport_groups[airport_id].append(runway)
            except (IndexError, AttributeError) as e:
                 print(f"Warning (Dialog Sort): Could not parse airport ID from runway ID '{runway.get('id', 'N/A')}': {e}")
                 airport_groups["Unknown"].append(runway)
        
        desired_airport_order = ['LTFM', 'LTFJ', 'LTBA']
        processed_airports = set()
        final_sorted_runways = []

        for airport_id in desired_airport_order:
            if airport_id in airport_groups:
                runway_list = sorted(airport_groups[airport_id], key=lambda x: x['id'])
                # Custom sort for LTFM
                if airport_id == 'LTFM':
                    rwy_0927 = None
                    temp_list = []
                    target_id_part = "09/27" 
                    for rwy in runway_list:
                        try:
                            rwy_id_part = rwy['id'].split(' ', 1)[1]
                            if rwy_id_part == target_id_part:
                                 rwy_0927 = rwy
                            else:
                                 temp_list.append(rwy)
                        except IndexError:
                            temp_list.append(rwy)
                    runway_list = temp_list
                    if rwy_0927:
                        runway_list.append(rwy_0927)
                final_sorted_runways.extend(runway_list)
                processed_airports.add(airport_id)

        remaining_airports = sorted([aid for aid in airport_groups if aid not in processed_airports])
        for airport_id in remaining_airports:
            runway_list = sorted(airport_groups[airport_id], key=lambda x: x['id'])
            final_sorted_runways.extend(runway_list)
            
        return final_sorted_runways

    def _setup_table(self):
        """Create the table widget to display runway options."""
        self.table = QTableWidget()
        self.table.setColumnCount(4) # Runway, Ends, Length, Style
        self.table.setHorizontalHeaderLabels(["Runway", "Show Centerline Ends", "Length (NM)", "Line Style"])
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        # Runway ID can stretch
        header.setSectionResizeMode(0, QHeaderView.Stretch) 
        # Give checkbox column enough space but allow stretch if needed (or fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents) 
        header.setMinimumSectionSize(100) # Minimum width for checkboxes
        # Length and Style columns
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        self.layout.addWidget(self.table)

    def _populate_table(self):
        """Fill the table with runway data and controls (using pre-sorted self.runways)."""
        if not self.runways:
            return 
            
        self.table.setRowCount(len(self.runways))
        line_styles = ["Solid", "Dashed", "Dotted", "Bold Solid"]

        for i, runway in enumerate(self.runways): 
            runway_id = runway.get('id', f"Unknown_{i}")
            # Extract end names
            try:
                 display_id_part = runway_id.split(' ', 1)[-1]
                 end1_name, end2_name = display_id_part.split('/')
                 display_id = f"{runway_id.split()[0]} {display_id_part}"
            except Exception:
                 display_id = runway_id 
                 end1_name = "End1" 
                 end2_name = "End2"
            key_end1 = f'show_{end1_name}'
            key_end2 = f'show_{end2_name}'
            
            # --- Widgets --- 
            le_length = QLineEdit()
            combo_style = QComboBox()
            cb_end1 = QCheckBox(end1_name) # Checkbox for the first end with name
            cb_end2 = QCheckBox(end2_name) # Checkbox for the second end with name
            
            # --- Configure Widgets --- 
            id_item = QTableWidgetItem(display_id)
            id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
            
            le_length.setValidator(QDoubleValidator(0.1, 100.0, 1))
            le_length.setText(str(runway.get('centerline_length', 15.0)))
            le_length.setFixedWidth(60)
            
            combo_style.addItems(line_styles)
            current_style = runway.get('centerline_style', "Dashed")
            if current_style in line_styles:
                combo_style.setCurrentText(current_style)
            combo_style.setFixedWidth(90)
                
            cb_end1.setChecked(runway.get(key_end1, False)) # Default to False
            cb_end2.setChecked(runway.get(key_end2, False)) # Default to False
            
            # Connect state changes to toggle controls
            cb_end1.stateChanged.connect(lambda state, c1=cb_end1, c2=cb_end2, le=le_length, cs=combo_style: \
                                         self._toggle_controls(c1, c2, le, cs))
            cb_end2.stateChanged.connect(lambda state, c1=cb_end1, c2=cb_end2, le=le_length, cs=combo_style: \
                                         self._toggle_controls(c1, c2, le, cs))
            
            # Initial enable/disable state based on checkboxes
            is_either_checked = cb_end1.isChecked() or cb_end2.isChecked()
            le_length.setEnabled(is_either_checked)
            combo_style.setEnabled(is_either_checked)

            # --- Create container for checkboxes --- 
            checkbox_container = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_container)
            checkbox_layout.addWidget(cb_end1)
            checkbox_layout.addWidget(cb_end2)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            checkbox_layout.setContentsMargins(0,0,0,0)
            checkbox_layout.setSpacing(5)

            # --- Add Widgets to Table --- 
            self.table.setItem(i, 0, id_item)
            self.table.setCellWidget(i, 1, checkbox_container) # Add container with checkboxes
            self.table.setCellWidget(i, 2, self._center_widget(le_length))
            self.table.setCellWidget(i, 3, self._center_widget(combo_style))
            
            # --- Store Widgets --- 
            self.widgets_by_runway[runway_id] = {
                'length': le_length,
                'style': combo_style,
                key_end1: cb_end1, 
                key_end2: cb_end2,
                'end1_name': end1_name,
                'end2_name': end2_name
            }
            
    def _center_widget(self, widget):
        """Helper to center a widget within a table cell."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.addWidget(widget)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0,0,0,0)
        container.setLayout(layout)
        return container
        
    def _toggle_controls(self, cb_end1, cb_end2, length_edit, style_combo):
        """Enable/disable dependent controls based on end checkboxes."""
        enabled = cb_end1.isChecked() or cb_end2.isChecked()
        length_edit.setEnabled(enabled)
        style_combo.setEnabled(enabled)

    def _setup_buttons(self):
        """Add OK and Cancel buttons."""
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonBox)

    def get_updated_runway_options(self):
        """Return the updated options for each runway."""
        updated_options = {}
        for runway_id, widgets in self.widgets_by_runway.items():
            try:
                 length = float(widgets['length'].text())
            except ValueError:
                 length = 15.0
                 
            end1_name = widgets.get('end1_name', 'End1')
            end2_name = widgets.get('end2_name', 'End2')
            key_end1 = f'show_{end1_name}'
            key_end2 = f'show_{end2_name}'
            
            show_end1_state = widgets.get(key_end1).isChecked() if key_end1 in widgets else False
            show_end2_state = widgets.get(key_end2).isChecked() if key_end2 in widgets else False
            
            # Determine overall show_centerline based on individual ends
            show_centerline = show_end1_state or show_end2_state
            
            options = {
                # Store the overall flag for potential use, though drawing uses specific flags
                'show_centerline': show_centerline, 
                'centerline_length': length,
                'centerline_style': widgets['style'].currentText(),
                key_end1: show_end1_state,
                key_end2: show_end2_state
            }
            updated_options[runway_id] = options
        return updated_options 