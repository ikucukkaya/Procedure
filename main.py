import sys
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox
from airspace_visualizer import AirspaceVisualizer

if __name__ == "__main__":
    # Geliştirme sırasında hataları daha net görmek için
    print("=== Uygulama Başlatılıyor ===")
    
    app = QApplication(sys.argv)
    window = AirspaceVisualizer()
    
    # Debug mesajı
    print("AirspaceVisualizer yüklendi")
    print("=== Butonlar ve bağlantıları kontrol ediliyor ===")
    
    # Çizim butonunun bağlantısını kontrol et
    if hasattr(window.left_sidebar, 'load_drawings_btn'):
        print("- 'load_drawings_btn' bulundu")
        print(f"- Bağlı sinyal sayısı: {window.left_sidebar.load_drawings_btn.receivers(window.left_sidebar.load_drawings_btn.clicked)}")
    else:
        print("- 'load_drawings_btn' bulunamadı!")

    window.show()
    sys.exit(app.exec_())