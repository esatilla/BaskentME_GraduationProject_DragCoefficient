# Optik Hesap Raporu — Kamera Yerleşim Mesafesi

**Proje:** Drag Tracker — ME491 Bitirme Projesi  
**Kamera:** Basler acA1440-220uc  
**Lens:** Computar C125-1218-5M (f = 12 mm)  
**Kurulum:** Kamera 90° yan çevrilmiş (portrait mod)

---

## 1. Donanım Parametreleri

### 1.1 Sensör (Sony IMX273)

| Parametre | Değer |
|---|---|
| Çözünürlük | 1440 × 1080 piksel |
| Piksel boyutu | 3.45 µm = 0.00345 mm |
| Sensör genişliği | 1440 × 0.00345 = **4.968 mm** |
| Sensör yüksekliği | 1080 × 0.00345 = **3.726 mm** |

### 1.2 Lens

| Parametre | Değer |
|---|---|
| Odak uzaklığı | f = 12 mm |
| Format | 1/2" C-mount |
| Çözünürlük | 5 MP |

---

## 2. Koordinat Sistemi — 90° Dönüş Etkisi

Kamera dik (portrait) konuma çevrildiğinde piksel eksenleri yer değiştirir:

```
Normal (landscape):          90° yan çevrilmiş (portrait):
─────────────────────        ─────────────────────
Yatay → 1440 px (4.968 mm)  Yatay → 1080 px (3.726 mm)
Dikey → 1080 px (3.726 mm)  Dikey → 1440 px (4.968 mm)
```

Sonuç: **Dikey görüş alanı sensörün uzun kenarıyla (4.968 mm) belirlenir.**

---

## 3. İnce Mercek Formülü

Kamera optiğinin temel denklemi:

$$\frac{1}{f} = \frac{1}{d_o} + \frac{1}{d_i}$$

| Sembol | Anlam |
|---|---|
| f | Odak uzaklığı (mm) |
| d_o | Nesne mesafesi — kamera ile nesne arası (mm) |
| d_i | Görüntü mesafesi — lens ile sensör arası (mm) |

### Büyütme

$$m = \frac{d_i}{d_o} = \frac{\text{sensör boyutu}}{\text{nesne boyutu}}$$

### d_o İçin Çözüm

m tanımından: d_i = m · d_o

Lens denklemine koyunca:

$$\frac{1}{f} = \frac{1}{d_o} + \frac{1}{m \cdot d_o} = \frac{1 + \frac{1}{m}}{d_o}$$

$$\boxed{d_o = f \cdot \left(1 + \frac{1}{m}\right)}$$

---

## 4. Görüş Alanı (FOV) Hesabı

Verilen bir d_o mesafesinde görüş alanı:

$$\text{FOV} = \frac{\text{sensör boyutu}}{m} = \text{sensör boyutu} \cdot \frac{d_o}{d_i}$$

Büyük çalışma mesafelerinde (d_o >> f) yaklaşık formül:

$$\text{FOV} \approx \frac{\text{sensör boyutu} \times d_o}{f}$$

---

## 5. Senaryo Hesapları

### Senaryo A — 1 m Nesneyi Tam Görmek

**Hedef:** FOV_dikey = 1000 mm

$$m = \frac{4.968}{1000} = 0.004968$$

$$d_o = 12 \times \left(1 + \frac{1}{0.004968}\right) = 12 \times 202.3 = 2427.5 \text{ mm}$$

$$d_i = \frac{1}{\frac{1}{12} - \frac{1}{2427.5}} = 12.060 \text{ mm}$$

| Sonuç | Değer |
|---|---|
| Çalışma mesafesi | **~243 cm** |
| Dikey FOV (1440 px) | 1000 mm = 100 cm |
| Yatay FOV (1080 px) | 750 mm = 75 cm |
| Piksel çözünürlüğü | 1000/1440 = **0.69 mm/px** |

---

### Senaryo B — 2 m Sabit Mesafe

**Hedef:** d_o = 2000 mm (sabit)

$$d_i = \frac{1}{\frac{1}{12} - \frac{1}{2000}} = \frac{24000}{1988} = 12.073 \text{ mm}$$

