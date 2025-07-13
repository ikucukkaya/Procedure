from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QWidget, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal

class RoutePopupDialog(QDialog):
    """User Route düzenleme popup menüsü"""
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
        
        # İçerik alanı
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 10, 10, 0)
        
        # Rota bilgisi
        info_label = QLabel(f"Route: {route_name}")
        info_label.setStyleSheet("font-size: 11px;")
        content_layout.addWidget(info_label)
        
        # Waypoint sayısı bilgisi
        points = self.config.get('points', [])
        waypoint_count = len(points)
        waypoints_label = QLabel(f"Waypoints: {waypoint_count}")
        waypoints_label.setStyleSheet("font-size: 11px;")
        content_layout.addWidget(waypoints_label)
        
        # İçerik widget'ını ana layout'a ekle
        layout.addWidget(content_widget)
        
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
            
        content_layout.addLayout(btn_layout)
        
        self.setFixedSize(380, 150)  # Rotate butonu eklendiğinden biraz daha geniş
    
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
