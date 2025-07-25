# Popup Dialog'larında Detay Sekmelerinin İşlenmesi

Bu belge, projede kullanılan üç ana popup dialog'undaki (Point Merge, Route ve Trombone) detay sekmelerinin genel işleyiş mantığını ve kavramsal yapısını açıklar.

## Genel Kavramsal Yapı

Projede tüm popup dialog'larda tutarlı bir kullanıcı deneyimi sağlamak için ortak bir yaklaşım benimsenmiştir:

### İki Sekmeli Dialog Yapısı

Her popup dialog iki ana bölümden oluşur:

1. **Ayarlar Sekmesi**: Kullanıcının nesne parametrelerini değiştirebildiği interaktif alan
2. **Detay Sekmesi**: Nesnenin mevcut durumunu gösteren, salt okunur bilgi alanı

### Kullanıcı Etkileşim Mantığı

- Kullanıcı ayarlar sekmesinde parametre değişikliği yapar
- Bu değişiklikler anında detay sekmesine yansır
- Detay sekmesi her zaman güncel durumu gösterir
- Kullanıcı hem düzenleme yapabilir hem de sonuçları görebilir

## Point Merge Popup - Detay Sekmesi Mantığı

### Detay Bilgilerinin Amacı
Point Merge popup'ındaki detay sekmesi, kullanıcının oluşturduğu point merge pattern'ının tüm özelliklerini kapsamlı bir şekilde gösterir.

### Gösterilen Bilgi Kategorileri

1. **Temel Tanımlama Bilgileri**
   - Pattern'ın benzersiz kimliği
   - Pattern'ın adı ve tipi
   - Sistem tarafından atanan özellikler

2. **Yapılandırma Parametreleri**
   - Merge noktasından uzaklık (nautical mile cinsinden)
   - Track açısı (derece cinsinden)
   - Segment sayısı
   - *Bu değerler kullanıcı ayarlar sekmesinde değişiklik yaptıkça otomatik güncellenir*

3. **Coğrafi Koordinat Bilgileri**
   - Merge noktasının enlem ve boylam koordinatları
   - Pattern üzerindeki tüm waypoint'lerin koordinatları

4. **Geometrik Hesaplama Sonuçları**
   - Her segment için mesafe ve açı bilgileri
   - Toplam pattern mesafesi
   - Geometrik ilişkiler

### Dinamik Güncelleme Mantığı
Kullanıcı ayarlar sekmesinde herhangi bir parametre değiştirdiğinde, detay sekmesi anında yenilenir ve yeni hesaplanan değerleri gösterir.

## Route Popup - Detay Sekmesi Mantığı

### Detay Bilgilerinin Amacı
Route popup'ındaki detay sekmesi, kullanıcının çizdiği rota hakkında kapsamlı bilgi sunar ve rotanın görsel özelliklerindeki değişiklikleri anında yansıtır.

### Gösterilen Bilgi Kategorileri

1. **Rota Tanımlama Bilgileri**
   - Rotanın benzersiz kimliği
   - Kullanıcı tarafından verilen rota adı
   - Rota tipini belirten kategori

2. **Navigasyon Bilgileri**
   - Rota üzerindeki tüm waypoint'lerin koordinatları
   - Her waypoint'in adı veya otomatik numaralandırması
   - Waypoint'ler arası mesafe ve açı bilgileri

3. **Geometrik Özellikler**
   - Her segment için ayrı mesafe hesaplamaları
   - Segment'ler arası açı değerleri
   - Rotanın toplam uzunluğu

4. **Görsel Stil Bilgileri**
   - Rotanın mevcut rengi (kullanıcı değiştirince güncellenir)
   - Çizgi kalınlığı (kullanıcı değiştirince güncellenir)
   - Diğer görsel özellikler

5. **Zaman Damgaları**
   - Rotanın oluşturulma zamanı
   - Son değişiklik zamanı (varsa)

### Stil Değişikliklerinin Anında Yansıması
Kullanıcı rota rengini veya çizgi kalınlığını değiştirdiğinde, detay sekmesi bu değişiklikleri anında gösterir.

### Left Sidebar Line Settings Entegrasyonu
Mevcut popup'larda bulunan renk ve kalınlık ayarları, Left Sidebar'daki Map Controls > Line Settings bölümünden alınarak entegre edilebilir:

