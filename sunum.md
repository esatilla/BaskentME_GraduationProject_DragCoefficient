# Sürüklenme Katsayısı Ölçüm Sistemi — Sunum Referans Dokümanı

**Proje:** ME491 Bitirme Projesi — Başkent Üniversitesi Makine Mühendisliği
**Öğrenciler:** Selin KAPLAN, Atilla ES
**Danışman:** Doç. Erol Çubukçu

---

## 1. Projenin Amacı

Silindirik bir tüp içinde viskoz sıvıda serbest düşen küresel parçacıkların:
- **Terminal hızını** (v_t) otomatik olarak ölçmek
- **Sürüklenme katsayısını** (Cd) hesaplamak
- **Reynolds sayısını** (Re) belirleyerek akış rejimini sınıflandırmak
- Sonuçları Stokes yasası ve Schiller-Naumann ampirik korelasyonu ile karşılaştırmak

---

## 2. Teorik Altyapı

### 2.1 Sürüklenme Kuvveti ve Terminal Hız

Bir küre viskoz sıvıda düştüğünde üç kuvvet etkir:

| Kuvvet | Formül | Yön |
|---|---|---|
| Ağırlık (F_g) | F_g = ρ_p · V · g | Aşağı |
| Kaldırma (F_b) | F_b = ρ_f · V · g | Yukarı |
| Sürüklenme (F_d) | F_d = ½ · Cd · ρ_f · A · v² | Yukarı |

Burada:
- ρ_p = parçacık yoğunluğu (kg/m³)
- ρ_f = akışkan yoğunluğu (kg/m³)
- V = parçacık hacmi = (π/6)·d³
- A = parçacık kesit alanı = (π/4)·d²
- g = yerçekimi ivmesi = 9.81 m/s²
- v = düşme hızı (m/s)

**Terminal hız:** Kuvvetler dengeye ulaştığında (F_g = F_b + F_d) ivme sıfırlanır ve parçacık sabit hızla düşer. Bu sabit hız **terminal hız** (v_t) olarak adlandırılır.

### 2.2 Sürüklenme Katsayısı (Cd) Hesabı

Terminal hızda kuvvet dengesinden:

```
F_g - F_b = F_d
(ρ_p - ρ_f) · V · g = ½ · Cd · ρ_f · A · v_t²
```

Cd için çözüldüğünde:

```
Cd = (4/3) · (d / v_t²) · ((ρ_p - ρ_f) / ρ_f) · g
```

### 2.3 Reynolds Sayısı

```
Re = (ρ_f · v_t · d) / μ
```

Burada μ = dinamik viskozite (Pa·s).

Reynolds sayısı akış rejimini belirler:

| Re Aralığı | Akış Rejimi | Özellik |
|---|---|---|
| Re < 0.5 | Stokes (Sürüngen) | Viskoz kuvvetler baskın, Cd = 24/Re |
| 0.5 < Re < 2 | Alt Geçiş | Stokes'tan sapmalar başlar |
| 2 < Re < 500 | Ara Rejim | Atalet ve viskoz kuvvetler karışık |
| 500 < Re < 2×10⁵ | Newton Rejimi | Cd ≈ 0.44 (sabit) |
| Re > 2×10⁵ | Türbülanslı | Sınır tabaka geçişi, Cd düşer |

### 2.4 Teorik Karşılaştırma Modelleri

**Stokes Yasası (Re < 0.5):**
```
Cd_Stokes = 24 / Re
v_Stokes = (2·r²·(ρ_p - ρ_f)·g) / (9·μ)
```

**Schiller-Naumann Korelasyonu (Re < 1000):**
```
Cd_SN = (24/Re) · (1 + 0.15 · Re^0.687)
```

### 2.5 Duvar Etkisi Düzeltmesi (Francis/Ladenburg)

Sonlu çaplı silindirde düşen parçacık, sonsuz ortama göre daha yavaş düşer. Düzeltme faktörü:

```
λ = d_parçacık / d_silindir    (çap oranı)
k = 1 / (1 - 2.104·λ + 2.089·λ³ - 0.948·λ⁵)
v_gerçek = v_ölçülen / k
```

---

## 3. Deney Düzeneği

