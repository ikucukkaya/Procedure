# Generated Scripts

Bu klasör, SID (Standard Instrument Departure) prosedürlerini yeniden düzenlemek ve analiz etmek için oluşturulan Python scriptlerini içerir.

## Dosyalar

### 1. `reorganize_sids.py`
**Amaç:** STAR_SID.xml dosyasındaki SID prosedürlerini yeniden düzenler ve konfigürasyonlara göre gruplandırır.

**Özellikler:**
- `generated_sids.xml` dosyasından SID verilerini okur
- SID'leri 4 farklı konfigürasyona göre gruplandırır:
  - **KUZEY**: 1C, 1D, 1E varyantları
  - **GÜNEY**: 1F, 1G, 1H varyantları  
  - **TERS_KUZEY**: Çoğunlukla 1C, 1D, 1E (VICEN için 1Q, 1R, 1S)
  - **TERS_GÜNEY**: Çoğunlukla 1F, 1G, 1H (özel durumlar için 1V, 1T, 1U)
- Mevcut STAR prosedürlerini korur
- Yeni `STAR_SID.xml` dosyası oluşturur

**Kullanım:**
```bash
python reorganize_sids.py
```

### 2. `generate_complete_sids.py`
**Amaç:** Excel dosyasından SID verilerini okuyup tam SID prosedürlerini XML formatında oluşturur.

**Özellikler:**
- LTFM_SID_Data.xlsx dosyasından SID verilerini okur
- Her SID için waypoint rotalarını oluşturur
- Altitude, Speed, Turn bilgilerini ekler
- `generated_sids.xml` dosyası oluşturur

**Kullanım:**
```bash
python generate_complete_sids.py
```

### 3. `parse_sids.py`
**Amaç:** SID verilerini analiz eder ve doğrulama yapar.

**Özellikler:**
- Excel verilerini okuyup analiz eder
- SID türlerini ve varyantlarını listeler
- Veri doğruluğunu kontrol eder
- İstatistiksel bilgiler sağlar

**Kullanım:**
```bash
python parse_sids.py
```

## Gereksinimler

Bu scriptler aşağıdaki Python kütüphanelerini gerektirir:
- `pandas` (Excel dosyalarını okumak için)
- `openpyxl` (Excel dosya desteği için)
- `xml.etree.ElementTree` (XML işlemleri için - standart kütüphane)

## Kurulum

```bash
pip install pandas openpyxl
```

## Çalışma Akışı

1. **Analiz**: `parse_sids.py` ile veri analizi yapın
2. **Üretim**: `generate_complete_sids.py` ile SID XML'i oluşturun
3. **Düzenleme**: `reorganize_sids.py` ile final STAR_SID.xml'i oluşturun

## Çıktı Dosyaları

- `generated_sids.xml`: Ham SID prosedürleri
- `STAR_SID_new.xml`: Yeniden düzenlenmiş prosedürler
- `STAR_SID.xml`: Final dosya (mevcut dosyanın üzerine yazılır)

## Notlar

- Scriptler LTFM havalimanı için özelleştirilmiştir
- SID konfigürasyonları Türkiye hava sahası standartlarına göre düzenlenmiştir
- Dosya yolları script'lerin bulunduğu dizine göre relatif olarak ayarlanmıştır

## Versiyon

Bu scriptler 13-14 Temmuz 2025 tarihlerinde oluşturulmuştur ve GitHub Copilot yardımıyla geliştirilmiştir.
