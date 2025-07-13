import math
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, 
                          QComboBox, QLabel, QLineEdit, QRadioButton, QCheckBox,
                          QDialogButtonBox, QStackedWidget, QButtonGroup, QWidget, QPushButton,
                          QFrame, QScrollArea, QMessageBox, QTabWidget, QSizePolicy)
from PyQt5.QtGui import QDoubleValidator, QIntValidator
from PyQt5.QtCore import Qt, pyqtSignal
import re # Import re for threshold extraction

from pointmerge import calculate_point_merge_waypoints, parse_dms, DMS, dms_to_decimal, decimal_to_dms

class PathExtensionDialog(QDialog):
    """Dialog for configuring a path extension from a runway"""
    # Signal emitted when pattern type changes
    patternChanged = pyqtSignal(bool)  # True for point-merge, False for trombone
    
    def __init__(self, all_runways, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Path Extension Configuration")
        # Store the full runway list
        self.all_runways = all_runways 
        # Filter runways that have at least one ARR or MIX threshold for the first dropdown
        self.eligible_runways_for_trombone = self._filter_runways_for_trombone(all_runways)
        self.setMinimumWidth(600)
        self.setMinimumHeight(700)

        # Initialize variables
        self.has_second_leg = False
        self.segment_distances = []
        self.segment_distances_second = []
        
        # Doğrulanmış konfigürasyon için değişken
        self.current_config = None
        self.validated_config = None

        self.main_layout = QVBoxLayout(self)
        self._setup_pattern_selector()
        self._setup_pattern_parameters()
        self._setup_dialog_buttons()

    def _filter_runways_for_trombone(self, all_runways):
        filtered = []
        for runway in all_runways:
            try:
                parts = runway['id'].split()
                if len(parts) < 2: continue
                thr_parts = parts[1].split('/')
                if len(thr_parts) < 2: continue
                thr1_name, thr2_name = thr_parts[0], thr_parts[1]
                
                thr1_key = f'type_{thr1_name}'
                thr2_key = f'type_{thr2_name}'

                # Check if *either* threshold is ARR or MIX
                type1 = runway.get(thr1_key, 'DEP') # Default to DEP if missing
                type2 = runway.get(thr2_key, 'DEP') # Default to DEP if missing
                
                if type1 in ['ARR', 'MIX'] or type2 in ['ARR', 'MIX']:
                    filtered.append(runway)
            except Exception as e:
                print(f"Warning: Error filtering runway {runway.get('id', 'N/A')} for trombone: {e}")
        return filtered

    def _setup_pattern_selector(self):
        """Setup pattern type selector section"""
        pattern_group = QGroupBox("Pattern Type")
        pattern_layout = QHBoxLayout()
        
        self.trombone_radio = QRadioButton("Trombone")
        self.pointmerge_radio = QRadioButton("Point-Merge")
        self.trombone_radio.setChecked(True)
        
        self.pattern_group = QButtonGroup()
        self.pattern_group.addButton(self.trombone_radio, 1)
        self.pattern_group.addButton(self.pointmerge_radio, 2)
        self.pattern_group.buttonClicked.connect(self.on_pattern_changed)
        
        pattern_layout.addWidget(self.trombone_radio)
        pattern_layout.addWidget(self.pointmerge_radio)
        pattern_group.setLayout(pattern_layout)
        self.main_layout.addWidget(pattern_group)

    def _setup_pattern_parameters(self):
        """Setup stacked widget with pattern-specific parameters"""
        self.stacked_widget = QStackedWidget()
        
        # Create parameter widgets
        self._setup_trombone_parameters()
        self._setup_pointmerge_parameters()
        
        # Add widgets to stacked widget
        self.stacked_widget.addWidget(self.trombone_widget)
        self.stacked_widget.addWidget(self.pointmerge_widget)
        
        self.main_layout.addWidget(self.stacked_widget)

    def _create_distance_input(self, default_value, min_val=0.0, max_val=100.0):
        """Helper to create a distance input with validator"""
        input_field = QLineEdit()
        validator = QDoubleValidator(min_val, max_val, 1)
        validator.setNotation(QDoubleValidator.StandardNotation)
        input_field.setValidator(validator)
        input_field.setText(str(default_value))
        
        # Sadece boş değerler için FocusOut event'ini bağla
        # 0 değerleri artık kabul edilebilir
        input_field.focusOutEvent = lambda event: self._validate_input_not_empty_or_zero(input_field, event, default_value)
        
        return input_field
        
    def _validate_input_not_empty_or_zero(self, input_field, event, default_value):
        """Input içeriğinin boş olmamasını sağla (0 değeri kabul edilebilir)"""
        # Standart FocusOut event işlemini çağır
        QLineEdit.focusOutEvent(input_field, event)
        
        # Sadece boş değerleri kontrol et, 0 değerlerine izin ver
        current_text = input_field.text().strip()
        if not current_text:
            input_field.setText(str(default_value))

    def _setup_trombone_parameters(self):
        """Setup trombone pattern parameters with two-step runway/threshold selection"""
        self.trombone_widget = QWidget()
        trombone_layout = QVBoxLayout(self.trombone_widget)
        
        # --- Runway and Threshold Selection Group ---
        runway_threshold_group = QGroupBox("Runway and Threshold")
        rt_layout = QGridLayout(runway_threshold_group) # Use grid for better alignment
        
        # Runway selection (First Dropdown)
        rt_layout.addWidget(QLabel("Runway:"), 0, 0)
        self.trombone_runway_combo = QComboBox()
        self.trombone_runway_combo.setMinimumWidth(150) # Give it some minimum width
        # Populate with eligible FULL runway IDs
        self.trombone_runway_combo.clear()
        if self.eligible_runways_for_trombone:
            # Add a placeholder item first
            self.trombone_runway_combo.addItem("-- Select Runway --", userData=None)
            for runway_data in self.eligible_runways_for_trombone:
                # Display the full ID (e.g., LTFM 36/18)
                # Store the full runway data dict as userData
                self.trombone_runway_combo.addItem(runway_data['id'], userData=runway_data)
        else:
            self.trombone_runway_combo.addItem("No eligible runways")
            self.trombone_runway_combo.setEnabled(False)
        rt_layout.addWidget(self.trombone_runway_combo, 0, 1)
            
        # Threshold selection (Second Dropdown)
        rt_layout.addWidget(QLabel("Approach Threshold:"), 1, 0)
        self.trombone_threshold_combo = QComboBox()
        self.trombone_threshold_combo.setMinimumWidth(100)
        self.trombone_threshold_combo.setEnabled(False) # Initially disabled
        self.trombone_threshold_combo.addItem("-- Select Runway First --")
        rt_layout.addWidget(self.trombone_threshold_combo, 1, 1)
        
        # Connect runway selection change to update threshold options
        self.trombone_runway_combo.currentIndexChanged.connect(self._update_threshold_options)
        
        # Add stretch to push elements to the left
        rt_layout.setColumnStretch(2, 1) 
        trombone_layout.addWidget(runway_threshold_group)

        # --- Threshold Distance ---
        # (Moved out of the runway selection group)
        threshold_dist_group = QGroupBox("Distance from Selected Threshold")
        threshold_dist_layout = QHBoxLayout(threshold_dist_group)
        threshold_dist_layout.addWidget(QLabel("Distance:"))
        self.threshold_input = self._create_distance_input(3.0)
        threshold_dist_layout.addWidget(self.threshold_input)
        threshold_dist_layout.addWidget(QLabel("NM"))
        threshold_dist_layout.addStretch() # Push to left
        trombone_layout.addWidget(threshold_dist_group)
        
        # --- Base Leg --- (No changes needed here)
        base_leg_group = QGroupBox("Base Leg")
        base_leg_layout = QHBoxLayout()
        
        # Angle input
        base_leg_layout.addWidget(QLabel("Angle from Centerline:"))
        self.base_angle_input = QLineEdit()
        self.base_angle_input.setValidator(QDoubleValidator(-180.0, 180.0, 1))
        self.base_angle_input.setText("90.0")
        base_leg_layout.addWidget(self.base_angle_input)
        base_leg_layout.addWidget(QLabel("°"))
        
        base_leg_layout.addSpacing(20)
        
        # Distance input
        base_leg_layout.addWidget(QLabel("Distance:"))
        self.base_input = self._create_distance_input(5.0)
        base_leg_layout.addWidget(self.base_input)
        base_leg_layout.addWidget(QLabel("NM"))
        base_leg_layout.addStretch() # Push to left
        
        base_leg_group.setLayout(base_leg_layout)
        trombone_layout.addWidget(base_leg_group)

        # --- Extension leg --- (No changes needed here)
        extension_group = QGroupBox("Extension Leg")
        extension_layout = QVBoxLayout()
        
        # Extension length
        length_layout = QHBoxLayout()
        length_layout.addWidget(QLabel("Length:")) # Add label for clarity
        self.extension_input = self._create_distance_input(3.0)
        length_layout.addWidget(self.extension_input)
        length_layout.addWidget(QLabel("NM"))
        length_layout.addStretch() # Push to left
        extension_layout.addLayout(length_layout)
        
        # --- REMOVE Extension direction --- 
        # direction_layout = QHBoxLayout()
        # self.direction_towards = QRadioButton("Towards Runway Centerline")
        # self.direction_away = QRadioButton("Away from Runway Centerline")
        # self.direction_towards.setChecked(True)
        # direction_layout.addWidget(self.direction_towards)
        # direction_layout.addWidget(self.direction_away)
        # direction_layout.addStretch() # Push to left
        # extension_layout.addLayout(direction_layout)
        
        extension_group.setLayout(extension_layout)
        trombone_layout.addWidget(extension_group)
        
        trombone_layout.addStretch() # Push all groups to the top

    def _update_threshold_options(self):
        self.trombone_threshold_combo.clear()
        selected_index = self.trombone_runway_combo.currentIndex()
        
        # Check if a valid runway (not the placeholder) is selected
        if selected_index <= 0: 
            self.trombone_threshold_combo.addItem("-- Select Runway First --")
            self.trombone_threshold_combo.setEnabled(False)
            return

        runway_data = self.trombone_runway_combo.itemData(selected_index)
        if not runway_data:
            self.trombone_threshold_combo.addItem("Error: Invalid Runway Data")
            self.trombone_threshold_combo.setEnabled(False)
            return            # Debug: Show the selected runway data
            print(f"Selected runway data: {runway_data}")

        try:
            parts = runway_data['id'].split()
            airport_name = parts[0]
            thr_parts = parts[1].split('/')
            thr1_name = thr_parts[0]
            thr2_name = thr_parts[1]

            eligible_thresholds_found = False
            
            # Check threshold 1
            thr1_key = f'type_{thr1_name}'
            type1 = runway_data.get(thr1_key, 'DEP') 
            if type1 in ['ARR', 'MIX']:
                # Store the threshold name and the original runway data
                self.trombone_threshold_combo.addItem(thr1_name, userData={'threshold': thr1_name, 'runway': runway_data})
                eligible_thresholds_found = True

            # Check threshold 2
            thr2_key = f'type_{thr2_name}'
            type2 = runway_data.get(thr2_key, 'DEP')
            if type2 in ['ARR', 'MIX']:
                self.trombone_threshold_combo.addItem(thr2_name, userData={'threshold': thr2_name, 'runway': runway_data})
                eligible_thresholds_found = True

            if eligible_thresholds_found:
                self.trombone_threshold_combo.setEnabled(True)
            else:
                # Should not happen if _filter_runways_for_trombone works correctly
                self.trombone_threshold_combo.addItem("No ARR/MIX Thresholds")
                self.trombone_threshold_combo.setEnabled(False)

        except Exception as e:
            print(f"Error processing runway {runway_data.get('id', 'N/A')} for thresholds: {e}")
            self.trombone_threshold_combo.addItem("Error Processing")
            self.trombone_threshold_combo.setEnabled(False)

    def _setup_pointmerge_parameters(self):
        """Setup point-merge pattern parameters with tabbed interface"""
        self.pointmerge_widget = QWidget()
        pointmerge_layout = QVBoxLayout(self.pointmerge_widget)
        
        # Create tab widget for point merge
        self.pointmerge_tab_widget = QTabWidget()
        pointmerge_layout.addWidget(self.pointmerge_tab_widget)
        
        # Create tabs
        self.pm_main_tab = QWidget()
        self.pm_second_leg_tab = QWidget()
        self.pm_segment_tab = QWidget()
        self.pm_connections_tab = QWidget()
        
        # Setup layouts for each tab
        self.pm_main_tab_layout = QVBoxLayout(self.pm_main_tab)
        self.pm_second_leg_tab_layout = QVBoxLayout(self.pm_second_leg_tab)
        self.pm_segment_tab_layout = QVBoxLayout(self.pm_segment_tab)
        self.pm_connections_tab_layout = QVBoxLayout(self.pm_connections_tab)
        
        # Add tabs to widget
        self.pointmerge_tab_widget.addTab(self.pm_main_tab, "Main Leg")
        self.pointmerge_tab_widget.addTab(self.pm_second_leg_tab, "Second Leg")
        self.pointmerge_tab_widget.addTab(self.pm_segment_tab, "Segment Distances")
        self.pointmerge_tab_widget.addTab(self.pm_connections_tab, "Connections")
        
        # Connect tab changed signal to automatically create segment distances when tab is selected
        self.pointmerge_tab_widget.currentChanged.connect(self._on_tab_selection_changed)
        
        # ---- Main Leg Tab ----
        
        # Merge Point Parameters section
        merge_group = QGroupBox("Merge Point Parameters")
        merge_layout = QVBoxLayout()
        
        # Latitude input
        lat_container = QHBoxLayout()
        lat_container.addWidget(QLabel("Latitude:"))
        
        self.merge_lat_d = QLineEdit()
        self.merge_lat_d.setValidator(QIntValidator(0, 90))
        self.merge_lat_d.setFixedWidth(50)
        lat_container.addWidget(self.merge_lat_d)
        
        lat_container.addWidget(QLabel("°"))
        
        self.merge_lat_m = QLineEdit()
        self.merge_lat_m.setValidator(QIntValidator(0, 59))
        self.merge_lat_m.setFixedWidth(40)
        lat_container.addWidget(self.merge_lat_m)
        
        lat_container.addWidget(QLabel("'"))
        
        self.merge_lat_s = QLineEdit()
        self.merge_lat_s.setValidator(QDoubleValidator(0.0, 59.999, 3))
        self.merge_lat_s.setFixedWidth(70)
        lat_container.addWidget(self.merge_lat_s)
        
        lat_container.addWidget(QLabel("\""))
        
        self.merge_lat_dir = QComboBox()
        self.merge_lat_dir.addItems(["N", "S"])
        self.merge_lat_dir.setFixedWidth(50)
        lat_container.addWidget(self.merge_lat_dir)
        
        lat_container.addStretch()
        merge_layout.addLayout(lat_container)
        
        # Longitude input
        lon_container = QHBoxLayout()
        lon_container.addWidget(QLabel("Longitude:"))
        
        self.merge_lon_d = QLineEdit()
        self.merge_lon_d.setValidator(QIntValidator(0, 180))
        self.merge_lon_d.setFixedWidth(50)
        lon_container.addWidget(self.merge_lon_d)
        
        lon_container.addWidget(QLabel("°"))
        
        self.merge_lon_m = QLineEdit()
        self.merge_lon_m.setValidator(QIntValidator(0, 59))
        self.merge_lon_m.setFixedWidth(40)
        lon_container.addWidget(self.merge_lon_m)
        
        lon_container.addWidget(QLabel("'"))
        
        self.merge_lon_s = QLineEdit()
        self.merge_lon_s.setValidator(QDoubleValidator(0.0, 59.999, 3))
        self.merge_lon_s.setFixedWidth(70)
        lon_container.addWidget(self.merge_lon_s)
        
        lon_container.addWidget(QLabel("\""))
        
        self.merge_lon_dir = QComboBox()
        self.merge_lon_dir.addItems(["E", "W"])
        self.merge_lon_dir.setFixedWidth(50)
        lon_container.addWidget(self.merge_lon_dir)
        
        lon_container.addStretch()
        merge_layout.addLayout(lon_container)

        merge_group.setLayout(merge_layout)
        self.pm_main_tab_layout.addWidget(merge_group)
        
        # Sequencing Leg Parameters section
        main_leg_group = QGroupBox("Sequencing Leg Parameters")
        main_leg_layout = QGridLayout()
        
        main_leg_layout.addWidget(QLabel("Distance from Merge Point (NM):"), 0, 0)
        self.first_point_distance = self._create_distance_input(15.0, 5.0, 50.0)
        main_leg_layout.addWidget(self.first_point_distance, 0, 1)
        
        main_leg_layout.addWidget(QLabel("Track Angle from Merge Point (°):"), 1, 0)
        self.track_angle = QLineEdit()
        self.track_angle.setValidator(QDoubleValidator(0.0, 360.0, 1))
        self.track_angle.setText("90")
        main_leg_layout.addWidget(self.track_angle, 1, 1)
        
        main_leg_layout.addWidget(QLabel("Number of Segments:"), 2, 0)
        self.num_segments = QLineEdit()
        self.num_segments.setValidator(QIntValidator(1, 20))
        self.num_segments.setText("5")
        main_leg_layout.addWidget(self.num_segments, 2, 1)
        
        main_leg_group.setLayout(main_leg_layout)
        self.pm_main_tab_layout.addWidget(main_leg_group)
        
        # Arc Direction section
        direction_group = QGroupBox("Arc Direction")
        direction_layout = QHBoxLayout()
        
        self.clockwise_radio = QRadioButton("Clockwise")
        self.counter_clockwise_radio = QRadioButton("Counter-Clockwise")
        
        # Set default
        self.clockwise_radio.setChecked(True)
        
        # Add to layout
        direction_layout.addWidget(self.clockwise_radio)
        direction_layout.addWidget(self.counter_clockwise_radio)
        
        direction_group.setLayout(direction_layout)
        self.pm_main_tab_layout.addWidget(direction_group)
        
        # ---- Second Leg Tab ----
        
        # Second Sequencing Leg section
        second_leg_group = QGroupBox("Second Sequencing Leg")
        second_leg_layout = QVBoxLayout()
        
        self.enable_second_leg = QCheckBox("Enable Second Leg")
        self.enable_second_leg.stateChanged.connect(self._toggle_second_leg)
        second_leg_layout.addWidget(self.enable_second_leg)
        
        # Container for second leg options
        self.second_leg_options = QWidget()
        second_leg_options_layout = QGridLayout(self.second_leg_options)
        
        second_leg_options_layout.addWidget(QLabel("Leg Type:"), 0, 0)
        self.leg_type = QComboBox()
        self.leg_type.addItems(["Inner", "Outer"])
        second_leg_options_layout.addWidget(self.leg_type, 0, 1)
        
        second_leg_options_layout.addWidget(QLabel("Distance Between Legs (NM):"), 1, 0)
        self.leg_distance = QLineEdit()
        self.leg_distance.setValidator(QDoubleValidator(0.1, 100.0, 1))
        self.leg_distance.setText("5.0")
        second_leg_options_layout.addWidget(self.leg_distance, 1, 1)
        
        second_leg_options_layout.addWidget(QLabel("Number of Segments:"), 2, 0)
        self.num_segments_second = QLineEdit()
        self.num_segments_second.setValidator(QIntValidator(1, 20))
        self.num_segments_second.setText("5")
        second_leg_options_layout.addWidget(self.num_segments_second, 2, 1)
        
        # Hide second leg options initially
        self.second_leg_options.setVisible(False)
        second_leg_layout.addWidget(self.second_leg_options)
        
        second_leg_group.setLayout(second_leg_layout)
        self.pm_second_leg_tab_layout.addWidget(second_leg_group)
        
        # ---- Segment Distances Tab ----
        
        # Segment Distances section
        segment_group = QGroupBox("Segment Distances")
        segment_layout = QVBoxLayout()
        segment_layout.setSpacing(5)  # Reduce overall vertical spacing
        
        # Container for segment distance inputs
        self.segments_container = QHBoxLayout()
        self.segments_container.setSpacing(10)  # Reduce spacing between containers
        
        # First leg segment container with scroll area
        self.first_leg_segment_container = QGroupBox("Main Leg")
        first_leg_container_layout = QVBoxLayout(self.first_leg_segment_container)
        first_leg_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create scroll area for first leg
        first_leg_scroll = QScrollArea()
        first_leg_scroll.setWidgetResizable(True)
        first_leg_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        first_leg_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        first_leg_container_layout.addWidget(first_leg_scroll)
        
        # Create content widget for scroll area
        first_leg_content = QWidget()
        self.first_leg_segment_layout = QVBoxLayout(first_leg_content)
        self.first_leg_segment_layout.setSpacing(3)  # Reduce spacing between segment inputs
        self.first_leg_segment_layout.setAlignment(Qt.AlignTop)  # Align to top
        
        # Add content widget to scroll area
        first_leg_scroll.setWidget(first_leg_content)
        
        # Configure sizing
        self.first_leg_segment_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.segments_container.addWidget(self.first_leg_segment_container, 1)  # Equal width (stretch factor 1)
        
        # Second leg segment container with scroll area
        self.second_leg_segment_container = QGroupBox("Second Leg")
        second_leg_container_layout = QVBoxLayout(self.second_leg_segment_container)
        second_leg_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create scroll area for second leg
        second_leg_scroll = QScrollArea()
        second_leg_scroll.setWidgetResizable(True)
        second_leg_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        second_leg_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        second_leg_container_layout.addWidget(second_leg_scroll)
        
        # Create content widget for scroll area
        second_leg_content = QWidget()
        self.second_leg_segment_layout = QVBoxLayout(second_leg_content)
        self.second_leg_segment_layout.setSpacing(3)  # Reduce spacing between segment inputs
        self.second_leg_segment_layout.setAlignment(Qt.AlignTop)  # Align to top
        
        # Add content widget to scroll area
        second_leg_scroll.setWidget(second_leg_content)
        
        # Configure sizing
        self.second_leg_segment_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.segments_container.addWidget(self.second_leg_segment_container, 1)  # Equal width (stretch factor 1)
        
        segment_layout.addLayout(self.segments_container)
        segment_group.setLayout(segment_layout)
        self.pm_segment_tab_layout.addWidget(segment_group)
        
        # ---- Connections Tab ----
        
        # Define Connections section
        connections_group = QGroupBox("Define Connections")
        connections_layout = QVBoxLayout()
        
        # Main and second leg connections
        leg_connections_layout = QHBoxLayout()
        
        # Main leg connections
        main_leg_conn_layout = QVBoxLayout()
        main_leg_conn_layout.addWidget(QLabel("Main Leg Connections:"))
        
        self.connect_merge_main_start = QCheckBox("Merge Point to Start")
        main_leg_conn_layout.addWidget(self.connect_merge_main_start)
        
        self.connect_merge_main_end = QCheckBox("Merge Point to End")
        main_leg_conn_layout.addWidget(self.connect_merge_main_end)
        
        leg_connections_layout.addLayout(main_leg_conn_layout)
        
        # Second leg connections
        second_leg_conn_layout = QVBoxLayout()
        second_leg_conn_layout.addWidget(QLabel("Second Leg Connections:"))
        
        self.connect_merge_second_start = QCheckBox("Merge Point to Start")
        second_leg_conn_layout.addWidget(self.connect_merge_second_start)
        
        self.connect_merge_second_end = QCheckBox("Merge Point to End")
        second_leg_conn_layout.addWidget(self.connect_merge_second_end)
        
        leg_connections_layout.addLayout(second_leg_conn_layout)
        
        connections_layout.addLayout(leg_connections_layout)
        
        # Between legs connections
        between_legs_layout = QVBoxLayout()
        between_legs_layout.addWidget(QLabel("Connect Between Legs:"))
        
        between_legs_checkboxes = QHBoxLayout()
        self.connect_legs_start = QCheckBox("Start to Start")
        between_legs_checkboxes.addWidget(self.connect_legs_start)
        
        self.connect_legs_end = QCheckBox("End to End")
        between_legs_checkboxes.addWidget(self.connect_legs_end)
        
        between_legs_layout.addLayout(between_legs_checkboxes)
        connections_layout.addLayout(between_legs_layout)
        
        connections_group.setLayout(connections_layout)
        self.pm_connections_tab_layout.addWidget(connections_group)

    def _toggle_second_leg(self, state):
        """Toggle visibility of second leg options"""
        self.has_second_leg = (state == Qt.Checked)
        self.second_leg_options.setVisible(self.has_second_leg)
        
        # Hide/show second leg segment container if it exists
        if hasattr(self, 'second_leg_segment_container'):
            self.second_leg_segment_container.setVisible(self.has_second_leg)

    def _create_segment_distance_inputs(self):
        """Create input fields for segment distances"""
        # Clear existing segment inputs
        for layout in [self.first_leg_segment_layout, self.second_leg_segment_layout]:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        
        # Get number of segments for first leg
        try:
            if not self.num_segments.text():
                # Create at least one segment if num_segments is empty
                self.segment_distances = []
                return
            
            num_segments_first = int(self.num_segments.text())
            if num_segments_first <= 0:
                num_segments_first = 1  # Always create at least one segment
            
            # Create input fields for first leg
            self.segment_distances = []
            for i in range(num_segments_first):
                segment_layout = QHBoxLayout()
                segment_layout.setSpacing(5)  # Reduce horizontal spacing
                
                # Create label with fixed width - increased to fit two-digit numbers
                segment_label = QLabel(f"Segment {i+1}:")
                segment_label.setFixedWidth(100)  # Increased from 80 to 100
                segment_layout.addWidget(segment_label)
                
                # Create input field with reduced width
                distance_input = QLineEdit()
                # Use more permissive validator to handle different number formats
                validator = QDoubleValidator(0.1, 100.0, 2)
                validator.setNotation(QDoubleValidator.StandardNotation)
                distance_input.setValidator(validator)
                distance_input.setFixedWidth(80)  # Reduced from 100 to 80
                # Default to a reasonable value to avoid empty fields
                distance_input.setText("5.0")  
                segment_layout.addWidget(distance_input)
                
                nm_label = QLabel("NM")
                nm_label.setFixedWidth(30)
                segment_layout.addWidget(nm_label)
                
                # Add stretch to align items to the left
                segment_layout.addStretch()
                
                self.first_leg_segment_layout.addLayout(segment_layout)
                self.segment_distances.append(distance_input)
            
            # Create input fields for second leg if enabled
            if self.has_second_leg:
                if not self.num_segments_second.text():
                    # Create at least one segment if num_segments_second is empty
                    self.segment_distances_second = []
                    return
                
                num_segments_second = int(self.num_segments_second.text())
                if num_segments_second <= 0:
                    num_segments_second = 1  # Always create at least one segment
                
                # Create input fields
                self.segment_distances_second = []
                for i in range(num_segments_second):
                    segment_layout = QHBoxLayout()
                    segment_layout.setSpacing(5)  # Reduce horizontal spacing
                    
                    # Create label with fixed width - increased to fit two-digit numbers
                    segment_label = QLabel(f"Segment {i+1}:")
                    segment_label.setFixedWidth(100)  # Increased from 80 to 100
                    segment_layout.addWidget(segment_label)
                    
                    # Create input field with reduced width
                    distance_input = QLineEdit()
                    # Use more permissive validator to handle different number formats
                    validator = QDoubleValidator(0.1, 100.0, 2)
                    validator.setNotation(QDoubleValidator.StandardNotation)
                    distance_input.setValidator(validator)
                    distance_input.setFixedWidth(80)  # Reduced from 100 to 80
                    # Default to a reasonable value to avoid empty fields
                    distance_input.setText("5.0")
                    segment_layout.addWidget(distance_input)
                    
                    nm_label = QLabel("NM")
                    nm_label.setFixedWidth(30)
                    segment_layout.addWidget(nm_label)
                    
                    # Add stretch to align items to the left
                    segment_layout.addStretch()
                    
                    self.second_leg_segment_layout.addLayout(segment_layout)
                    self.segment_distances_second.append(distance_input)
                
                # Show/hide second leg segment container based on checkbox
                self.second_leg_segment_container.setVisible(self.has_second_leg)
            
        except ValueError as e:
            # Log error but continue with default values
            print(f"Error in _create_segment_distance_inputs: {str(e)}")
            # Ensure segments are created even in error case
            if not hasattr(self, 'segment_distances') or not self.segment_distances:
                self.segment_distances = []
        except Exception as e:
            # Log error but continue with default values
            print(f"Error in _create_segment_distance_inputs: {str(e)}")
            # Ensure segments are created even in error case
            if not hasattr(self, 'segment_distances') or not self.segment_distances:
                self.segment_distances = []

    def _setup_dialog_buttons(self):
        """Setup dialog buttons"""
        self.buttonBox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        
        # Connect directly to accept/reject - we'll override accept to add validation
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        
        self.main_layout.addWidget(self.buttonBox)
    
    def accept(self):
        """Override accept to validate inputs before accepting dialog"""
        try:
            # Önce yapılandırmayı al ve doğrula
            self.validated_config = None
            
            if self.pointmerge_radio.isChecked():
                # Point-merge için tüm girdileri doğrula
                # Segment distance girdilerinin oluşturulmasını zorla - bu kritik
                self._create_segment_distance_inputs()
                    
                # Sonra girdileri doğrula
                if not self._validate_point_merge_inputs():
                    # Doğrulama başarısızsa kabul etme
                    return # Dialog'da kal
                
                # For point merge, save the configuration if validation passed
                self.validated_config = self.get_configuration()
                if not self.validated_config:
                    QMessageBox.warning(self, "Configuration Error", 
                                       "Configuration was validated but could not be created. Please check all values.")
                    return # Stay in dialog
            elif self.trombone_radio.isChecked():
                # Trombone pattern için detaylı doğrulama
                
                # 1. Pist seçimini kontrol et
                runway_index = self.trombone_runway_combo.currentIndex()
                if runway_index <= 0 or not self.trombone_runway_combo.itemData(runway_index):
                    QMessageBox.warning(self, "Runway Error", "Please select a valid runway. If there are no runways in the list, there may not be any runway with ARR or MIX type thresholds in the configuration files.")
                    self.trombone_runway_combo.setFocus()
                    # Disable threshold selection if no runway is selected
                    self.trombone_threshold_combo.clear()
                    self.trombone_threshold_combo.addItem("-- Select Runway First --")
                    self.trombone_threshold_combo.setEnabled(False)
                    return # Stay in dialog
                
                # 2. Eşik seçimini kontrol et
                threshold_index = self.trombone_threshold_combo.currentIndex()
                # İndeks > -1 VE etkin olup olmadığını kontrol et (geçerli seçenekler doldurulmuş anlamına gelir)
                if threshold_index < 0 or not self.trombone_threshold_combo.isEnabled(): 
                    QMessageBox.warning(self, "Threshold Error", "Please select an approach threshold. If there are no thresholds in the list, the selected runway may not have any ARR or MIX type thresholds.")
                    self.trombone_threshold_combo.setFocus()
                    return # Stay in dialog
                
                # Additional validation for threshold selection
                selected_threshold_data = self.trombone_threshold_combo.currentData()
                if not selected_threshold_data:
                    QMessageBox.warning(self, "Threshold Data Error", "Invalid threshold selection. Please select a valid approach threshold.")
                    self.trombone_threshold_combo.setFocus()
                    return # Stay in dialog
                
                # 3. Sayısal alan doğrulamaları
                
                # 3.1. Distance from Threshold kontrolü
                threshold_distance_text = self.threshold_input.text().strip()
                if not threshold_distance_text:
                    QMessageBox.warning(self, "Distance Error", "Please enter a distance from threshold value.")
                    self.threshold_input.setFocus()
                    self.threshold_input.selectAll()
                    return # Stay in dialog
                
                # Numeric value check - zero values are now acceptable
                try:
                    threshold_distance_value = float(threshold_distance_text)
                except ValueError:
                    QMessageBox.warning(self, "Format Error", "Please enter a valid numeric value for the distance from threshold.")
                    self.threshold_input.setFocus()
                    self.threshold_input.selectAll()
                    return # Stay in dialog
                
                # 3.2. Base angle kontrolü
                base_angle_text = self.base_angle_input.text().strip()
                if not base_angle_text:
                    QMessageBox.warning(self, "Angle Error", "Please enter an angle value for the base leg.")
                    self.base_angle_input.setFocus()
                    self.base_angle_input.selectAll()
                    return # Stay in dialog
                
                # Numeric value and range check for the angle
                try:
                    base_angle_value = float(base_angle_text)
                    if base_angle_value < -180 or base_angle_value > 180:
                        QMessageBox.warning(self, "Angle Error", "Base leg angle must be between -180° and +180°.")
                        self.base_angle_input.setFocus()
                        self.base_angle_input.selectAll()
                        return # Stay in dialog
                except ValueError:
                    QMessageBox.warning(self, "Format Error", "Please enter a valid numeric value for the base leg angle.")
                    self.base_angle_input.setFocus()
                    self.base_angle_input.selectAll()
                    return # Stay in dialog
                    
                # 3.3. Base distance check
                base_distance_text = self.base_input.text().strip()
                if not base_distance_text:
                    QMessageBox.warning(self, "Distance Error", "Please enter a distance value for the base leg.")
                    self.base_input.setFocus()
                    self.base_input.selectAll()
                    return # Stay in dialog
                
                # Numeric value check - zero values are now acceptable
                try:
                    base_distance_value = float(base_distance_text)
                except ValueError:
                    QMessageBox.warning(self, "Format Error", "Please enter a valid numeric value for the base leg distance.")
                    self.base_input.setFocus()
                    self.base_input.selectAll()
                    return # Stay in dialog
                    
                # 3.4. Extension length check
                extension_length_text = self.extension_input.text().strip()
                if not extension_length_text:
                    QMessageBox.warning(self, "Length Error", "Please enter a length value for the extension leg.")
                    self.extension_input.setFocus()
                    self.extension_input.selectAll()
                    return # Stay in dialog
                
                # Numeric value check - zero values are now acceptable
                try:
                    extension_length_value = float(extension_length_text)
                except ValueError:
                    QMessageBox.warning(self, "Format Error", "Please enter a valid numeric value for the extension leg length.")
                    self.extension_input.setFocus()
                    self.extension_input.selectAll()
                    return # Stay in dialog
                
                # For trombone, save the configuration if validation passed
                self.validated_config = self.get_configuration()
                if not self.validated_config:
                    QMessageBox.warning(self, "Configuration Error", 
                                       "Configuration was validated but could not be created. Please check all values.")
                    return # Stay in dialog

            # If validation was successful and configuration was obtained,
            # save the configuration for use by the on_path_extension_accepted() method
            self.current_config = self.validated_config
            
            # If validation passed for the selected model type, call the parent's accept method
            super().accept()
        except Exception as e:
            # Log the error and show a message instead of crashing
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Unexpected Error", f"An unexpected error occurred during validation: {str(e)}")
            # Don't accept the dialog in case of an unexpected error
            return 

    def get_configuration(self):
        """Return the path extension configuration based on selected pattern type"""
        try:
            if self.trombone_radio.isChecked():
                # Get selected threshold data (contains threshold name and original runway dict)
                runway_index = self.trombone_runway_combo.currentIndex()
                threshold_index = self.trombone_threshold_combo.currentIndex()
                
                # Tüm temel doğrulama kontrollerini yap
                if runway_index <= 0 or not self.trombone_runway_combo.itemData(runway_index):
                    QMessageBox.warning(self, "Configuration Error", "Geçerli bir pist seçmelisiniz.")
                    self.trombone_runway_combo.setFocus()
                    return None
                
                if threshold_index < 0 or not self.trombone_threshold_combo.isEnabled():
                    QMessageBox.warning(self, "Configuration Error", "Geçerli bir yaklaşma eşiği seçmelisiniz.")
                    self.trombone_threshold_combo.setFocus()
                    return None
                    
                selected_threshold_data = self.trombone_threshold_combo.currentData()
                
                if not selected_threshold_data:
                    QMessageBox.warning(self, "Configuration Error", "Seçilen eşik verileri geçerli değil.")
                    self.trombone_threshold_combo.setFocus()
                    return None
                    
                runway_data = selected_threshold_data['runway']
                selected_threshold_name = selected_threshold_data['threshold']

                # --- Determine correct start/end coordinates based on selected threshold ---
                start_lat, start_lon, end_lat, end_lon = None, None, None, None
                
                # Extract threshold names from the original runway ID
                parts = runway_data['id'].split()
                thr_parts = parts[1].split('/')
                thr1_name = thr_parts[0]
                # thr2_name = thr_parts[1] # Don't strictly need thr2_name here

                # If the selected threshold name matches the *first* threshold name in the ID
                if selected_threshold_name == thr1_name:
                    # The 'start' coords of the runway object ARE the coords for this threshold
                    start_lat = runway_data['start_lat']
                    start_lon = runway_data['start_lon']
                    # The 'end' coords are the coords of the *other* threshold (used for direction)
                    end_lat = runway_data['end_lat']
                    end_lon = runway_data['end_lon']
                else: # Otherwise, the selected threshold must be the *second* one
                    # The 'end' coords of the runway object ARE the coords for this threshold
                    start_lat = runway_data['end_lat']
                    start_lon = runway_data['end_lon']
                     # The 'start' coords are the coords of the *other* threshold (used for direction)
                    end_lat = runway_data['start_lat']
                    end_lon = runway_data['start_lon']
                    
                if start_lat is None: # Should not happen if validation passed
                     QMessageBox.critical(self, "Error", f"Could not determine coordinates for selected threshold '{selected_threshold_name}'.")
                     return None

                # Construct the data dictionary needed by calculate_trombone_waypoints
                # It expects a 'runway'-like dict with oriented start/end coords
                approach_data = {
                    'id': f"{parts[0]} {selected_threshold_name}", # ID for the specific approach
                    'start_lat': start_lat,
                    'start_lon': start_lon,
                    'end_lat': end_lat, 
                    'end_lon': end_lon
                }

                # Trombone parametrelerini kontrol et ve geçerli sayısal değerler olduğundan emin ol
                threshold_distance = self.threshold_input.text().strip()
                base_angle = self.base_angle_input.text().strip()
                base_distance = self.base_input.text().strip()
                extension_length = self.extension_input.text().strip()
                
                # Sayısal değerleri kontrol et - daha detaylı hata mesajlarıyla
                try:
                    # Sayısal alan kontrolü
                    if not threshold_distance:
                        QMessageBox.warning(self, "Configuration Error", "Eşikten uzaklık değeri belirtilmemiş.")
                        self.threshold_input.setFocus()
                        return None
                        
                    if not base_angle:
                        QMessageBox.warning(self, "Configuration Error", "Taban kolu açı değeri belirtilmemiş.")
                        self.base_angle_input.setFocus()
                        return None
                        
                    if not base_distance:
                        QMessageBox.warning(self, "Configuration Error", "Taban kolu uzaklık değeri belirtilmemiş.")
                        self.base_input.setFocus()
                        return None
                        
                    if not extension_length:
                        QMessageBox.warning(self, "Configuration Error", "Uzatma kolu uzunluk değeri belirtilmemiş.")
                        self.extension_input.setFocus()
                        return None
                        
                    # Sayısal dönüşüm kontrolü
                    threshold_distance_float = float(threshold_distance)
                    base_angle_float = float(base_angle)
                    base_distance_float = float(base_distance)
                    extension_length_float = float(extension_length)
                    
                    # Sadece açı değerinin -180 ile 180 arasında olup olmadığını kontrol et
                    # Not: Artık uzaklık değerleri için minimum sınır kontrolü yapmıyoruz, 0 değeri kabul edilebilir
                    if base_angle_float < -180 or base_angle_float > 180:
                        QMessageBox.warning(self, "Configuration Error", "Taban kolu açısı -180° ile +180° arasında olmalıdır.")
                        self.base_angle_input.setFocus()
                        self.base_angle_input.selectAll()
                        return None
                        
                except ValueError:
                    QMessageBox.warning(self, "Format Error", "Tüm trombone parametreleri geçerli sayılar olmalıdır.")
                    return None
                
                return {
                    'pattern_type': 'trombone',
                    # Pass the oriented approach data instead of the full runway object
                    'runway': approach_data, 
                    'threshold_distance': threshold_distance_float,
                    'base_angle': base_angle_float,
                    'base_distance': base_distance_float,
                    'extension_length': extension_length_float,
                }
            else:
                # Point merge configuration - don't validate here, already done in accept()
                # Safety check for empty fields
                if (not self.track_angle.text().strip() or 
                    not self.first_point_distance.text().strip() or
                    not self.num_segments.text().strip() or
                    not hasattr(self, 'segment_distances') or 
                    len(self.segment_distances) == 0):
                    return None
                
                # Get segment distances for first leg - with safety check
                first_leg_segments = []
                for input_field in self.segment_distances:
                    text = input_field.text().strip()
                    if text:
                        first_leg_segments.append(float(text))
                    else:
                        first_leg_segments.append(0.0)
                
                # Get merge point coordinates
                try:
                    merge_coords = self._get_merge_point_coords()
                except ValueError:
                    # Don't show message here - already handled in accept()
                    return None
                
                # Get second leg configuration if enabled
                second_leg_config = None
                if self.has_second_leg:
                    if not self.leg_distance.text():
                        return None
                    
                    leg_distance = float(self.leg_distance.text() or 0)
                    is_inner = self.leg_type.currentText() == "Inner"
                    
                    # Get second leg segments with safety check
                    second_leg_segments = []
                    if hasattr(self, 'segment_distances_second'):
                        for input_field in self.segment_distances_second:
                            text = input_field.text().strip()
                            if text:
                                second_leg_segments.append(float(text))
                            else:
                                second_leg_segments.append(0.0)
                    
                    second_leg_config = {
                        'type': self.leg_type.currentText().lower(),
                        'distance': leg_distance,
                        'segments': second_leg_segments
                    }
                
                # Create configuration with safety checks
                config = {
                    'pattern_type': 'pointmerge',
                    'first_point_distance': float(self.first_point_distance.text() or 0),
                    'track_angle': float(self.track_angle.text() or 0),
                    'num_segments': int(self.num_segments.text() or 0),
                    'segments': first_leg_segments,
                    'clockwise': self.clockwise_radio.isChecked(),
                    'second_leg': second_leg_config,
                    'connections': {
                        'merge_to_main_start': self.connect_merge_main_start.isChecked(),
                        'merge_to_main_end': self.connect_merge_main_end.isChecked(),
                        'merge_to_second_start': self.connect_merge_second_start.isChecked() and self.has_second_leg,
                        'merge_to_second_end': self.connect_merge_second_end.isChecked() and self.has_second_leg,
                        'legs_start_to_start': self.connect_legs_start.isChecked() and self.has_second_leg,
                        'legs_end_to_end': self.connect_legs_end.isChecked() and self.has_second_leg
                    },
                    'merge_lat': merge_coords[0],
                    'merge_lon': merge_coords[1]
                }
                
                return config
        except ValueError as e:
            QMessageBox.warning(self, "Input Error", f"Invalid numeric input: {e}")
            return None
        except Exception as e:
            # Log the error and show a message instead of crashing
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"An unexpected error occurred getting configuration: {str(e)}")
            return None

    def on_pattern_changed(self, button):
        """Handle pattern type change"""
        is_point_merge = button == self.pointmerge_radio
        self.stacked_widget.setCurrentIndex(1 if is_point_merge else 0)
        
        # Reset to first tab if switching to point-merge
        if is_point_merge:
            # Make sure we start at the first tab
            self.pointmerge_tab_widget.setCurrentIndex(0)
        
        # Emit signal to notify of pattern type change
        self.patternChanged.emit(is_point_merge)

    def _validate_point_merge_inputs(self):
        """Validate all point-merge inputs before calculation"""
        # Check merge point coordinates
        if not all([
            self.merge_lat_d.text(),
            self.merge_lat_m.text(),
            self.merge_lat_s.text(),
            self.merge_lon_d.text(),
            self.merge_lon_m.text(),
            self.merge_lon_s.text()
        ]):
            QMessageBox.warning(self, "Input Error", "Please enter complete merge point coordinates")
            # Focus on the first empty field
            if not self.merge_lat_d.text():
                self.merge_lat_d.setFocus()
            elif not self.merge_lat_m.text():
                self.merge_lat_m.setFocus()
            elif not self.merge_lat_s.text():
                self.merge_lat_s.setFocus()
            elif not self.merge_lon_d.text():
                self.merge_lon_d.setFocus()
            elif not self.merge_lon_m.text():
                self.merge_lon_m.setFocus()
            elif not self.merge_lon_s.text():
                self.merge_lon_s.setFocus()
            return False
        
        # Check first leg parameters
        if not self.first_point_distance.text():
            QMessageBox.warning(self, "Input Error", "Please enter distance from merge point")
            self.first_point_distance.setFocus()
            return False
        
        if not self.track_angle.text():
            QMessageBox.warning(self, "Input Error", "Please enter track angle from merge point")
            self.track_angle.setFocus()
            return False
        
        if not self.num_segments.text():
            QMessageBox.warning(self, "Input Error", "Please enter number of segments for main leg")
            self.num_segments.setFocus()
            return False
        
        # Check segment distances for first leg
        if not hasattr(self, 'segment_distances') or not self.segment_distances:
            QMessageBox.warning(self, "Input Error", "Please set segment distances for main leg")
            # Switch to segment distances tab
            self.pointmerge_tab_widget.setCurrentIndex(2)
            return False
        
        # Check for empty segment distances with improved validation
        empty_fields = []
        empty_field_index = -1
        for i, input_field in enumerate(self.segment_distances):
            if not input_field.text().strip():
                empty_fields.append(i+1)
                if empty_field_index == -1:
                    empty_field_index = i
        
        if empty_fields:
            if len(empty_fields) == 1:
                QMessageBox.warning(self, "Input Error", f"Please enter distance for segment {empty_fields[0]} of main leg")
            else:
                QMessageBox.warning(self, "Input Error", f"Please enter distances for segments {', '.join(map(str, empty_fields))} of main leg")
            
            # Switch to segment distances tab and focus on first empty field
            self.pointmerge_tab_widget.setCurrentIndex(2)
            if empty_field_index >= 0:
                self.segment_distances[empty_field_index].setFocus()
            return False
        
        # Check second leg parameters if enabled
        if self.has_second_leg:
            if not self.leg_distance.text():
                QMessageBox.warning(self, "Input Error", "Please enter distance between legs")
                # Switch to second leg tab
                self.pointmerge_tab_widget.setCurrentIndex(1)
                self.leg_distance.setFocus()
                return False
            
            if not self.num_segments_second.text():
                QMessageBox.warning(self, "Input Error", "Please enter number of segments for second leg")
                # Switch to second leg tab
                self.pointmerge_tab_widget.setCurrentIndex(1)
                self.num_segments_second.setFocus()
                return False
            
            # Check segment distances for second leg
            if not hasattr(self, 'segment_distances_second') or not self.segment_distances_second:
                QMessageBox.warning(self, "Input Error", "Please set segment distances for second leg")
                # Switch to segment distances tab
                self.pointmerge_tab_widget.setCurrentIndex(2)
                return False
            
            # Check for empty segment distances with improved validation
            empty_fields = []
            empty_field_index = -1
            for i, input_field in enumerate(self.segment_distances_second):
                if not input_field.text().strip():
                    empty_fields.append(i+1)
                    if empty_field_index == -1:
                        empty_field_index = i
            
            if empty_fields:
                if len(empty_fields) == 1:
                    QMessageBox.warning(self, "Input Error", f"Please enter distance for segment {empty_fields[0]} of second leg")
                else:
                    QMessageBox.warning(self, "Input Error", f"Please enter distances for segments {', '.join(map(str, empty_fields))} of second leg")
                
                # Switch to segment distances tab and focus on first empty field
                self.pointmerge_tab_widget.setCurrentIndex(2)
                if empty_field_index >= 0:
                    self.segment_distances_second[empty_field_index].setFocus()
                return False
        
        return True
        
    def _get_merge_point_coords(self):
        """Get merge point coordinates in decimal degrees"""
        try:
            # Validate that all fields have values
            if not all([
                self.merge_lat_d.text().strip(),
                self.merge_lat_m.text().strip(),
                self.merge_lat_s.text().strip(),
                self.merge_lon_d.text().strip(),
                self.merge_lon_m.text().strip(),
                self.merge_lon_s.text().strip()
            ]):
                raise ValueError("Coordinates are incomplete. Please fill in all fields.")
            
            # Parse latitude
            lat_dms = parse_dms(
                self.merge_lat_d.text(),
                self.merge_lat_m.text(),
                self.merge_lat_s.text(),
                self.merge_lat_dir.currentText()
            )
            
            # Parse longitude
            lon_dms = parse_dms(
                self.merge_lon_d.text(),
                self.merge_lon_m.text(),
                self.merge_lon_s.text(),
                self.merge_lon_dir.currentText()
            )
            
            # Convert to decimal
            lat_decimal = dms_to_decimal(lat_dms, self.merge_lat_dir.currentText())
            lon_decimal = dms_to_decimal(lon_dms, self.merge_lon_dir.currentText())
            
            return (lat_decimal, lon_decimal)
        except ValueError as e:
            raise ValueError(f"Invalid coordinates: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error processing coordinates: {str(e)}")

    def set_coordinates(self, lat, lon, modifiers=None):
        """Set coordinates based on map click. If Ctrl is pressed, move merge point only"""
        # Check if Ctrl is pressed
        if modifiers is not None and modifiers & Qt.ControlModifier:
            # If Ctrl is pressed, only update merge point coordinates
            print(f"Ctrl+click detected at {lat}, {lon} - Moving merge point")
            self.set_merge_point_coordinates(lat, lon)
        else:
            # Regular coordinate picking behavior - same as before
            self.set_merge_point_coordinates(lat, lon)
    
    def set_merge_point_coordinates(self, lat, lon):
        """Set the merge point coordinate fields using decimal degrees"""
        # Convert from decimal degrees to DMS
        lat_dms = decimal_to_dms(abs(lat))
        lon_dms = decimal_to_dms(abs(lon))
        
        # Set latitude fields
        self.merge_lat_d.setText(str(int(abs(lat_dms.degrees))))
        self.merge_lat_m.setText(str(int(lat_dms.minutes)))
        self.merge_lat_s.setText(f"{lat_dms.seconds:.3f}")
        self.merge_lat_dir.setCurrentText("N" if lat >= 0 else "S")
        
        # Set longitude fields
        self.merge_lon_d.setText(str(int(abs(lon_dms.degrees))))
        self.merge_lon_m.setText(str(int(lon_dms.minutes)))
        self.merge_lon_s.setText(f"{lon_dms.seconds:.3f}")
        self.merge_lon_dir.setCurrentText("E" if lon >= 0 else "W")

    def _on_tab_selection_changed(self, index):
        """Perform tab-specific actions when a tab is selected"""
        # If segment distances tab is selected, automatically create inputs
        if index == 2 and self.pointmerge_radio.isChecked():  # Segment Distances tab
            self._create_segment_distance_inputs()

    def closeEvent(self, event):
        """Handle window close event (X button click)"""
        # Disable coordinate picking mode before closing
        self.patternChanged.emit(False)
        
        # Notify parent window that dialog is being closed (similar to reject)
        if self.parent():
            try:
                # Try to call parent's on_path_extension_rejected method if it exists
                if hasattr(self.parent(), 'on_path_extension_rejected'):
                    self.parent().on_path_extension_rejected()
            except Exception:
                # Ignore any errors if the method doesn't exist or can't be called
                pass
                
        # Accept the close event
        event.accept()