### 3.1 Genel Kurulum

```
                    Parçacık bırakma noktası
                           ↓
                    ┌──────────────┐
                    │  Cam silindir │  ← Viskoz sıvı (ör. gliserin)
                    │  (iç çap: D)  │
                    │              │
                    │  ┌────────┐  │  ← İzlenen bölge (60 cm)
                    │  │ Kamera │  │
                    │  │  FOV   │  │
                    │  └────────┘  │
                    │              │
                    └──────────────┘
                           
    ← ~146 cm →     Kamera (90° yan)
                    Basler acA1440-220uc
                    + Arka aydınlatma (LED panel)
```

### 3.2 Aydınlatma — Backlit (Arka Aydınlatma) Yöntemi

Parçacık tespiti **silüet yöntemi** ile yapılır:
- Tüpün **arkasına** güçlü beyaz ışık kaynağı (LED panel) yerleştirilir
- Kamera **önden** bakar
- Arka plan **parlak/beyaz**, parçacık **koyu/siyah** silüet olarak görünür
- Bu yüksek kontrast, hızlı ve güvenilir tespit sağlar

Avantajları:
- Nesne rengi/dokusu önemsiz — sadece şekil (gölge) algılanır
- Yüksek FPS'de bile güvenilir tespit
- Basit threshold ile ayrılabilir (karmaşık algoritmaya gerek yok)

---

## 4. Donanım

### 4.1 Kamera: Basler acA1440-220uc

