from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QWidget, QMessageBox, QSpinBox, QColorDialog, QTabWidget, QTextEdit)
from PyQt5.QtCore import Qt, pyqtSignal

class RoutePopupDialog(QDialog):
    """User Route düzenleme popup menüsü"""
    routeRemoveRequested = pyqtSignal(str)  # Route ID'sini gönderir
    routeExportJsonRequested = pyqtSignal(str)  # Route ID'sini gönderir - JSON formatında kaydetmek için
    routeMoveRequested = pyqtSignal(str)  # Taşıma modu için Route ID'sini gönderir
    routeRotateRequested = pyqtSignal(str)  # Döndürme modu için Route ID'sini gönderir
    routeColorChanged = pyqtSignal(str, str)  # Route ID ve yeni renk
    routeLineWidthChanged = pyqtSignal(str, int)  # Route ID ve yeni line width

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
                border: 1px solid #cccccc;
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
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        settings_layout.setContentsMargins(10, 10, 10, 0)
        
        # Rota bilgisi
        info_label = QLabel(f"Route: {route_name}")
        info_label.setStyleSheet("font-size: 11px;")
        settings_layout.addWidget(info_label)
        
        # Waypoint sayısı bilgisi
        points = self.config.get('points', [])
        waypoint_count = len(points)
        waypoints_label = QLabel(f"Waypoints: {waypoint_count}")
        waypoints_label.setStyleSheet("font-size: 11px;")
        settings_layout.addWidget(waypoints_label)
        
        # Route style kontrollerini ekle
        self.add_route_style_controls(settings_layout)
        
        # Detay sekmesi
        details_tab = QWidget()
        details_layout = QVBoxLayout(details_tab)
        details_layout.setContentsMargins(10, 10, 10, 10)
        
        # Detay bilgilerini ekle
        self.add_route_details(details_layout)
        
        # Sekmeleri tab widget'a ekle
        self.tab_widget.addTab(settings_tab, "Ayarlar")
        self.tab_widget.addTab(details_tab, "Detay")
        
        # Tab widget'ını ana layout'a ekle
        layout.addWidget(self.tab_widget)
        
        # Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)
        
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
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.move_btn)
        btn_layout.addWidget(self.rotate_btn)
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        # Buton genişliklerini popup genişliğine göre orantılı olarak ayarla
        buttons = [self.save_btn, self.move_btn, self.rotate_btn, self.cancel_btn, self.remove_btn]
        button_count = len(buttons)
        popup_width = 380  # Popup genişliği
        button_space = popup_width - 80  # Kenar boşlukları ve butonlar arası boşluk için çıkarma
        button_width = button_space / button_count
        
        # Tüm butonlar için aynı genişliği uygula
        for btn in buttons:
            btn.setFixedWidth(int(button_width))
            
        # Buton layout'unu ana layout'a ekle
        layout.addLayout(btn_layout)
        
        self.setFixedSize(380, 250)  # Sekme yapısı için boyut artırıldı
    
    def add_route_style_controls(self, layout):
        """Route style kontrollerini ekle"""
        # Route color kontrolü
        color_layout = QHBoxLayout()
        color_label = QLabel("Route Color:")
        color_label.setStyleSheet("font-size: 11px;")
        
        self.color_btn = QPushButton()
        # Mevcut route rengini al
        route_color = self.config.get('color', '#FF0000')
        self.color_btn.setStyleSheet(f"background-color: {route_color}; min-width: 30px; max-width: 30px; min-height: 20px; max-height: 20px;")
        self.color_btn.clicked.connect(self.on_color_change)
        
        color_layout.addWidget(color_label)
        color_layout.addWidget(self.color_btn)
        color_layout.addStretch()
        
        # Route line width kontrolü
        width_layout = QHBoxLayout()
        width_label = QLabel("Line Width:")
        width_label.setStyleSheet("font-size: 11px;")
        
        self.width_spinbox = QSpinBox()
        self.width_spinbox.setMinimum(1)
        self.width_spinbox.setMaximum(10)
        # Mevcut line width'i al
        line_width = self.config.get('line_width', 2)
        self.width_spinbox.setValue(line_width)
        self.width_spinbox.valueChanged.connect(self.on_width_change)
        
        width_layout.addWidget(width_label)
        width_layout.addWidget(self.width_spinbox)
        width_layout.addStretch()
        
        layout.addLayout(color_layout)
        layout.addLayout(width_layout)
        
    def on_color_change(self):
        """Route color değiştiğinde çağrılır"""
        color = QColorDialog.getColor()
        if color.isValid():
            color_hex = color.name()
            self.color_btn.setStyleSheet(f"background-color: {color_hex}; min-width: 30px; max-width: 30px; min-height: 20px; max-height: 20px;")
            # Sinyal emit et
            rid = self.config.get('id', '')
            if rid:
                self.routeColorChanged.emit(rid, color_hex)
                # Detay sekmesini güncelle
                self.update_details_tab()
                
    def on_width_change(self, value):
        """Route line width değiştiğinde çağrılır"""
        rid = self.config.get('id', '')
        if rid:
            self.routeLineWidthChanged.emit(rid, value)
            # Detay sekmesini güncelle
            self.update_details_tab()
    
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

    def add_route_details(self, layout):
        """Route detaylarını ekle"""
        # Route detay bilgilerini göster
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setStyleSheet("font-family: monospace; font-size: 10px;")
        
        # Detay bilgilerini hazırla
        details_content = self.generate_route_details()
        self.details_text.setPlainText(details_content)
        
        layout.addWidget(self.details_text)
        
    def generate_route_details(self):
        """Route detay bilgilerini oluştur"""
        details = []
        
        # Temel bilgiler
        details.append("=== ROUTE DETAILS ===")
        details.append(f"Route ID: {self.config.get('id', 'N/A')}")
        details.append(f"Route Name: {self.config.get('name', 'N/A')}")
        details.append(f"Route Type: {self.config.get('type', 'N/A')}")
        details.append("")
        
        # Waypoint bilgileri
        points = self.config.get('points', [])
        waypoint_names = self.config.get('waypoint_names', [])
        
        if points:
            details.append("=== WAYPOINTS ===")
            for i, point in enumerate(points):
                lat, lon = point
                waypoint_name = waypoint_names[i] if i < len(waypoint_names) else f"WP{i+1}"
                details.append(f"{waypoint_name}: {lat:.6f}, {lon:.6f}")
            details.append("")
        
        # Segment bilgileri
        segment_distances = self.config.get('segment_distances', [])
        segment_angles = self.config.get('segment_angles', [])
        
        if segment_distances:
            details.append("=== SEGMENTS ===")
            for i, distance in enumerate(segment_distances):
                angle = segment_angles[i] if i < len(segment_angles) else 0
                details.append(f"Segment {i+1}: {distance:.2f} NM, {angle:.1f}°")
            details.append("")
        
        # Toplam mesafe
        if segment_distances:
            total_distance = sum(d for d in segment_distances if d > 0)
            details.append(f"Total Distance: {total_distance:.2f} NM")
            details.append("")
        
        # Style bilgileri (UI'dan güncel değerleri al)
        details.append("=== STYLE ===")
        # Renk butonundan güncel rengi al - styleSheet'ten çıkar
        button_style = self.color_btn.styleSheet()
        current_color = "N/A"
        if "background-color:" in button_style:
            # StyleSheet'ten renk kodunu çıkar
            start = button_style.find("background-color:") + len("background-color:")
            end = button_style.find(";", start)
            if end == -1:
                end = len(button_style)
            current_color = button_style[start:end].strip()
        details.append(f"Color: {current_color}")
        details.append(f"Line Width: {self.width_spinbox.value()}")
        details.append("")
        
        # Zaman bilgileri (varsa)
        if 'created_at' in self.config:
            details.append("=== TIMING ===")
            details.append(f"Created: {self.config.get('created_at', 'N/A')}")
            if 'modified_at' in self.config:
                details.append(f"Modified: {self.config.get('modified_at', 'N/A')}")
        
        return "\n".join(details)
    
    def update_details_tab(self):
        """Detay sekmesini günceller"""
        # Yeni detay metnini oluştur
        details_text = self.generate_route_details()
        # Detay metin alanını güncelle
        self.details_text.setPlainText(details_text)
