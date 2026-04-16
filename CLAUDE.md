# Drag Tracker — Sürükleme Katsayısı Ölçüm Sistemi

Baskent Üniversitesi Makine Mühendisliği ME491 bitirme projesi.
Silindirik bir tüp içinde viskoz sıvıda düşen küresel parçacıkların terminal hızını ve sürükleme katsayısını (Cd) otomatik olarak ölçer.

**GitHub:** https://github.com/esatilla/BaskentME_GraduationProject_DragCoefficient

---

## Proje Yapısı

```
drag_tracker/
├── main.py                      # __init__, mixin birleştirme, entry point
├── camera_interface.py          # BaslerCamera / VideoFileSource / MockCamera
├── detector.py                  # Silüet tabanlı nesne tespiti (threshold + centroid)
├── tracker.py                   # CSRT + Kalman filtreli parçacık takibi (eski, kullanılmıyor)
├── physics.py                   # Hız, terminal hız, Cd, duvar düzeltmesi hesabı
├── calibration.py               # Lens distorsiyonu + silindirik refraksiyon kalibrasyonu
├── diagnose_camera.py           # Kamera bağlantı tanılama aracı
│
├── ui/                          # GUI modülleri (mixin mimarisi)
│   ├── __init__.py
│   ├── theme.py                 # Renk sabitleri ve font tanımları
│   ├── widget_helpers.py        # _sec, _btn, _bsm, _ent, _slider (WidgetHelpersMixin)
│   ├── panels.py                # _build_ui, _build_left/center/right (PanelsMixin)
│   ├── video_loop_mixin.py      # _launch_loop, _video_loop, _show_frame, grab callback (VideoLoopMixin)
│   ├── source_mixin.py          # Kamera başlat/durdur toggle, canlı ROI değiştirme (SourceMixin)
│   ├── calibration_mixin.py     # Birleşik kalibrasyon + zoom + otomatik kaydet/yükle (CalibrationMixin)
│   ├── tracking_mixin.py        # Ölçüm başlat/durdur toggle, threshold ayarı (TrackingMixin)
│   ├── results_mixin.py         # Cd hesap, terminal hız kontrolü, sonuç gösterimi (ResultsMixin)
│   ├── export_mixin.py          # Belleğe kayıt, izle (ileri/geri/pause), dosyaya kaydet (ExportMixin)
│   └── settings_mixin.py        # ROI/FPS/Gain ayarları, Mono8'de WB gizli (SettingsMixin)
│
├── pyproject.toml               # uv bağımlılık yönetimi
├── uv.lock                      # Kilitleme dosyası
├── requirements.txt             # Eski pip bağımlılıkları (referans)
├── run.bat                      # uv run ile başlatma (Windows)
├── calibration_auto.json        # Otomatik kalibrasyon (gitignore'da)
├── basler.md                    # Kamera donanım referans kılavuzu
├── optik.md                     # Lens/sensör optik hesapları
└── README.md                    # Kullanım kılavuzu
```

---

## Paket Yönetimi — uv

```bash
uv sync                        # bağımlılıkları kur (.venv/ oluşturur)
uv run python main.py           # uygulamayı çalıştır
```

Veya Windows'ta: `run.bat` çift tıkla.

---

## Mixin Mimarisi

`DragCoefficientApp` tüm mixin'lerden miras alır:

```python
class DragCoefficientApp(
    WidgetHelpersMixin, PanelsMixin, VideoLoopMixin, SourceMixin,
    CalibrationMixin, TrackingMixin, ResultsMixin, ExportMixin, SettingsMixin,
):
```

Her mixin `self.root`, `self.calibrator`, `self.detector` gibi `__init__`'te tanımlanan
instance değişkenlerine doğrudan erişir.

---

## Kritik Mimari Kararlar

### Piksel Formatı: Mono8
Kamera Mono8 (gri, 1 byte/piksel) kullanır. BGR dönüşümü gereksiz, bant genişliği minimum.
Mono8'de White Balance anlamsız — ayarlar panelinde WB bölümü gizlenir.