- **Merkezi Ayar Yönetimi**: Line Settings'ten varsayılan renk ve kalınlık değerleri alınır
- **Popup Seviyesinde Özelleştirme**: Her popup kendi nesnesine özel ayarlar yapabilir
- **İki Yönlü Senkronizasyon**: Popup'ta yapılan değişiklikler Line Settings'e de yansıtılabilir
- **Tutarlı Varsayılanlar**: Yeni oluşturulan nesneler Line Settings'teki değerleri kullanır

## Trombone Popup - Detay Sekmesi Mantığı

### Detay Bilgilerinin Amacı
Trombone popup'ı en karmaşık detay sekmesine sahiptir çünkü trombone pattern'ları çok sayıda parametre ve farklı durumları barındırır.

### Gösterilen Bilgi Kategorileri

1. **Trombone Kimlik Bilgisi**
   - Trombone pattern'ının benzersiz tanımlayıcısı

2. **Parametrik Yapılandırma**
   - Threshold Distance: Pistten uzaklık mesafesi
   - Base Angle: Temel açı değeri
   - Base Distance: Temel mesafe değeri
   - Extension Length: Uzatma boyu
   - *Bu değerler kullanıcı ayarlar sekmesinde değişiklik yaptıkça güncellenir*

3. **Durum Bilgisi ve Kısıtlamalar**
   - Trombone'un taşınıp taşınmadığı bilgisi
   - Trombone'un döndürülüp döndürülmediği bilgisi
   - Parametre değişikliği yapılıp yapılamayacağı durumu
   - Kısıtlamaların nedenleri

4. **Waypoint Bilgilerinin Çoklu Kaynak Analizi**
   - Sistem farklı kaynaklardan waypoint bilgilerini toplar
   - Ana uygulama verilerinden waypoint'ler
   - Trombone'a özel hesaplanmış waypoint'ler
   - Konfigürasyon dosyasından waypoint'ler
   - Sistem, mevcut olan en güncel waypoint bilgilerini gösterir

### Özel Durum Yönetimi
Trombone detay sekmesi, pattern'ın durumuna göre farklı bilgiler gösterir:

- **Normal Durum**: Tüm parametreler ve waypoint'ler gösterilir
- **Taşınmış/Döndürülmüş Durum**: Uyarı mesajları ve kısıtlama bilgileri eklenir
- **Eksik Veri Durumu**: Sistem mevcut veri kaynaklarını tarar ve bulunanları gösterir

## Benzer Programa Ekleme Rehberi

### Temel Kavramsal Yaklaşım

Benzer bir uygulamaya bu özelliği eklemek için aşağıdaki kavramsal adımları takip edebilirsiniz:

### 1. İkili Sekme Yapısının Kurulması

Dialog pencerenizi iki ana bölüme ayırın:
- **Ayarlar Bölümü**: Kullanıcının parametre değiştirebildiği alan
- **Detay Bölümü**: Mevcut durumu gösteren salt okunur alan

### 2. Detay Bölümünün İçerik Stratejisi

Detay bölümünde gösterilecek bilgileri kategorilere ayırın:
- **Tanımlama Bilgileri**: Nesnenin kimliği, adı, tipi
- **Parametrik Bilgiler**: Kullanıcının ayarlayabileceği değerler
- **Hesaplanmış Bilgiler**: Parametrelerden türetilen sonuçlar
- **Durum Bilgileri**: Nesnenin mevcut durumu ve kısıtlamaları
- **Zaman Bilgileri**: Oluşturma ve değişiklik zamanları

### 3. Dinamik Güncelleme Mantığı

- Kullanıcı ayarlar bölümünde değişiklik yaptığında
- Detay bölümü otomatik olarak yenilenmeli
- Yeni parametrelerle hesaplanan değerler anında gösterilmeli
- Görsel değişiklikler (renk, stil) detay bölümünde yansımalı

### 4. Çoklu Veri Kaynağı Yönetimi

Nesnenizin bilgileri farklı kaynaklardan gelebilir:
- Ana uygulama veritabanından
- Kullanıcı girdilerinden
- Hesaplanmış değerlerden
- Konfigürasyon dosyalarından

Sistem, mevcut en güncel veriyi bulup göstermelidir.

### 5. Kullanıcı Deneyimi Prensipleri

