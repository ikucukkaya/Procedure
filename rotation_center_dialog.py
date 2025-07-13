from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QWidget, QRadioButton, QButtonGroup, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal

class RotationCenterDialog(QDialog):
    """Rota döndürme merkezi seçimi için dialog"""
    rotationCenterSelected = pyqtSignal(int)  # Seçilen nokta indeksi

    def __init__(self, route_points, parent=None):
        super().__init__(parent)
        self.route_points = route_points
        self.selected_point_index = 0  # Varsayılan olarak ilk nokta
        
        self.setWindowTitle("Döndürme Merkezi Seçimi")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        
        # Dragging variables
        self.dragging = False
        self.drag_position = None
        
        # Stil
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
        self.title_bar.setCursor(Qt.SizeAllCursor)
        self.title_bar.setMaximumHeight(30)
        
        title_bar_layout = QHBoxLayout(self.title_bar)
        title_bar_layout.setContentsMargins(10, 2, 10, 2)
        
        # Başlık
        title_label = QLabel("Döndürme Merkez Noktası Seçimi")
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
        
        # İçerik alanı
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(15, 10, 15, 10)
        
        # Açıklama
        info_label = QLabel("Rotayı hangi nokta etrafında döndürmek istiyorsunuz?")
        info_label.setWordWrap(True)
        content_layout.addWidget(info_label)
        
        # Nokta seçim radio butonları
        self.radio_group = QButtonGroup(self)
        
        # Waypoint sayısına göre radio butonları oluştur
        for i, (lat, lon) in enumerate(self.route_points):
            radio_btn = QRadioButton(f"Waypoint {i+1} (Lat: {lat:.6f}, Lon: {lon:.6f})")
            self.radio_group.addButton(radio_btn, i)
            content_layout.addWidget(radio_btn)
            
            # İlk noktayı varsayılan olarak seç
            if i == 0:
                radio_btn.setChecked(True)
        
        # İçerik widget'ını ana layout'a ekle
        layout.addWidget(content_widget)
        
        # Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(15, 0, 15, 10)
        btn_layout.setSpacing(10)
        
        self.ok_btn = QPushButton("Tamam")
        self.ok_btn.clicked.connect(self.on_ok)
        self.ok_btn.setStyleSheet("QPushButton { background-color: #e6f2ff; }")
        
        self.cancel_btn = QPushButton("İptal")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        
        # Dialog boyutu - waypoint sayısına göre boyutlandır
        height = 150 + min(len(self.route_points) * 30, 200)  # Maksimum 200px ekstra yükseklik
        self.setFixedSize(400, height)
        
    def on_ok(self):
        """Seçimi onayla"""
        selected_id = self.radio_group.checkedId()
        if selected_id >= 0 and selected_id < len(self.route_points):
            self.selected_point_index = selected_id
            self.rotationCenterSelected.emit(selected_id)
            self.accept()
        else:
            QMessageBox.warning(self, "Seçim Hatası", "Lütfen döndürme merkezi için bir nokta seçin.")
    
    def mousePressEvent(self, event):
        """Fare tıklama olayını yakala - sadece başlık çubuğundan sürüklenmeye izin ver"""
        if event.button() == Qt.LeftButton and self.title_bar.rect().contains(event.pos()):
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Fare hareket olayını yakala - sürükleme için"""
        if event.buttons() == Qt.LeftButton and self.dragging:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Fare bırakma olayını yakala - sürüklemeyi sonlandır"""
        self.dragging = False
        super().mouseReleaseEvent(event)