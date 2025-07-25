import math
import numpy as np
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, 
                          QComboBox, QLabel, QLineEdit, QRadioButton, QCheckBox,
                          QDialogButtonBox, QFrame, QScrollArea, QPushButton,
                          QButtonGroup, QWidget, QGridLayout, QTextEdit, QMessageBox,
                          QTabWidget)
from PyQt5.QtGui import QDoubleValidator, QIntValidator
from PyQt5.QtCore import Qt

class DMS:
    """Degrees, Minutes, Seconds coordinate component"""
    def __init__(self, degrees=0, minutes=0, seconds=0.0):
        self.degrees = degrees
        self.minutes = minutes
        self.seconds = seconds

def dms_to_decimal(dms, direction=None):
    """Convert DMS coordinates to decimal degrees"""
    decimal = abs(dms.degrees) + (dms.minutes / 60.0) + (dms.seconds / 3600.0)
    if direction in ['S', 'W'] or dms.degrees < 0:
        decimal = -decimal
    return decimal

def decimal_to_dms(decimal_degrees):
    """Convert decimal degrees to DMS"""
    is_negative = decimal_degrees < 0
    decimal_degrees = abs(decimal_degrees)
    degrees = int(decimal_degrees)
    minutes_float = (decimal_degrees - degrees) * 60
    minutes = int(minutes_float)
    seconds = (minutes_float - minutes) * 60
    
    # If negative, adjust degrees
    if is_negative:
        degrees = -degrees
        
    return DMS(degrees, minutes, seconds)

def format_dms_output(decimal_degrees, is_latitude=True):
    """Format decimal degrees as DMS string"""
    dms = decimal_to_dms(abs(decimal_degrees))
    direction = 'N' if decimal_degrees >= 0 and is_latitude else 'S' if is_latitude else 'E' if decimal_degrees >= 0 else 'W'
    return f"{abs(dms.degrees):02d}°{dms.minutes:02d}'{dms.seconds:06.3f}\"{direction}"

def parse_dms(degrees_str, minutes_str, seconds_str, direction=None):
    """Parse DMS strings into a DMS object"""
    try:
        degrees = int(degrees_str) if degrees_str else 0
        minutes = int(minutes_str) if minutes_str else 0
        seconds = float(seconds_str) if seconds_str else 0.0
        
        # Handle negation based on direction
        if direction in ['S', 'W']:
            degrees = -abs(degrees)
            
        return DMS(degrees, minutes, seconds)
    except ValueError:
        raise ValueError("Invalid coordinate format")

def calculate_point_from_bearing(lat, lon, distance_nm, bearing_deg):
    """Calculate a point at given distance and bearing from starting point
    
    Args:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        distance_nm: Distance in nautical miles
        bearing_deg: Bearing in degrees (0 = North, 90 = East, 180 = South, 270 = West)
        
    Returns:
        Tuple of (latitude, longitude) in decimal degrees
    """
    # Convert to radians
    lat1 = math.radians(lat)
    lon1 = math.radians(lon)
    bearing = math.radians(bearing_deg)
    
    # Earth radius in nautical miles
    R = 3440.065  # Earth radius in NM
    
    # Calculate distance in radians
    d = distance_nm / R
    
    # Calculate the destination point using exact spherical formulas
    lat2 = math.asin(math.sin(lat1) * math.cos(d) + 
                    math.cos(lat1) * math.sin(d) * math.cos(bearing))
    
    lon2 = lon1 + math.atan2(math.sin(bearing) * math.sin(d) * math.cos(lat1),
                             math.cos(d) - math.sin(lat1) * math.sin(lat2))
    
    # Convert back to degrees
    return (math.degrees(lat2), math.degrees(lon2))