$$m = \frac{12.073}{2000} = 0.006036$$

$$\text{FOV}_{\text{dikey}} = \frac{4.968}{0.006036} = 822.9 \text{ mm}$$

$$\text{FOV}_{\text{yatay}} = \frac{3.726}{0.006036} = 617.1 \text{ mm}$$

| Sonuç | Değer |
|---|---|
| Çalışma mesafesi | 200 cm |
| Dikey FOV (1440 px) | **823 mm ≈ 82 cm** |
| Yatay FOV (1080 px) | **617 mm ≈ 62 cm** |
| Piksel çözünürlüğü | 823/1440 = **0.57 mm/px** |

---

### Senaryo C — 60 cm Orta Bölge (Seçilen Kurulum)

**Hedef:** FOV_dikey = 600 mm (1 m tüpün ortasındaki 60 cm aktif düşüş bölgesi)

$$m = \frac{4.968}{600} = 0.00828$$

$$d_o = 12 \times \left(1 + \frac{1}{0.00828}\right) = 12 \times \left(1 + 120.77\right) = 12 \times 121.77 = 1461.3 \text{ mm}$$

$$d_i = \frac{1}{\frac{1}{12} - \frac{1}{1461.3}} = 12.099 \text{ mm}$$

$$\text{FOV}_{\text{yatay}} = \frac{3.726}{0.00828} = 450.0 \text{ mm}$$

| Sonuç | Değer |
|---|---|
| **Çalışma mesafesi** | **~146 cm** |
| Dikey FOV (1440 px) | **600 mm = 60 cm** ✓ |
| Yatay FOV (1080 px) | **450 mm = 45 cm** |
| **Piksel çözünürlüğü** | 600/1440 = **0.42 mm/px** |

---

## 6. Karşılaştırma Tablosu

| Senaryo | Mesafe | Dikey FOV | Yatay FOV | mm/piksel |
|---|---|---|---|---|
| A — Tam tüp | 243 cm | 100 cm | 75 cm | 0.69 |
| B — 2 m sabit | 200 cm | 82 cm | 62 cm | 0.57 |
| **C — 60 cm orta** | **146 cm** | **60 cm** | **45 cm** | **0.42** |

Mesafe azaldıkça piksel başına düşen fiziksel boyut küçülür → daha hassas hız ve Cd ölçümü.

---

## 7. Piksel Çözünürlüğünün Ölçüm Hassasiyetine Etkisi

Piksel çözünürlüğü doğrudan hız ölçüm hassasiyetini etkiler:

$$\Delta v = \frac{\text{mm/piksel}}{\Delta t}$$

220 fps'de Δt = 1/220 = 4.55 ms olduğunda:

| Senaryo | mm/px | Minimum ölçülebilir hız |
|---|---|---|
| A (243 cm) | 0.69 | 0.69 / 0.00455 = **151 mm/s** |
| B (200 cm) | 0.57 | 0.57 / 0.00455 = **125 mm/s** |
| **C (146 cm)** | **0.42** | 0.42 / 0.00455 = **92 mm/s** |

Senaryo C, terminal hıza yakın yavaş hareket eden parçacıklar için en iyi hassasiyeti sağlar.

---

## 8. Sonuç ve Öneri

**Önerilen kurulum: Kameradan tüpe ~146 cm mesafe**

- Tüpün üst ve alt ucundan 20 cm'er kenar payı bırakarak 60 cm'lik orta bölge izlenir
- Parçacık bu bölgeye girdiğinde terminal hıza ulaşmış olur (başlangıç ivmesinden arınmış)
- 0.42 mm/piksel çözünürlük, Cd hesabı için yeterli hassasiyeti sağlar
- Yatay FOV (45 cm) tüp çapını rahatlıkla kapsar

```
Tüp (1 m):
┌──────────────────────────┐  ← üst (kamera görmez, 20 cm)
│  ························  │
│  ·  İzlenen Bölge  ·  ·  │  ← 60 cm (kamera görür)
│  ························  │
└──────────────────────────┘  ← alt (kamera görmez, 20 cm)

Kamera ←————— ~146 cm —————→ Tüp
```