- **Tutarlılık**: Tüm popup'larda aynı görsel ve işlevsel yapı
- **Anında Geri Bildirim**: Değişiklikler hemen görünür olmalı
- **Kapsamlı Bilgi**: Kullanıcı nesne hakkında her şeyi görebilmeli
- **Salt Okunur Güvenlik**: Detay bölümünde yanlışlıkla değişiklik yapılamaz

### 6. Left Sidebar Line Settings Entegrasyonu

Benzer programa ekleme yaparken, merkezi ayar yönetimi için şu yaklaşım benimsenebilir:

- **Varsayılan Değer Kaynağı**: Left Sidebar'daki Line Settings bölümünden renk ve kalınlık değerleri alınır
- **Popup Özelleştirmesi**: Her popup kendi nesnesine özel renk ve kalınlık ayarlayabilir
- **Merkezi Güncelleme**: Line Settings'te yapılan değişiklikler yeni nesnelere otomatik uygulanır
- **Nesne Bazlı Ayrıştırma**: Route, Point Merge ve Trombone için farklı varsayılan değerler tutulabilir
- **Senkronizasyon Seçenekleri**: Popup'ta yapılan değişikliklerin Line Settings'e geri yansıtılıp yansıtılmayacağı belirlenebilir

## Önemli Tasarım Prensipleri

### 1. Bilgi Sunumu
- **Monospace Font Kullanımı**: Koordinatlar ve sayısal değerler düzgün hizalanır
- **Kategorik Organizasyon**: Bilgiler mantıklı gruplara ayrılır
- **Hiyerarşik Başlıklar**: Kullanıcı istediği bilgiyi hızlıca bulabilir

### 2. Kullanıcı Güvenliği
- **Salt Okunur Alan**: Detay sekmesinde yanlışlıkla değişiklik yapılamaz
- **Anında Doğrulama**: Değişiklikler hemen kontrol edilir ve gösterilir
- **Durum Bildirimi**: Sistem durumu ve kısıtlamalar açıkça belirtilir

### 3. Veri Bütünlüğü
- **Çoklu Kaynak Kontrolü**: Farklı veri kaynaklarından bilgi toplanır
- **Öncelik Sıralaması**: En güncel ve güvenilir veri kaynaklarından başlanır
- **Eksik Veri Yönetimi**: Veri eksikse alternatif kaynaklar aranır

### 4. Performans Optimizasyonu
- **Lazy Loading**: Detay bilgileri sadece gerektiğinde üretilir
- **Akıllı Güncelleme**: Sadece değişen bilgiler yeniden hesaplanır
- **Cache Mekanizması**: Sık kullanılan hesaplamalar önbelleğe alınır

### 5. Erişilebilirlik
- **Açık Etiketleme**: Her bilgi kategorisi net şekilde belirtilir
- **Tutarlı Format**: Aynı türdeki bilgiler her zaman aynı formatta gösterilir
- **Debug Desteği**: Geliştirici için ek debug bilgileri dahil edilebilir

## Sistem Faydaları

### Kullanıcı Açısından
- **Tam Kontrol**: Nesnenin her özelliğini görebilir
- **Anında Geri Bildirim**: Değişikliklerin sonucunu hemen görür
- **Hata Önleme**: Yanlış değerleri detay sekmesinde fark edebilir
- **Öğrenme**: Sistemin nasıl çalıştığını anlayabilir

### Geliştirici Açısından
- **Tutarlı Yapı**: Tüm popup'larda aynı mantık kullanılır
- **Kolay Bakım**: Yeni bilgi kategorileri kolayca eklenebilir
- **Debug Kolaylığı**: Sistem durumu net şekilde görülebilir
- **Modüler Tasarım**: Her popup kendi detay üretim mantığına sahiptir

### Sistem Açısından
- **Veri Doğrulama**: Bilgilerin tutarlılığı sürekli kontrol edilir
- **Performans İzleme**: Hesaplama süreleri ve kaynak kullanımı takip edilir
- **Hata Toleransı**: Eksik veya hatalı verilerle başa çıkılabilir
- **Genişletilebilirlik**: Yeni nesne türleri için kolayca uyarlanabilir

Bu yapı sayesinde kullanıcılar hem nesne parametrelerini düzenleyebilir hem de sistemin anlık durumunu kapsamlı bir şekilde görebilirler.
