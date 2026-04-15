# Basler acA1440-220uc — Kamera Referans Kılavuzu

Bu dosya bağlı kameradan doğrudan okunarak elde edilmiş gerçek değerleri içerir.

---

## Kamera Kimliği

| Özellik | Değer |
|---|---|
| Model | acA1440-220uc |
| Seri Numarası | 40567127 |
| Üretici | Basler |
| Donanım Versiyonu | 107653-15 |
| Sensör Çözünürlüğü | 1456 × 1088 px |
| Aktif Görüntü Alanı | 1440 × 1080 px |
| Bağlantı | USB 3.0 SuperSpeed |
| Link Hızı | 500 Mbps |
| Çalışma Sıcaklığı | 62 °C (ölçüm anında) |

---

## 1. ROI (Region of Interest — İlgi Bölgesi)

ROI, sensörün yalnızca bir bölümünü aktif hale getirerek daha yüksek kare hızı veya daha az bant genişliği kullanmayı sağlar.

### Gerçek Değer Aralıkları (kameradan okundu)

| Parametre | Mevcut | Min | Max | Artış (inc) |
|---|---|---|---|---|
| OffsetX | 8 px | 0 | 16 | 4 px |
| OffsetY | 4 px | 0 | 8 | 2 px |
| Width | 1440 px | 4 | 1448 | 4 px |
| Height | 1080 px | 2 | 1084 | 2 px |

> **Not:** `Width` ve `Height` değerleri `inc` adımlarının katı olmalıdır.
> Offset + boyut ≤ maksimum sensör sınırını aşmamalıdır.

### pypylon Kodu

```python
from pypylon import pylon

factory = pylon.TlFactory.GetInstance()
usb_tl  = factory.CreateTl("BaslerUsb")
cam     = pylon.InstantCamera(usb_tl.CreateDevice(usb_tl.EnumerateDevices()[0]))
cam.Open()

# Tam ROI sıfırlama (önce offset'leri sıfırla, sonra boyutu ayarla)
cam.OffsetX.SetValue(0)
cam.OffsetY.SetValue(0)
cam.Width.SetValue(cam.Width.GetMax())
cam.Height.SetValue(cam.Height.GetMax())

# Özel ROI: 720×540 merkez kırpma
roi_w, roi_h = 720, 540
cam.Width.SetValue(roi_w)
cam.Height.SetValue(roi_h)
cam.OffsetX.SetValue((cam.SensorWidth.GetValue()  - roi_w) // 2)
cam.OffsetY.SetValue((cam.SensorHeight.GetValue() - roi_h) // 2)

# Mevcut değerleri okuma
print(f"ROI: {cam.Width.GetValue()}x{cam.Height.GetValue()} "
      f"@ offset ({cam.OffsetX.GetValue()}, {cam.OffsetY.GetValue()})")
```

### camera_interface.py'ye Entegrasyon

```python
def set_roi(self, offset_x, offset_y, width, height):
    """ROI ayarla. Önce offset'leri sıfırla, sonra boyutu ver."""
    if not self.is_open:
        return False, "Kamera açık değil"
    try:
        self.camera.OffsetX.SetValue(0)
        self.camera.OffsetY.SetValue(0)
        self.camera.Width.SetValue(width)
        self.camera.Height.SetValue(height)
        self.camera.OffsetX.SetValue(offset_x)
        self.camera.OffsetY.SetValue(offset_y)
        return True, f"ROI: {width}x{height} @ ({offset_x},{offset_y})"
    except Exception as e:
        return False, str(e)

def reset_roi(self):
    """Tam sensör alanına dön."""
    if not self.is_open:
        return
    self.camera.OffsetX.SetValue(0)
    self.camera.OffsetY.SetValue(0)
    self.camera.Width.SetValue(self.camera.Width.GetMax())
    self.camera.Height.SetValue(self.camera.Height.GetMax())
```

---

## 2. FPS (Kare Hızı)

### Gerçek Değer Aralıkları (kameradan okundu)