def calculate_leg_points(merge_lat, merge_lon, initial_track, leg_distance, segment_distances, clockwise=True):
    """Calculate points along a sequencing leg
    
    Args:
        merge_lat: Merge point latitude in decimal degrees
        merge_lon: Merge point longitude in decimal degrees
        initial_track: Initial track angle in degrees where:
                      - 0 degrees = North
                      - 90 degrees = East
                      - 180 degrees = South
                      - 270 degrees = West
        leg_distance: Distance from merge point to leg in NM
        segment_distances: List of segment distances in NM
        clockwise: Whether the arc goes clockwise from the initial point
        
    Returns:
        List of points (lat, lon) along the leg
    """
    try:
        # Validate inputs
        if merge_lat is None or merge_lon is None:
            raise ValueError("Merge point coordinates cannot be None")
            
        if leg_distance <= 0:
            raise ValueError("Leg distance must be positive")
            
        if not segment_distances:
            raise ValueError("Segment distances list cannot be empty")
            
        for i, dist in enumerate(segment_distances):
            if dist <= 0:
                raise ValueError(f"Segment {i+1} distance must be positive")
        
        points = []
        
        # Calculate initial angle in radians
        initial_angle_rad = math.radians(initial_track)
        
        # Determine angular segment sizes
        total_arc_length = sum(segment_distances)
        
        # Calculate angles for each point directly from the merge point
        # Start with the initial angle
        current_angle_rad = initial_angle_rad
        
        # Add initial point
        points.append(calculate_point_from_bearing(merge_lat, merge_lon, leg_distance, initial_track))
        
        # Calculate cumulative arc lengths
        cumulative_arc = 0
        
        # Direction multiplier
        direction = 1 if clockwise else -1
        
        # Calculate each waypoint
        for segment_length in segment_distances:
            # Add segment length to accumulated arc length
            cumulative_arc += segment_length
            
            # Calculate angular displacement (in radians)
            # arc_length = radius * angle => angle = arc_length / radius
            angular_displacement = cumulative_arc / leg_distance
            
            # Apply direction
            angle_displacement_with_direction = direction * angular_displacement
            
            # Calculate new angle (in degrees)
            new_angle_deg = (initial_track + math.degrees(angle_displacement_with_direction)) % 360
                
            # Calculate point at exact distance from merge point
            point = calculate_point_from_bearing(merge_lat, merge_lon, leg_distance, new_angle_deg)
            points.append(point)
        
        return points
    except Exception as e:
        print(f"Error in calculate_leg_points: {str(e)}")
        import traceback
        traceback.print_exc()
        raise ValueError(f"Failed to calculate leg points: {str(e)}")

