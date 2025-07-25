from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, 
    QDoubleSpinBox, QPushButton, QWidget, QGridLayout, QMessageBox,
    QTabWidget, QTextEdit, QScrollArea, QSlider, QColorDialog)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor
import math

class PointMergePopupDialog(QDialog):
    """Point Merge düzenleme popup menüsü"""
    pointMergeSettingsChanged = pyqtSignal(dict)
    pointMergeFlipRequested = pyqtSignal(str) # New signal for flip
    pointMergeRemoveRequested = pyqtSignal(str)
    pointMergeExportJsonRequested = pyqtSignal(str)  # CSV yerine artık JSON olarak çalışacak
    pointMergeMoveRequested = pyqtSignal(str)  # Taşıma modu için Route ID'sini gönderir
    pointMergeRotateRequested = pyqtSignal(str)  # Döndürme modu için Route ID'sini gönderir

    def __init__(self, config, parent=None):
        super().__init__(parent)
        # Ensure pattern_type for update
        config['pattern_type'] = 'pointmerge'
        self.config = config.copy()
        
        # Debug: config içeriğini göster
        print(f"Point Merge popup'ı açılıyor, config: {self.config}")
        
        # Normalize segments: if list provided, use its length
        segs = self.config.get('segments', None)
        if isinstance(segs, list):
            segs = len(segs)
        elif not isinstance(segs, int):
            segs = 3
        self.config['segments'] = segs
        
        # Eğer 'first_point_distance' varsa, 'distance' olarak kullan
        if 'first_point_distance' in self.config and 'distance' not in self.config:
            self.config['distance'] = self.config['first_point_distance']
        
        # Eğer 'track_angle' varsa, 'angle' olarak kullan
        if 'track_angle' in self.config and 'angle' not in self.config:
            self.config['angle'] = self.config['track_angle']
        self.setWindowTitle("Point Merge Ayarları")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        # Dragging variables
        self.dragging = False
        self.drag_position = None
        
        # Basit bir border eklemek için stil
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border: 1px solid #cccccc;
                border-radius: 1px;
            }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
            QSpinBox::up-button, QSpinBox::down-button {
                width: 16px;
                border-radius: 2px;
                border: 1px solid #cccccc;
            }
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 2px;
                padding: 4px 8px;
                min-width: 45px;
                text-align: center;
                font-family: Arial; /* İstenen font ailesi */
                font-size: 10px;    /* Font boyutu */
                font-weight: bold; /* Kalınlık: normal, bold, 100-900 arası değerler */
            }
            QPushButton:hover {
                background-color: #e5e5e5;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
            QLabel {
                font-weight: normal;
            }
            QDoubleSpinBox, QSpinBox {
                padding: 2px 4px;
                border: 1px solid #cccccc;
                border-radius: 2px;
            }
            #titleBar {
                background-color: #f0f0f0;
                border-bottom: 1px solid #cccccc;
                padding: 4px;
            }
        """)
        
        # Ana layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(5)
        
        # Başlık çubuğu (sürüklenebilir alan)
        self.title_bar = QWidget()
        self.title_bar.setObjectName("titleBar")
        self.title_bar.setCursor(Qt.SizeAllCursor)  # İşaretçi değişimi
        self.title_bar.setMaximumHeight(30)  # Başlık çubuğu yüksekliği azaltıldı
        
        title_bar_layout = QHBoxLayout(self.title_bar)
        title_bar_layout.setContentsMargins(10, 2, 10, 2)  # Kenar boşlukları azaltıldı
        
        # Başlık
        title_label = QLabel("Point Merge Parameters")
        title_label.setStyleSheet("font-weight: bold; font-size: 12px;")  # Font boyutu küçültüldü
        title_bar_layout.addWidget(title_label)
        title_bar_layout.addStretch()
        
        # Kapat butonu
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-weight: bold;
                min-width: 20px;
            }
            QPushButton:hover {
                background-color: #e81123;
                color: white;
            }
        """)
        self.close_btn.clicked.connect(self.reject)
        title_bar_layout.addWidget(self.close_btn)
        
        layout.addWidget(self.title_bar)
        
        # Tab widget oluştur
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-bottom: none;
                padding: 6px 12px;
                margin-right: 2px;
                font-size: 10px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
            QTabBar::tab:hover {
                background-color: #e5e5e5;
            }
        """)
        
        # Ayarlar sekmesi
        self.settings_tab = QWidget()
        self.create_settings_tab()
        self.tab_widget.addTab(self.settings_tab, "Settings")
        
        # Detay sekmesi
        self.details_tab = QWidget()
        self.create_details_tab()
        self.tab_widget.addTab(self.details_tab, "Details")
        
        layout.addWidget(self.tab_widget)
        
        # Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)
        
        self.update_btn = QPushButton("Update")
        self.update_btn.clicked.connect(self.on_apply)
        self.update_btn.setDefault(True)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.on_export_json)
        
        self.move_btn = QPushButton("Move")
        self.move_btn.clicked.connect(self.on_move)
        self.move_btn.setStyleSheet("QPushButton { background-color: #e6f2ff; text-align: center; }")
        
        self.rotate_btn = QPushButton("Rotate")
        self.rotate_btn.clicked.connect(self.on_rotate)
        self.rotate_btn.setStyleSheet("QPushButton { background-color: #fff2e6; text-align: center; }")

        # Flip button
        self.flip_btn = QPushButton("Flip")
        self.flip_btn.clicked.connect(self.on_flip)
        self.flip_btn.setToolTip("Flip the pattern")
        
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(self.on_remove)
        self.remove_btn.setStyleSheet("QPushButton { background-color: #ffeded; text-align: center; }")
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.update_btn)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.move_btn)
        btn_layout.addWidget(self.rotate_btn)
        btn_layout.addWidget(self.flip_btn)
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        # Buton genişliklerini popup genişliğine göre orantılı olarak ayarla
        buttons = [self.update_btn, self.save_btn, self.move_btn, self.rotate_btn, self.flip_btn, self.cancel_btn, self.remove_btn]
        button_count = len(buttons)
        popup_width = 520  # Popup genişliği artırıldı
        button_space = popup_width - 90  # Kenar boşlukları ve butonlar arası boşluk için çıkarma
        button_width = button_space / button_count
        
        # Tüm butonlar için aynı genişliği uygula
        for btn in buttons:
            btn.setFixedWidth(int(button_width))
            
        layout.addLayout(btn_layout)
        
        self.setFixedSize(520, 320)  # Popup boyutu artırıldı
        
        # Tab değişikliğinde detay sekmesini güncelle
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
    
    def create_settings_tab(self):
        """Ayarlar sekmesini oluşturur"""
    def create_settings_tab(self):
        """Ayarlar sekmesini oluşturur"""
        content_layout = QVBoxLayout(self.settings_tab)
        content_layout.setContentsMargins(10, 10, 10, 10)

        # Parametreler için grid layout
        grid = QGridLayout()
        grid.setVerticalSpacing(8)
        grid.setHorizontalSpacing(10)
        
        grid.addWidget(QLabel("Distance from Merge (NM):"), 0, 0)
        self.distance_spin = QDoubleSpinBox()
        self.distance_spin.setRange(0.1, 100.0)
        self.distance_spin.setSingleStep(0.1)
        self.distance_spin.setDecimals(1)
        self.distance_spin.setFixedWidth(80)
        self.distance_spin.setButtonSymbols(QDoubleSpinBox.UpDownArrows)
        self.distance_spin.setValue(self.config.get('distance', self.config.get('first_point_distance', 15.0)))
        self.distance_spin.valueChanged.connect(self.update_details_tab)
        grid.addWidget(self.distance_spin, 0, 1)
        
        grid.addWidget(QLabel("Track Angle from Merge (°):"), 1, 0)
        self.angle_spin = QDoubleSpinBox()
        self.angle_spin.setRange(0, 360)
        self.angle_spin.setSingleStep(1.0)
        self.angle_spin.setDecimals(1)
        self.angle_spin.setFixedWidth(80)
        self.angle_spin.setButtonSymbols(QDoubleSpinBox.UpDownArrows)
        self.angle_spin.setValue(self.config.get('angle', self.config.get('track_angle', 90.0)))
        self.angle_spin.valueChanged.connect(self.update_details_tab)
        grid.addWidget(self.angle_spin, 1, 1)
        
        grid.addWidget(QLabel("Number of Segments:"), 2, 0)
        self.segments_spin = QSpinBox()
        self.segments_spin.setRange(1, 20)
        self.segments_spin.setFixedWidth(80)
        self.segments_spin.setButtonSymbols(QSpinBox.UpDownArrows)
        self.segments_spin.setValue(self.config.get('segments', self.config.get('num_segments', 3)))
        self.segments_spin.valueChanged.connect(self.update_details_tab)
        grid.addWidget(self.segments_spin, 2, 1)
        
        content_layout.addLayout(grid)
        
        # Görsel ayarlar bölümü
        visual_label = QLabel("Visual Settings:")
        visual_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        content_layout.addWidget(visual_label)
        
        visual_layout = QGridLayout()
        visual_layout.setVerticalSpacing(8)
        visual_layout.setHorizontalSpacing(10)
        
        # Renk ayarı
        visual_layout.addWidget(QLabel("Pattern Color:"), 0, 0)
        self.color_button = QPushButton()
        self.color_button.setFixedSize(40, 25)
        # Config'de renk yoksa varsayılan rengi config'e kaydet
        if 'color' not in self.config:
            self.config['color'] = self.get_default_color()
        current_color = self.config.get('color', self.get_default_color())
        self.color_button.setStyleSheet(f"background-color: {current_color}; border: 1px solid #444444;")
        self.color_button.clicked.connect(self.on_color_changed)
        visual_layout.addWidget(self.color_button, 0, 1)
        
        # Kalınlık ayarı
        visual_layout.addWidget(QLabel("Line Width:"), 1, 0)
        self.width_slider = QSlider(Qt.Horizontal)
        self.width_slider.setRange(1, 6)
        # Config'de width yoksa varsayılan değeri config'e kaydet
        if 'width' not in self.config:
            self.config['width'] = self.get_default_width()
        self.width_slider.setValue(self.config.get('width', self.get_default_width()))
        self.width_slider.valueChanged.connect(self.on_width_changed)
        visual_layout.addWidget(self.width_slider, 1, 1)
        
        self.width_label = QLabel(f"{self.config.get('width', self.get_default_width())}px")
        visual_layout.addWidget(self.width_label, 1, 2)
        
        content_layout.addLayout(visual_layout)
        content_layout.addStretch()
    
    def create_details_tab(self):
        """Detay sekmesini oluşturur"""
        content_layout = QVBoxLayout(self.details_tab)
        content_layout.setContentsMargins(10, 10, 10, 10)
        
        # Scroll area oluştur
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameStyle(QScrollArea.NoFrame)
        
        # Detay içeriği için widget
        self.details_content = QWidget()
        self.details_layout = QVBoxLayout(self.details_content)
        
        # Monospace font oluştur
        mono_font = QFont("Courier New", 9)
        mono_font.setFixedPitch(True)
        
        # Detay text alanı
        self.details_text = QTextEdit()
        self.details_text.setFont(mono_font)
        self.details_text.setReadOnly(True)
        self.details_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f8f8;
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 8px;
                font-family: 'Courier New', monospace;
                font-size: 9px;
                line-height: 1.4;
            }
        """)
        
        self.details_layout.addWidget(self.details_text)
        scroll_area.setWidget(self.details_content)
        content_layout.addWidget(scroll_area)
        
        # İlk detay içeriğini oluştur
        self.update_details_content()
    
    def update_details_tab(self):
        """Ayarlar değiştiğinde detay sekmesini günceller"""
        self.update_details_content()
    
    def on_tab_changed(self, index):
        """Tab değiştiğinde detay sekmesini günceller"""
        if index == 1:  # Detay sekmesi seçildi
            self.update_details_content()
    
    def update_details_content(self):
        """Detay sekmesinin içeriğini günceller"""
        try:
            # Mevcut değerleri al
            distance = self.distance_spin.value()
            angle = self.angle_spin.value()
            segments_count = self.segments_spin.value()
            
            # Detay bilgilerini oluştur
            details = []
            
            # Temel tanımlama bilgileri
            details.append("=== POINT MERGE PATTERN DETAILS ===\n")
            details.append("1. IDENTIFICATION INFORMATION")
            details.append(f"   Pattern ID       : {self.config.get('id', 'N/A')}")
            details.append(f"   Pattern Name     : Point Merge Pattern")
            details.append(f"   Pattern Type     : pointmerge")
            details.append("")
            
            # Yapılandırma parametreleri
            details.append("2. CONFIGURATION PARAMETERS")
            details.append(f"   Distance from Merge : {distance:.1f} NM")
            details.append(f"   Track Angle         : {angle:.1f}°")
            details.append(f"   Number of Segments  : {segments_count}")
            details.append("")
            
            # Coğrafi koordinat bilgileri
            details.append("3. GEOGRAPHIC COORDINATES")
            merge_lat = self.config.get('merge_lat', 'N/A')
            merge_lon = self.config.get('merge_lon', 'N/A')
            details.append(f"   Merge Point Latitude  : {merge_lat}")
            details.append(f"   Merge Point Longitude : {merge_lon}")
            details.append("")
            
            # Geometrik hesaplama sonuçları
            details.append("4. GEOMETRIC CALCULATIONS")
            total_arc_width = 60.0  # Varsayılan yay genişliği
            arc_length_nm = math.radians(total_arc_width) * distance
            segment_distance = arc_length_nm / segments_count if segments_count > 0 else 0
            
            details.append(f"   Arc Width           : {total_arc_width:.1f}°")
            details.append(f"   Total Arc Length    : {arc_length_nm:.2f} NM")
            details.append(f"   Segment Distance    : {segment_distance:.2f} NM")
            details.append("")
            
            # Segment detayları
            details.append("5. SEGMENT DETAILS")
            for i in range(segments_count):
                segment_angle = angle + (i - segments_count//2) * (total_arc_width / segments_count)
                details.append(f"   Segment {i+1:2d}        : Angle {segment_angle:6.1f}°, Distance {distance:.1f} NM")
            
            details.append("")
            
            # Double PMS bilgileri ve waypoint'ler
            details.append("5. DOUBLE PMS CONFIGURATION")
            double_pms_enabled = self.config.get('double_pms_enabled', False)
            details.append(f"   Double PMS Enabled  : {'Yes' if double_pms_enabled else 'No'}")
            
            if double_pms_enabled:
                details.append(f"   Configuration       : Dual Point Merge System")
                details.append(f"   Pattern Complexity  : Enhanced")
                
                # Double PMS için ek parametreler
                base_segment_distance = self.config.get('base_segment_distance', 0)
                details.append(f"   Base Segment Dist   : {base_segment_distance:.1f} NM")
                
                # Double PMS waypoint'lerini hesapla ve göster
                try:
                    from pointmerge import calculate_point_merge_waypoints
                    waypoints_data = calculate_point_merge_waypoints(None, self.config)
                    
                    if waypoints_data:
                        details.append("")
                        details.append("   DOUBLE PMS WAYPOINTS:")
                        
                        # Main leg waypoints
                        main_leg_waypoints = [wp for wp in waypoints_data if wp['name'].startswith('L1')]
                        if main_leg_waypoints:
                            details.append(f"   Main Leg ({len(main_leg_waypoints)} waypoints):")
                            for wp in main_leg_waypoints:
                                details.append(f"   {wp['name']:8s}        : {wp['lat']:9.6f}°, {wp['lon']:10.6f}°")
                        
                        # Double leg waypoints
                        double_leg_waypoints = [wp for wp in waypoints_data if wp['name'].startswith('L2')]
                        if double_leg_waypoints:
                            details.append(f"   Double Leg ({len(double_leg_waypoints)} waypoints):")
                            for wp in double_leg_waypoints:
                                details.append(f"   {wp['name']:8s}        : {wp['lat']:9.6f}°, {wp['lon']:10.6f}°")
                        
                        # Merge point
                        merge_point = [wp for wp in waypoints_data if wp['name'] == 'MP']
                        if merge_point:
                            mp = merge_point[0]
                            details.append(f"   MP              : {mp['lat']:9.6f}°, {mp['lon']:10.6f}° (Merge Point)")
                        
                        # Double PMS sistem bilgileri
                        details.append("")
                        details.append("   DOUBLE PMS SYSTEM PARAMETERS:")
                        first_point_distance = self.config.get('first_point_distance', 0)
                        details.append(f"   Main Leg Radius     : {first_point_distance:.1f} NM")
                        double_leg_radius = first_point_distance - base_segment_distance
                        details.append(f"   Double Leg Radius   : {double_leg_radius:.1f} NM")
                        details.append(f"   Total Waypoints     : {len(waypoints_data)}")
                        
                except Exception as e:
                    details.append(f"   Error calculating waypoints: {str(e)}")
            else:
                details.append(f"   Configuration       : Single Point Merge System")
                details.append(f"   Additional Merge    : Not configured")
                details.append(f"   Pattern Complexity  : Standard")
            
            details.append("")
            
            # Görsel stil bilgileri
            details.append("6. VISUAL STYLE PROPERTIES")
            details.append(f"   Pattern Color    : {self.config.get('color', self.get_default_color())}")
            details.append(f"   Line Width       : {self.config.get('width', self.get_default_width())}px")
            details.append("")
            
            # Durum bilgileri
            details.append("7. STATUS INFORMATION")
            details.append(f"   Pattern Status      : Active")
            details.append(f"   Last Modified       : Current Session")
            details.append(f"   Editable           : Yes")
            
            # Detay metnini güncelle
            self.details_text.setPlainText("\n".join(details))
            
        except Exception as e:
            self.details_text.setPlainText(f"Error generating details: {str(e)}")
    
    def get_default_color(self):
        """Point Merge için varsayılan renk"""
        return '#0066CC'  # Mavi
    
    def get_default_width(self):
        """Point Merge için varsayılan kalınlık"""
        return 2
    
    def on_color_changed(self):
        """Renk değiştiğinde çağrılır"""
        current_color = self.config.get('color', self.get_default_color())
        print(f"Point Merge color dialog opening with current color: {current_color}")
        
        # QColorDialog'u modal olarak aç
        color_dialog = QColorDialog(QColor(current_color), self)
        color_dialog.setOption(QColorDialog.ShowAlphaChannel, False)
        color_dialog.setWindowTitle("Select Point Merge Color")
        color_dialog.setModal(True)  # Modal yap
        
        # Dialog'u göster ve sonucu kontrol et
        if color_dialog.exec_() == QColorDialog.Accepted:
            color = color_dialog.selectedColor()
            if color.isValid():
                color_hex = color.name()
                print(f"Point Merge color changed to: {color_hex}")
                self.config['color'] = color_hex
                self.color_button.setStyleSheet(f"background-color: {color_hex}; border: 1px solid #444444;")
                self.update_details_content()
                # Sadece görsel ayarları güncelle
                self.update_visual_settings_only()
                
                # Popup'ı öne getir
                self.raise_()
                self.activateWindow()
            else:
                print("Point Merge color dialog cancelled")
        else:
            print("Point Merge color dialog cancelled")
            # Popup'ı öne getir
            self.raise_()
            self.activateWindow()
    
    def on_width_changed(self, value):
        """Kalınlık değiştiğinde çağrılır"""
        print(f"Point Merge width changed to: {value}")
        self.config['width'] = value
        self.width_label.setText(f"{value}px")
        self.update_details_content()
        # Sadece görsel ayarları güncelle
        self.update_visual_settings_only()
    
    def update_visual_settings_only(self):
        """Sadece görsel ayarları günceller - geometrik parametreleri değiştirmez"""
        # Sadece mevcut rotanın color ve width değerlerini güncelle
        visual_cfg = self.config.copy()
        visual_cfg.update({
            'color': self.config.get('color', self.get_default_color()),
            'width': self.config.get('width', self.get_default_width()),
            'visual_only_update': True  # Bu bir sadece görsel güncelleme olduğunu belirten flag
        })
        
        print(f"Point Merge visual settings updated: {visual_cfg}")
        self.pointMergeSettingsChanged.emit(visual_cfg)
    
    def on_apply(self):
        """Point merge ayarlarını güncelle"""
        # Debug mesajı
        print("Point Merge güncelleniyor...")
        print(f"Yeni değerler - Distance: {self.distance_spin.value()}, Angle: {self.angle_spin.value()}, Segments: {self.segments_spin.value()}")
        
        # Mevcut config'den tam bir kopyasını oluştur
        updated_cfg = self.config.copy()
        
        # Segment sayısını al
        num_segments = self.segments_spin.value()
        
        # Arayüzden aldığımız yeni değerleri ayarla  
        updated_cfg.update({
            'pattern_type': 'pointmerge',
            # Parametre değerleri
            'distance': self.distance_spin.value(),
            'first_point_distance': self.distance_spin.value(),
            'angle': self.angle_spin.value(),
            'track_angle': self.angle_spin.value(),
            'num_segments': num_segments,
            # Görsel ayarlar
            'color': self.config.get('color', self.get_default_color()),
            'width': self.config.get('width', self.get_default_width()),
        })
        
        # Özellikle 'segments' değerini liste olarak ayarla
        total_arc_width = 60.0  # Varsayılan yay genişliği (derece)
        arc_length_nm = math.radians(total_arc_width) * self.distance_spin.value()
        segment_distance = arc_length_nm / num_segments if num_segments > 0 else arc_length_nm
        updated_cfg['segments'] = [segment_distance] * num_segments
        
        # ID'yi kesinlikle dahil et
        if 'id' in self.config:
            updated_cfg['id'] = self.config['id']
        
        # Kesinlikle merge point koordinatlarını dahil et
        if not 'merge_lat' in updated_cfg or not 'merge_lon' in updated_cfg:
            print("UYARI: Merge koordinatları eksik!")
            
        # Debug bilgisi
        print(f"Güncellenen Point Merge konfigürasyonu: {updated_cfg}")
            
        # Parametre değişim sinyalini gönder
        self.pointMergeSettingsChanged.emit(updated_cfg)
        # popup açık kalsın
    
    def on_flip(self):
        """Emit a signal to flip the route directly."""
        route_id = self.config.get('id')
        if route_id:
            self.pointMergeFlipRequested.emit(route_id)
            self.accept() # Close the dialog

    def on_export_json(self):
        rid = self.config.get('id', '')
        if rid:
            self.pointMergeExportJsonRequested.emit(rid)
        self.accept()
    
    def on_remove(self):
        rid = self.config.get('id', '')
        if rid:
            resp = QMessageBox.question(self, 'Remove PM', 'Remove this Point Merge?', 
                                        QMessageBox.Yes|QMessageBox.No)
            if resp == QMessageBox.Yes:
                self.pointMergeRemoveRequested.emit(rid)
                self.accept()
    
    def on_move(self):
        """Point Merge'i taşıma modunu etkinleştir"""
        rid = self.config.get('id', '')
        if rid:
            self.pointMergeMoveRequested.emit(rid)
            self.accept()  # İşlem sonrası popup'ı kapat
            
    def on_rotate(self):
        """Point Merge'i döndürme modunu etkinleştir"""
        rid = self.config.get('id', '')
        if rid:
            self.pointMergeRotateRequested.emit(rid)
            self.accept()  # İşlem sonrası popup'ı kapat
    
    def mousePressEvent(self, event):
        """Fare tıklama olayını yakala - sadece başlık çubuğundan sürüklenmeye izin ver"""
        if event.button() == Qt.LeftButton and self.title_bar.rect().contains(event.pos()):
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Fare hareket olayını yakala - sürükleme işlemi için"""
        if event.buttons() == Qt.LeftButton and self.dragging:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Fare bırakma olayını yakala - sürükleme işlemini bitir"""
        if event.button() == Qt.LeftButton and self.dragging:
            self.dragging = False
            event.accept()
            # Drag sonrası popup pozisyonunu kaydet
            parent = self.parent()
            if parent and hasattr(parent, 'last_pointmerge_popup_pos'):
                parent.last_pointmerge_popup_pos = self.pos()
        else:
            super().mouseReleaseEvent(event)