### 800 FPS Deney Modu
- Grab callback (`_on_grab_frame`): raw Mono8 array → `detect_fast()` (morfolojisiz, döndürmesiz)
- Koordinat dönüşümü ile 90°CW rotasyon simüle edilir (döndürme 0.6ms, bütçe 1.25ms — döndürme atlanır)
- BGR dönüşümü sadece ~30 FPS ekran için yapılır (grab loop'ta throttle)
- ROI yüksekliği ile FPS ilişkisi: 270px→~620 FPS, 200px→~790 FPS, 150px→800 FPS

### GENICAM_GENTL64_PATH Düzeltmesi
Sistemde Pylon SDK kuruluysa `GENICAM_GENTL64_PATH` ortam değişkeni sistem DLL'lerine
işaret eder — pypylon ile çakışıp segfault verir. `camera_interface.py` başında
pypylon paket dizinine yönlendirilir. **Bu düzeltme olmadan VS Code'dan çalıştırma crash eder.**

### Kalibrasyon Otomatik Kayıt
Kalibrasyon yapıldığında `calibration_auto.json`'a otomatik kaydedilir.
Uygulama açılışında `_auto_load_calib()` ile otomatik yüklenir.
Manuel kaydet/yükle butonları kaldırılmıştır.

### Terminal Hız Kontrolü
`detect_terminal_velocity()` stabil bölge bulamazsa `None` döner (fallback kaldırıldı).
Cd hesabı terminal hız olmadan yapılmaz — "Terminal hıza ulaşılamadı" uyarısı verir.

### Video Kayıt Akışı
Kayıt → belleğe frame biriktir → Durdur → İzle (slider ile ileri/geri, play/pause) → Dosyaya Kaydet.
Grab loop'ta HER frame belleğe yazılır (tam FPS). İzleme modunda bellekten oynatılır.

---

## UI Buton Davranışları

| Buton | Davranış |
|---|---|
| Kamerayı Başlat | Toggle: Başlat ↔ Durdur (yeşil ↔ kırmızı) |
| Ölçümü Başlat | Toggle: Başlat ↔ Durdur |
| ROI (270/220/180/150) | Kamera açıkken canlı ROI değiştirir (grab durdur/ayarla/başlat) |
| Kaynak: Video Dosyası | Kamerayı otomatik durdurur |
| ⏺ Kayıt | Belleğe frame biriktirmeye başlar |
| ▶ İzle | Playback bar açılır (slider, play/pause, frame sayacı) |
| 💾 Videoyu Kaydet | Bellekten dosyaya yazar |

---

## Donanım

**Kamera: Basler acA1440-220uc** — USB 3.0, Sony IMX273, 1440×1080, Mono8
**Lens: Computar C125-1218-5M** — 12mm, F1.8, C-mount
**Çalışma mesafesi:** ~146 cm → 60cm dikey FOV, 0.42 mm/piksel
**ROI:** 1440×270 (varsayılan), merkez OffsetY sensörden dinamik hesaplanır: `((sensor_h - h) // 2 // 2) * 2`

---

## Tespit Algoritması

Parlak arka plan (backlit) — karanlık nesne (silüet):
1. Threshold: `gray < threshold` → binary mask (morfoloji yok, hız için)
2. findContours → en büyük blob
3. moments → centroid (ağırlık merkezi)
4. Koordinat dönüşümü (90°CW): `new_cx = h-1-cy, new_cy = cx`

Parlaklık eşiği slider ile ayarlanabilir (10–250).

---

## Bağımlılıklar

| Paket | Kullanım |
|---|---|
| opencv-python | Kamera, tespit, görüntü işleme |
| numpy | Vektörel hesaplar |
| scipy | Smoothing, interpolasyon |
| Pillow | Tkinter görüntü dönüşümü |
| matplotlib | Grafik ve analiz plotları |
| pypylon | Basler Pylon SDK Python bağlayıcısı |

---

## Geliştirme Notları

- Yeni özellik eklerken uygun mixin'e ekle; `main.py`'ye mümkünse dokunma
- Tüm UI güncellemeleri `root.after(0, callback)` ile yapılmalıdır (thread safety)
- Grab callback'te ağır işlem yapma (bütçe: <1ms/frame)
- ROI OffsetY ve Height her zaman çift sayı olmalı (kamera inc=2 gerektiriyor)
- Mono8'de WB ayarları çalışmaz — pypylon exception verir, `except` yakalar

---

## Güncelleme Geçmişi

| Tarih | Değişiklik |
|---|---|
| 2026-04-12 | İlk kurulum: venv, mixin mimarisi, basler.md, optik.md |
| 2026-04-12 | settings_mixin: ROI/FPS/Gain/WB, 800 FPS preset, döndürme |
| 2026-04-12 | Deney modu: BayerRG8 + HW ROI + 800 FPS, otomatik configure |
| 2026-04-15 | Crash fix: _grab_loop exception handling, GENICAM_GENTL64_PATH düzeltmesi |
| 2026-04-15 | 800 FPS optimizasyon: grab callback + detect_fast (morfolojisiz, döndürmesiz) |
| 2026-04-15 | ROI OffsetY dinamik merkez hesabı (sensörden), preset tutarlılığı |
| 2026-04-15 | Kamera başlat/durdur toggle, kaynak değişiminde otomatik kamera durdurma |
| 2026-04-15 | Birleşik kalibrasyon (ölçek+kırılma), zoom ile hassas nokta seçimi |
| 2026-04-15 | Kalibrasyon otomatik kaydet/yükle (calibration_auto.json) |
| 2026-04-15 | Terminal hız fallback kaldırıldı — Cd hesabı sadece stabil hız varken |
| 2026-04-15 | Ölçüm başlat/durdur toggle, parlaklık eşiği slider |
| 2026-04-15 | Canlı ROI değiştirme butonları (270/220/180/150), kamera açıkken geçerli |
| 2026-04-15 | Mono8 piksel formatı, WB Mono8'de gizli, Gain "Bir Kez" polling |
| 2026-04-15 | BGR dönüşümü grab loop'ta throttle (~30 FPS), raw callback her frame |
| 2026-04-15 | uv paket yönetimi, pyproject.toml, GitHub push |
| 2026-04-15 | Video kayıt: belleğe biriktir → İzle (slider ileri/geri, play/pause) → Kaydet |
| 2026-04-15 | UI: container tabanlı kaynak paneli (pack sıralama düzeltmesi) |
| 2026-04-15 | Geçmiş denemeler: yatay scrollbar |
