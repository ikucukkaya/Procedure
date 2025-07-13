import os
import json

# Örnek bir rota çizimi oluşturup kaydetme testi yapan kod
test_folder = os.path.dirname(os.path.abspath(__file__))
test_json_path = os.path.join(test_folder, "test_cizim.json")

# Test amaçlı örnek bir çizim oluştur
test_drawing = {
    "routes": [
        {
            "type": "user_route",
            "id": "test_route_1",
            "name": "Test Rotası 1",
            "points": [
                [41.0, 29.0],
                [41.1, 29.1],
                [41.2, 29.05],
                [41.15, 28.95]
            ]
        },
        {
            "type": "trombone",
            "id": "trombone_1",
            "name": "Test Trombone",
            "points": [
                [41.3, 29.2],
                [41.4, 29.3],
                [41.35, 29.4],
                [41.25, 29.35]
            ]
        }
    ]
}

print(f"Test JSON dosyası oluşturuluyor: {test_json_path}")

try:
    with open(test_json_path, 'w', encoding='utf-8') as f:
        json.dump(test_drawing, f, indent=4)
    print(f"Test JSON dosyası başarıyla kaydedildi: {test_json_path}")
    print("Şimdi uygulamayı başlatıp 'Çizimleri Yükle' butonuna tıklayarak bu dosyayı seçin.")
except Exception as e:
    print(f"Hata: {e}")
