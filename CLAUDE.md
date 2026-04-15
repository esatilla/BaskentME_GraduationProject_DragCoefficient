# Drag Tracker — Sürükleme Katsayısı Ölçüm Sistemi

Baskent Üniversitesi Makine Mühendisliği ME491 bitirme projesi.
Silindirik bir tüp içinde viskoz sıvıda düşen küresel parçacıkların terminal hızını ve sürükleme katsayısını (Cd) otomatik olarak ölçer.

---

## Proje Yapısı

```
drag_tracker/
├── main.py                      # __init__, mixin birleştirme, entry point (~90 satır)
├── camera_interface.py          # BaslerCamera / VideoFileSource / MockCamera
├── tracker.py                   # CSRT + Kalman filtreli parçacık takibi
├── physics.py                   # Hız, terminal hız, Cd, duvar düzeltmesi hesabı
├── calibration.py               # Lens distorsiyonu + silindirik refraksiyon kalibrasyonu
├── diagnose_camera.py           # Kamera bağlantı tanılama aracı
│
├── ui/                          # GUI modülleri (mixin mimarisi)
│   ├── __init__.py
│   ├── theme.py                 # Renk sabitleri ve font tanımları
│   ├── widget_helpers.py        # _sec, _btn, _bsm, _ent, _slider (WidgetHelpersMixin)
│   ├── panels.py                # _build_ui, _build_left/center/right (PanelsMixin)
│   ├── video_loop_mixin.py      # _launch_loop, _video_loop, _show_frame (VideoLoopMixin)
│   ├── source_mixin.py          # Kamera/video kaynak yönetimi (SourceMixin)
│   ├── calibration_mixin.py     # Kalibrasyon UI + canvas tıklama (CalibrationMixin)
│   ├── tracking_mixin.py        # Manuel ROI, otomatik tespit (TrackingMixin)
│   ├── results_mixin.py         # Cd hesap, sonuç gösterimi, grafik (ResultsMixin)
│   ├── export_mixin.py          # Video kayıt, ekran görüntüsü, CSV/JSON (ExportMixin)
│   └── settings_mixin.py        # ROI/FPS/Gain/WB ayarları + canlı önizleme (SettingsMixin)
│
├── requirements.txt             # Bağımlılıklar
├── run.bat                      # Venv ile başlatma scripti (Windows)
└── venv/                        # Python sanal ortamı (Python 3.14)
```

---

## Mixin Mimarisi

`DragCoefficientApp` tüm mixin'lerden miras alır:

```python
class DragCoefficientApp(
    WidgetHelpersMixin,
    PanelsMixin,
    VideoLoopMixin,
    SourceMixin,
    CalibrationMixin,
    TrackingMixin,
    ResultsMixin,
    ExportMixin,
    SettingsMixin,
):
```

Her mixin `self.root`, `self.calibrator`, `self.tracker` gibi `__init__`'te tanımlanan
instance değişkenlerine doğrudan erişir. Mixin'ler arası bağımlılık yoktur.

---

## Venv ile Çalıştırma

```bat
run.bat
```

Veya manuel:

```bat
venv\Scripts\activate
python main.py
```

---

## Modüller

### main.py — Orkestrasyon
- `DragCoefficientApp.__init__()`: tüm state değişkenleri, mixin birleştirme
- `_on_close()`: temiz kapanma (kamera, video, kayıt serbest bırakma)

### camera_interface.py — Kamera Arayüzü
- `BaslerCamera`: pypylon ile Basler acA1440-220uc USB kamerası
- `VideoFileSource`: OpenCV ile MP4/AVI/MOV/MKV oynatma
- `MockCamera`: Gerçek kamera olmadan test için simülasyon

### Donanım Özellikleri

