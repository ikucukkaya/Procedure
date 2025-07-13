from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, 
                          QScrollArea, QPushButton, QLabel, QFrame, QGroupBox, QSizePolicy, QLayout, 
                          QStyle, QSlider, QComboBox, QDoubleSpinBox, QSpinBox, QColorDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QColor
from collections import defaultdict

from ui_components import CollapsibleSection

class LeftSidebar(QWidget):
    """Left sidebar for map control and procedure selection"""
    
    # Define signals
    procedureToggled = pyqtSignal(bool, str, str, str, str)  # checked, proc_type, airport, runway, procedure
    runwayToggled = pyqtSignal(bool, str)  # checked, runway_id
    resetViewRequested = pyqtSignal()
    # Signal for the new dialog
    runwayDisplayOptionsRequested = pyqtSignal()
    # Harita kontrolleri için sinyal tanımlamaları
    # showSidsToggled = pyqtSignal(bool)  # Şu an için devre dışı
    # showStarsToggled = pyqtSignal(bool)  # Şu an için devre dışı
    showWaypointsToggled = pyqtSignal(bool)
    showTmaBoundaryToggled = pyqtSignal(bool)  # TMA sınırları için sinyal
    showRestrictedAreasToggled = pyqtSignal(bool)  # LTD_P_R sahaları için sinyal
    showSegmentDistancesToggled = pyqtSignal(bool)  # Segment mesafelerini gösterme/gizleme sinyali
    # Snap ayarları için sinyaller
    snapEnabledToggled = pyqtSignal(bool)
    snapModeChanged = pyqtSignal(int)
    snapToleranceChanged = pyqtSignal(int)
    # Çizgi ayarları için sinyal tanımları
    routeLineWidthChanged = pyqtSignal(int)
    selectedRouteLineWidthChanged = pyqtSignal(int)
    routeColorChanged = pyqtSignal(object)  # QColor nesnesi
    selectedRouteColorChanged = pyqtSignal(object)  # QColor nesnesi
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(200)  # Panel minimum genişliği azaltıldı
        self.setMaximumWidth(350)  # Panel maximum genişliği azaltıldı
        
        # Create layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Tüm panele modern görünüm vermek için stil ekle
        self.setStyleSheet("""
            QWidget {
                background-color: #f7f7f7;
            }
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
            QCheckBox {
                padding: 2px;
            }
            QCheckBox:hover {
                background-color: rgba(240, 240, 240, 0.7);
                border-radius: 2px;
            }
        """)
        
        # Create scroll area for sidebar content
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Create content widget for scroll area
        self.scroll_content = QWidget()
        self.scroll_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        # Create layout for scroll content
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setSpacing(2)
        self.scroll_layout.setContentsMargins(1, 1, 1, 1)
        
        # Setup sidebar sections
        self.setup_procedure_section()
        self.setup_runway_section()
        self.setup_map_controls_section()
        
        # Add stretch to push content to top
        self.scroll_layout.addStretch()
        
        # Set scroll widget
        self.scroll.setWidget(self.scroll_content)
        
        # Add scroll area to layout with stretch
        self.layout.addWidget(self.scroll, 1)
        
        # Apply style to ensure scrollbar appears when needed
        self.scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #ffffff;
            }
            QScrollBar:vertical {
                border: none;
                background: #ffffff;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #cccccc;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)
    
    def setup_procedure_section(self):
        """Setup procedure selection section"""
        # Create procedures section header
        self.procedures_section = CollapsibleSection("Procedures")
        # CollapsibleSection bileşenine özel stil ekle
        self.procedures_section.setStyleSheet("""
            QFrame {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: white;
                margin: 2px;
            }
            QToolButton {
                border: none;
                background: transparent;
            }
            QLabel {
                color: #444444;
            }
        """)
        self.procedures_layout = QVBoxLayout()
        self.procedures_layout.setSpacing(5)
        self.procedures_layout.setContentsMargins(8, 8, 8, 8)
        
        # This will be populated by populate_procedures() when data is available
        
        # Set layout for section
        self.procedures_section.setContentLayout(self.procedures_layout)
        
        # Add section to sidebar
        self.scroll_layout.addWidget(self.procedures_section)
    
    def setup_runway_section(self):
        """Setup runway selection section"""
        # Create runways section header
        self.runways_section = CollapsibleSection("Runways")
        # CollapsibleSection bileşenine özel stil ekle
        self.runways_section.setStyleSheet("""
            QFrame {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: white;
                margin: 2px;
            }
            QToolButton {
                border: none;
                background: transparent;
            }
            QLabel {
                color: #444444;
            }
        """)
        section_content_widget = QWidget()
        self.runways_layout = QVBoxLayout(section_content_widget)
        self.runways_layout.setSpacing(5)
        self.runways_layout.setContentsMargins(8, 8, 8, 8)
        
        # Layout specifically for the runway checkboxes list
        self.runway_list_layout = QVBoxLayout()
        self.runways_layout.addLayout(self.runway_list_layout)
        
        # Add the options button below the list area, using an icon
        self.options_button = QPushButton("Runway Display Settings")
        style = self.style()
        icon = style.standardIcon(QStyle.SP_FileDialogDetailedView)
        self.options_button.setIcon(icon)
        self.options_button.setIconSize(QSize(16, 16))
        self.options_button.setToolTip("Configure runway display options") 
        self.options_button.setStyleSheet("""
            QPushButton {
                background-color: #f7f7f7;
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 3px 8px;
                margin-top: 5px;
                font-size: 11px;
                font-weight: bold;
                color: #444444;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-color: #bbbbbb;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
        """)
        self.options_button.clicked.connect(self.runwayDisplayOptionsRequested.emit)
        self.options_button.setVisible(False) # Initially hidden until runways are populated
        
        # Add button to a horizontal layout to control its alignment (e.g., left)
        button_hbox = QHBoxLayout()
        button_hbox.addWidget(self.options_button)
        button_hbox.addStretch(1) # Pushes button to the left
        self.runways_layout.addLayout(button_hbox) # Add the hbox instead of the button directly
        
        # Add stretch to keep button at the bottom if list is short
        self.runways_layout.addStretch(1)
        
        # Set layout for section
        self.runways_section.setContentLayout(self.runways_layout)
        
        # Add section to sidebar
        self.scroll_layout.addWidget(self.runways_section)
    
    def setup_map_controls_section(self):
        """Setup map controls section with visibility toggles"""
        # Create map controls section header
        self.map_controls_section = CollapsibleSection("Map Controls")
        # CollapsibleSection bileşenine özel stil ekle
        self.map_controls_section.setStyleSheet("""
            QFrame {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: white;
                margin: 2px;
            }
            QToolButton {
                border: none;
                background: transparent;
            }
            QLabel {
                color: #444444;
            }
        """)
        
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(5)
        controls_layout.setContentsMargins(8, 8, 8, 8)
        
        # Add display toggles
        # SID ve STAR gösterme kontrolleri şu an için devre dışı bırakıldı
        # (ileride SID ve STAR'lar için ayrı bir görsel kontrol sistemi eklenmeli)
        
        # Sadece waypoint görünürlük kontrolü ekleniyor
        self.cb_show_waypoints = QCheckBox("Show Waypoints")
        self.cb_show_waypoints.setChecked(True)  # DataManager ile uyumlu olarak başlangıçta işaretli yapılıyor
        self.cb_show_waypoints.toggled.connect(self.on_show_waypoints_toggled)
        controls_layout.addWidget(self.cb_show_waypoints)
        
        # TMA sınırları için kontrol ekliyoruz
        self.cb_show_tma_boundary = QCheckBox("Show TMA Boundaries")
        self.cb_show_tma_boundary.setChecked(True)  # Başlangıçta işaretli
        self.cb_show_tma_boundary.toggled.connect(self.on_show_tma_boundary_toggled)
        controls_layout.addWidget(self.cb_show_tma_boundary)
        
        # LTD_P_R yasaklı sahalar için kontrol
        self.cb_show_restricted_areas = QCheckBox("Show LTD_P_R Areas")
        self.cb_show_restricted_areas.setChecked(True)  # Başlangıçta işaretli
        self.cb_show_restricted_areas.toggled.connect(self.on_show_restricted_areas_toggled)
        controls_layout.addWidget(self.cb_show_restricted_areas)
        
        # Segment mesafe etiketleri için kontrol
        self.cb_show_segment_distances = QCheckBox("Show Distance Labels")
        self.cb_show_segment_distances.setChecked(True)  # Başlangıçta işaretli
        self.cb_show_segment_distances.toggled.connect(self.on_show_segment_distances_toggled)
        controls_layout.addWidget(self.cb_show_segment_distances)
        
        # Ayırıcı çizgi ekle
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #e0e0e0; margin-top: 10px; margin-bottom: 10px;")
        controls_layout.addWidget(separator)
        
        # Çizgi ayarları başlığı
        line_settings_label = QLabel("Line Settings")
        line_settings_label.setStyleSheet("font-weight: bold; color: #444444; margin-top: 5px;")
        controls_layout.addWidget(line_settings_label)
        
        # Rota çizgisi kalınlık ayarı
        route_width_layout = QHBoxLayout()
        route_width_layout.addWidget(QLabel("Route Line Width:"))
        self.route_line_width_slider = QSlider(Qt.Horizontal)
        self.route_line_width_slider.setRange(1, 6)
        self.route_line_width_slider.setValue(2)  # Varsayılan kalınlık
        self.route_line_width_slider.setTickPosition(QSlider.TicksBelow)
        self.route_line_width_slider.setTickInterval(1)
        self.route_line_width_slider.valueChanged.connect(self.on_route_line_width_changed)
        
        self.route_width_value_label = QLabel("2px")
        route_width_layout.addWidget(self.route_line_width_slider)
        route_width_layout.addWidget(self.route_width_value_label)
        controls_layout.addLayout(route_width_layout)
        
        # Seçili rota çizgisi kalınlık ayarı
        selected_route_width_layout = QHBoxLayout()
        selected_route_width_layout.addWidget(QLabel("Selected Route Width:"))
        self.selected_route_line_width_slider = QSlider(Qt.Horizontal)
        self.selected_route_line_width_slider.setRange(2, 8)
        self.selected_route_line_width_slider.setValue(4)  # Varsayılan kalınlık
        self.selected_route_line_width_slider.setTickPosition(QSlider.TicksBelow)
        self.selected_route_line_width_slider.setTickInterval(1)
        self.selected_route_line_width_slider.valueChanged.connect(self.on_selected_route_line_width_changed)
        
        self.selected_route_width_value_label = QLabel("4px")
        selected_route_width_layout.addWidget(self.selected_route_line_width_slider)
        selected_route_width_layout.addWidget(self.selected_route_width_value_label)
        controls_layout.addLayout(selected_route_width_layout)
        
        # Rota rengi ayarı
        route_color_layout = QHBoxLayout()
        route_color_layout.addWidget(QLabel("Route Color:"))
        self.route_color_button = QPushButton()
        self.route_color_button.setFixedSize(25, 25)
        self.route_color_button.setStyleSheet("background-color: #800080; border: 1px solid #444444;")  # Mor renk
        self.route_color_button.clicked.connect(self.on_route_color_button_clicked)
        route_color_layout.addWidget(self.route_color_button)
        route_color_layout.addStretch(1)
        controls_layout.addLayout(route_color_layout)
        
        # Seçili rota rengi ayarı
        selected_route_color_layout = QHBoxLayout()
        selected_route_color_layout.addWidget(QLabel("Selected Route Color:"))
        self.selected_route_color_button = QPushButton()
        self.selected_route_color_button.setFixedSize(25, 25)
        self.selected_route_color_button.setStyleSheet("background-color: #FFA500; border: 1px solid #444444;")  # Turuncu renk
        self.selected_route_color_button.clicked.connect(self.on_selected_route_color_button_clicked)
        selected_route_color_layout.addWidget(self.selected_route_color_button)
        selected_route_color_layout.addStretch(1)
        controls_layout.addLayout(selected_route_color_layout)
        
        # Set layout for section
        self.map_controls_section.setContentLayout(controls_layout)
        
        # Add section to sidebar
        self.scroll_layout.addWidget(self.map_controls_section)
        
        # Snap ayarları bölümünü ekle
        self.setup_snap_settings_section()
    

    
    def setup_snap_settings_section(self):
        """Snap (yakalama) ayarları bölümünü ayarla"""
        # Snap ayarları için bölüm başlığı oluştur
        self.snap_settings_section = CollapsibleSection("Snap Settings")
        self.snap_settings_section.setStyleSheet("""
            QFrame {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: white;
                margin: 2px;
            }
            QToolButton {
                border: none;
                background: transparent;
            }
            QLabel {
                color: #444444;
            }
        """)
        
        # Snap ayarları düzeni
        snap_layout = QVBoxLayout()
        snap_layout.setSpacing(5)
        snap_layout.setContentsMargins(8, 8, 8, 8)
        
        # Snap özelliğini açma/kapama kontrolü
        self.cb_snap_enabled = QCheckBox("Enable Snap Feature")
        self.cb_snap_enabled.setChecked(True)
        self.cb_snap_enabled.toggled.connect(self.on_snap_enabled_toggled)
        snap_layout.addWidget(self.cb_snap_enabled)
        
        # Snap modu seçimi - Checkboxlar olarak düzenlendi
        snap_mode_label = QLabel("Snap Modes:")
        snap_mode_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        snap_layout.addWidget(snap_mode_label)
        
        # Snap mod checkboxları için bir grup kutusu oluştur
        snap_modes_box = QGroupBox()
        snap_modes_box.setStyleSheet("QGroupBox { border: 1px solid #e0e0e0; border-radius: 3px; margin-top: 0px; padding: 5px; background-color: #f8f8f8; }")
        snap_modes_layout = QVBoxLayout(snap_modes_box)
        snap_modes_layout.setSpacing(5)
        snap_modes_layout.setContentsMargins(8, 5, 8, 5)
        
        # Tümünü seç/hiçbirini seçme kontrolü
        self.cb_snap_all = QCheckBox("All")
        self.cb_snap_all.setChecked(False)  # Başlangıçta işaretsiz
        self.cb_snap_all.toggled.connect(self.on_snap_all_toggled)
        snap_modes_layout.addWidget(self.cb_snap_all)
        
        # Ayırıcı çizgi ekleyelim
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #e0e0e0;")
        snap_modes_layout.addWidget(separator)
        
        # Uç noktalara snap
        self.cb_snap_endpoint = QCheckBox("Endpoints")
        self.cb_snap_endpoint.setChecked(True)  # Açık olacak
        self.cb_snap_endpoint.toggled.connect(self.on_snap_mode_checkboxes_toggled)
        snap_modes_layout.addWidget(self.cb_snap_endpoint)
        
        # Orta noktalara snap
        self.cb_snap_midpoint = QCheckBox("Midpoints")
        self.cb_snap_midpoint.setChecked(True)  # Açık olacak
        self.cb_snap_midpoint.toggled.connect(self.on_snap_mode_checkboxes_toggled)
        snap_modes_layout.addWidget(self.cb_snap_midpoint)
        
        # Kesişim noktalarına snap
        self.cb_snap_intersection = QCheckBox("Intersections")
        self.cb_snap_intersection.setChecked(False)  # Kapalı olacak
        self.cb_snap_intersection.toggled.connect(self.on_snap_mode_checkboxes_toggled)
        snap_modes_layout.addWidget(self.cb_snap_intersection)
        
        # Waypoint'lere snap
        self.cb_snap_waypoint = QCheckBox("Waypoints")
        self.cb_snap_waypoint.setChecked(True)  # Varsayılan olarak açık
        self.cb_snap_waypoint.toggled.connect(self.on_snap_mode_checkboxes_toggled)
        snap_modes_layout.addWidget(self.cb_snap_waypoint)
        
        snap_layout.addWidget(snap_modes_box)
        
        # Snap toleransı ayarı
        snap_tolerance_layout = QHBoxLayout()
        snap_tolerance_layout.addWidget(QLabel("Tolerance:"))
        self.snap_tolerance_slider = QSlider(Qt.Horizontal)
        self.snap_tolerance_slider.setRange(5, 30)
        self.snap_tolerance_slider.setValue(15)
        self.snap_tolerance_slider.setTickPosition(QSlider.TicksBelow)
        self.snap_tolerance_slider.setTickInterval(5)
        self.snap_tolerance_slider.valueChanged.connect(self.on_snap_tolerance_changed)
        
        self.tolerance_value_label = QLabel("15px")
        snap_tolerance_layout.addWidget(self.snap_tolerance_slider)
        snap_tolerance_layout.addWidget(self.tolerance_value_label)
        snap_layout.addLayout(snap_tolerance_layout)
        
        # Bölüm düzenini ayarla
        self.snap_settings_section.setContentLayout(snap_layout)
        
        # Bölümü yan çubuğa ekle
        self.scroll_layout.addWidget(self.snap_settings_section)
        
    def on_snap_enabled_toggled(self, checked):
        """Snap özelliği açma/kapama sinyalini gönder"""
        self.snapEnabledToggled.emit(checked)
        
    def on_snap_all_toggled(self, checked):
        """Tümü checkbox durumunu diğer tüm checkbox'lara uygula"""
        # Sinyalleri geçici olarak blokla
        self.cb_snap_endpoint.blockSignals(True)
        self.cb_snap_midpoint.blockSignals(True)
        self.cb_snap_intersection.blockSignals(True)
        self.cb_snap_waypoint.blockSignals(True)
        
        # Tüm checkbox'ları aynı duruma getir
        self.cb_snap_endpoint.setChecked(checked)
        self.cb_snap_midpoint.setChecked(checked)
        self.cb_snap_intersection.setChecked(checked)
        self.cb_snap_waypoint.setChecked(checked)
        
        # Sinyalleri tekrar aktif et
        self.cb_snap_endpoint.blockSignals(False)
        self.cb_snap_midpoint.blockSignals(False)
        self.cb_snap_intersection.blockSignals(False)
        self.cb_snap_waypoint.blockSignals(False)
        
        # Mod değişikliğini gönder
        self.on_snap_mode_checkboxes_toggled()
    
    def on_snap_mode_checkboxes_toggled(self):
        """Snap modu checkbox değişiklikleri sinyalini gönder"""
        # Seçili checkboxlara göre mod değerini hesapla
        mode_value = 0
        
        if self.cb_snap_endpoint.isChecked():
            mode_value |= 1  # SNAP_ENDPOINT = 1
        
        if self.cb_snap_midpoint.isChecked():
            mode_value |= 2  # SNAP_MIDPOINT = 2
            
        if self.cb_snap_intersection.isChecked():
            mode_value |= 4  # SNAP_INTERSECTION = 4
            
        if self.cb_snap_waypoint.isChecked():
            mode_value |= 16  # SNAP_WAYPOINT = 16
        
        # "Tümü" checkbox durumunu güncelle
        all_checked = all([
            self.cb_snap_endpoint.isChecked(),
            self.cb_snap_midpoint.isChecked(),
            self.cb_snap_intersection.isChecked(),
            self.cb_snap_waypoint.isChecked()
        ])
        
        none_checked = not any([
            self.cb_snap_endpoint.isChecked(),
            self.cb_snap_midpoint.isChecked(),
            self.cb_snap_intersection.isChecked(),
            self.cb_snap_waypoint.isChecked()
        ])
        
        # Tümü checkbox'ının sinyallerini blokla
        self.cb_snap_all.blockSignals(True)
        
        # Tüm checkbox'lar işaretliyse "Tümü" de işaretle, değilse kaldır
        self.cb_snap_all.setChecked(all_checked)
        
        # Karışık durum (bazıları işaretli bazıları değil)
        if not all_checked and not none_checked:
            self.cb_snap_all.setTristate(True)
            self.cb_snap_all.setCheckState(Qt.PartiallyChecked)
        else:
            self.cb_snap_all.setTristate(False)
        
        # Tümü checkbox'ının sinyallerini tekrar aktif et
        self.cb_snap_all.blockSignals(False)
            
        # Hesaplanan mod değerini gönder
        self.snapModeChanged.emit(mode_value)
        
    def on_snap_tolerance_changed(self, value):
        """Snap toleransı değişikliği sinyalini gönder"""
        self.tolerance_value_label.setText(f"{value}px")
        self.snapToleranceChanged.emit(value)
        
    def set_snap_mode_checkboxes(self, mode):
        """Snap modu değerine göre checkbox durumlarını ayarla"""
        # Sinyalleri geçici olarak blokla
        self.cb_snap_all.blockSignals(True)
        self.cb_snap_endpoint.blockSignals(True)
        self.cb_snap_midpoint.blockSignals(True)
        self.cb_snap_intersection.blockSignals(True)
        self.cb_snap_waypoint.blockSignals(True)
        
        # Mod değerine göre checkbox durumlarını ayarla
        endpoint_checked = bool(mode & 1)      # SNAP_ENDPOINT = 1
        midpoint_checked = bool(mode & 2)      # SNAP_MIDPOINT = 2
        intersection_checked = bool(mode & 4)  # SNAP_INTERSECTION = 4
        waypoint_checked = bool(mode & 16)     # SNAP_WAYPOINT = 16
        
        self.cb_snap_endpoint.setChecked(endpoint_checked)
        self.cb_snap_midpoint.setChecked(midpoint_checked)
        self.cb_snap_intersection.setChecked(intersection_checked)
        self.cb_snap_waypoint.setChecked(waypoint_checked)
        
        # Tümü checkbox'ının durumunu güncelle
        all_checked = all([endpoint_checked, midpoint_checked, intersection_checked, waypoint_checked])
        none_checked = not any([endpoint_checked, midpoint_checked, intersection_checked, waypoint_checked])
        
        if all_checked:
            self.cb_snap_all.setTristate(False)
            self.cb_snap_all.setChecked(True)
        elif none_checked:
            self.cb_snap_all.setTristate(False)
            self.cb_snap_all.setChecked(False)
        else:
            self.cb_snap_all.setTristate(True)
            self.cb_snap_all.setCheckState(Qt.PartiallyChecked)
        
        # Sinyalleri tekrar aktif et
        self.cb_snap_all.blockSignals(False)
        self.cb_snap_endpoint.blockSignals(False)
        self.cb_snap_midpoint.blockSignals(False)
        self.cb_snap_intersection.blockSignals(False)
        self.cb_snap_waypoint.blockSignals(False)
    
    def populate_procedures(self, procedures):
        """Populate procedure selection based on loaded data"""
        # Clear existing content
        for i in reversed(range(self.procedures_layout.count())):
            item = self.procedures_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        
        # Get unique airports from both SID and STAR procedures
        airports = set()
        for proc_type in ["SID", "STAR"]:
            airports.update(procedures[proc_type].keys())
        
        # Create sections for each airport
        for airport in sorted(airports):
            airport_section = CollapsibleSection(airport)
            # Havalimanı bölümüne özel stil ekle
            airport_section.setStyleSheet("""
                QFrame {
                    border: 1px solid #e8e8e8;
                    border-radius: 4px;
                    background-color: #fcfcfc;
                    margin: 2px;
                }
                QToolButton {
                    border: none;
                    background: transparent;
                }
                QLabel {
                    font-weight: bold;
                    color: #333333;
                }
            """)
            airport_layout = QVBoxLayout()
            airport_layout.setSpacing(5)
            airport_layout.setContentsMargins(5, 5, 5, 5)
            
            # Create STAR and SID sections for this airport
            for proc_type in ["STAR", "SID"]:
                if airport in procedures[proc_type]:
                    # Use QGroupBox instead of CollapsibleSection for proc_type
                    proc_group_box = QGroupBox(f"{proc_type} Prosedürleri")
                    proc_group_box.setStyleSheet("""
                        QGroupBox {
                            font-weight: bold;
                            border: 1px solid #dddddd;
                            border-radius: 3px;
                            margin-top: 10px;
                            padding-top: 8px;
                        }
                        QGroupBox::title {
                            subcontrol-origin: margin;
                            left: 7px;
                            padding: 0 3px;
                            background-color: #fcfcfc;
                        }
                    """)
                    proc_group_layout = QVBoxLayout() # Layout for the group box
                    proc_group_layout.setSpacing(5)
                    proc_group_layout.setContentsMargins(5, 8, 5, 5)
                    
                    # Special handling for STAR procedures with North/South categorization
                    if proc_type == "STAR":
                        # Group procedures by runway first
                        runway_procedures = {}
                        for runway in procedures[proc_type][airport]:
                            runway_procedures[runway] = procedures[proc_type][airport][runway]
                        
                        # Create North and South sections for STARs
                        for region in ["Kuzey", "Güney"]:
                            region_section = CollapsibleSection(region)
                            region_section.setStyleSheet("""
                                QFrame {
                                    border: 1px solid #e0e0e0;
                                    border-radius: 3px;
                                    background-color: #fcfcfc;
                                    margin: 2px;
                                }
                                QToolButton {
                                    border: none;
                                    background: transparent;
                                    font-weight: bold;
                                }
                                QLabel {
                                    font-weight: bold;
                                    color: #333333;
                                }
                            """)
                            region_layout = QVBoxLayout()
                            region_layout.setSpacing(2)
                            region_layout.setContentsMargins(5, 5, 5, 5)
                            
                            # Determine runway based on region
                            if region == "Kuzey":
                                target_runway = "34L"
                            else:  # Güney
                                target_runway = "16R"
                            
                            # Add procedures for this region
                            if target_runway in runway_procedures:
                                for procedure in sorted(runway_procedures[target_runway]):
                                    cb = QCheckBox(procedure)
                                    cb.setStyleSheet("""
                                        QCheckBox {
                                            padding: 4px;
                                            border-radius: 2px;
                                            font-size: 11px;
                                        }
                                        QCheckBox:hover {
                                            background-color: rgba(240, 240, 240, 0.7);
                                        }
                                    """)
                                    cb.toggled.connect(
                                        lambda checked, p=procedure, t=proc_type, a=airport, r=target_runway: 
                                        self.procedureToggled.emit(checked, t, a, r, p)
                                    )
                                    region_layout.addWidget(cb)
                            
                            region_section.setContentLayout(region_layout)
                            proc_group_layout.addWidget(region_section)
                    
                    else:  # SID procedures - use configuration-based grouping like STARs
                        # Group procedures by runway configuration
                        runway_procedures = {}
                        for runway in procedures[proc_type][airport]:
                            runway_procedures[runway] = procedures[proc_type][airport][runway]
                        
                        # Create configuration sections for SIDs
                        sid_configs = ["KUZEY", "GÜNEY", "TERS_KUZEY", "TERS_GÜNEY"]
                        
                        for config in sid_configs:
                            config_section = CollapsibleSection(config)
                            config_section.setStyleSheet("""
                                QFrame {
                                    border: 1px solid #e0e0e0;
                                    border-radius: 3px;
                                    background-color: #fcfcfc;
                                    margin: 2px;
                                }
                                QToolButton {
                                    border: none;
                                    background: transparent;
                                    font-weight: bold;
                                }
                                QLabel {
                                    font-weight: bold;
                                    color: #333333;
                                }
                            """)
                            config_layout = QVBoxLayout()
                            config_layout.setSpacing(2)
                            config_layout.setContentsMargins(5, 5, 5, 5)
                            
                            # Add procedures for this configuration
                            if config in runway_procedures:
                                for procedure in sorted(runway_procedures[config]):
                                    cb = QCheckBox(procedure)
                                    cb.setStyleSheet("""
                                        QCheckBox {
                                            padding: 4px;
                                            border-radius: 2px;
                                            font-size: 11px;
                                        }
                                        QCheckBox:hover {
                                            background-color: rgba(240, 240, 240, 0.7);
                                        }
                                    """)
                                    cb.toggled.connect(
                                        lambda checked, p=procedure, t=proc_type, a=airport, r=config: 
                                        self.procedureToggled.emit(checked, t, a, r, p)
                                    )
                                    config_layout.addWidget(cb)
                            
                            config_section.setContentLayout(config_layout)
                            proc_group_layout.addWidget(config_section)
                    
                    proc_group_box.setLayout(proc_group_layout)
                    airport_layout.addWidget(proc_group_box)
            
            airport_section.setContentLayout(airport_layout)
            self.procedures_layout.addWidget(airport_section)
    
    def populate_runways(self, runways):
        """Populate runway selection based on loaded data with specific sorting."""
        # Clear existing content from the list layout
        while self.runway_list_layout.count():
            item = self.runway_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not runways:
            self.runway_list_layout.addWidget(QLabel("No runways loaded."))
            self.options_button.setVisible(False)
            return
        
        # Group runways by airport identifier
        airport_groups = defaultdict(list)
        for runway in runways:
            # Attempt to extract airport ID, handle potential errors
            airport_id_found = None
            try:
                airport_id_found = runway['id'].split()[0]
            except (IndexError, AttributeError) as e:
                print(f"Warning: Could not parse airport ID from runway ID '{runway.get('id', 'N/A')}': {e}")
                airport_groups["Unknown"].append(runway)
            else:
                if airport_id_found:
                     airport_groups[airport_id_found].append(runway)
        
        # --- Custom Sorting Logic --- 
        desired_airport_order = ['LTFM', 'LTFJ', 'LTBA']
        processed_airports = set()
        
        # Function to add airport section to layout
        def add_airport_section(airport_id):
            if airport_id not in airport_groups:
                return # Skip if this airport has no loaded runways
                
            airport_name = airport_id
            airport_label = QLabel(airport_name)
            airport_label.setStyleSheet("""
                font-weight: bold; 
                margin-top: 5px;
                padding: 3px 5px;
                background-color: #f0f0f0;
                border-radius: 3px;
                color: #333333;
            """)
            self.runway_list_layout.addWidget(airport_label)
            
            runway_list = airport_groups[airport_id]
            
            # Default sort first
            sorted_runways = sorted(runway_list, key=lambda x: x['id'])
            
            # Custom sort for LTFM: Move 09/27 to the end
            if airport_id == 'LTFM':
                rwy_0927 = None
                temp_list = []
                target_id_part = "09/27" 
                for rwy in sorted_runways:
                    try:
                        rwy_id_part = rwy['id'].split(' ', 1)[1]
                        if rwy_id_part == target_id_part:
                             rwy_0927 = rwy
                        else:
                             temp_list.append(rwy)
                    except IndexError:
                        temp_list.append(rwy) # Keep runways with unexpected IDs
                sorted_runways = temp_list
                if rwy_0927:
                    sorted_runways.append(rwy_0927)
            
            # Create checkbox for each runway
            for runway in sorted_runways:
                runway_id = runway['id']
                try:
                    display_id = runway_id.split(' ', 1)[1] # Get part after airport code (e.g., 16L/34R)
                except IndexError:
                    display_id = runway_id # Fallback if format is unexpected
                    
                cb = QCheckBox(display_id)
                cb.setToolTip(f"Show/hide runway {display_id}")
                cb.setStyleSheet("""
                    QCheckBox { 
                        margin-left: 10px;
                        padding: 3px;
                    }
                    QCheckBox:hover {
                        background-color: rgba(240, 240, 240, 0.7);
                        border-radius: 2px;
                    }
                """) 
                cb.toggled.connect(lambda checked, r=runway_id: self.runwayToggled.emit(checked, r))
                cb.setChecked(True)  # Varsayılan olarak seçili olsun
                self.runway_list_layout.addWidget(cb)
                
            # Add spacer
            spacer = QFrame()
            spacer.setFrameShape(QFrame.HLine)
            spacer.setFrameShadow(QFrame.Plain)
            spacer.setStyleSheet("border: none; background: transparent; height: 1px; margin-top: 3px; margin-bottom: 3px;")
            self.runway_list_layout.addWidget(spacer)
            processed_airports.add(airport_id)
                
        # Add airports in the desired order
        for airport_id in desired_airport_order:
            add_airport_section(airport_id)
                
        # Add any remaining airports alphabetically
        remaining_airports = sorted([aid for aid in airport_groups if aid not in processed_airports])
        for airport_id in remaining_airports:
            add_airport_section(airport_id)
        # --- End Custom Sorting Logic --- 

        self.runway_list_layout.addStretch() # Push airport groups to top
        self.options_button.setVisible(True) # Show button now that runways are populated
    
    def get_base_runway(self, runway):
        """Extract the base runway number without the L/R/C suffix"""
        return ''.join(c for c in runway if c.isdigit())
    
    # SID ve STAR görünürlük kontrolleri için metodlar şu an için devre dışı bırakıldı
    # def on_show_sids_toggled(self, checked):
    #     """Handle SID visibility toggle"""
    #     self.showSidsToggled.emit(checked)
    # 
    # def on_show_stars_toggled(self, checked):
    #     """Handle STAR visibility toggle"""
    #     self.showStarsToggled.emit(checked)
        
    def on_show_waypoints_toggled(self, checked):
        """Handle waypoint visibility toggle"""
        self.showWaypointsToggled.emit(checked)
        
        # Show Waypoints kapatıldığında Snap Waypoints'i de kapat
        # ama Show Waypoints açıldığında Snap Waypoints otomatik açılmasın
        if not checked:
            # Snap Waypoints özelliği aktif durumdaysa devre dışı bırak
            if self.cb_snap_waypoint.isChecked():
                self.cb_snap_waypoint.blockSignals(True)
                self.cb_snap_waypoint.setChecked(False)
                self.cb_snap_waypoint.blockSignals(False)
                
            # Ayrıca Snap Waypoints seçeneğini devre dışı bırak
            self.cb_snap_waypoint.setEnabled(False)
            
            # Snap modu güncelle (waypoint snap'i devre dışı bırak)
            self.on_snap_mode_checkboxes_toggled()
        else:
            # Show Waypoints aktif, Snap Waypoints seçeneğini aktifleştir
            self.cb_snap_waypoint.setEnabled(True)
        
    def on_show_tma_boundary_toggled(self, checked):
        """Handle TMA boundary visibility toggle"""
        self.showTmaBoundaryToggled.emit(checked)
        
    def on_show_restricted_areas_toggled(self, checked):
        """Handle LTD_P_R restricted areas visibility toggle"""
        self.showRestrictedAreasToggled.emit(checked)

    def on_show_segment_distances_toggled(self, checked):
        """Handle segment distance labels visibility toggle"""
        self.showSegmentDistancesToggled.emit(checked)
        
    def on_route_line_width_changed(self, value):
        """Rota çizgisi kalınlık değişikliği sinyalini gönder"""
        self.route_width_value_label.setText(f"{value}px")
        self.routeLineWidthChanged.emit(value)
        
    def on_selected_route_line_width_changed(self, value):
        """Seçili rota çizgisi kalınlık değişikliği sinyalini gönder"""
        self.selected_route_width_value_label.setText(f"{value}px")
        self.selectedRouteLineWidthChanged.emit(value)
    
    def on_route_color_button_clicked(self):
        """Rota rengi seçici diyalog kutusunu göster"""
        current_color = self.route_color_button.palette().button().color()
        color_dialog = QColorDialog(current_color, self)
        color_dialog.setOption(QColorDialog.ShowAlphaChannel, False)
        color_dialog.setWindowTitle("Select Route Color")
        
        if color_dialog.exec_() == QColorDialog.Accepted:
            selected_color = color_dialog.selectedColor()
            if selected_color.isValid():
                self.update_route_color_button(selected_color)
                self.routeColorChanged.emit(selected_color)
    
    def on_selected_route_color_button_clicked(self):
        """Seçili rota rengi seçici diyalog kutusunu göster"""
        current_color = self.selected_route_color_button.palette().button().color()
        color_dialog = QColorDialog(current_color, self)
        color_dialog.setOption(QColorDialog.ShowAlphaChannel, False)
        color_dialog.setWindowTitle("Select Selected Route Color")
        
        if color_dialog.exec_() == QColorDialog.Accepted:
            selected_color = color_dialog.selectedColor()
            if selected_color.isValid():
                self.update_selected_route_color_button(selected_color)
                self.selectedRouteColorChanged.emit(selected_color)
    
    def update_route_color_button(self, color):
        """Rota rengi butonunun arka plan rengini güncelle"""
        self.route_color_button.setStyleSheet(
            f"background-color: {color.name()}; border: 1px solid #444444;"
        )
    
    def update_selected_route_color_button(self, color):
        """Seçili rota rengi butonunun arka plan rengini güncelle"""
        self.selected_route_color_button.setStyleSheet(
            f"background-color: {color.name()}; border: 1px solid #444444;"
        )
    
    def post_init(self):
        """
        Sol kenar çubuğu oluşturulup ayarlandıktan sonra çağrılmalı.
        Başlangıçta waypoint görünürlüğü ile snap ayarlarını senkronize et.
        """
        # Waypoints görünürlüğünü kontrol et ve snap özelliğini buna göre ayarla
        show_waypoints = self.cb_show_waypoints.isChecked()
        
        # Waypoints görünürlüğü ve snap durumu arasındaki ilişkiyi ayarla
        self.cb_snap_waypoint.setEnabled(show_waypoints)
        
        # İlk başlangıçta aktif snap modlarını yeniden hesapla ve gönder
        self.on_snap_mode_checkboxes_toggled()