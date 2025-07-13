from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit,
    QDoubleSpinBox, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt, pyqtSignal

class GradientCalculatorDialog(QDialog):
    # Add signal to notify when altitudes should be applied to route waypoints
    altitudesCalculated = pyqtSignal(list, list)
    
    def __init__(self, routes, parent=None):
        """
        routes: Dictionary of routes {'route_id': {'name': 'Route Name', 'points': [(lat, lon), ...], 'waypoint_names': [...]}
        """
        super().__init__(parent)
        self.setWindowTitle("Gradient Calculator")
        # Dialog özelliklerini ayarlıyoruz - yeniden boyutlandırılabilir, simge durumuna küçültülebilir
        self.setWindowFlags(Qt.Dialog | Qt.WindowMinMaxButtonsHint | Qt.WindowStaysOnTopHint | Qt.WindowMinimizeButtonHint)
        self.routes = routes
        self.selected_route_id = None
        self.current_waypoints = []
        self.calculated_indices = []
        self.calculated_altitudes = []
        self.init_ui()
        
        # İlk rotayı otomatik olarak seç (eğer rota varsa)
        if self.routes and len(self.routes) > 0:
            first_route_id = list(self.routes.keys())[0]
            self.route_combo.setCurrentIndex(0)
            self.on_route_selection_changed(0)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(7)  # Daha kompakt görünüm için aralığı daha da azalt
        layout.setContentsMargins(10, 10, 10, 10)  # Kenarlıkları küçült

        # Rota seçimi (yeni eklenen)
        route_layout = QHBoxLayout()
        route_layout.addWidget(QLabel("Rota:"), 0)
        self.route_combo = QComboBox()
        self.route_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        
        # Mevcut rotaları ekle
        if self.routes:
            for route_id, route_info in self.routes.items():
                route_name = route_info.get('name', route_id)
                waypoint_count = len(route_info.get('points', []))
                self.route_combo.addItem(f"{route_name} ({waypoint_count} waypoints)", route_id)
                
        self.route_combo.currentIndexChanged.connect(self.on_route_selection_changed)
        route_layout.addWidget(self.route_combo, 1)
        layout.addLayout(route_layout)

        # İlk Waypoint seçimi (alt alta)
        first_wp_layout = QHBoxLayout()
        first_wp_layout.addWidget(QLabel("İlk Waypoint:"), 0)
        self.start_combo = QComboBox()
        self.start_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.start_combo.currentIndexChanged.connect(self.on_waypoint_selection_changed)  # Otomatik güncelleme
        first_wp_layout.addWidget(self.start_combo, 1)
        layout.addLayout(first_wp_layout)

        # Son Waypoint seçimi (alt alta)
        last_wp_layout = QHBoxLayout()
        last_wp_layout.addWidget(QLabel("Son Waypoint:"), 0)
        self.end_combo = QComboBox()
        self.end_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.end_combo.currentIndexChanged.connect(self.on_waypoint_selection_changed)  # Otomatik güncelleme
        last_wp_layout.addWidget(self.end_combo, 1)
        layout.addLayout(last_wp_layout)

        # Initial altitude
        alt_layout = QHBoxLayout()
        alt_layout.addWidget(QLabel("Başlangıç İrtifası:"), 0)
        self.altitude_edit = QLineEdit()
        self.altitude_edit.setPlaceholderText("ft")
        self.altitude_edit.setText("30000")  # Varsayılan değer: 30000 ft
        self.altitude_edit.setMaximumWidth(100)  # Genişliği sınırla
        self.altitude_edit.textChanged.connect(self.on_input_changed)  # Otomatik güncelleme
        alt_layout.addWidget(self.altitude_edit, 1)
        layout.addLayout(alt_layout)

        # Gradient input (% olarak sabit)
        grad_layout = QHBoxLayout()
        grad_layout.addWidget(QLabel("Alçalma Oranı (%):"), 0)
        self.gradient_spin = QDoubleSpinBox()
        self.gradient_spin.setRange(0.1, 10.0)
        self.gradient_spin.setSingleStep(0.1)
        self.gradient_spin.setValue(3.0)
        self.gradient_spin.setMaximumWidth(80)  # Genişliği sınırla
        self.gradient_spin.valueChanged.connect(self.on_input_changed)  # Otomatik güncelleme
        grad_layout.addWidget(self.gradient_spin, 1)
        # Birim seçenekleri kaldırıldı, sadece % kullanılacak
        self.gradient_unit_combo = QComboBox()  # Geriye dönük uyumluluk için gizli olarak tutalım
        self.gradient_unit_combo.addItems(["% (yüzde)", "ft/NM"])
        self.gradient_unit_combo.hide()  # Arayüzden gizle
        layout.addLayout(grad_layout)

        # İrtifa birimi kaldırıldı, her zaman ft kullanılacak
        self.alt_unit_combo = QComboBox()  # Geriye dönük uyumluluk için gizli olarak tutalım
        self.alt_unit_combo.addItems(["ft", "m"])
        self.alt_unit_combo.hide()  # Arayüzden gizle

        # Button layout
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        # Calculate button
        self.calc_btn = QPushButton("Hesapla")
        self.calc_btn.clicked.connect(self.calculate_gradient)
        self.calc_btn.setMaximumWidth(120)  # Buton genişliğini sınırla
        buttons_layout.addWidget(self.calc_btn)
        
        # Apply to Waypoint button
        self.apply_btn = QPushButton("Waypoint'e uygula")
        self.apply_btn.clicked.connect(self.apply_altitudes_to_waypoints)
        self.apply_btn.setMaximumWidth(150)  # Buton genişliğini sınırla
        self.apply_btn.setEnabled(False)  # Başlangıçta devre dışı bırak, hesaplama yapılınca etkinleşecek
        buttons_layout.addWidget(self.apply_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Waypoint", "Mesafe (NM)", "İrtifa"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # Tabloyu kompakt hale getir
        self.results_table.verticalHeader().setVisible(False)  # Satır başlıklarını gizle
        self.results_table.setAlternatingRowColors(True)  # Alternatif satır renkleri
        self.results_table.setMinimumHeight(150)  # Minimum yükseklik
        self.results_table.setMaximumHeight(200)  # Maksimum yükseklik
        self.results_table.horizontalHeader().setMinimumSectionSize(50)  # Minimum sütun genişliği
        self.results_table.horizontalHeader().setDefaultSectionSize(80)  # Varsayılan sütun genişliği
        self.results_table.verticalHeader().setDefaultSectionSize(20)  # Varsayılan satır yüksekliği (daha kompakt)
        layout.addWidget(self.results_table)
        
        # Pencere boyutunu ayarlıyoruz ama yeniden boyutlandırılabilir olarak
        self.setMinimumSize(280, 300)  # Minimum boyut
        # Başlangıç boyutu olarak önerilen değer
        self.resize(320, 400)  # Yeni sekme için biraz daha yüksek yaptık
        
        # Yeterli waypoint yoksa butonları devre dışı bırak
        self.update_ui_state()

    def on_route_selection_changed(self, index):
        """Rota seçimi değiştiğinde çağrılır"""
        if index < 0 or self.route_combo.count() <= 0:
            return
            
        # Seçilen rota ID'sini al
        self.selected_route_id = self.route_combo.itemData(index)
        
        if self.selected_route_id and self.selected_route_id in self.routes:
            # Seçilen rotayı al
            selected_route = self.routes[self.selected_route_id]
            
            # Waypoint'leri güncelle
            self.current_waypoints = selected_route.get('points', [])
            waypoint_names = selected_route.get('waypoint_names', [])
            
            # Waypoint combo'larını güncelle
            self.start_combo.clear()
            self.end_combo.clear()
            
            # Waypoint isimlerine göre combo boxları doldur
            if waypoint_names and len(waypoint_names) == len(self.current_waypoints):
                waypoint_labels = waypoint_names
            else:
                waypoint_labels = [f"WP{i+1}" for i in range(len(self.current_waypoints))]
                
            if self.current_waypoints:
                self.start_combo.addItems(waypoint_labels)
                self.end_combo.addItems(waypoint_labels)
                
                if len(self.current_waypoints) > 1:
                    self.end_combo.setCurrentIndex(len(self.current_waypoints) - 1)
            
            # Sonuç tablosunu temizle
            self.results_table.setRowCount(0)
            self.apply_btn.setEnabled(False)
            
            # UI durumunu güncelle
            self.update_ui_state()
            
            # Yeterli waypoint varsa otomatik hesapla
            if len(self.current_waypoints) >= 2 and self.altitude_edit.text():
                self.calculate_gradient()

    def calculate_gradient(self):
        try:
            # Seçili bir rota yoksa hata ver
            if not self.selected_route_id or not self.current_waypoints:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(self, "Rota Seçilmedi", "Gradient hesaplayabilmek için lütfen önce bir rota seçin.")
                return
                
            # En az iki waypoint olmalı
            if len(self.current_waypoints) < 2:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(self, "Yetersiz Waypoint", "Gradient hesaplayabilmek için en az 2 waypoint gerekli.")
                return
                
            start_idx = self.start_combo.currentIndex()
            end_idx = self.end_combo.currentIndex()
            if start_idx == end_idx:
                raise ValueError("İlk ve son waypoint farklı olmalı.")
            if start_idx > end_idx:
                indices = list(range(start_idx, end_idx-1, -1))
            else:
                indices = list(range(start_idx, end_idx+1))
            
            # Başlangıç yüksekliği boşsa hata ver
            if not self.altitude_edit.text():
                raise ValueError("Lütfen başlangıç irtifasını girin.")

            initial_alt = float(self.altitude_edit.text())
            grad_val = self.gradient_spin.value()
            # grad_unit artık kullanılmıyor, her zaman % olarak işlem yapılacak
            alt_unit = "ft"  # Sabit ft birimi

            # Mesafeleri hesapla
            from utils import calculate_distance
            points = [self.current_waypoints[i] for i in indices]
            segment_distances = []
            for i in range(len(points)-1):
                d = calculate_distance(points[i][0], points[i][1], points[i+1][0], points[i+1][1])
                segment_distances.append(d)
            cum_distances = [0]
            for d in segment_distances:
                cum_distances.append(cum_distances[-1] + d)

            # % değeri doğrudan ft/NM'e çevir
            grad_ft_per_nm = grad_val * 100  # 1% = 100 ft/NM

            # Her waypoint için irtifa hesapla
            altitudes = []
            for dist in cum_distances:
                alt = initial_alt - grad_ft_per_nm * dist
                altitudes.append(alt)

            # Sonuçları tabloya yaz
            self.results_table.setRowCount(len(indices))
            
            # Waypoint isimleri için seçilmiş rotadan waypoint isimlerini al
            waypoint_names = self.routes[self.selected_route_id].get('waypoint_names', [])
            
            for i, idx in enumerate(indices):
                # Eğer waypoint isimleri varsa ve indeks aralıktaysa ismi kullan, yoksa WP formatını kullan
                if waypoint_names and 0 <= idx < len(waypoint_names):
                    wp_name = waypoint_names[idx]
                else:
                    wp_name = f"WP{idx+1}"
                    
                self.results_table.setItem(i, 0, QTableWidgetItem(wp_name))
                self.results_table.setItem(i, 1, QTableWidgetItem(f"{cum_distances[i]:.2f}"))
                self.results_table.setItem(i, 2, QTableWidgetItem(f"{altitudes[i]:.0f} ft"))
            
            # Hesaplanan değerleri sakla
            self.calculated_indices = indices
            self.calculated_altitudes = [int(alt) for alt in altitudes]
            
            # "Waypoint'e uygula" butonunu etkinleştir
            self.apply_btn.setEnabled(True)
            
            # Otomatik olarak son satıra kaydır
            if len(indices) > 0:
                # Son satır ve sütunu seç
                last_row = len(indices) - 1
                self.results_table.scrollToItem(self.results_table.item(last_row, 0))
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Hata", str(e))
            self.apply_btn.setEnabled(False)

    def update_routes(self, routes):
        """Rota listesini güncelle ve UI'yi yenile"""
        self.routes = routes
        
        # ComboBox'ı temizle ve rotaları yeniden ekle
        self.route_combo.clear()
        
        if self.routes:
            for route_id, route_info in self.routes.items():
                route_name = route_info.get('name', route_id)
                waypoint_count = len(route_info.get('points', []))
                self.route_combo.addItem(f"{route_name} ({waypoint_count} waypoints)", route_id)
                
        # UI durumunu güncelle
        self.update_ui_state()
        
        # İlk rotayı otomatik olarak seç (eğer rota varsa)
        if self.routes and len(self.routes) > 0:
            self.route_combo.setCurrentIndex(0)
        else:
            # Rota yoksa Waypoint listelerini temizle
            self.start_combo.clear()
            self.end_combo.clear()
            self.current_waypoints = []
            self.selected_route_id = None
            self.results_table.setRowCount(0)
            self.apply_btn.setEnabled(False)

    def update_ui_state(self):
        # Rota seçimi kontrolleri
        if not self.routes or len(self.routes) == 0:
            self.route_combo.setEnabled(False)
            self.start_combo.setEnabled(False)
            self.end_combo.setEnabled(False)
            self.calc_btn.setEnabled(False)
            self.apply_btn.setEnabled(False)
            return
            
        self.route_combo.setEnabled(True)
        
        # Waypoint kontrolleri
        if not self.current_waypoints or len(self.current_waypoints) < 2:
            self.start_combo.setEnabled(False)
            self.end_combo.setEnabled(False)
            self.calc_btn.setEnabled(False)
            self.apply_btn.setEnabled(False)
        else:
            self.start_combo.setEnabled(True)
            self.end_combo.setEnabled(True)
            self.calc_btn.setEnabled(True)
            # apply_btn durumunu sadece hesaplama yapıldığında etkinleştiriyoruz
            
    def on_waypoint_selection_changed(self):
        """Waypoint seçimi değiştiğinde otomatik olarak hesapla"""
        # İki kombo da değer içeriyorsa ve farklı değerler seçiliyse hesapla
        if self.start_combo.count() > 0 and self.end_combo.count() > 0:
            if self.start_combo.currentIndex() != self.end_combo.currentIndex() and self.altitude_edit.text():
                self.calculate_gradient()
                
    def on_input_changed(self):
        """İrtifa veya alçalma oranı değiştiğinde otomatik olarak hesapla"""
        # Gerekli koşullar sağlanıyorsa hesapla
        if (self.current_waypoints and len(self.current_waypoints) >= 2 and 
            self.start_combo.currentIndex() != self.end_combo.currentIndex() and 
            self.altitude_edit.text()):
            try:
                # Sayısal bir değer girildiğinden emin ol
                float(self.altitude_edit.text())
                self.calculate_gradient()
            except ValueError:
                # Sayısal olmayan bir değer girilirse hesaplama yapma
                pass
                
    def apply_altitudes_to_waypoints(self):
        """Hesaplanan irtifaları rota waypoint'lerine uygula"""
        if not self.selected_route_id or not self.calculated_indices or not self.calculated_altitudes:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Hata", "Önce gradient hesaplaması yapılmalıdır.")
            return
            
        # Waypoint indeksleri ve irtifaları rota çizim sistemine gönder
        self.altitudesCalculated.emit(self.calculated_indices, self.calculated_altitudes)
        
        # Kullanıcıya bilgi ver
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(self, "Başarılı", f"{len(self.calculated_indices)} waypoint için irtifa değerleri güncellendi.")