| Özellik | Değer | Açıklama |
|---|---|---|
| Sensör | Sony IMX273 (1/2.9") | Global shutter CMOS |
| Çözünürlük | 1440 × 1080 piksel | 1.6 MP |
| Piksel boyutu | 3.45 µm | Alt-milimetre hassasiyeti |
| Sensör boyutu | 4.968 mm × 3.726 mm | 1/2.9" format |
| Arayüz | USB 3.0 SuperSpeed | 500 Mbps bant genişliği |
| Maks. kare hızı | 220 fps (tam çözünürlük) | ROI ile 800+ fps |
| Piksel formatı | Mono8 | 8-bit gri, 1 byte/piksel |
| Shutter tipi | Global shutter | Hareket bulanıklığı yok |
| Çalışma sıcaklığı | ~62°C | Sürekli çalışmada |

**Global Shutter Önemi:** Rolling shutter'dan farklı olarak tüm pikseller aynı anda pozlanır. Hızlı hareket eden nesnelerde bozulma/eğilme olmaz — terminal hız ölçümü için kritik.

**Mono8 Format:** Gri tonlamalı, 1 byte/piksel. Renkli formatlara (BGR8 = 3 byte/piksel) göre 3× daha az veri → 3× daha yüksek FPS potansiyeli. Silüet tespiti için renk bilgisi gereksiz.

### 4.2 ROI (Region of Interest) ile Yüksek Hız

Sensörün tamamı yerine sadece bir bölgesi okunarak FPS artırılır:

| ROI Yüksekliği | Çözünürlük | FPS | Açıklama |
|---|---|---|---|
| 1080 px (tam) | 1440 × 1080 | ~220 | Standart mod |
| 270 px | 1440 × 270 | ~620 | Varsayılan deney modu |
| 200 px | 1440 × 200 | ~790 | Yüksek hız |
| 150 px | 1440 × 150 | ~800 | Maksimum hız |

ROI sensörün dikey merkezine otomatik konumlandırılır:
```
OffsetY = ((sensör_yüksekliği - roi_yüksekliği) / 2)  →  çifte yuvarla (donanım kısıtı)
```

### 4.3 Lens: Computar C125-1218-5M

| Özellik | Değer |
|---|---|
| Odak uzaklığı | 12 mm |
| Maksimum diyafram | F1.8 |
| Bağlantı | C-mount |
| Çözünürlük | 5 MP |

### 4.4 Optik Kurulum

Kamera 90° yan çevrilmiş (portrait mod) kullanılır:
- Dikey FOV: 1440 piksel ekseni → daha uzun düşme mesafesi izlenir
- Yatay FOV: 1080 piksel ekseni → tüp genişliğini kapsar

**Seçilen çalışma mesafesi: ~146 cm**

| Parametre | Değer |
|---|---|
| Dikey FOV | 600 mm = 60 cm |
| Yatay FOV | 450 mm = 45 cm |
| Piksel çözünürlüğü | 0.42 mm/piksel |

İnce mercek formülünden:
```
m = sensör_boyutu / nesne_boyutu = 4.968 / 600 = 0.00828
d_o = f × (1 + 1/m) = 12 × (1 + 120.77) = 1461 mm ≈ 146 cm
```

---

## 5. Yazılım Mimarisi

### 5.1 Genel Yapı

Python + tkinter tabanlı GUI uygulaması. **Mixin** tasarım deseni ile modüler yapı:

| Modül | Sorumluluk |
|---|---|
| `main.py` | Uygulama başlatma, tüm mixin'leri birleştirme |
| `camera_interface.py` | Basler kamera kontrolü (pypylon SDK) |
| `detector.py` | Silüet tespiti (threshold + centroid) |
| `physics.py` | Cd, Re, terminal hız, duvar düzeltmesi hesapları |
| `calibration.py` | Piksel/mm ölçek + kırılma düzeltmesi |
| `ui/*.py` | GUI mixin modülleri (10 adet) |

### 5.2 Kamera Kontrol Katmanı (pypylon)

Basler Pylon SDK'nın Python bağlayıcısı olan **pypylon** kullanılır:

```
Uygulama → pypylon → Pylon SDK (C++) → USB 3.0 → Kamera
```

Temel akış:
1. `TlFactory.GetInstance()` → Transport Layer fabrikası
2. `CreateTl("BaslerUsb")` → USB transport layer (GigE değil)
3. `EnumerateDevices()` → Bağlı kameraları bul
4. `InstantCamera(device)` → Kamera nesnesi oluştur
5. `camera.Open()` → Bağlantıyı aç
6. Ayarlar: PixelFormat, ROI, FPS, Exposure, Gain
7. `camera.StartGrabbing()` → Frame yakalamaya başla
8. `camera.RetrieveResult()` → Frame al

### 5.3 Kamera Ayarları

| Ayar | Değer | Amaç |
|---|---|---|
| PixelFormat | Mono8 | Minimum bant genişliği |
| ExposureTime | 1000 µs | Hareket bulanıklığını önle |
| GainAuto | Once (başlangıçta) | Sahneye göre otomatik ayar |
| AcquisitionFrameRate | 800 fps | Maksimum zamansal çözünürlük |
| TriggerMode | Off | Sürekli (free-run) yakalama |

### 5.4 Çoklu Thread Mimarisi

```
┌─────────────────────┐
│   Ana Thread (UI)    │  ← tkinter event loop
│   - Butonlar         │
│   - Canvas gösterim  │
│   - root.after()     │
└────────┬────────────┘
         │ root.after(0, callback)
┌────────┴────────────┐
│  Grab Thread         │  ← camera._grab_loop()
│  - RetrieveResult()  │     HER frame için:
│  - detect_fast()     │     1. Raw array al
│  - Belleğe kayıt     │     2. Tespit callback çağır
│  - ~30 FPS ekrana    │     3. Kayıt varsa frame biriktir
└─────────────────────┘     4. ~30 FPS'de BGR → ekran kuyruğu
         │
┌────────┴────────────┐
│  Video Loop Thread   │  ← _video_loop()
│  - Ekran kuyruğundan │     Son frame'i al, overlay çiz,
│    frame al          │     canvas'a gönder
│  - ~30 FPS gösterim  │
└─────────────────────┘
```

**Neden 3 thread?**
- **Grab thread:** Kamera donanımından veri almayı bloklamaz
- **Video loop:** Ekran gösterimini grab hızından bağımsız tutar
- **Ana thread:** UI'ın donmamasını sağlar
- Thread'ler arası iletişim: `queue.Queue` ve `threading.Event`

---

## 6. Nesne Tespit Algoritması

### 6.1 Silüet Yöntemi (Backlit Detection)

Arka aydınlatmalı kurulumda parçacık koyu silüet olarak görünür. Tespit adımları:

```
Ham Frame (Mono8, gri)
    ↓
Threshold (gray < eşik → nesne)
    ↓
Binary Mask (0/255)
    ↓
findContours → En büyük kontur
    ↓
moments → Ağırlık merkezi (centroid)
    ↓
Koordinat dönüşümü (90°CW → fiziksel y ekseni)
    ↓
Pozisyon kaydı (x, y, timestamp)
```

### 6.2 Hızlı Tespit (detect_fast)

800 FPS'de her frame için tespit yapılır. Performans kritik:

| İşlem | Süre | Açıklama |
|---|---|---|
| Threshold | ~0.05 ms | `cv2.threshold(gray, T, 255, THRESH_BINARY_INV)` |
| findContours | ~0.1 ms | `cv2.findContours(mask, RETR_EXTERNAL, ...)` |
| moments | ~0.02 ms | `cv2.moments(cnt)` → centroid |
| **Toplam** | **~0.2 ms** | 800 FPS bütçesi: 1.25 ms ✓ |

**Neden morfoloji yok?** Morfolojik işlemler (open/close) ~0.7 ms ekler → toplam 0.9 ms → hala bütçe içinde ama marjinal. Backlit kurulumda gürültü düşük olduğundan morfoloji gereksiz.

**Neden döndürme yok?** `cv2.rotate()` ~0.6 ms alır → bütçeyi aşar. Bunun yerine tespit sonrası koordinat dönüşümü yapılır:
```
90°CW döndürme: (cx, cy) → (H - 1 - cy, cx)
```
Bu sadece iki aritmetik işlem — süre: ~0.001 ms.

### 6.3 Parlaklık Eşiği (Threshold)

Kullanıcı arayüzünde slider ile ayarlanabilir (10–250 arası):
- **Düşük eşik (ör. 30):** Sadece çok koyu nesneler algılanır → gürültüye dayanıklı
- **Yüksek eşik (ör. 150):** Daha açık tonlar da algılanır → hassas ama gürültülü

Optimum değer sahne aydınlatmasına bağlıdır. Tipik backlit kurulumda 60–100 arası.

---

## 7. Hız Ölçümü

### 7.1 Segment Yöntemi

Düşme mesafesi sabit uzunluktaki segmentlere (varsayılan 50 mm) bölünür:

```
Pozisyon 1 ──┐
             │ Segment 1: Δy₁ piksel, Δt₁ saniye
Pozisyon N ──┘
             │ Segment 2: Δy₂ piksel, Δt₂ saniye
Pozisyon M ──┘
             ...
```

Her segment için ortalama hız:
```
v_segment = (Δy / px_per_mm) / Δt    [mm/s]
```

### 7.2 Terminal Hız Tespiti

Hız-mesafe grafiğinde stabil bölge aranır:

1. Segment hızları kayan ortalama ile düzleştirilir
2. Her pencere (min 15 nokta) için varyasyon katsayısı hesaplanır:
   ```
   CV = std(v) / mean(v)
   ```
3. CV < %5 olan ilk pencere → terminal hız bölgesi
4. Bu bölgenin ortalaması = terminal hız

**Terminal hıza ulaşılamazsa** Cd hesabı yapılmaz — kullanıcıya uyarı verilir.

---

## 8. Kalibrasyon

### 8.1 Neden Kalibrasyon Gerekli?

1. **Piksel → mm dönüşümü:** Kameranın gördüğü piksel sayısının fiziksel uzunluğa karşılığı
2. **Silindirik kırılma:** Cam tüp + sıvı kombinasyonu optik bozulma yaratır

### 8.2 Birleşik Kalibrasyon Yöntemi

Kullanıcı görüntüde en az 5 referans noktasına tıklar (zoom ile hassas seçim):

1. Her ardışık nokta çifti için gerçek mesafe (mm) girilir
2. **Ölçek:** Tüm çiftlerin piksel/mm oranlarının ortalaması
3. **Kırılma düzeltmesi:** Görünen y-koordinatları ile gerçek y-koordinatları arasında 3. derece polinom fit

### 8.3 Otomatik Kayıt/Yükleme

Kalibrasyon tamamlandığında `calibration_auto.json` dosyasına otomatik kaydedilir. Uygulama tekrar açıldığında otomatik yüklenir — her seferinde yeniden kalibrasyon gerekmez.

---

## 9. Video Kayıt ve Analiz

### 9.1 Kayıt Akışı

```
⏺ Kayıt Başlat
    ↓
Grab loop'ta HER frame belleğe biriktir (tam FPS, döndürülmüş)
    ↓
⏹ Durdur
    ↓
▶ İzle (bellekten oynat, slider ile ileri/geri, play/pause)
    ↓
💾 Videoyu Kaydet (dosyaya yaz)
```

Bu akış kullanıcıya:
- Önce yüksek hızda kayıt yapma
- Sonra ağır çekimde inceleme
- Kaydedilmiş videodan tekrar analiz yapma imkanı verir

---

## 10. Sonuç Hesaplama Akışı

```
1. Kalibrasyon yap (piksel/mm ölçek)
2. Kamerayı başlat (deney modu: Mono8 + ROI + 800 FPS)
3. Ölçümü başlat
4. Parçacığı sıvıya bırak
5. Sistem otomatik olarak:
   a. Her frame'de parçacık konumunu tespit eder
   b. Anlık hızı hesaplar ve grafik çizer
   c. Terminal hız bölgesini arar
6. Ölçümü durdur
7. "Cd Hesapla" butonuna bas
8. Sistem:
   a. Terminal hız tespit edildi mi kontrol eder
   b. Duvar etkisi düzeltmesi uygular (isteğe bağlı)
   c. Cd, Re hesaplar
   d. Stokes ve Schiller-Naumann ile karşılaştırır
   e. Hata yüzdeleri hesaplar
   f. Akış rejimini belirler
```

---

## 11. Tipik Deney Parametreleri

### Çelik Bilye + Gliserin Örneği

| Parametre | Değer | Birim |
|---|---|---|
| Parçacık çapı | 5.0 | mm |
| Parçacık yoğunluğu | 7800 | kg/m³ |
| Akışkan yoğunluğu | 1260 | kg/m³ |
| Dinamik viskozite | 1.41 | Pa·s |
| Silindir iç çapı | 50 | mm |
| Çap oranı (λ) | 0.1 | - |
| Beklenen Re | ~1–10 | - (Ara rejim) |

---

## 12. Kullanılan Teknolojiler

| Teknoloji | Amaç |
|---|---|
| Python 3.14 | Ana programlama dili |
| tkinter | Grafik kullanıcı arayüzü |
| OpenCV (cv2) | Görüntü işleme, tespit, video I/O |
| NumPy | Sayısal hesaplamalar |
| SciPy | İstatistiksel analiz, interpolasyon |
| Matplotlib | Hız-mesafe grafikleri |
| Pillow | Tkinter görüntü dönüşümü |
| pypylon | Basler Pylon SDK Python bağlayıcısı |
| uv | Paket yönetimi |

---

## 13. Sistemin Avantajları

1. **Yüksek zamansal çözünürlük:** 800 FPS ile hızlı parçacıklar bile yakalanır
2. **Otomatik tespit:** Manuel müdahale gerektirmez — silüet yöntemi güvenilir
3. **Gerçek zamanlı analiz:** Düşme sırasında anlık hız görüntülenir
4. **Tekrarlanabilirlik:** Video kaydedip sonra analiz yapılabilir
5. **Doğrulama:** Stokes ve ampirik korelasyonlarla karşılaştırma
6. **Duvar düzeltmesi:** Sonlu çaplı silindir etkisi hesaba katılır
7. **Kalibrasyon hafızası:** Bir kez kalibre et, her açılışta otomatik yükle

---

## 14. Sınırlamalar ve Gelecek Çalışmalar

**Mevcut sınırlamalar:**
- Tek parçacık takibi (aynı anda birden fazla parçacık desteklenmez)
- Küresel parçacık varsayımı (düzensiz şekiller için Cd formülü farklı)
- 800 FPS'de belleğe kayıt süresi RAM ile sınırlı

**Potansiyel geliştirmeler:**
- Çoklu parçacık takibi
- Farklı parçacık şekilleri için Cd korelasyonları
- Sıcaklık sensörü entegrasyonu (viskozite sıcaklığa bağlı)
- Otomatik kalibrasyon deseni tanıma
