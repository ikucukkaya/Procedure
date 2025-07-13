"""
CSV Rota İçe Aktarma Testi

Bu script, bir CSV dosyasının models.py'daki load_route_from_csv 
fonksiyonuyla yüklenip yüklenemeyeceğini test eder.
"""

import os
import sys
from models import DataManager

def test_csv_import(csv_path):
    """Test CSV rota importunu"""
    data_manager = DataManager()
    
    print(f"Test edilen CSV dosyası: {csv_path}")
    if not os.path.exists(csv_path):
        print(f"HATA: '{csv_path}' dosyası bulunamadı!")
        return
    
    success, message, loaded_route = data_manager.load_route_from_csv(csv_path)
    
    print(f"Yükleme başarılı: {success}")
    print(f"Mesaj: {message}")
    
    if loaded_route:
        print("\nYüklenen Rota Bilgileri:")
        print(f"  ID: {loaded_route.get('id', 'Yok')}")
        print(f"  İsim: {loaded_route.get('name', 'İsimsiz')}")
        print(f"  Tür: {loaded_route.get('type', 'Bilinmiyor')}")
        print(f"  Nokta sayısı: {len(loaded_route.get('points', []))}")
        
        if 'points' in loaded_route and loaded_route['points']:
            print("\nİlk 3 nokta:")
            for i, point in enumerate(loaded_route['points'][:3]):
                print(f"  Nokta {i+1}: Lat={point[0]:.6f}, Lon={point[1]:.6f}")
            
        if 'segment_distances' in loaded_route:
            print(f"\nSegment mesafeleri: {', '.join([f'{d:.2f} NM' for d in loaded_route['segment_distances']])}")
            
        if 'track_angles' in loaded_route:
            print(f"Track açıları: {', '.join([f'{a:.1f}°' for a in loaded_route['track_angles']])}")

if __name__ == "__main__":
    # Argüman olarak verilen dosyayı test et, yoksa default olarak "Route 1.csv" kullan
    test_file = sys.argv[1] if len(sys.argv) > 1 else "Route 1.csv"
    test_csv_import(test_file)