| Parametre | Değer |
|---|---|
| `AcquisitionFrameRateEnable` | False (devre dışı) |
| `AcquisitionFrameRate` aralığı | 0.006 – 1.000.000 fps |
| `ResultingFrameRate` (mevcut) | **227.74 fps** (exposure limiti ile) |

> **Önemli:** `AcquisitionFrameRateEnable = False` olduğunda FPS, exposure süresi
> tarafından belirlenir: `FPS_max ≈ 1 / ExposureTime_s`  
> Örnek: 3000 μs exposure → max 333 fps (sensör sınırı: ~227 fps)

### pypylon Kodu

```python
# FPS sınırlamasını etkinleştir
cam.AcquisitionFrameRateEnable.SetValue(True)

# FPS ayarla (izin verilen maks değeri aşmadan)
target_fps = 100.0
max_fps    = cam.AcquisitionFrameRate.GetMax()
cam.AcquisitionFrameRate.SetValue(min(target_fps, max_fps))

# Gerçekte elde edilen FPS'i oku (exposure'dan kısıtlanmış olabilir)
print(f"Hedef FPS : {target_fps}")
print(f"Elde edilen: {cam.ResultingFrameRate.GetValue():.2f} fps")

# FPS sınırlamasını kaldır (maksimum hız için)
cam.AcquisitionFrameRateEnable.SetValue(False)
```

### FPS – Exposure İlişkisi

| Exposure (μs) | Teorik Max FPS | Sensör Sınırı |
|---|---|---|
| 100 | 10.000 | ~227 fps |
| 1.000 | 1.000 | ~227 fps |
| 3.000 | 333 | ~227 fps |
| 5.000 | 200 | 200 fps |
| 10.000 | 100 | 100 fps |
| 50.000 | 20 | 20 fps |

---

## 3. Gain (Kazanç)

### Gerçek Değer Aralıkları (kameradan okundu)

| Parametre | Değer |
|---|---|
| `GainAuto` | Off |
| `GainSelector` | `All` (tek kanal, renkli sensör tek gain) |
| Mevcut Gain | 0.0 dB |
| Minimum | 0.0 dB |
| Maksimum | **36.0 dB** |

> **Rehber:** Her 6 dB artış, sinyal gücünü iki katına çıkarır (SNR düşer).
> Düşük ışık için 6–12 dB arası önerilir. 24 dB üzeri görüntü gürültüsü belirginleşir.

### pypylon Kodu

```python
# Manuel gain ayarı
cam.GainAuto.SetValue("Off")
cam.GainSelector.SetValue("All")   # Tek kanal (bu kamera için tek seçenek)

gain_db = 6.0   # 0.0 – 36.0 dB arası
cam.Gain.SetValue(gain_db)
print(f"Gain: {cam.Gain.GetValue():.2f} dB")

# Otomatik gain
cam.GainAuto.SetValue("Once")       # Bir kez ayarla, sonra kilitle
cam.GainAuto.SetValue("Continuous") # Sürekli otomatik (hareket eden sahnede titrer)
cam.GainAuto.SetValue("Off")        # Manuel mod
```

### camera_interface.py'ye Entegrasyon

```python
def set_gain(self, gain_db):
    """Gain ayarla (0.0 – 36.0 dB)."""
    if not self.is_open:
        return
    try:
        self.camera.GainAuto.SetValue("Off")
        g_min = self.camera.Gain.GetMin()
        g_max = self.camera.Gain.GetMax()
        self.camera.Gain.SetValue(max(g_min, min(gain_db, g_max)))
    except Exception:
        pass
```

---

## 4. White Balance (Beyaz Dengesi)

### Gerçek Değer Aralıkları (kameradan okundu)

| Kanal | Mevcut Oran | Min | Max |
|---|---|---|---|
| Red | 1.0000 | 0.0 | 15.9998 |
| Green | 1.0667 | 0.0 | 15.9998 |
| Blue | **7.5757** | 0.0 | 15.9998 |

