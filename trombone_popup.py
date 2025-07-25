from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                          QPushButton, QWidget, QGridLayout, QFrame, QDoubleSpinBox,
                          QMessageBox, QTabWidget, QTextEdit, QScrollArea, QSlider, QColorDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtGui import QPalette, QColor, QDoubleValidator, QFont

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
        
        self.layout.addWidget(self.tab_widget)
        
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
        buttons = [self.update_btn, self.save_btn, self.move_btn, self.rotate_btn, self.remove_btn, self.cancel_btn]
        button_count = len(buttons)
        popup_width = 520  # Popup genişliği
        button_space = popup_width - 90  # Kenar boşlukları ve butonlar arası boşluk için çıkarma
        button_width = button_space / button_count
        
        # Tüm butonlar için aynı genişliği uygula
        for btn in buttons:
            btn.setFixedWidth(int(button_width))
            
        self.layout.addLayout(btn_layout)
        
        self.setFixedSize(520, 380)  # Popup boyutu artırıldı
        
        # Tab değişikliğinde detay sekmesini güncelle
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
    
    def create_settings_tab(self):
        """Ayarlar sekmesini oluşturur"""
        content_layout = QVBoxLayout(self.settings_tab)
        content_layout.setContentsMargins(10, 10, 10, 10)
        
        # Parametreler için grid layout
        param_layout = QGridLayout()
        param_layout.setVerticalSpacing(8)
        param_layout.setHorizontalSpacing(10)
        
        # Threshold Distance
        param_layout.addWidget(QLabel("Threshold Distance (NM):"), 0, 0)
        self.threshold_distance = QDoubleSpinBox()
        self.threshold_distance.setRange(0.1, 100.0)
        self.threshold_distance.setSingleStep(0.1)
        self.threshold_distance.setDecimals(1)
        self.threshold_distance.setFixedWidth(80)
        self.threshold_distance.setButtonSymbols(QDoubleSpinBox.UpDownArrows)
        self.threshold_distance.setValue(self.trombone_config.get('threshold_distance', 2.0))
        self.threshold_distance.valueChanged.connect(self.update_details_tab)
        param_layout.addWidget(self.threshold_distance, 0, 1)
        
        # Base Angle
        param_layout.addWidget(QLabel("Base Angle (°):"), 1, 0)
        self.base_angle = QDoubleSpinBox()
        self.base_angle.setRange(-180.0, 180.0)
        self.base_angle.setSingleStep(1.0)
        self.base_angle.setDecimals(1)
        self.base_angle.setFixedWidth(80)
        self.base_angle.setButtonSymbols(QDoubleSpinBox.UpDownArrows)
        self.base_angle.setValue(self.trombone_config.get('base_angle', 90.0))
        self.base_angle.valueChanged.connect(self.update_details_tab)
        param_layout.addWidget(self.base_angle, 1, 1)
        
        # Base Distance
        param_layout.addWidget(QLabel("Base Distance (NM):"), 2, 0)
        self.base_distance = QDoubleSpinBox()
        self.base_distance.setRange(0.1, 100.0)
        self.base_distance.setSingleStep(0.1)
        self.base_distance.setDecimals(1)
        self.base_distance.setFixedWidth(80)
        self.base_distance.setButtonSymbols(QDoubleSpinBox.UpDownArrows)
        self.base_distance.setValue(self.trombone_config.get('base_distance', 5.0))
        self.base_distance.valueChanged.connect(self.update_details_tab)
        param_layout.addWidget(self.base_distance, 2, 1)
        
        # Extension Length
        param_layout.addWidget(QLabel("Extension Length (NM):"), 3, 0)
        self.extension_length = QDoubleSpinBox()
        self.extension_length.setRange(0.1, 100.0)
        self.extension_length.setSingleStep(0.1)
        self.extension_length.setDecimals(1)
        self.extension_length.setFixedWidth(80)
        self.extension_length.setButtonSymbols(QDoubleSpinBox.UpDownArrows)
        self.extension_length.setValue(self.trombone_config.get('extension_length', 3.0))
        self.extension_length.valueChanged.connect(self.update_details_tab)
        param_layout.addWidget(self.extension_length, 3, 1)
        
        # Eğer rota taşındı veya döndürüldüyse tüm parametre alanlarını devre dışı bırak
        if self.moved_or_rotated:
            # Uyarı mesajı ekle
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
        
        # Görsel ayarlar bölümü (sadece taşınmamış/döndürülmemiş rotalar için)
        if not self.moved_or_rotated:
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
            if 'color' not in self.trombone_config:
                self.trombone_config['color'] = self.get_default_color()
            current_color = self.trombone_config.get('color', self.get_default_color())
            self.color_button.setStyleSheet(f"background-color: {current_color}; border: 1px solid #444444;")
            self.color_button.clicked.connect(self.on_color_changed)
            visual_layout.addWidget(self.color_button, 0, 1)
            
            # Kalınlık ayarı
            visual_layout.addWidget(QLabel("Line Width:"), 1, 0)
            self.width_slider = QSlider(Qt.Horizontal)
            self.width_slider.setRange(1, 6)
            # Config'de width yoksa varsayılan değeri config'e kaydet
            if 'width' not in self.trombone_config:
                self.trombone_config['width'] = self.get_default_width()
            self.width_slider.setValue(self.trombone_config.get('width', self.get_default_width()))
            self.width_slider.valueChanged.connect(self.on_width_changed)
            visual_layout.addWidget(self.width_slider, 1, 1)
            
            self.width_label = QLabel(f"{self.trombone_config.get('width', self.get_default_width())}px")
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
            threshold_dist = self.threshold_distance.value()
            base_angle = self.base_angle.value()
            base_dist = self.base_distance.value()
            ext_length = self.extension_length.value()
            
            # Detay bilgilerini oluştur
            details = []
            
            # Temel tanımlama bilgileri
            details.append("=== TROMBONE PATTERN DETAILS ===\n")
            details.append("1. TROMBONE IDENTIFICATION")
            details.append(f"   Pattern ID       : {self.trombone_config.get('id', 'N/A')}")
            details.append(f"   Pattern Type     : Trombone")
            details.append("")
            
            # Parametrik yapılandırma
            details.append("2. PARAMETRIC CONFIGURATION")
            details.append(f"   Threshold Distance : {threshold_dist:.1f} NM")
            details.append(f"   Base Angle         : {base_angle:.1f}°")
            details.append(f"   Base Distance      : {base_dist:.1f} NM") 
            details.append(f"   Extension Length   : {ext_length:.1f} NM")
            details.append("")
            
            # Durum bilgisi ve kısıtlamalar
            details.append("3. STATUS AND CONSTRAINTS")
            details.append(f"   Moved/Rotated    : {'Yes' if self.moved_or_rotated else 'No'}")
            details.append(f"   Parameter Editable : {'No' if self.moved_or_rotated else 'Yes'}")
            if self.moved_or_rotated:
                details.append("   Constraint Reason : Pattern has been moved or rotated")
            details.append("")
            
            # Waypoint bilgileri
            details.append("4. WAYPOINT INFORMATION")
            waypoints = self.trombone_config.get('waypoints', [])
            if waypoints:
                details.append(f"   Total Waypoints  : {len(waypoints)}")
                details.append("")
                details.append("   Waypoint Details:")
                for i, wp in enumerate(waypoints):
                    if isinstance(wp, dict):
                        lat = wp.get('lat', 0)
                        lon = wp.get('lon', 0)
                        details.append(f"   WP{i+1:2d}             : {lat:9.6f}°, {lon:10.6f}°")
                    else:
                        details.append(f"   WP{i+1:2d}             : {wp}")
            else:
                details.append("   No waypoint data available")
                details.append("   System will calculate waypoints from parameters")
            
            details.append("")
            
            # Geometrik hesaplamalar
            details.append("5. GEOMETRIC CALCULATIONS")
            total_pattern_length = base_dist + ext_length + threshold_dist
            details.append(f"   Total Pattern Length : {total_pattern_length:.2f} NM")
            details.append(f"   Entry Leg Length     : {base_dist:.1f} NM")
            details.append(f"   Extension Leg Length : {ext_length:.1f} NM")
            details.append(f"   Exit Leg Length      : {threshold_dist:.1f} NM")
            details.append("")
            
            # Görsel stil bilgileri
            details.append("6. VISUAL STYLE PROPERTIES")
            details.append(f"   Pattern Color    : {self.trombone_config.get('color', self.get_default_color())}")
            details.append(f"   Line Width       : {self.trombone_config.get('width', self.get_default_width())}px")
            details.append("")
            
            # Sistem durumu
            details.append("7. SYSTEM STATUS")
            details.append(f"   Pattern Active   : Yes")
            details.append(f"   Last Modified    : Current Session")
            details.append(f"   Data Sources     : Configuration, User Input")
            
            # Detay metnini güncelle
            self.details_text.setPlainText("\n".join(details))
            
        except Exception as e:
            self.details_text.setPlainText(f"Error generating details: {str(e)}")
    
    def get_default_color(self):
        """Trombone için varsayılan renk"""
        return '#CC6600'  # Turuncu
    
    def get_default_width(self):
        """Trombone için varsayılan kalınlık"""
        return 2
    
    def on_color_changed(self):
        """Renk değiştiğinde çağrılır"""
        if not self.moved_or_rotated:
            current_color = self.trombone_config.get('color', self.get_default_color())
            print(f"Trombone color dialog opening with current color: {current_color}")
            
            # QColorDialog'u modal olarak aç
            color_dialog = QColorDialog(QColor(current_color), self)
            color_dialog.setOption(QColorDialog.ShowAlphaChannel, False)
            color_dialog.setWindowTitle("Select Trombone Color")
            color_dialog.setModal(True)  # Modal yap
            
            # Dialog'u göster ve sonucu kontrol et
            if color_dialog.exec_() == QColorDialog.Accepted:
                color = color_dialog.selectedColor()
                if color.isValid():
                    color_hex = color.name()
                    print(f"Trombone color changed to: {color_hex}")
                    self.trombone_config['color'] = color_hex
                    self.color_button.setStyleSheet(f"background-color: {color_hex}; border: 1px solid #444444;")
                    self.update_details_content()
                    # Sadece görsel ayarları güncelle
                    self.update_visual_settings_only()
                    
                    # Popup'ı öne getir
                    self.raise_()
                    self.activateWindow()
                else:
                    print("Trombone color dialog cancelled")
            else:
                print("Trombone color dialog cancelled")
                # Popup'ı öne getir
                self.raise_()
                self.activateWindow()
    
    def on_width_changed(self, value):
        """Kalınlık değiştiğinde çağrılır"""
        if not self.moved_or_rotated:
            print(f"Trombone width changed to: {value}")
            self.trombone_config['width'] = value
            self.width_label.setText(f"{value}px")
            self.update_details_content()
            # Sadece görsel ayarları güncelle
            self.update_visual_settings_only()
    
    def update_visual_settings_only(self):
        """Sadece görsel ayarları günceller - geometrik parametreleri değiştirmez"""
        # Sadece mevcut rotanın color ve width değerlerini güncelle
        visual_cfg = self.trombone_config.copy()
        visual_cfg.update({
            'color': self.trombone_config.get('color', self.get_default_color()),
            'width': self.trombone_config.get('width', self.get_default_width()),
            'visual_only_update': True  # Bu bir sadece görsel güncelleme olduğunu belirten flag
        })
        
        print(f"Trombone visual settings updated: {visual_cfg}")
        self.tromboneSettingsChanged.emit(visual_cfg)
        
    def on_update(self):
        """Trombone ayarlarını güncelle"""
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
            'extension_length': extension_length,
            # Görsel ayarlar (sadece taşınmamış/döndürülmemiş rotalar için)
            'color': self.trombone_config.get('color', self.get_default_color()) if not self.moved_or_rotated else self.trombone_config.get('color', self.get_default_color()),
            'width': self.trombone_config.get('width', self.get_default_width()) if not self.moved_or_rotated else self.trombone_config.get('width', self.get_default_width())
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
    
    def on_flip(self):
        """Flip the trombone pattern horizontally by negating the base angle."""
        # Get a copy of the current config
        updated_config = self.trombone_config.copy()
        
        # Flip the base angle
        current_angle = updated_config.get('base_angle', 90.0)
        updated_config['base_angle'] = -current_angle
        
        # Emit the signal to update the path and close the dialog
        self.tromboneSettingsChanged.emit(updated_config)
        self.accept()

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