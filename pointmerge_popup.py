from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, 
    QDoubleSpinBox, QPushButton, QWidget, QGridLayout, QMessageBox, QTabWidget, QTextEdit)
from PyQt5.QtCore import Qt, pyqtSignal
import math

class PointMergePopupDialog(QDialog):
    """Point Merge düzenleme popup menüsü"""
    pointMergeSettingsChanged = pyqtSignal(dict)
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

        # Parametreler için grid layout
        grid = QGridLayout()
        grid.setVerticalSpacing(5)
        grid.setHorizontalSpacing(10)
        
        grid.addWidget(QLabel("Distance from Merge (NM):"), 0, 0)
        self.distance_spin = QDoubleSpinBox()
        self.distance_spin.setRange(0.1, 100.0)
        self.distance_spin.setSingleStep(0.1)
        self.distance_spin.setDecimals(1)  # 1 ondalık basamak (trombone ile aynı)
        self.distance_spin.setFixedWidth(80)  # Genişliği sabit
        self.distance_spin.setButtonSymbols(QDoubleSpinBox.UpDownArrows)  # Yukarı/aşağı oklar
        # Önce 'distance' ile, sonra 'first_point_distance' ile dene
        self.distance_spin.setValue(self.config.get('distance', self.config.get('first_point_distance', 15.0)))
        grid.addWidget(self.distance_spin, 0, 1)
        
        grid.addWidget(QLabel("Track Angle from Merge (°):"), 1, 0)
        self.angle_spin = QDoubleSpinBox()
        self.angle_spin.setRange(0, 360)
        self.angle_spin.setSingleStep(1.0)
        self.angle_spin.setDecimals(1)  # 1 ondalık basamak (trombone ile aynı)
        self.angle_spin.setFixedWidth(80)  # Genişliği sabit  
        self.angle_spin.setButtonSymbols(QDoubleSpinBox.UpDownArrows)  # Yukarı/aşağı oklar
        # Önce 'angle' ile, sonra 'track_angle' ile dene
        self.angle_spin.setValue(self.config.get('angle', self.config.get('track_angle', 90.0)))
        grid.addWidget(self.angle_spin, 1, 1)
        
        grid.addWidget(QLabel("Number of Segments:"), 2, 0)
        self.segments_spin = QSpinBox()
        self.segments_spin.setRange(1, 20)
        self.segments_spin.setFixedWidth(80)  # Genişliği sabit
        self.segments_spin.setButtonSymbols(QSpinBox.UpDownArrows)  # Yukarı/aşağı oklar
        # Önce 'segments', sonra 'num_segments' ile dene
        self.segments_spin.setValue(self.config.get('segments', self.config.get('num_segments', 3)))
        grid.addWidget(self.segments_spin, 2, 1)
        
        settings_layout.addLayout(grid)
        
        # Detay sekmesi
        details_tab = QWidget()
        details_layout = QVBoxLayout(details_tab)
        details_layout.setContentsMargins(10, 10, 10, 10)
        
        # Detay bilgilerini ekle
        self.add_pointmerge_details(details_layout)
        
        # Sekmeleri tab widget'a ekle
        self.tab_widget.addTab(settings_tab, "Ayarlar")
        self.tab_widget.addTab(details_tab, "Detay")
        
        # Tab widget'ını ana layout'a ekle
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
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        # Buton genişliklerini popup genişliğine göre orantılı olarak ayarla
        buttons = [self.update_btn, self.save_btn, self.move_btn, self.rotate_btn, self.cancel_btn, self.remove_btn]
        button_count = len(buttons)
        popup_width = 390  # Popup genişliği
        button_space = popup_width - 90  # Kenar boşlukları ve butonlar arası boşluk için çıkarma
        button_width = button_space / button_count
        
        # Tüm butonlar için aynı genişliği uygula
        for btn in buttons:
            btn.setFixedWidth(int(button_width))
            
        # Buton layout'unu ana layout'a ekle
        layout.addLayout(btn_layout)
        
        self.setFixedSize(390, 250)  # Sekme yapısı için boyut artırıldı
    
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
            # Arayüzden alınan değerleri hem 'distance' hem de 'first_point_distance' olarak kaydet
            'distance': self.distance_spin.value(),
            'first_point_distance': self.distance_spin.value(),
            # Açı değerini hem 'angle' hem de 'track_angle' olarak kaydet
            'angle': self.angle_spin.value(),
            'track_angle': self.angle_spin.value(),
            # Önemli: segments bir liste olmalı - eşit uzaklıkta segmentler oluştur
            'num_segments': num_segments,
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
        
        # Detay sekmesini güncelle
        self.update_details_tab()
        
        # popup açık kalsın
    
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
    
    def add_pointmerge_details(self, layout):
        """Point Merge detaylarını ekle"""
        # Point Merge detay bilgilerini göster
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setStyleSheet("font-family: monospace; font-size: 10px;")
        
        # Detay bilgilerini hazırla
        details_content = self.generate_pointmerge_details()
        self.details_text.setPlainText(details_content)
        
        layout.addWidget(self.details_text)
    
    def update_details_tab(self):
        """Detay sekmesini günceller"""
        # Yeni detay metnini oluştur
        details_text = self.generate_pointmerge_details()
        # Detay metin alanını güncelle
        self.details_text.setPlainText(details_text)
    
    def generate_pointmerge_details(self):
        """Point Merge detay bilgilerini oluştur"""
        details = []
        
        # Temel bilgiler
        details.append("=== POINT MERGE DETAILS ===")
        details.append(f"Pattern ID: {self.config.get('id', 'N/A')}")
        details.append(f"Pattern Name: {self.config.get('name', 'N/A')}")
        details.append(f"Pattern Type: {self.config.get('pattern_type', 'pointmerge')}")
        details.append("")
        
        # Yapılandırma parametreleri (UI'dan güncel değerleri al)
        details.append("=== CONFIGURATION ===")
        details.append(f"Distance from Merge: {self.distance_spin.value():.1f} NM")
        details.append(f"Track Angle: {self.angle_spin.value():.1f}°")
        details.append(f"Number of Segments: {self.segments_spin.value()}")
        details.append("")
        
        # Merge point bilgileri
        merge_point = self.config.get('merge_point', [])
        if merge_point:
            details.append("=== MERGE POINT ===")
            details.append(f"Latitude: {merge_point[0]:.6f}")
            details.append(f"Longitude: {merge_point[1]:.6f}")
            details.append("")
        
        # Waypoint bilgileri
        # Debug: Mevcut config'i kontrol et
        print(f"Point Merge config keys: {list(self.config.keys())}")
        print(f"Points from config: {self.config.get('points', [])}")
        
        # Parent'tan waypoint bilgilerini al
        parent_points = []
        parent = self.parent()
        if parent and hasattr(parent, 'drawn_elements'):
            for route in parent.drawn_elements.get('routes', []):
                if route.get('id') == self.config.get('id'):
                    parent_points = route.get('points', [])
                    print(f"Parent'tan alınan points: {parent_points}")
                    break
        
        points = self.config.get('points', []) or parent_points
        waypoint_names = self.config.get('waypoint_names', [])
        waypoints_found = False
        
        if points:
            details.append("=== WAYPOINTS ===")
            waypoints_found = True
            for i, point in enumerate(points):
                if isinstance(point, (list, tuple)) and len(point) >= 2:
                    lat, lon = point[0], point[1]
                    waypoint_name = waypoint_names[i] if i < len(waypoint_names) else f"WP{i+1}"
                    details.append(f"• {waypoint_name}: {lat:.6f}, {lon:.6f}")
                else:
                    waypoint_name = waypoint_names[i] if i < len(waypoint_names) else f"WP{i+1}"
                    details.append(f"• {waypoint_name}: {point}")
            details.append("")
        
        # Eğer points yoksa diğer olası anahtarları kontrol et
        if not waypoints_found:
            for key, value in self.config.items():
                if 'waypoint' in key.lower() or 'point' in key.lower():
                    print(f"Possible waypoint key found: {key} = {value}")
                    if isinstance(value, list) and value:
                        details.append("=== WAYPOINTS ===")
                        waypoints_found = True
                        for i, item in enumerate(value):
                            if isinstance(item, dict):
                                lat = item.get('lat', 'N/A')
                                lon = item.get('lon', 'N/A')
                                name = item.get('name', f'WP{i+1}')
                                if lat != 'N/A' and lon != 'N/A':
                                    details.append(f"• {name}: {lat:.6f}, {lon:.6f}")
                                else:
                                    details.append(f"• {name}: {lat}, {lon}")
                            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                                lat, lon = item[0], item[1]
                                details.append(f"• WP{i+1}: {lat:.6f}, {lon:.6f}")
                            else:
                                details.append(f"• WP{i+1}: {item}")
                        details.append("")
                        break
        
        if not waypoints_found:
            details.append("=== WAYPOINTS ===")
            details.append("• Henüz tanımlanmamış")
            details.append("")
            print("No waypoints found in any config key!")
        
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
        
        # Zaman bilgileri (varsa)
        if 'created_at' in self.config:
            details.append("=== TIMING ===")
            details.append(f"Created: {self.config.get('created_at', 'N/A')}")
            if 'modified_at' in self.config:
                details.append(f"Modified: {self.config.get('modified_at', 'N/A')}")
        
        return "\n".join(details)
    
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