> `BalanceWhiteAuto = Continuous` — Kamera otomatik ayarlamaktadır.
> Blue oranının yüksek olması (7.57) mavi kanalın daha az hassas olduğunu gösterir
> (soğuk beyaz ışık / LED aydınlatma altında tipiktir).

### pypylon Kodu

```python
# Otomatik beyaz dengesi
cam.BalanceWhiteAuto.SetValue("Continuous")  # Sürekli otomatik
cam.BalanceWhiteAuto.SetValue("Once")        # Bir kez ayarla, kilitle
cam.BalanceWhiteAuto.SetValue("Off")         # Manuel mod

# Manuel oran ayarı
cam.BalanceWhiteAuto.SetValue("Off")

cam.BalanceRatioSelector.SetValue("Red")
cam.BalanceRatio.SetValue(1.2)

cam.BalanceRatioSelector.SetValue("Green")
cam.BalanceRatio.SetValue(1.0)   # Referans kanal genellikle Green=1.0

cam.BalanceRatioSelector.SetValue("Blue")
cam.BalanceRatio.SetValue(1.8)

# Mevcut değerleri oku
for ch in ["Red", "Green", "Blue"]:
    cam.BalanceRatioSelector.SetValue(ch)
    print(f"  {ch:5}: {cam.BalanceRatio.GetValue():.4f}")
```

### camera_interface.py'ye Entegrasyon

```python
def set_white_balance(self, red=1.0, green=1.0, blue=1.0):
    """Manuel beyaz dengesi oranları ayarla."""
    if not self.is_open:
        return
    try:
        self.camera.BalanceWhiteAuto.SetValue("Off")
        for ch, val in [("Red", red), ("Green", green), ("Blue", blue)]:
            self.camera.BalanceRatioSelector.SetValue(ch)
            self.camera.BalanceRatio.SetValue(val)
    except Exception:
        pass

def auto_white_balance_once(self):
    """Bir kez otomatik beyaz dengesi uygula, sonra kilitle."""
    if not self.is_open:
        return
    try:
        self.camera.BalanceWhiteAuto.SetValue("Once")
        import time
        time.sleep(0.5)   # Kameranın hesaplaması için bekle
        # Once modu tamamlandığında otomatik olarak Off'a döner
    except Exception:
        pass
```

---

## 5. Diğer Önemli Ayarlar

### Pixel Format

| Format | Açıklama | Kullanım |
|---|---|---|
| `BayerRG8` | Ham Bayer 8-bit (mevcut) | Ham görüntü, converter gerekir |
| `BGR8` | 8-bit renkli (dönüştürülmüş) | OpenCV doğrudan kullanır |
| `RGB8` | 8-bit renkli | PIL/NumPy için uygun |
| `Mono8` | 8-bit gri | En hızlı, en düşük bant genişliği |
| `BayerRG12` | Ham 12-bit | Yüksek dinamik aralık |
| `YCbCr422_8` | Video formatı | Video kaydı için |

```python
cam.PixelFormat.SetValue("BGR8")   # OpenCV ile doğrudan kullanım
cam.PixelFormat.SetValue("Mono8")  # Gri ölçek, en hızlı mod
```

### Black Level (Siyah Seviye)

| Parametre | Mevcut | Min | Max |
|---|---|---|---|
| `BlackLevel` | 0.0 | 0.0 | 31.9375 |

```python
cam.BlackLevel.SetValue(0.0)   # Varsayılan: 0
```

### Gamma

| Parametre | Değer |
|---|---|
| `GammaEnable` | (donanım desteği yok) |
| `Gamma` | 1.0 (doğrusal) |

```python
# Gamma düzeltmesi (1.0 = doğrusal, 0.45 = sRGB benzeri)
cam.Gamma.SetValue(1.0)
```

### Binning (Piksel Birleştirme)

ROI ile birlikte kullanılarak çözünürlük düşürülür, SNR artar.

