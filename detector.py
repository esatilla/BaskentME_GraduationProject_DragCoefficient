"""
detector.py — Silüet tabanlı nesne tespiti
Parlak arka plan (backlit) karşısında karanlık nesneyi bulur.
Threshold → en büyük karanlık blob → ağırlık merkezi (centroid).
"""
import time
import cv2
import numpy as np


class SilhouetteDetector:
    """
    Kullanım:
        detector.is_active = True   # ölçüm başlasın
        pos, cnt = detector.detect(frame, timestamp)
        frame = detector.draw_overlay(frame, pos, cnt, label="120 mm/s")
        detector.reset()            # sıfırla
    """

    def __init__(self, threshold=80, min_area=150):
        self.threshold  = threshold   # karanlık eşiği (0–255); altı = nesne
        self.min_area   = min_area    # minimum blob alanı (piksel²)
        self.is_active  = False       # True iken pozisyon kaydeder
        self.positions  = []          # [(x, y), ...]  piksel
        self.timestamps = []          # [t, ...]  saniye
        self.frame_count = 0

    # ── Temel işlemler ────────────────────────────────────────────────────────

    def reset(self):
        self.positions.clear()
        self.timestamps.clear()
        self.frame_count = 0
        self.is_active = False

    def detect(self, frame, timestamp=None):
        """
        Frame'deki en büyük karanlık bölgeyi bul.
        is_active=True iken bulunan konumu kaydeder.

        Returns:
            ((cx, cy), contour)  — bulundu
            (None, None)         — nesne yok / alan çok küçük
        """
        if timestamp is None:
            timestamp = time.time()

        # Gri ton
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame

        # Threshold: threshold'un altındaki pikseller = karanlık bölge
        _, mask = cv2.threshold(gray, self.threshold, 255, cv2.THRESH_BINARY_INV)

        # Morfolojik temizleme
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  k)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)

        # En büyük kontur
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            return None, None

        cnt = max(cnts, key=cv2.contourArea)
        if cv2.contourArea(cnt) < self.min_area:
            return None, None

        M = cv2.moments(cnt)
        if M['m00'] == 0:
            return None, None

        cx = int(M['m10'] / M['m00'])
        cy = int(M['m01'] / M['m00'])

        if self.is_active:
            self.positions.append((cx, cy))
            self.timestamps.append(timestamp)
            self.frame_count += 1

        return (cx, cy), cnt

    def detect_fast(self, frame, timestamp, coord_transform=None):
        """Hızlı tespit: morfoloji yok, sadece threshold + centroid.
        800 FPS grab thread'inde kullanılır.

        coord_transform: (cx, cy, h, w) → (new_cx, new_cy) dönüşüm fonksiyonu.
        Pozisyon kaydı dönüştürülmüş koordinatlarla yapılır.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        _, mask = cv2.threshold(gray, self.threshold, 255, cv2.THRESH_BINARY_INV)
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            return None
        cnt = max(cnts, key=cv2.contourArea)
        if cv2.contourArea(cnt) < self.min_area:
            return None
        M = cv2.moments(cnt)
        if M['m00'] == 0:
            return None
        cx = int(M['m10'] / M['m00'])
        cy = int(M['m01'] / M['m00'])

        # Koordinat dönüşümü (örn. 90° CW rotasyon)
        if coord_transform is not None:
            h, w = frame.shape[:2]
            cx, cy = coord_transform(cx, cy, h, w)

        if self.is_active:
            self.positions.append((cx, cy))
            self.timestamps.append(timestamp)
            self.frame_count += 1
        return (cx, cy)

    # ── Görselleştirme ────────────────────────────────────────────────────────

    def draw_overlay(self, frame, pos, cnt, label=None):
        """Tespit sonucunu frame üzerine çiz (in-place değil, kopyaya)."""
        if pos is None:
            return frame
        cx, cy = pos

        # Sınır kutusu
        if cnt is not None:
            x, y, w, h = cv2.boundingRect(cnt)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Ağırlık merkezi
        cv2.circle(frame, (cx, cy), 6, (0, 255, 255), -1)
        cv2.drawMarker(frame, (cx, cy), (0, 255, 255),
                       cv2.MARKER_CROSS, 24, 2, cv2.LINE_AA)

        # Hız etiketi
        if label:
            cv2.putText(frame, label, (cx + 12, cy - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0, 255, 255), 2, cv2.LINE_AA)
        return frame

    # ── Özet (results_mixin uyumluluğu) ──────────────────────────────────────

    def get_tracking_summary(self):
        return {
            'total_points': len(self.positions),
            'positions':    list(self.positions),
            'timestamps':   list(self.timestamps),
            'duration':     (self.timestamps[-1] - self.timestamps[0])
                            if len(self.timestamps) > 1 else 0,
            'is_tracking':  self.is_active,
            'track_lost':   False,
        }