def calculate_path_extension_waypoints(runway, config):
    """Calculate waypoints for path extension based on pattern type"""
    pattern_type = config.get('pattern_type', 'trombone')
    try:
        if pattern_type == 'pointmerge':
            return calculate_point_merge_waypoints(runway, config)
        else:
            return calculate_trombone_waypoints(runway, config)
    except Exception as e:
        print(f"Error in calculate_path_extension_waypoints: {str(e)}")
        import traceback
        traceback.print_exc()
        QMessageBox.critical(None, "Error Generating Path", 
                            f"Failed to generate path: {str(e)}")
        return []


def calculate_trombone_waypoints(runway, config):
    """Calculate waypoints for trombone pattern. Extension always points towards threshold."""
    # Get APPROACH threshold coordinates and centerline direction
    # 'runway' here is the approach_data dict created in get_configuration
    
    # Import math module at function level to ensure it's always available
    import math
    from utils import calculate_point_at_distance_and_bearing
    
    # Hata önleme ve eksik değerlerin kontrolü
    if not runway:
        print("Error: Runway data is missing or empty")
        return []
    
    # Eksik 'start_lat' veya 'start_lon' için kontrol
    if 'start_lat' not in runway or 'start_lon' not in runway:
        # Threshold değerleri varsa onları kullan
        if 'threshold_lat' in runway and 'threshold_lon' in runway:
            runway['start_lat'] = runway['threshold_lat'] 
            runway['start_lon'] = runway['threshold_lon']
        else:
            print("Error: Required coordinate data missing in runway")
            return []
    
    # Eksik 'end_lat' veya 'end_lon' için kontrol - bunlar hesaplanacak açı için gerekli
    if 'end_lat' not in runway or 'end_lon' not in runway:
        # Varsayılan bir yön belirlememiz gerekiyor - kuzeye doğru
        # Eğer end noktası yoksa, threshold'dan 1 NM kuzeye bir nokta belirle
        north_bearing = 0  # Kuzeye doğru
        runway['end_lat'], runway['end_lon'] = calculate_point_at_distance_and_bearing(
            runway['start_lat'], runway['start_lon'], 1.0, north_bearing)
        print(f"Warning: Created default end coordinates for runway calculation")
    
    # Değerleri al
    start_lat, start_lon = runway['start_lat'], runway['start_lon']
    end_lat, end_lon = runway['end_lat'], runway['end_lon'] 
    
    # --- DEBUG --- 
    print(f"\n[DEBUG] Trombone Calc Input:")
    print(f"  Approach ID: {runway.get('id', 'N/A')}")
    print(f"  Start Coords (Threshold): Lat={start_lat}, Lon={start_lon}")
    print(f"  End Coords (Opposite):  Lat={end_lat}, Lon={end_lon}")
    # --- END DEBUG ---
    
    # Calculate runway heading (direction AWAY from the start threshold)
    try:
        # Koordinatların geçerli sayısal değerler olduğunu kontrol et
        if not (isinstance(start_lat, (int, float)) and isinstance(start_lon, (int, float)) and 
                isinstance(end_lat, (int, float)) and isinstance(end_lon, (int, float))):
            print(f"Error: Invalid coordinate values: start_lat={start_lat}, start_lon={start_lon}, end_lat={end_lat}, end_lon={end_lon}")
            # Varsayılan değerlerle devam et - 0 derece (kuzey)
            runway_heading_rad = 0
            runway_heading_deg = 0
        else:
            # Aynı nokta olma durumunda (end ve start aynı) kontrolü yap
            if abs(end_lat - start_lat) < 0.00001 and abs(end_lon - start_lon) < 0.00001:
                print("Warning: Start and end points are too close, using default north heading")
                runway_heading_rad = 0  # Kuzey (0 derece)
                runway_heading_deg = 0
            else:
                runway_heading_rad = math.atan2(end_lon - start_lon, end_lat - start_lat)
                runway_heading_deg = (math.degrees(runway_heading_rad) + 360) % 360 # Normalize to 0-360
    except Exception as e:
        print(f"Error calculating runway heading: {e}")
        runway_heading_rad = 0
        runway_heading_deg = 0
    
    # Calculate the APPROACH heading (direction TOWARDS the start threshold)
    approach_heading_rad = runway_heading_rad + math.pi
    approach_heading_deg = (math.degrees(approach_heading_rad) + 360) % 360
    
    # --- DEBUG --- 
    print(f"  Calculated Runway Heading (Away from Threshold): {runway_heading_deg:.2f} degrees")
    print(f"  Calculated Approach Heading (Towards Threshold): {approach_heading_deg:.2f} degrees")
    # --- END DEBUG ---
    
    nm_to_deg = 1 / 60.0  # Approximate conversion: 1 NM ≈ 1/60 degree

    # Point 'A': The point on the centerline extended, 'threshold_distance' NM OUT along the APPROACH path
    # 'threshold_distance' parametresi: Pist eşiğinden A noktasına olan mesafe (NM olarak)
    # 
    # Bu parametre diğerlerinden farklıdır, değiştiğinde A noktasının konumu değişmelidir.
    # - threshold_distance arttığında: A noktası pistten daha uzaklaşır
    # - threshold_distance azaldığında: A noktası piste yaklaşır
    # - Diğer parametreler değişirse: A noktası aynı kalır, sadece B ve C noktaları değişir
    #
    # Pist threshold'dan, threshold_distance kadar uzaklıktaki noktayı hesapla
    from utils import calculate_point_at_distance_and_bearing
    approach_heading_deg = math.degrees(approach_heading_rad)
    
    print(f"  Calculating point A at threshold_distance={config['threshold_distance']} NM from runway threshold")
    print(f"  Using runway coordinates: lat={start_lat}, lon={start_lon}")
    point_a_lat, point_a_lon = calculate_point_at_distance_and_bearing(
        start_lat, start_lon, 
        config['threshold_distance'],
        approach_heading_deg
    )
    
    # Point 'B': Base leg turn point
    # Base angle is relative to the APPROACH centerline
    # Subtract angle for clockwise interpretation (90 deg = right turn)
    base_leg_angle_rel_north_rad = approach_heading_rad - math.radians(config['base_angle'])
    
    # Daha doğru hesaplama için basit nm_to_deg çarpımı yerine büyük daire hesaplaması kullanıyoruz
    from utils import calculate_point_at_distance_and_bearing
    point_b_lat, point_b_lon = calculate_point_at_distance_and_bearing(
        point_a_lat, point_a_lon, 
        config['base_distance'],
        math.degrees(base_leg_angle_rel_north_rad)
    )
    
    # Point 'C': Extension leg end point
    # Extension should be parallel to the approach centerline, but point AWAY from the threshold
    # This direction is the same as the runway heading (away from threshold).
    extension_leg_angle_rad = runway_heading_rad 
    extension_leg_angle_deg = math.degrees(extension_leg_angle_rad)

    # Daha doğru hesaplama için büyük daire hesaplaması kullanıyoruz
    from utils import calculate_point_at_distance_and_bearing
    point_c_lat, point_c_lon = calculate_point_at_distance_and_bearing(
        point_b_lat, point_b_lon, 
        config['extension_length'],
        extension_leg_angle_deg
    )
    
    # Waypoints are A -> B -> C (logical order from threshold to extension)
    # Format: List of dictionaries {'lat': ..., 'lon': ..., 'name': ...}
    waypoints_coords = [
        (point_a_lat, point_a_lon),  # Point A - Threshold point (First point)
        (point_b_lat, point_b_lon),  # Point B - Base leg turn point (Middle point)
        (point_c_lat, point_c_lon)   # Point C - Extension end point (Last point)
    ]
    
    # Generate names for the waypoints
    approach_id_simple = runway.get('id', 'RWY??').replace(" ", "") # e.g., LTFM36
    base_angle_str = f"{config['base_angle']:.0f}".replace("-", "M") # e.g., 90 or M90
    base_dist_str = f"{config['base_distance']:.0f}" # e.g., 5
    ext_dist_str = f"{config['extension_length']:.0f}" # e.g., 3
    # No direction character needed anymore
    prefix = f"T{approach_id_simple}A{base_angle_str}B{base_dist_str}E{ext_dist_str}"

    named_waypoints = [
        {'lat': lat, 'lon': lon, 'name': f"{prefix}_{i+1}"} 
        for i, (lat, lon) in enumerate(waypoints_coords)
    ]

    print(f"Calculated Trombone Waypoints ({prefix}): {named_waypoints}") # Debug print
    return named_waypoints