**Kamera: Basler acA1440-220uc**
| Özellik | Değer |
|---|---|
| Sensör | Sony IMX273 (1/2.9") |
| Çözünürlük | 1440 × 1080 px |
| Piksel boyutu | 3.45 µm |
| Sensör boyutu | 4.968 mm × 3.726 mm |
| Arayüz | USB 3.0 |
| Maks. kare hızı | 220 fps |

**Lens: Computar C125-1218-5M**
| Özellik | Değer |
|---|---|
| Odak uzaklığı | 12 mm |
| Maksimum diyafram | F1.8 |
| Format | 1/2" C-mount |
| Çözünürlük | 5 MP |

**Kurulum Geometrisi (kamera 90° yan)**

Kamera dik çevrilince 1440-piksel ekseni dikey yönü, 1080-piksel ekseni yatay yönü kapsar.

1 metre yüksekliğindeki nesneyi tam görmek için gereken mesafe:

```
m = sensör_yükseklik / nesne_yükseklik = 4.968 mm / 1000 mm = 0.004968
d_nesne = f × (1 + 1/m) = 12 × (1 + 1000/4.968) ≈ 2428 mm ≈ 243 cm
```

| Parametre | Değer |
|---|---|
| **Önerilen çalışma mesafesi** | **~146 cm** (60 cm orta bölge, yüksek çözünürlük) |
| Dikey görüş alanı (1440 px) | 600 mm = 60 cm |
| Yatay görüş alanı (1080 px) | ~450 mm = 45 cm |
| Piksel çözünürlüğü | **~0.42 mm/piksel** |
| *(Referans) 243 cm mesafe* | *1 m tam frame, 0.69 mm/piksel* |

> Hedef: 1 m'lik tüpün ortasındaki 60 cm'lik aktif düşüş bölgesini izlemek.
> Detaylı optik hesap için bkz. [optik.md](optik.md).

### tracker.py — Parçacık Takibi
- `ParticleTracker` sınıfı
- Otomatik tespit: MOG2 + dairesellik skoru
- Takip: OpenCV CSRT + 4-durumlu Kalman filtresi [x, y, vx, vy]

### physics.py — Fizik Hesapları
- `calculate_instantaneous_velocity()` — sonlu farklar ile piksel→mm/s
- `detect_terminal_velocity()` — kayan pencere stabilite analizi
- `apply_wall_correction()` — Francis/Ladenburg duvar etkisi (λ = d_p / d_cyl)
- `calculate_drag_coefficient()` — kuvvet dengesi, Re, Stokes/Schiller-Naumann karşılaştırması

**Cd formülü:**
```
Cd = (4/3) × (d / v²) × ((ρ_p - ρ_f) / ρ_f) × g
Re = ρ_f × v × d / μ
```

**Akış rejimleri:**
| Re | Rejim |
|---|---|
| < 0.5 | Stokes |
| 0.5 – 2 | Alt geçiş |
| 2 – 500 | Ara |
| 500 – 2×10⁵ | Newton |
| > 2×10⁵ | Türbülanslı |

### calibration.py — Kalibrasyon
- Checkerboard: OpenCV lens distorsiyonu
- 2 nokta tıklamayla piksel/mm ölçek
- Silindirik refraksiyon: 3. derece polinom

---

## Bağımlılıklar

| Paket | Kullanım |
|---|---|
| opencv-python | Kamera, tracker, görüntü işleme |
| numpy | Vektörel hesaplar |
| scipy | Smoothing, interpolasyon |
| Pillow | Tkinter görüntü dönüşümü |
| matplotlib | Grafik ve analiz plotları |
| pypylon | Basler Pylon SDK Python bağlayıcısı |

---

## Görev Yürütme Kuralları

Yeni bir görev geldiğinde şu sırayı uygula:

1. **Planla** — Hangi dosyalar etkilenecek? Hangi bağımlılıklar var? Adımları listele.
2. **Paralel yürüt** — Bağımsız dosya yazımları / araştırmalar aynı anda çalıştırılır.
3. **Subagent kullan** — Büyük keşif veya araştırma görevlerini `Explore` ya da `general-purpose`
   subagent'e delege et; ana context'i şişirme.
4. **Test et** — Sözdizimi kontrolü (`python -c "import ..."`) her yeni modülden sonra.
5. **CLAUDE.md güncelle** — Güncelleme Geçmişi tablosuna satır ekle.

**Ne zaman subagent aç:**
- Yeni bir kütüphane / API araştırması (pypylon, OpenCV, vs.)
- Birden fazla dosyayı etkileyen kapsamlı yeniden yapılandırma
- Kodun büyük bölümünü okuyup analiz etmek gerektiğinde

**Ne zaman paralel araç çağrısı yap:**
- Birbirinden bağımsız dosya yazımları (aynı mesajda birden fazla `Write`)
- Bağımsız doğrulama adımları

---

## Geliştirme Notları

- Gerçek Basler kamera yoksa `MockCamera` simülasyonu kullanılabilir
- Yeni özellik eklerken uygun mixin'e ekle; `main.py`'ye dokunma
- Tüm UI güncellemeleri `root.after(0, callback)` ile yapılmalıdır (thread safety)
- `diagnose_camera.py` kamera bağlantı sorunlarını tanılamak için ayrıca çalıştırılabilir

---

## Güncelleme Geçmişi

| Tarih | Değişiklik |
|---|---|
| 2026-04-12 | venv kurulumu, main.py → ui/ mixin mimarisine bölündü |
| 2026-04-12 | basler.md oluşturuldu — ROI/FPS/Gain/WB gerçek değerleri ve pypylon kodları |
| 2026-04-12 | settings_mixin.py eklendi — Gelişmiş Kamera Ayarları penceresi + canlı önizleme |
| 2026-04-12 | settings_mixin.py güncellendi — ROI preset butonları, anlık FPS tahmini, otomatik ResultingFPS yenileme |
| 2026-04-12 | Görüntü döndürme eklendi — settings_mixin + video_loop_mixin; 0°/90°CW/180°/90°CCW, undistort sonrası takip öncesi |
| 2026-04-12 | Donanım özellikleri eklendi — acA1440-220uc sensör tablosu, C125-1218-5M lens, 243 cm çalışma mesafesi hesabı |
| 2026-04-12 | Çalışma mesafesi 146 cm olarak güncellendi — hedef 60 cm orta bölge, 0.42 mm/px; optik.md oluşturuldu |
| 2026-04-12 | settings_mixin.py düzeltildi — `selectforeground` hatası (Python 3.14 uyumsuzluğu) kaldırıldı; tüm bölümler try/except ile korundu |
| 2026-04-12 | WB "Bir Kez" polling eklendi — otomatik ayar bitince sliderlar yeni değere güncellenir; "Sürekli" modda sliderlar kilitli kalır |
| 2026-04-12 | 800 FPS preset düzeltildi — BayerRG8 piksel formatı eklendi (BGR8→1byte/px); set_roi'ye pixel_format parametresi eklendi |
| 2026-04-12 | Ana menüden FPS slider kaldırıldı — sadece Gelişmiş Ayarlar'da; settings preview ROI overlay düzeltildi (kamera koordinatlarıyla dikdörtgen → metin etiketi) |
| 2026-04-12 | Simülasyon modu kaldırıldı (panels/source_mixin/main); Deney Modu preseti FPS slider'ını da 800'e günceller |
| 2026-04-12 | Uygulama deney modunda açılır — rotation_code=1 (90°CW), kamera başlayınca configure_experiment_mode() otomatik çağrılır (BayerRG8+ROI+800FPS) |
