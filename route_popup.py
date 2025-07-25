from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QWidget, QMessageBox, QTabWidget, QTextEdit, QScrollArea,
    QGridLayout, QSlider, QColorDialog)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor
import math

class RoutePopupDialog(QDialog):
    """User Route düzenleme popup menüsü"""
    routeSettingsChanged = pyqtSignal(dict)  # Route ayarları güncellemesi için
    routeRemoveRequested = pyqtSignal(str)  # Route ID'sini gönderir
    routeExportJsonRequested = pyqtSignal(str)  # Route ID'sini gönderir - JSON formatında kaydetmek için
    routeMoveRequested = pyqtSignal(str)  # Taşıma modu için Route ID'sini gönderir
    routeRotateRequested = pyqtSignal(str)  # Döndürme modu için Route ID'sini gönderir

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config.copy()
        
        # Debug: config içeriğini göster
        print(f"Route popup'ı açılıyor, config: {self.config}")
        
        self.setWindowTitle("Route Options")
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
        self.title_bar.setMaximumHeight(30)  # Başlık çubuğu yüksekliği
        
        title_bar_layout = QHBoxLayout(self.title_bar)
        title_bar_layout.setContentsMargins(10, 2, 10, 2)  # Kenar boşlukları
        
        # Başlık
        route_name = self.config.get('name', 'Route')
        title_label = QLabel(f"{route_name} Options")
        title_label.setStyleSheet("font-weight: bold; font-size: 12px;")
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
        self.update_btn.clicked.connect(self.on_update)
        self.update_btn.setDefault(True)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.on_export_json)
        
        self.move_btn = QPushButton("Move")
        self.move_btn.clicked.connect(self.on_move)
        self.move_btn.setStyleSheet("QPushButton { background-color: #e6f2ff; text-align: center; }")
        
        self.rotate_btn = QPushButton("Rotate")
        self.rotate_btn.clicked.connect(self.on_rotate)
        self.rotate_btn.setStyleSheet("QPushButton { background-color: #fff2e6; text-align: center; }")
        
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(self.on_remove)
        self.remove_btn.setStyleSheet("QPushButton { background-color: #ffeded; text-align: center; }")
        
        self.cancel_btn = QPushButton("Close")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.update_btn)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.move_btn)
        btn_layout.addWidget(self.rotate_btn)
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        # Buton genişliklerini popup genişliğine göre orantılı olarak ayarla
        buttons = [self.update_btn, self.save_btn, self.move_btn, self.rotate_btn, self.cancel_btn, self.remove_btn]
        button_count = len(buttons)
        popup_width = 480  # Popup genişliği
        button_space = popup_width - 80  # Kenar boşlukları ve butonlar arası boşluk için çıkarma
        button_width = button_space / button_count
        
        # Tüm butonlar için aynı genişliği uygula
        for btn in buttons:
            btn.setFixedWidth(int(button_width))
            
        layout.addLayout(btn_layout)
        
        self.setFixedSize(480, 350)  # Popup boyutu artırıldı
        
        # Tab değişikliğinde detay sekmesini güncelle
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
    
    def create_settings_tab(self):
        """Ayarlar sekmesini oluşturur"""
        content_layout = QVBoxLayout(self.settings_tab)
        content_layout.setContentsMargins(10, 10, 10, 10)
        
        # Rota bilgisi
        route_name = self.config.get('name', 'Route')
        info_label = QLabel(f"Route: {route_name}")
        info_label.setStyleSheet("font-size: 11px; font-weight: bold;")
        content_layout.addWidget(info_label)
        
        # Waypoint sayısı bilgisi
        points = self.config.get('points', [])
        waypoint_count = len(points)
        waypoints_label = QLabel(f"Waypoints: {waypoint_count}")
        waypoints_label.setStyleSheet("font-size: 11px;")
        content_layout.addWidget(waypoints_label)
        
        # Görsel ayarlar
        visual_settings_layout = QGridLayout()
        visual_settings_layout.setVerticalSpacing(8)
        visual_settings_layout.setHorizontalSpacing(10)
        
        # Renk ayarı
        visual_settings_layout.addWidget(QLabel("Route Color:"), 0, 0)
        self.color_button = QPushButton()
        self.color_button.setFixedSize(40, 25)
        # Config'de renk yoksa varsayılan rengi config'e kaydet
        if 'color' not in self.config:
            self.config['color'] = self.get_default_color()
        current_color = self.config.get('color', self.get_default_color())
        self.color_button.setStyleSheet(f"background-color: {current_color}; border: 1px solid #444444;")
        self.color_button.clicked.connect(self.on_color_changed)
        visual_settings_layout.addWidget(self.color_button, 0, 1)
        
        # Kalınlık ayarı
        visual_settings_layout.addWidget(QLabel("Line Width:"), 1, 0)
        self.width_slider = QSlider(Qt.Horizontal)
        self.width_slider.setRange(1, 8)
        # Config'de width yoksa varsayılan değeri config'e kaydet
        if 'width' not in self.config:
            self.config['width'] = self.get_default_width()
        self.width_slider.setValue(self.config.get('width', self.get_default_width()))
        self.width_slider.valueChanged.connect(self.on_width_changed)
        visual_settings_layout.addWidget(self.width_slider, 1, 1)
        
        self.width_label = QLabel(f"{self.config.get('width', self.get_default_width())}px")
        visual_settings_layout.addWidget(self.width_label, 1, 2)
        
        content_layout.addLayout(visual_settings_layout)
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
    
    def on_color_changed(self):
        """Renk değiştiğinde çağrılır"""
        current_color = self.config.get('color', self.get_default_color())
        print(f"Color dialog opening with current color: {current_color}")
        
        # QColorDialog'u modal olarak aç
        color_dialog = QColorDialog(QColor(current_color), self)
        color_dialog.setOption(QColorDialog.ShowAlphaChannel, False)
        color_dialog.setWindowTitle("Select Route Color")
        color_dialog.setModal(True)  # Modal yap
        
        # Dialog'u göster ve sonucu kontrol et
        if color_dialog.exec_() == QColorDialog.Accepted:
            color = color_dialog.selectedColor()
            if color.isValid():
                color_hex = color.name()
                print(f"Color changed to: {color_hex}")
                self.config['color'] = color_hex
                self.color_button.setStyleSheet(f"background-color: {color_hex}; border: 1px solid #444444;")
                self.update_details_content()
                
                # Popup'ı öne getir
                self.raise_()
                self.activateWindow()
            else:
                print("Color dialog cancelled")
        else:
            print("Color dialog cancelled")
            # Popup'ı öne getir
            self.raise_()
            self.activateWindow()
    
    def on_width_changed(self, value):
        """Kalınlık değiştiğinde çağrılır"""
        print(f"Width changed to: {value}")
        self.config['width'] = value
        self.width_label.setText(f"{value}px")
        self.update_details_content()
    
    def on_tab_changed(self, index):
        """Tab değiştiğinde detay sekmesini günceller"""
        if index == 1:  # Detay sekmesi seçildi
            self.update_details_content()
    
    def update_details_content(self):
        """Detay sekmesinin içeriğini günceller"""
        try:
            # Debug: points yapısını kontrol et
            points = self.config.get('points', [])
            print(f"Points type: {type(points)}")
            if points:
                print(f"First point type: {type(points[0])}")
                print(f"First point content: {points[0]}")
            
            # Detay bilgilerini oluştur
            details = []
            
            # Temel tanımlama bilgileri
            details.append("=== ROUTE DETAILS ===\n")
            details.append("1. ROUTE IDENTIFICATION")
            details.append(f"   Route ID         : {self.config.get('id', 'N/A')}")
            details.append(f"   Route Name       : {self.config.get('name', 'N/A')}")
            details.append(f"   Route Type       : User Route")
            details.append("")
            
            # Navigasyon bilgileri
            details.append("2. NAVIGATION INFORMATION")
            details.append(f"   Total Waypoints  : {len(points)}")
            details.append("")
            
            if points:
                details.append("   Waypoint Details:")
                total_distance = 0
                for i, point in enumerate(points):
                    # Points tuple ise (lat, lon) formatında
                    if isinstance(point, tuple) and len(point) >= 2:
                        lat, lon = point[0], point[1]
                    # Points dict ise
                    elif isinstance(point, dict):
                        lat = point.get('lat', 0)
                        lon = point.get('lon', 0)
                    else:
                        lat, lon = 0, 0
                        
                    details.append(f"   WP{i+1:2d}             : {lat:9.6f}°, {lon:10.6f}°")
                    
                    # Mesafe hesaplama (bir sonraki waypoint'e kadar)
                    if i < len(points) - 1:
                        next_point = points[i + 1]
                        if isinstance(next_point, tuple) and len(next_point) >= 2:
                            next_lat, next_lon = next_point[0], next_point[1]
                        elif isinstance(next_point, dict):
                            next_lat = next_point.get('lat', 0)
                            next_lon = next_point.get('lon', 0)
                        else:
                            next_lat, next_lon = 0, 0
                        
                        # Haversine formula ile mesafe hesaplama
                        distance = self.calculate_distance(lat, lon, next_lat, next_lon)
                        total_distance += distance
                        
                        # Bearing hesaplama
                        bearing = self.calculate_bearing(lat, lon, next_lat, next_lon)
                        details.append(f"                    → Distance: {distance:6.2f} NM, Bearing: {bearing:6.1f}°")
                
                details.append("")
                details.append("3. GEOMETRIC PROPERTIES")
                details.append(f"   Total Route Length : {total_distance:.2f} NM")
            
            # Görsel stil bilgileri
            details.append("")
            details.append("4. VISUAL STYLE PROPERTIES")
            details.append(f"   Route Color      : {self.config.get('color', self.get_default_color())}")
            details.append(f"   Line Width       : {self.config.get('width', self.get_default_width())}px")
            details.append("")
            
            # Zaman damgaları
            details.append("5. TIMESTAMPS")
            details.append(f"   Created          : Current Session")
            details.append(f"   Last Modified    : Current Session")
            details.append("")
            
            # Durum bilgileri
            details.append("6. STATUS INFORMATION")
            details.append(f"   Route Status     : Active")
            details.append(f"   Editable         : Yes")
            details.append(f"   Exportable       : Yes")
            
            # Detay metnini güncelle
            self.details_text.setPlainText("\n".join(details))
            
        except Exception as e:
            self.details_text.setPlainText(f"Error generating details: {str(e)}")
    
    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """İki nokta arasındaki mesafeyi nautical mile cinsinden hesaplar"""
        # Haversine formula
        R = 3440.065  # Dünya yarıçapı nautical mile cinsinden
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def calculate_bearing(self, lat1, lon1, lat2, lon2):
        """İki nokta arasındaki bearing'i hesaplar"""
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lon = math.radians(lon2 - lon1)
        
        y = math.sin(delta_lon) * math.cos(lat2_rad)
        x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon)
        
        bearing = math.atan2(y, x)
        bearing = math.degrees(bearing)
        bearing = (bearing + 360) % 360
        
        return bearing
    
    def get_default_color(self):
        """Route için varsayılan renk"""
        return '#800080'  # Mor
    
    def get_default_width(self):
        """Route için varsayılan kalınlık"""
        return 2
    
    def on_update(self):
        """Route ayarlarını güncelle"""
        # Güncellenmiş konfigürasyonu oluştur
        updated_config = self.config.copy()
        updated_config.update({
            'color': self.config.get('color', self.get_default_color()),
            'width': self.config.get('width', self.get_default_width())
        })
        
        # Route güncellemesi sinyalini gönder
        self.routeSettingsChanged.emit(updated_config)
        print(f"Route settings updated: {updated_config}")
        
    def on_export_json(self):
        """Rotayı JSON olarak kaydet"""
        rid = self.config.get('id', '')
        if rid:
            self.routeExportJsonRequested.emit(rid)
        self.accept()
    
    def on_remove(self):
        """Rotayı kaldır"""
        rid = self.config.get('id', '')
        if rid:
            resp = QMessageBox.question(self, 'Remove Route', 'Remove this route?', 
                                        QMessageBox.Yes|QMessageBox.No)
            if resp == QMessageBox.Yes:
                self.routeRemoveRequested.emit(rid)
                self.accept()
    
    def on_move(self):
        """Rotayı taşıma modunu etkinleştir"""
        rid = self.config.get('id', '')
        if rid:
            self.routeMoveRequested.emit(rid)
            self.accept()  # İşlem sonrası popup'ı kapat
            
    def on_rotate(self):
        """Rotayı döndürme modunu etkinleştir"""
        rid = self.config.get('id', '')
        if rid:
            self.routeRotateRequested.emit(rid)
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
            if parent and hasattr(parent, 'last_route_popup_pos'):
                parent.last_route_popup_pos = self.pos()
        else:
            super().mouseReleaseEvent(event)
