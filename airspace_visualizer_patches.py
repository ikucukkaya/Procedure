"""
Airspace Visualizer için düzeltme dosyası

Bu modül, airspace_visualizer.py dosyasındaki hatayı düzeltmek ve
CSV formatında kaydetme işlevselliğini eklemek için yama niteliğindedir.

Kullanım:
1. Bu dosyayı airspace_visualizer.py dosyasının bulunduğu klasöre kopyalayın
2. import edin veya doğrudan çalıştırın
"""

import csv
from utils import calculate_distance, calculate_bearing, decimal_to_dms

def get_save_methods():
    """
    CSV formatında kaydetme ve yükleme metotlarını döndürür.
    
    Airspace_visualizer sınıfınıza bu metotları eklemek için kullanın:
    
    from airspace_visualizer_patches import get_save_methods
    AirspaceVisualizer.on_save = get_save_methods()['on_save']
    """
    
    def on_save(self):
        """Save the current project"""
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        
        # Hem JSON hem CSV formatı seçeneği sun
        fileFormats = "JSON Dosyası (*.json);;CSV Dosyaları (*.csv);;Tüm Dosyalar (*)"
        filePath, selectedFilter = QFileDialog.getSaveFileName(
            self, "Çizimleri Kaydet", "", 
            fileFormats, 
            options=options
        )
        
        if not filePath:
            return
        
        # Map widget'taki veriyi önce DataManager'a aktar
        self.data_manager.drawn_elements = self.map_widget.drawn_elements
        
        # Seçilen formatı kontrol et
        if "JSON" in selectedFilter or filePath.lower().endswith('.json'):
            # JSON uzantısını kontrol et
            if not filePath.lower().endswith('.json'):
                filePath += '.json'
            
            # JSON formatında kaydet
            success, message = self.data_manager.save_drawings_to_json(filePath)
            
            if success:
                self.statusBar().showMessage(message, 5000)
            else:
                QMessageBox.warning(self, "Kaydetme Hatası", message)
                
        elif "CSV" in selectedFilter or filePath.lower().endswith('.csv'):
            # CSV uzantısını kontrol et
            if not filePath.lower().endswith('.csv'):
                filePath += '.csv'
            
            # Klasör yolu oluştur
            basePath = os.path.splitext(filePath)[0]
            
            # Tüm çizimleri CSV olarak kaydet
            routes = self.map_widget.drawn_elements.get('routes', [])
            
            if not routes:
                QMessageBox.warning(self, "Kaydetme Hatası", "Kaydedilecek çizim bulunamadı.")
                return
            
            # İlk rota dosyasını belirtilen yola kaydet, diğerlerini otomatik adlandır
            saved_count = 0
            for i, route in enumerate(routes):
                route_name = route.get('name', f"Route_{i+1}")
                route_id = route.get('id', '')
                
                # İlk rota için seçilen ismi kullan, diğerleri için otomatik isimlendirme yap
                if i == 0:
                    route_file = filePath
                else:
                    # Aynı klasördeki yeni bir dosya ismi oluştur
                    route_dir = os.path.dirname(filePath)
                    route_file = os.path.join(route_dir, f"{route_name}.csv")
                
                try:
                    # CSV dosyasını oluştur
                    with open(route_file, 'w', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        # Başlık satırı
                        writer.writerow(['Waypoint', 'Latitude', 'Longitude', 'Lat (DMS)', 'Lon (DMS)', 'Segment Distance (NM)', 'Track (°)'])
                        
                        # Nokta verilerini ve segment mesafelerini hesapla ve yaz
                        if 'points' in route:
                            for j, (lat, lon) in enumerate(route['points']):
                                wp_name = f"WP{j+1}"
                                lat_dms = decimal_to_dms(lat, 'lat')
                                lon_dms = decimal_to_dms(lon, 'lon')
                                
                                # Segment mesafesi ve açısını hesapla (ilk nokta hariç)
                                dist = ""
                                track = ""
                                if j > 0:
                                    prev_lat, prev_lon = route['points'][j-1]
                                    dist = f"{calculate_distance(prev_lat, prev_lon, lat, lon):.1f}"
                                    track = f"{calculate_bearing(prev_lat, prev_lon, lat, lon):.1f}"
                                
                                writer.writerow([wp_name, f"{lat:.6f}", f"{lon:.6f}", lat_dms, lon_dms, dist, track])
                    saved_count += 1
                
                except Exception as e:
                    QMessageBox.warning(self, "CSV Kaydetme Hatası", 
                                      f"{route_name} rotası kaydedilirken hata oluştu: {str(e)}")
            
            # Başarılı mesajı göster
            if saved_count > 0:
                self.statusBar().showMessage(f"{saved_count} rota CSV formatında kaydedildi.", 5000)
            else:
                QMessageBox.warning(self, "Kaydetme Hatası", "Hiçbir rota kaydedilemedi.")
    
    return {
        'on_save': on_save
    }

def fix_on_open(self):
    """
    Düzeltilmiş on_open metodu
    """
    print("on_open fonksiyonu çağrıldı")
    options = QFileDialog.Options()
    options |= QFileDialog.DontUseNativeDialog
    filePath, fileFilter = QFileDialog.getOpenFileName(
        self, "Çizimleri Yükle", "", 
        "Tüm Desteklenen Dosyalar (*.json *.csv);;JSON Dosyaları (*.json);;CSV Rotaları (*.csv);;Tüm Dosyalar (*)", 
        options=options
    )
    
    if not filePath:
        print("Dosya seçilmedi")
        return
        
    print(f"Seçilen dosya: {filePath}")
    
    # Dosya uzantısına göre işlem yap
    if filePath.lower().endswith('.json'):
        success, message = self.data_manager.load_drawings_from_json(filePath)
        print(f"JSON yükleme sonucu: başarı={success}, mesaj={message}")
    
        if success:
            # Çizimleri map_widget'a aktar (sadece routes anahtarını güncelle)
            # İlk olarak mevcut trajectories ve waypoints değerlerini kaydedelim
            trajectories = self.map_widget.drawn_elements.get('trajectories', [])
            waypoints = self.map_widget.drawn_elements.get('waypoints', [])
            
            # Şimdi routes listesini güncelleyelim
            self.map_widget.drawn_elements['routes'] = self.data_manager.drawn_elements['routes']
            
            # Diğer anahtarların değerlerini koruyalım
            self.map_widget.drawn_elements['trajectories'] = trajectories
            self.map_widget.drawn_elements['waypoints'] = waypoints
            
            self.map_widget.update()
            self.statusBar().showMessage(message, 5000)
            print("Çizimler başarıyla yüklendi ve map_widget güncellendi")
        else:
            QMessageBox.warning(self, "Yükleme Hatası", message)
            print(f"Yükleme hatası: {message}")
            
    elif filePath.lower().endswith('.csv'):
        # CSV dosyasından rota yükleme
        success, message, loaded_route = self.data_manager.load_route_from_csv(filePath)
        print(f"CSV yükleme sonucu: başarı={success}, mesaj={message}")
        
        if success and loaded_route:
            # İlk olarak mevcut trajectories ve waypoints değerlerini kaydedelim
            trajectories = self.map_widget.drawn_elements.get('trajectories', [])
            waypoints = self.map_widget.drawn_elements.get('waypoints', [])
            
            # Yüklenen rotayı drawn_elements listesine ekle
            if 'routes' not in self.map_widget.drawn_elements:
                self.map_widget.drawn_elements['routes'] = []
            
            # Rotayı ekle
            self.map_widget.drawn_elements['routes'].append(loaded_route)
            
            # Diğer anahtarların değerlerini koruyalım
            self.map_widget.drawn_elements['trajectories'] = trajectories
            self.map_widget.drawn_elements['waypoints'] = waypoints
            
            # Haritayı güncelle
            self.map_widget.update()
            self.statusBar().showMessage(f"CSV Rotası Yüklendi: {message}", 5000)
            print(f"CSV rotası başarıyla yüklendi: {loaded_route['name']}")
        else:
            QMessageBox.warning(self, "CSV Yükleme Hatası", message)
            print(f"CSV yükleme hatası: {message}")

def apply_patches():
    """
    airspace_visualizer.py dosyasındaki hatalı fonksiyonları düzeltir.
    """
    try:
        import sys
        sys.path.append('.')  # Mevcut klasörü arama yoluna ekle
        
        # AirspaceVisualizer sınıfını içe aktar
        from airspace_visualizer import AirspaceVisualizer
        
        # Metodları değiştir
        AirspaceVisualizer.on_save = get_save_methods()['on_save']
        AirspaceVisualizer.on_open = fix_on_open
        
        print("Başarıyla yamalandı! Artık CSV formatında kaydetme ve yükleme işlevselliği çalışacaktır.")
        return True
    except Exception as e:
        print(f"Hata oluştu: {str(e)}")
        return False

if __name__ == "__main__":
    apply_patches()