class PointMergeDialog(QDialog):
    """Dialog for configuring a Point Merge System"""
    def __init__(self, parent=None, runways=None):
        super().__init__(parent)
        self.setWindowTitle("Point Merge System Configuration")
        self.setMinimumWidth(650)
        self.setMinimumHeight(700)
        
        # Initialize variables
        self.has_second_leg = False
        self.segment_distances = []
        self.segment_distances_second = []
        self.runways = runways or {}
        
        # Main layout
        self.main_layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.main_tab = QWidget()
        self.segments_tab = QWidget()
        self.connections_tab = QWidget()
        
        # Setup layouts for each tab
        self.main_tab_layout = QVBoxLayout(self.main_tab)
        self.segments_tab_layout = QVBoxLayout(self.segments_tab)
        self.connections_tab_layout = QVBoxLayout(self.connections_tab)
        
        # Add tabs to widget
        self.tab_widget.addTab(self.main_tab, "Main Configuration")
        self.tab_widget.addTab(self.segments_tab, "Segment Distances")
        self.tab_widget.addTab(self.connections_tab, "Connections")
        
        # Setup sections on tabs
        self._setup_merge_point_section()
        self._setup_legs_section()
        self._setup_arc_direction_section()
        self._setup_segment_distances_section()
        self._setup_connections_section()
        self._setup_buttons_section()
        self._setup_results_section()

    def _setup_merge_point_section(self):
        """Setup merge point coordinates input section with runway selection option"""
        merge_group = QGroupBox("Merge Point Parameters")
        merge_layout = QVBoxLayout()
        
        # Coordinate input method selection
        method_layout = QHBoxLayout()
        self.coords_radio = QRadioButton("Use Coordinates")
        self.runway_radio = QRadioButton("Use Runway")
        method_layout.addWidget(self.coords_radio)
        method_layout.addWidget(self.runway_radio)
        self.coords_radio.setChecked(True)
        
        # Setup button group
        self.merge_point_method = QButtonGroup()
        self.merge_point_method.addButton(self.coords_radio, 1)
        self.merge_point_method.addButton(self.runway_radio, 2)
        self.merge_point_method.buttonClicked.connect(self._toggle_merge_point_method)
        
        merge_layout.addLayout(method_layout)
        
        # Container for coordinate inputs
        self.coords_container = QWidget()
        coords_layout = QGridLayout(self.coords_container)
        
        # Latitude input
        coords_layout.addWidget(QLabel("Lat:"), 0, 0)
        lat_container = QHBoxLayout()
        
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
        coords_layout.addLayout(lat_container, 0, 1)
        
        # Longitude input
        coords_layout.addWidget(QLabel("Lon:"), 1, 0)
        lon_container = QHBoxLayout()
        
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
        coords_layout.addLayout(lon_container, 1, 1)
        
        # Container for runway inputs
        self.runway_container = QWidget()
        runway_layout = QGridLayout(self.runway_container)
        
        runway_layout.addWidget(QLabel("Select Runway:"), 0, 0)
        self.runway_combo = QComboBox()
        if self.runways:
            self.runway_combo.addItems(list(self.runways.keys()))
        else:
            self.runway_combo.addItem("No runways available")
        runway_layout.addWidget(self.runway_combo, 0, 1)
        
        runway_layout.addWidget(QLabel("Distance from Threshold (NM):"), 1, 0)
        self.threshold_distance = QLineEdit()
        self.threshold_distance.setValidator(QDoubleValidator(0.1, 100.0, 1))
        runway_layout.addWidget(self.threshold_distance, 1, 1)
        
        runway_layout.addWidget(QLabel("Distance to Merge Point (NM):"), 2, 0)
        self.merge_point_distance = QLineEdit()
        self.merge_point_distance.setValidator(QDoubleValidator(0.1, 100.0, 1))
        runway_layout.addWidget(self.merge_point_distance, 2, 1)
        
        # Hide runway container initially
        self.runway_container.hide()
        
        merge_layout.addWidget(self.coords_container)
        merge_layout.addWidget(self.runway_container)
        
        merge_group.setLayout(merge_layout)
        self.main_tab_layout.addWidget(merge_group)

    def _toggle_merge_point_method(self, button):
        """Toggle between coordinate input and runway selection"""
        self.coords_container.setVisible(button == self.coords_radio)
        self.runway_container.setVisible(button == self.runway_radio)

    def _setup_legs_section(self):
        """Setup sequencing legs parameters section"""
        legs_container = QVBoxLayout()
        
        # Main Sequencing Leg
        main_leg_group = QGroupBox("Sequencing Leg Parameters")
        main_leg_layout = QGridLayout()
        
        main_leg_layout.addWidget(QLabel("Distance from Merge Point (NM):"), 0, 0)
        self.first_point_distance = QLineEdit()
        self.first_point_distance.setValidator(QDoubleValidator(0.1, 100.0, 1))
        main_leg_layout.addWidget(self.first_point_distance, 0, 1)
        
        main_leg_layout.addWidget(QLabel("Track Angle from Merge Point (°):"), 1, 0)
        self.track_angle = QLineEdit()
        self.track_angle.setValidator(QDoubleValidator(0.0, 360.0, 1))
        main_leg_layout.addWidget(self.track_angle, 1, 1)
        
        main_leg_layout.addWidget(QLabel("Number of Segments:"), 2, 0)
        self.num_segments = QLineEdit()
        self.num_segments.setValidator(QIntValidator(1, 20))
        main_leg_layout.addWidget(self.num_segments, 2, 1)
        
        main_leg_group.setLayout(main_leg_layout)
        legs_container.addWidget(main_leg_group)
        
        # Second Sequencing Leg
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
        second_leg_options_layout.addWidget(self.leg_distance, 1, 1)
        
        second_leg_options_layout.addWidget(QLabel("Number of Segments:"), 2, 0)
        self.num_segments_second = QLineEdit()
        self.num_segments_second.setValidator(QIntValidator(1, 20))
        second_leg_options_layout.addWidget(self.num_segments_second, 2, 1)
        
        # Hide second leg options initially
        self.second_leg_options.setVisible(False)
        second_leg_layout.addWidget(self.second_leg_options)
        
        second_leg_group.setLayout(second_leg_layout)
        legs_container.addWidget(second_leg_group)
        
        self.main_tab_layout.addLayout(legs_container)

    def _setup_connections_section(self):
        """Setup connections configuration section"""
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
        self.connections_tab_layout.addWidget(connections_group)

    def _setup_segment_distances_section(self):
        """Setup segment distances configuration section"""
        segment_group = QGroupBox("Segment Distances")
        segment_layout = QVBoxLayout()
        
        # Button to configure segment distances
        set_distances_btn = QPushButton("Set Segment Distances")
        set_distances_btn.clicked.connect(self._create_segment_distance_inputs)
        segment_layout.addWidget(set_distances_btn)
        
        # Container for segment distance inputs
        self.segments_container = QHBoxLayout()
        
        # First leg segment container
        self.first_leg_segment_container = QGroupBox("Main Leg")
        self.first_leg_segment_layout = QVBoxLayout(self.first_leg_segment_container)
        self.segments_container.addWidget(self.first_leg_segment_container)
        
        # Second leg segment container
        self.second_leg_segment_container = QGroupBox("Second Leg")
        self.second_leg_segment_layout = QVBoxLayout(self.second_leg_segment_container)
        self.segments_container.addWidget(self.second_leg_segment_container)
        
        # Hide segment containers initially
        self.first_leg_segment_container.hide()
        self.second_leg_segment_container.hide()
        
        segment_layout.addLayout(self.segments_container)
        segment_group.setLayout(segment_layout)
        self.segments_tab_layout.addWidget(segment_group)

    def _setup_arc_direction_section(self):
        """Setup arc direction selection section"""
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
        self.main_tab_layout.addWidget(direction_group)

    def _setup_buttons_section(self):
        """Setup action buttons section"""
        buttons_group = QGroupBox()
        buttons_layout = QHBoxLayout(buttons_group)
        
        self.generate_btn = QPushButton("Generate")
        self.generate_btn.clicked.connect(self._generate_coordinates)
        buttons_layout.addWidget(self.generate_btn)
        
        self.save_csv_btn = QPushButton("Save to CSV")
        self.save_csv_btn.setEnabled(False)
        buttons_layout.addWidget(self.save_csv_btn)
        
        self.save_kml_btn = QPushButton("Save to KML")
        self.save_kml_btn.setEnabled(False)
        buttons_layout.addWidget(self.save_kml_btn)
        
        self.view_btn = QPushButton("Open in Browser")
        self.view_btn.setEnabled(False)
        buttons_layout.addWidget(self.view_btn)
        
        self.main_layout.addWidget(buttons_group)

    def _setup_results_section(self):
        """Setup results display section"""
        results_group = QGroupBox("Generated Coordinates")
        results_layout = QVBoxLayout()
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMinimumHeight(150)
        results_layout.addWidget(self.results_text)
        
        results_group.setLayout(results_layout)
        self.main_layout.addWidget(results_group)

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
                raise ValueError("Please enter number of segments for main leg")
            
            num_segments_first = int(self.num_segments.text())
            if num_segments_first <= 0:
                raise ValueError("Number of segments must be positive")
            
            # Create input fields for first leg
            self.segment_distances = []
            for i in range(num_segments_first):
                segment_layout = QHBoxLayout()
                segment_layout.addWidget(QLabel(f"Segment {i+1}:"))
                
                distance_input = QLineEdit()
                distance_input.setValidator(QDoubleValidator(0.1, 100.0, 2))
                segment_layout.addWidget(distance_input)
                
                segment_layout.addWidget(QLabel("NM"))
                self.first_leg_segment_layout.addLayout(segment_layout)
                self.segment_distances.append(distance_input)
            
            # Show first leg segment container
            self.first_leg_segment_container.show()
            
            # Create input fields for second leg if enabled
            if self.has_second_leg:
                if not self.num_segments_second.text():
                    raise ValueError("Please enter number of segments for second leg")
                
                num_segments_second = int(self.num_segments_second.text())
                if num_segments_second <= 0:
                    raise ValueError("Number of segments for second leg must be positive")
                
                # Create input fields
                self.segment_distances_second = []
                for i in range(num_segments_second):
                    segment_layout = QHBoxLayout()
                    segment_layout.addWidget(QLabel(f"Segment {i+1}:"))
                    
                    distance_input = QLineEdit()
                    distance_input.setValidator(QDoubleValidator(0.1, 100.0, 2))
                    segment_layout.addWidget(distance_input)
                    
                    segment_layout.addWidget(QLabel("NM"))
                    self.second_leg_segment_layout.addLayout(segment_layout)
                    self.segment_distances_second.append(distance_input)
                
                # Show second leg segment container
                self.second_leg_segment_container.show()
            
        except ValueError as e:
            QMessageBox.warning(self, "Input Error", str(e))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"An error occurred: {str(e)}")

    def _get_merge_point_coords(self):
        """Get merge point coordinates in decimal degrees"""
        if self.coords_radio.isChecked():
            try:
                lat_dms = parse_dms(
                    self.merge_lat_d.text(),
                    self.merge_lat_m.text(),
                    self.merge_lat_s.text(),
                    self.merge_lat_dir.currentText()
                )
                
                lon_dms = parse_dms(
                    self.merge_lon_d.text(),
                    self.merge_lon_m.text(),
                    self.merge_lon_s.text(),
                    self.merge_lon_dir.currentText()
                )
                
                lat_decimal = dms_to_decimal(lat_dms, self.merge_lat_dir.currentText())
                lon_decimal = dms_to_decimal(lon_dms, self.merge_lon_dir.currentText())
                
                return (lat_decimal, lon_decimal)
            except ValueError as e:
                raise ValueError(f"Invalid coordinates: {str(e)}")
        else:
            # Calculate merge point from runway
            runway_name = self.runway_combo.currentText()
            if runway_name not in self.runways:
                raise ValueError("Please select a valid runway")
            
            runway = self.runways[runway_name]
            threshold_distance = float(self.threshold_distance.text())
            merge_point_distance = float(self.merge_point_distance.text())
            
            # Calculate runway heading
            start_lat, start_lon = runway['start_lat'], runway['start_lon']
            end_lat, end_lon = runway['end_lat'], runway['end_lon']
            
            delta_lon, delta_lat = end_lon - start_lon, end_lat - start_lat
            runway_heading_rad = math.atan2(delta_lon, delta_lat)
            runway_heading = math.degrees(runway_heading_rad)
            
            # Calculate threshold point
            nm_to_deg = 1/60  # 1 NM = 1/60 degree (approximate conversion)
            threshold_lat = start_lat + threshold_distance * nm_to_deg * math.cos(runway_heading_rad)
            threshold_lon = start_lon + threshold_distance * nm_to_deg * math.sin(runway_heading_rad)
            
            # Calculate merge point (perpendicular to runway)
            merge_point_angle_rad = runway_heading_rad + math.radians(90)  # 90° to the right
            merge_lat = threshold_lat + merge_point_distance * nm_to_deg * math.cos(merge_point_angle_rad)
            merge_lon = threshold_lon + merge_point_distance * nm_to_deg * math.sin(merge_point_angle_rad)
            
            return (merge_lat, merge_lon)

    def _validate_inputs(self):
        """Validate all inputs before calculation"""
        # Check merge point coordinates
        if self.coords_radio.isChecked():
            if not all([
                self.merge_lat_d.text(),
                self.merge_lat_m.text(),
                self.merge_lat_s.text(),
                self.merge_lon_d.text(),
                self.merge_lon_m.text(),
                self.merge_lon_s.text()
            ]):
                raise ValueError("Please enter complete merge point coordinates")
        else:
            if not self.runway_combo.currentText() or self.runway_combo.currentText() == "No runways available":
                raise ValueError("Please select a valid runway")
            
            if not self.threshold_distance.text():
                raise ValueError("Please enter distance from threshold")
                
            if not self.merge_point_distance.text():
                raise ValueError("Please enter distance to merge point")
        
        # Check first leg parameters
        if not self.first_point_distance.text():
            raise ValueError("Please enter distance from merge point")
        
        if not self.track_angle.text():
            raise ValueError("Please enter track angle from merge point")
        
        if not self.num_segments.text():
            raise ValueError("Please enter number of segments for main leg")
        
        # Check segment distances for first leg
        if not hasattr(self, 'segment_distances') or not self.segment_distances:
            raise ValueError("Please set segment distances for main leg")
        
        for i, input_field in enumerate(self.segment_distances):
            if not input_field.text():
                raise ValueError(f"Please enter distance for segment {i+1} of main leg")
        
        # Check second leg parameters if enabled
        if self.has_second_leg:
            if not self.leg_distance.text():
                raise ValueError("Please enter distance between legs")
            
            if not self.num_segments_second.text():
                raise ValueError("Please enter number of segments for second leg")
            
            # Check segment distances for second leg
            if not hasattr(self, 'segment_distances_second') or not self.segment_distances_second:
                raise ValueError("Please set segment distances for second leg")
            
            for i, input_field in enumerate(self.segment_distances_second):
                if not input_field.text():
                    raise ValueError(f"Please enter distance for segment {i+1} of second leg")
        
        return True

    def _generate_coordinates(self):
        """Generate and display point merge system coordinates"""
        try:
            # Validate inputs
            self._validate_inputs()
            
            # Get merge point coordinates
            merge_coords = self._get_merge_point_coords()
            merge_lat, merge_lon = merge_coords
            
            # Get parameters for first leg
            first_point_distance = float(self.first_point_distance.text())
            track_angle = float(self.track_angle.text())
            
            # Get segment distances for first leg
            first_leg_segments = [float(input_field.text()) for input_field in self.segment_distances]
            
            # Get arc direction
            clockwise = self.clockwise_radio.isChecked()
            
            # Calculate first leg points
            first_leg_points = calculate_leg_points(
                merge_lat, merge_lon,
                track_angle, first_point_distance,
                first_leg_segments, clockwise
            )
            
            # Store results
            self.merge_point = merge_coords
            self.leg_points = [first_leg_points]
            
            # Calculate second leg points if enabled
            if self.has_second_leg:
                leg_distance = float(self.leg_distance.text())
                is_inner = (self.leg_type.currentText() == "Inner")
                
                # Calculate distance from merge point to second leg
                second_leg_distance = (
                    first_point_distance - leg_distance if is_inner
                    else first_point_distance + leg_distance
                )
                
                # Get segment distances for second leg
                second_leg_segments = [float(input_field.text()) for input_field in self.segment_distances_second]
                
                # Calculate second leg points
                second_leg_points = calculate_leg_points(
                    merge_lat, merge_lon,
                    track_angle, second_leg_distance,
                    second_leg_segments, clockwise
                )
                
                # Add to results
                self.leg_points.append(second_leg_points)
            
            # Display results
            self._display_results()
            
            # Enable export buttons
            self.save_csv_btn.setEnabled(True)
            self.save_kml_btn.setEnabled(True)
            self.view_btn.setEnabled(True)
            
        except ValueError as e:
            QMessageBox.warning(self, "Input Error", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", f"An error occurred: {str(e)}")

    def _display_results(self):
        """Display generated coordinates in the results text area"""
        self.results_text.clear()
        
        # Display merge point
        self.results_text.append("Merge Point:")
        self.results_text.append(
            f"Lat: {format_dms_output(self.merge_point[0], True)}, " +
            f"Lon: {format_dms_output(self.merge_point[1], False)}\n"
        )
        
        # Display leg points
        for i, leg in enumerate(self.leg_points):
            self.results_text.append(f"Leg {i+1} Points:")
            for j, point in enumerate(leg):
                self.results_text.append(
                    f"Segment {j}: Lat: {format_dms_output(point[0], True)}, " +
                    f"Lon: {format_dms_output(point[1], False)}"
                )
            self.results_text.append("")

from PyQt5.QtWidgets import QTextEdit, QMessageBox

def calculate_point_merge_waypoints(runway, config):
    """Calculate waypoints for a Point Merge System based on the configuration
    
    Args:
        runway: Dictionary with runway coordinates (not used if direct coordinates provided)
        config: Configuration dictionary from PathExtensionDialog
        
    Returns:
        Dictionary with merge point and leg points for visualization
    """
    try:
        # Check if Double PMS is enabled and handle it
        if config.get('double_pms_enabled'):
            return _calculate_double_pms_from_config(config)

        # Debug gelen config
        print(f"calculate_point_merge_waypoints için config: {config}")
        
        # Determine merge point coordinates
        if 'merge_lat' not in config or 'merge_lon' not in config:
            raise ValueError("Merge point coordinates are missing from configuration")
            
        merge_lat, merge_lon = config.get('merge_lat', 0.0), config.get('merge_lon', 0.0)
        
        # Main leg configuration - her iki isimle de kontrol et
        # Önce 'first_point_distance', yoksa 'distance' kullan
        if 'first_point_distance' not in config and 'distance' not in config:
            raise ValueError("Distance from merge point is missing (first_point_distance/distance)")
            
        first_point_distance = config.get('first_point_distance', config.get('distance', 15.0))
        # Önce 'track_angle', yoksa 'angle' kullan
        track_angle = config.get('track_angle', config.get('angle', 0.0))
        clockwise = config.get('clockwise', True)
        
        # Extract segment distances for main leg, or create evenly spaced segments
        segment_distances = []
        
        # Eğer 'segments' bir liste ise, doğrudan kullan
        if 'segments' in config and isinstance(config['segments'], list):
            segment_distances = config['segments']
        # Eğer 'segments' bir sayı ise, eşit segmentler oluştur
        elif 'segments' in config and isinstance(config['segments'], (int, float)):
            num_segments = int(config['segments'])
            total_arc_width = config.get('arc_width', 60.0)  # In degrees
            arc_length_nm = math.radians(total_arc_width) * first_point_distance
            segment_distance = arc_length_nm / num_segments if num_segments > 0 else arc_length_nm
            segment_distances = [segment_distance] * num_segments
        # Eğer 'num_segments' varsa, bu sayıda eşit segment oluştur
        elif 'num_segments' in config:
            num_segments = int(config.get('num_segments', 10))
            total_arc_width = config.get('arc_width', 60.0)  # In degrees
            arc_length_nm = math.radians(total_arc_width) * first_point_distance
            segment_distances = [arc_length_nm / num_segments] * num_segments
        # Hiçbir segment bilgisi yoksa, varsayılan 5 segment oluştur
        else:
            num_segments = 5
            total_arc_width = config.get('arc_width', 60.0) 
            arc_length_nm = math.radians(total_arc_width) * first_point_distance
            segment_distances = [arc_length_nm / num_segments] * num_segments
            
        # Güvenlik kontrolü - segment_distances mutlaka bir liste olmalı
        if not isinstance(segment_distances, list) or len(segment_distances) == 0:
            print("UYARI: segment_distances düzgün bir liste değil, varsayılan liste oluşturuluyor")
            segment_distances = [5.0] * 5
        
        # Calculate main leg points
        main_leg_points = calculate_leg_points(
            merge_lat, merge_lon,
            track_angle, first_point_distance,
            segment_distances, clockwise
        )
        
        # Second leg configuration
        second_leg_points = []
        if 'second_leg' in config and config['second_leg']:
            second_leg = config['second_leg']
            
            if 'type' not in second_leg or 'distance' not in second_leg:
                raise ValueError("Second leg configuration is incomplete")
                
            is_inner = second_leg['type'] == 'inner'
            leg_distance = second_leg['distance']
            
            # Calculate distance from merge point to second leg
            second_leg_distance = (
                first_point_distance - leg_distance if is_inner
                else first_point_distance + leg_distance
            )
            
            # Use provided segment distances or create even segments
            if 'segments' in second_leg and second_leg['segments']:
                second_segment_distances = second_leg['segments']
            else:
                num_segments = int(config.get('num_segments', 10))
                total_arc_width = config.get('arc_width', 60.0)
                arc_length_nm = math.radians(total_arc_width) * second_leg_distance
                second_segment_distances = [arc_length_nm / num_segments] * num_segments
            
            # Calculate second leg points
            second_leg_points = calculate_leg_points(
                merge_lat, merge_lon,
                track_angle, second_leg_distance,
                second_segment_distances, clockwise
            )
        
        # Build result with all points and connection information
        result = {
            'merge_point': (merge_lat, merge_lon),
            'main_leg': main_leg_points,
            'second_leg': second_leg_points,
            'connections': config.get('connections', {
                'merge_to_main_start': True,
                'merge_to_main_end': False,
                'merge_to_second_start': False,
                'merge_to_second_end': False,
                'legs_start_to_start': False,
                'legs_end_to_end': False
            })
        }
        
        # Convert to flat list of points for compatibility with existing code
        # The merge point is added as the last point
        # all_points = main_leg_points.copy()
        
        # # Add second leg points if they exist
        # if second_leg_points:
        #     all_points.extend(second_leg_points)
        
        # # Add merge point as the last point
        # all_points.append((merge_lat, merge_lon))
        
        # --- FIX: Return list of dicts with lat/lon/name --- 
        all_waypoints_data = []
        leg_counter = 1
        # Add main leg points
        for i, (lat, lon) in enumerate(main_leg_points):
            all_waypoints_data.append({
                'lat': lat, 
                'lon': lon, 
                'name': f"L{leg_counter}WP{i+1}" 
            })
        
        # Add second leg points if they exist
        if second_leg_points:
            leg_counter += 1
            for i, (lat, lon) in enumerate(second_leg_points):
                 all_waypoints_data.append({
                     'lat': lat, 
                     'lon': lon, 
                     'name': f"L{leg_counter}WP{i+1}" 
                 })

        # Add merge point as the last point
        all_waypoints_data.append({
            'lat': merge_lat, 
            'lon': merge_lon, 
            'name': 'MP' # Merge Point
        })
        
        return all_waypoints_data
        
    except Exception as e:
        # Print error for debugging and re-raise with more context
        print(f"Error in calculate_point_merge_waypoints: {str(e)}")
        import traceback
        traceback.print_exc()
        raise ValueError(f"Failed to generate point merge: {str(e)}")

def _calculate_double_pms_from_config(config):
    """
    Calculates waypoints for a Double Point-Merge System.
    The structure involves a main leg, a perpendicular base segment leading
    to an inner "double" leg that curves back towards the initial approach line.
    """
    # Extract common parameters
    merge_lat, merge_lon = config['merge_lat'], config['merge_lon']
    track_angle = config['track_angle']
    first_point_distance = config['first_point_distance']
    clockwise = config['clockwise']
    base_segment_distance = config['base_segment_distance']
    
    # Handle segments - convert to list if needed
    segments_raw = config['segments']
    if isinstance(segments_raw, list):
        first_leg_segments = segments_raw
    elif isinstance(segments_raw, (int, float)):
        num_segments = int(segments_raw)
        total_arc_width = config.get('arc_width', 60.0)  # In degrees
        arc_length_nm = math.radians(total_arc_width) * first_point_distance
        segment_distance = arc_length_nm / num_segments if num_segments > 0 else arc_length_nm
        first_leg_segments = [segment_distance] * num_segments
    else:
        # Fallback: create 5 equal segments
        num_segments = 5
        total_arc_width = config.get('arc_width', 60.0) 
        arc_length_nm = math.radians(total_arc_width) * first_point_distance
        first_leg_segments = [arc_length_nm / num_segments] * num_segments

    # --- 1. Calculate Main Leg ---
    main_leg_points = calculate_leg_points(
        merge_lat, merge_lon,
        track_angle, first_point_distance,
        first_leg_segments, clockwise
    )
    if not main_leg_points:
        raise ValueError("Failed to generate main leg for Double PMS.")

    # --- 2. Calculate Double Leg Parameters ---
    # The double leg is an inner arc, so its radius is smaller.
    r_main = first_point_distance
    r_double = r_main - base_segment_distance
    if r_double <= 0:
        raise ValueError("Base Segment Distance is too large; it must be less than the main leg's distance from the merge point.")

    # Determine the start and end angles of the main leg arc
    direction = 1 if clockwise else -1
    total_arc_length_main = sum(first_leg_segments)
    angular_displacement_rad = total_arc_length_main / r_main
    
    start_angle_deg = track_angle
    end_angle_deg = (start_angle_deg + direction * math.degrees(angular_displacement_rad)) % 360

    # --- 3. Calculate Double Leg ---
    # The double leg starts at the same angle as the main leg's end, but on the inner radius.
    # It then curves back towards the main leg's start angle.
    # We use the same number of segments as the main leg.
    num_segments_double = len(first_leg_segments)
    arc_length_double = angular_displacement_rad * r_double
    double_leg_segment_dist = arc_length_double / num_segments_double if num_segments_double > 0 else 0
    double_leg_segments = [double_leg_segment_dist] * num_segments_double
    
    # We start from the end angle and go backwards, so the direction is reversed.
    double_leg_points = calculate_leg_points(
        merge_lat, merge_lon,
        end_angle_deg, r_double,
        double_leg_segments, not clockwise
    )
    if not double_leg_points:
        raise ValueError("Failed to generate double leg for Double PMS.")

    # The start of the drawn double leg is the first point calculated.
    p_double_start = double_leg_points[0]
    # The end is the last point, which lies on the line to the first point of the main leg.
    p_double_end = double_leg_points[-1]

    # --- 4. Assemble Waypoint List for Drawing ---
    # The drawing sequence is: Main Leg -> Base Segment -> Double Leg -> Merge Point
    # The base segment is the line from the end of the main leg to the start of the double leg.
    p_main_end = main_leg_points[-1]
    
    # The final list is constructed to create a continuous line for drawing.
    final_waypoints = []
    # Add main leg points (from start to end)
    final_waypoints.extend(main_leg_points)
    # Add the points for the double leg (from its start to its end)
    final_waypoints.extend(double_leg_points)
    # Finally, add the merge point to connect the end of the double leg to it.
    final_waypoints.append((merge_lat, merge_lon))

    # Convert to the required dictionary format with names
    all_waypoints_data = []
    # Name main leg points
    for i, (lat, lon) in enumerate(main_leg_points):
        all_waypoints_data.append({'lat': lat, 'lon': lon, 'name': f"L1WP{i+1}"})
    # Name double leg points
    for i, (lat, lon) in enumerate(double_leg_points):
        all_waypoints_data.append({'lat': lat, 'lon': lon, 'name': f"L2WP{i+1}"})
    # Name merge point
    all_waypoints_data.append({'lat': merge_lat, 'lon': merge_lon, 'name': 'MP'})

    return all_waypoints_data
