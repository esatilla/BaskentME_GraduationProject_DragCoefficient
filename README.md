# Sürüklenme Katsayısı Ölçüm Sistemi
**Basler acA 1440-220uc Kamera ile Otomatik Parçacık Takibi**

Başkent Üniversitesi Makine Mühendisliği Bitirme Projesi  
ME491 - Selin KAPLAN, Atilla ES  
Danışman: Doç. Erol Çubukçu

---

## Kurulum

### 1. Python Bağımlılıkları

```bash
pip install -r requirements.txt
```

### 2. Basler Kamera Sürücüsü (pypylon)

Basler Pylon SDK'yı https://www.baslerweb.com/en/downloads/software-downloads/ adresinden indirin.
Ardından:

```bash
pip install pypylon
```

**Not:** pypylon olmadan program "Simüle Mod" ile çalışır ve gerçek kamera olmadan test yapılabilir.

### 3. Çalıştırma

```bash
python main.py
```

---

## Dosya Yapısı

```
drag_tracker/
├── main.py              # Ana GUI uygulaması
├── physics.py           # Fizik hesaplamaları (Cd, Re, terminal hız)
├── calibration.py       # Optik kalibrasyon modülü
├── tracker.py           # Otomatik nesne takip sistemi
├── camera_interface.py  # Basler + Video dosyası arayüzü
└── requirements.txt     # Python bağımlılıkları
```

---

## Kullanım Kılavuzu

### Adım 1: Kaynak Seçimi

**Canlı Kamera Modu:**
- "Canlı Kamera" seçeneğini işaretleyin
- Exposure ve FPS değerlerini ayarlayın (acA 1440-220uc: max 220 FPS)
- "🔌 Kamerayı Başlat" butonuna tıklayın
- pypylon yüklü değilse "Simüle Mod" seçeneğini aktif edin

**Video Dosyası Modu:**
- "Video Dosyası" seçeneğini işaretleyin
- "📂 Video Dosyası Seç" ile kayıtlı videoyu açın
- ▶ Oynat / ⏸ Duraklat ile kontrol edin

### Adım 2: Kalibrasyon

#### A) Ölçek Kalibrasyonu (ZORUNLU)
1. "📏 Ölçek Kalibrasyonu" butonuna tıklayın
2. Görüntüde bilinen uzunluktaki referansın (cetvel, silindir çapı vb.) **başlangıç noktasına** tıklayın
3. **Bitiş noktasına** tıklayın
4. Açılan pencerede gerçek mesafeyi mm cinsinden girin
5. Sistem px/mm değerini otomatik hesaplar

#### B) Kırılma Düzeltmesi (ÖNERİLEN)
Silindirik cam tüp + sıvı kombinasyonu optik kırılmaya neden olur. Bu kırılmayı düzeltmek için:

**Yöntem 1 - Grid Noktaları:**
1. Tüpün içine bilinen mm koordinatlarında işaretler yerleştirin
2. "🔵 Kırılma Kalibrasyonu" butonuna tıklayın
3. Görüntüdeki noktalara sırayla tıklayın
4. Her nokta için gerçek koordinatı girin

**Yöntem 2 - Satranç Tahtası:**
1. Satranç tahtası desenini kameraya karşı farklı açılarda tutun
2. Her pozisyon için ekran görüntüsü alın
3. "♟ Satranç Tahtası Kalibrasyonu" ile görüntüleri seçin

#### C) Kalibrasyonu Kaydetme / Yükleme
- "💾 Kaydet" ile kalibrasyon verilerini JSON olarak kaydedin
- Sonraki deneyde "📂 Yükle" ile otomatik yükleyin

### Adım 3: Parçacık Parametreleri

| Parametre | Açıklama | Örnek (Çelik + Gliserin) |
|-----------|----------|--------------------------|
| Parçacık Çapı | mm cinsinden ölçülmüş gerçek çap | 5.0 mm |
| Parçacık Yoğunluğu | kg/m³ | 7800 (çelik) |
| Akışkan Yoğunluğu | kg/m³ | 1260 (gliserin 20°C) |
| Viskozite | Pa·s | 1.41 (gliserin 20°C) |
| Silindir İç Çapı | mm | 50.0 mm |

**Hızlı Seçim:** Yaygın malzeme ve akışkanlar için butonları kullanın.

### Adım 4: Takip

**Manuel ROI Seçimi (Önerilen):**
1. "🖱 Manuel Seçim (ROI)" butonuna tıklayın
2. Açılan pencerede parçacığın etrafını dikdörtgenle seçin
3. ENTER veya BOŞLUK tuşuna basın

**Otomatik Tespit:**
1. "🤖 Otomatik Tespit" butonuna tıklayın
2. Sistem en olası parçacığı arka plan çıkarma ile tespit eder
3. Tespit başarısızsa manuel seçim yapın

### Adım 5: Hesaplama

1. Parçacık tam olarak takip edildikten sonra (yeterli veri birikmesi için 2-3 sn bekleyin)
2. "🧮 C_d Hesapla" butonuna tıklayın
3. Sonuçlar sağ panelde görüntülenir

---

## Hesaplama Yöntemi

### Terminal Hız
Hız stabilitesi analizi: Kayan ortalama ile hız değişim oranı < %5 olan bölge terminal hız bölgesi kabul edilir.

### Sürüklenme Katsayısı
Kuvvet dengesi (terminal hızda):

```
F_drag = F_gravity - F_buoyancy

Cd = (4/3) × (d/v²) × ((ρ_p - ρ_f)/ρ_f) × g
```

### Duvar Etkisi Düzeltmesi (Francis/Ladenburg)
```
λ = d/D  (parçacık çapı / silindir çapı)
k = 1 / (1 - 2.104λ + 2.089λ³ - 0.948λ⁵)
v_gerçek = v_ölçülen / k
```

### Referans Değerler
- **Stokes Yasası:** Cd = 24/Re  (Re < 0.5 için geçerli)
- **Schiller-Naumann:** Cd = (24/Re)(1 + 0.15·Re^0.687)  (Re < 1000)

---

## Hata Giderme

| Sorun | Çözüm |
|-------|-------|
| "pypylon bulunamadı" | `pip install pypylon` veya Simüle Mod kullanın |
| Parçacık tespit edilemiyor | Işık koşullarını düzeltin, Min Alan değerini azaltın |
| Takip kayboldu | Manuel ROI seçimini yeniden yapın |
| Cd değeri çok yüksek/düşük | Ölçek kalibrasyonunu kontrol edin |
| Kırılma bozukluğu var | Kırılma kalibrasyonunu yapın |

---

## Teknik Özellikler - Basler acA 1440-220uc

| Özellik | Değer |
|---------|-------|
| Çözünürlük | 1440 × 1080 piksel |
| Maks. FPS | 220 fps |
| Piksel Boyutu | 4.8 μm |
| Sensör | 1/2" CMOS |
| Arayüz | USB 3.0 |
| Piksel Formatı | Mono8, BGR8 |

**Önerilen Kamera Ayarları:**
- Düşük hızlı parçacık (< 10 mm/s): 30-50 FPS, Exposure 2000-5000 μs
- Orta hız (10-100 mm/s): 100 FPS, Exposure 500-2000 μs
- Yüksek hız (> 100 mm/s): 220 FPS, Exposure 100-500 μs