```python
cam.BinningHorizontal.SetValue(2)   # Yatayda 2'ye 1 birleştir
cam.BinningVertical.SetValue(2)     # Dikeyde 2'ye 1 birleştir
# Sonuç: Efektif çözünürlük yarıya düşer, FPS ve SNR artar
```

### Trigger (Tetikleme)

```python
# Serbest çalışma (varsayılan)
cam.TriggerMode.SetValue("Off")

# Yazılım trigger
cam.TriggerMode.SetValue("On")
cam.TriggerSource.SetValue("Software")
cam.TriggerSelector.SetValue("FrameStart")
cam.TriggerSoftware.Execute()   # Kareyi tetikle

# Donanım trigger (Line1 — GPIO)
cam.TriggerMode.SetValue("On")
cam.TriggerSource.SetValue("Line1")
cam.TriggerActivation.SetValue("RisingEdge")
```

---

## 6. Tipik Deney Konfigürasyonları

### Yavaş Düşen Parçacık (viskoz sıvı, Stokes rejimi)
```python
cam.AcquisitionFrameRateEnable.SetValue(True)
cam.AcquisitionFrameRate.SetValue(30.0)      # 30 fps yeterli
cam.ExposureTime.SetValue(5000.0)            # 5 ms, bulanıklık az
cam.GainAuto.SetValue("Off")
cam.Gain.SetValue(6.0)                       # Biraz kazanç, ışık yetersizse
cam.BalanceWhiteAuto.SetValue("Once")
```

### Hızlı Düşen Parçacık (su, Newton rejimi)
```python
cam.AcquisitionFrameRateEnable.SetValue(True)
cam.AcquisitionFrameRate.SetValue(200.0)     # Yüksek FPS
cam.ExposureTime.SetValue(500.0)             # 0.5 ms, hareket bulanıklığını önler
cam.GainAuto.SetValue("Off")
cam.Gain.SetValue(12.0)                      # Kısa exposure'ı telafi et
cam.PixelFormat.SetValue("Mono8")            # Gri, daha hızlı transfer
```

### ROI ile Yüksek Hız
```python
# Küçük ROI → daha az veri → daha yüksek FPS
cam.OffsetX.SetValue(560)
cam.OffsetY.SetValue(270)
cam.Width.SetValue(320)
cam.Height.SetValue(540)
cam.AcquisitionFrameRateEnable.SetValue(True)
cam.AcquisitionFrameRate.SetValue(500.0)     # Küçük ROI'de çok daha yüksek FPS
```

---

## 7. Hızlı Referans Tablosu

| Ayar | pypylon Özelliği | Tür | Birim |
|---|---|---|---|
| ROI sol kenar | `OffsetX` | Int (0–16, adım 4) | px |
| ROI üst kenar | `OffsetY` | Int (0–8, adım 2) | px |
| ROI genişlik | `Width` | Int (4–1448, adım 4) | px |
| ROI yükseklik | `Height` | Int (2–1084, adım 2) | px |
| FPS aktif | `AcquisitionFrameRateEnable` | Bool | — |
| FPS değeri | `AcquisitionFrameRate` | Float (0.006–1M) | fps |
| Elde edilen FPS | `ResultingFrameRate` | Float (salt okunur) | fps |
| Exposure modu | `ExposureAuto` | `Off/Once/Continuous` | — |
| Exposure süresi | `ExposureTime` | Float (21–10.000.000) | μs |
| Gain modu | `GainAuto` | `Off/Once/Continuous` | — |
| Gain değeri | `Gain` | Float (0–36) | dB |
| WB modu | `BalanceWhiteAuto` | `Off/Once/Continuous` | — |
| WB kanal seç | `BalanceRatioSelector` | `Red/Green/Blue` | — |
| WB oran | `BalanceRatio` | Float (0–15.9998) | — |
| Piksel format | `PixelFormat` | Enum | — |
| Siyah seviye | `BlackLevel` | Float (0–31.9375) | — |
| Gamma | `Gamma` | Float | — |

---

*Veriler 2026-04-12 tarihinde acA1440-220uc (S/N: 40567127) kamerasından doğrudan okunmuştur.*
