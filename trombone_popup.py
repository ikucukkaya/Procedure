from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                          QPushButton, QWidget, QGridLayout, QFrame, QDoubleSpinBox,
                          QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtGui import QPalette, QColor, QDoubleValidator

class TrombonePopupDialog(QDialog):
    """Trombone özelliklerini düzenlemek için açılan hızlı menü"""
    
    # Trombone güncelleme sinyali
    tromboneSettingsChanged = pyqtSignal(dict)
    # Trombone silme sinyali
    tromboneRemoveRequested = pyqtSignal(str)
    # Trombone export sinyali (artık JSON olarak)
    tromboneExportJsonRequested = pyqtSignal(str)
    # Trombone taşıma sinyali
    tromboneMoveRequested = pyqtSignal(str)  # Taşıma modu için Route ID'sini gönderir
    # Trombone döndürme sinyali
    tromboneRotateRequested = pyqtSignal(str)  # Döndürme modu için Route ID'sini gönderir
    
    def __init__(self, trombone_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Trombone Ayarları")
        # Popup yerine normal dialog formunu kullan ve çerçevesiz olsun
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        
        # Sürükleme için gerekli değişkenler
        self.dragging = False
        self.drag_position = None
        
        # Trombone taşındı veya döndürüldü mü kontrolü
        self.moved_or_rotated = trombone_config.get('moved_or_rotated', False)
        
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
            QLineEdit, QDoubleSpinBox, QSpinBox {
                padding: 2px 4px;
                border: 1px solid #cccccc;
                border-radius: 2px;
            }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
            QSpinBox::up-button, QSpinBox::down-button {
                width: 16px;
                border-radius: 2px;
                border: 1px solid #cccccc;
            }
            #titleBar {
                background-color: #f0f0f0;
                border-bottom: 1px solid #cccccc;
                padding: 4px;
            }
        """)
        
        # Trombone konfigürasyonunu sakla
        self.trombone_config = trombone_config
        
        # Ana layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 10)
        self.layout.setSpacing(5)
        
        # Başlık çubuğu (sürüklenebilir alan)
        self.title_bar = QWidget()
        self.title_bar.setObjectName("titleBar")
        self.title_bar.setCursor(Qt.SizeAllCursor)  # İşaretçi değişimi
        self.title_bar.setMaximumHeight(30)  # Başlık çubuğu yüksekliği azaltıldı
        
        title_bar_layout = QHBoxLayout(self.title_bar)
        title_bar_layout.setContentsMargins(10, 2, 10, 2)  # Kenar boşlukları azaltıldı
        
        # Başlık
        title_label = QLabel("Trombone Ayarları")
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
        
        self.layout.addWidget(self.title_bar)
        
        # İçerik alanı
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 10, 10, 0)
        
        # Parametreler için grid layout
        param_layout = QGridLayout()
        param_layout.setVerticalSpacing(5)
        param_layout.setHorizontalSpacing(10)
        
        # Threshold Distance
        param_layout.addWidget(QLabel("Threshold Distance (NM):"), 0, 0)
        self.threshold_distance = QDoubleSpinBox()
        self.threshold_distance.setRange(0.1, 100.0)
        self.threshold_distance.setSingleStep(0.1)
        self.threshold_distance.setDecimals(1)
        self.threshold_distance.setFixedWidth(80)  # Sabit genişlik
        self.threshold_distance.setButtonSymbols(QDoubleSpinBox.UpDownArrows)  # Yukarı/aşağı oklar
        self.threshold_distance.setValue(trombone_config.get('threshold_distance', 2.0))
        param_layout.addWidget(self.threshold_distance, 0, 1)
        
        # Base Angle
        param_layout.addWidget(QLabel("Base Angle (°):"), 1, 0)
        self.base_angle = QDoubleSpinBox()
        self.base_angle.setRange(-180.0, 180.0)
        self.base_angle.setSingleStep(1.0)
        self.base_angle.setDecimals(1)
        self.base_angle.setFixedWidth(80)  # Sabit genişlik
        self.base_angle.setButtonSymbols(QDoubleSpinBox.UpDownArrows)  # Yukarı/aşağı oklar
        self.base_angle.setValue(trombone_config.get('base_angle', 90.0))
        param_layout.addWidget(self.base_angle, 1, 1)
        
        # Base Distance
        param_layout.addWidget(QLabel("Base Distance (NM):"), 2, 0)
        self.base_distance = QDoubleSpinBox()
        self.base_distance.setRange(0.1, 100.0)
        self.base_distance.setSingleStep(0.1)
        self.base_distance.setDecimals(1)
        self.base_distance.setFixedWidth(80)  # Sabit genişlik
        self.base_distance.setButtonSymbols(QDoubleSpinBox.UpDownArrows)  # Yukarı/aşağı oklar
        self.base_distance.setValue(trombone_config.get('base_distance', 5.0))
        param_layout.addWidget(self.base_distance, 2, 1)
        
        # Extension Length
        param_layout.addWidget(QLabel("Extension Length (NM):"), 3, 0)
        self.extension_length = QDoubleSpinBox()
        self.extension_length.setRange(0.1, 100.0)
        self.extension_length.setSingleStep(0.1)
        self.extension_length.setDecimals(1)
        self.extension_length.setFixedWidth(80)  # Sabit genişlik
        self.extension_length.setButtonSymbols(QDoubleSpinBox.UpDownArrows)  # Yukarı/aşağı oklar
        self.extension_length.setValue(trombone_config.get('extension_length', 3.0))
        param_layout.addWidget(self.extension_length, 3, 1)
        
        # Eğer rota taşındı veya döndürüldüyse tüm parametre alanlarını devre dışı bırak
        if self.moved_or_rotated:
            # Uyarı mesajı ekle (iki satır olarak)
            warning_layout = QVBoxLayout()
            warning_layout.setSpacing(0)
            warning_label1 = QLabel("Bu rota taşındı veya döndürüldü.")
            warning_label2 = QLabel("Parametre değişikliği devre dışı.")
            warning_label1.setStyleSheet("color: red; font-style: italic; font-size: 10px;")
            warning_label2.setStyleSheet("color: red; font-style: italic; font-size: 10px;")
            warning_layout.addWidget(warning_label1)
            warning_layout.addWidget(warning_label2)
            content_layout.addLayout(warning_layout)
            
            # Tüm düzenleme alanlarını devre dışı bırak
            self.threshold_distance.setEnabled(False)
            self.base_angle.setEnabled(False)
            self.base_distance.setEnabled(False)
            self.extension_length.setEnabled(False)
        
        content_layout.addLayout(param_layout)
        
        # Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)
        
        self.apply_btn = QPushButton("Update")
        self.apply_btn.clicked.connect(self.on_apply)
        self.apply_btn.setDefault(True)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.on_export_json)
        
        self.move_btn = QPushButton("Move")
        self.move_btn.clicked.connect(self.on_move)
        self.move_btn.setStyleSheet("QPushButton { background-color: #e6f2ff; text-align: center; }")
        
        self.rotate_btn = QPushButton("Rotate")
        self.rotate_btn.clicked.connect(self.on_rotate)
        self.rotate_btn.setStyleSheet("QPushButton { background-color: #fff2e6; text-align: center; }")
        
        # Eğer rota taşındı veya döndürüldüyse Güncelleme butonunu devre dışı bırak
        if self.moved_or_rotated:
            self.apply_btn.setEnabled(False)
            self.apply_btn.setToolTip("Taşınmış veya döndürülmüş rotaların parametreleri değiştirilemez")
        
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(self.on_remove)
        self.remove_btn.setStyleSheet("QPushButton { background-color: #ffeded; }")
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.apply_btn)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.move_btn)
        btn_layout.addWidget(self.rotate_btn)
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        content_layout.addLayout(btn_layout)
        
        # İçerik widget'ını ana layout'a ekle
        self.layout.addWidget(content_widget)
        
        # Buton genişliklerini popup genişliğine göre orantılı olarak ayarla
        buttons = [self.apply_btn, self.save_btn, self.move_btn, self.rotate_btn, self.cancel_btn, self.remove_btn]
        button_count = len(buttons)
        popup_width = 390  # Popup genişliği
        button_space = popup_width - 90  # Kenar boşlukları ve butonlar arası boşluk için çıkarma
        button_width = button_space / button_count
        
        # Tüm butonlar için aynı genişliği uygula
        for btn in buttons:
            btn.setFixedWidth(int(button_width))
        
        # Özellikle Remove butonunu özelleştir
        self.remove_btn.setStyleSheet("QPushButton { background-color: #ffeded; text-align: center; }")
        
        # Sabit bir boyut ayarla - Move butonu eklendiğinden biraz daha geniş
        self.setFixedSize(390, 200)
    
    def on_apply(self):
        """Değişiklikleri uygula"""
        # Güncellenecek değerleri al
        threshold_distance = self.threshold_distance.value()
        base_angle = self.base_angle.value()
        base_distance = self.base_distance.value()
        extension_length = self.extension_length.value()
        
        # Değerleri logla ve config'i güncelle
        print(f"Trombone güncellemesi:")
        print(f" - threshold_distance: {threshold_distance} NM (A noktası pistten bu kadar uzakta)")
        print(f" - base_angle: {base_angle}° (A'dan B'ye olan açı)")
        print(f" - base_distance: {base_distance} NM (A'dan B'ye olan mesafe)")
        print(f" - extension_length: {extension_length} NM (B'den C'ye olan mesafe)")
        
        # Güncel config'i oluştur 
        updated_config = {
            'threshold_distance': threshold_distance,
            'base_angle': base_angle,
            'base_distance': base_distance,
            'extension_length': extension_length
        }
        
        # Diğer konfigürasyon değerlerini koru
        for key, value in self.trombone_config.items():
            if key not in updated_config:
                updated_config[key] = value
        
        # Ensure runway data is present for update calculations
        if 'runway' not in updated_config and 'runway' in self.trombone_config:
            updated_config['runway'] = self.trombone_config['runway']
            
        # Runway verisini kontrol et ve iyileştir (CSV yüklemelerinde önemli)
        if 'runway' in updated_config:
            runway_data = updated_config['runway']
            
            # Koordinatların varlığını kontrol et
            if ('threshold_lat' in runway_data and 'threshold_lon' in runway_data and
                ('start_lat' not in runway_data or 'start_lon' not in runway_data)):
                # Threshold verilerini start için kullan
                runway_data['start_lat'] = runway_data['threshold_lat']
                runway_data['start_lon'] = runway_data['threshold_lon']
                print("Trombone güncellemesi: Eksik start koordinatları threshold'dan alındı")
        else:
            # Runway verisi hiç yoksa, güvenli bir basit yapı oluştur
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Warning", "No runway data found. Update may not work correctly.")
            print("Trombone güncellemesi: Runway verisi eksik!")
            
        # Trombone ID'sini ve tipini mutlaka ekleyelim
        updated_config['id'] = self.trombone_config.get('id', '')
        updated_config['pattern_type'] = 'trombone'  # Tip her zaman trombone olmalı
        
        # Orijinal ID boş değilse devam et
        if updated_config['id']:
            try:
                # Sinyali emit et
                self.tromboneSettingsChanged.emit(updated_config)
                print("Trombone update signal sent successfully")
            except Exception as e:
                from PyQt5.QtWidgets import QMessageBox
                error_msg = f"Error updating trombone: {str(e)}"
                QMessageBox.warning(self, "Update Error", error_msg)
                print(f"Error during trombone update: {e}")
                import traceback
                traceback.print_exc()
        else:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", "No valid ID found for this trombone.")
        # popup open; do not close
    
    def on_export_json(self):
        """Route'u JSON olarak kaydetmek için sinyal gönder"""
        route_id = self.trombone_config.get('id', '')
        if route_id:
            self.tromboneExportJsonRequested.emit(route_id)
        # dialog kapanabilir
        self.accept()
    
    def on_remove(self):
        """Trombone'u kaldır"""
        if 'id' in self.trombone_config:
            from PyQt5.QtWidgets import QMessageBox
            reply = QMessageBox.question(self, 'Trombone Sil', 
                                      'Bu trombone\'u silmek istediğinize emin misiniz?',
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                # Silme sinyalini gönder
                self.tromboneRemoveRequested.emit(self.trombone_config['id'])
                self.accept()
        else:
            self.reject()
    
    def on_move(self):
        """Trombone'u taşıma modunu etkinleştir"""
        route_id = self.trombone_config.get('id', '')
        if route_id:
            # pattern_type'ın trombone olduğunu teyit edelim
            self.trombone_config['pattern_type'] = 'trombone'
            
            # ID uyumluluğunu kontrol et ve düzelt
            if not route_id.startswith("trombone_") and "_" in route_id:
                print(f"UYARI: Trombone ID'si ({route_id}) 'trombone_' önekiyle başlamıyor.")
                # ID'yi koruyalım ama daha açıklayıcı debug mesajı yazalım
            
            # Trombone ID'si ve konfigürasyonu hakkında daha fazla bilgi yazdır
            print(f"Trombone taşıma modu başlatılıyor, ID: {route_id}")
            print(f"Trombone config: {self.trombone_config}")
            
            self.tromboneMoveRequested.emit(route_id)
            self.accept()  # İşlem sonrası popup'ı kapat
        else:
            print("Hata: Trombone taşıma için geçerli bir ID bulunamadı")
            
    def on_rotate(self):
        """Trombone'u döndürme modunu etkinleştir"""
        route_id = self.trombone_config.get('id', '')
        if route_id:
            # pattern_type'ın trombone olduğunu teyit edelim
            self.trombone_config['pattern_type'] = 'trombone'
            
            # ID uyumluluğunu kontrol et ve düzelt
            if not route_id.startswith("trombone_") and "_" in route_id:
                print(f"UYARI: Trombone ID'si ({route_id}) 'trombone_' önekiyle başlamıyor.")
                # ID'yi koruyalım ama daha açıklayıcı debug mesajı yazalım
            
            # Trombone ID'si ve konfigürasyonu hakkında daha fazla bilgi yazdır
            print(f"Trombone döndürme modu başlatılıyor, ID: {route_id}")
            print(f"Trombone config: {self.trombone_config}")
            
            self.tromboneRotateRequested.emit(route_id)
            self.accept()  # İşlem sonrası popup'ı kapat
        else:
            print("Hata: Trombone döndürme için geçerli bir ID bulunamadı")
    
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
        if event.button() == Qt.LeftButton:
            self.dragging = False
            event.accept()
            # Drag sonrası popup pozisyonunu kaydet
            parent = self.parent()
            if parent and hasattr(parent, 'last_trombone_popup_pos'):
                parent.last_trombone_popup_pos = self.pos()
        else:
            super().mouseReleaseEvent(event)