"""
tracker.py - Otomatik nesne takip modülü
Parçacığı arka plan çıkarma + kontur analizi + OpenCV tracker ile takip eder.
"""
import numpy as np
import cv2
import time


class ParticleTracker:
    """
    Sıvı içinde düşen küresel parçacıkları takip eder.
    
    İki aşamalı yaklaşım:
    1. Otomatik tespit: Arka plan çıkarma + dairesel kontur analizi
    2. Takip: CSRT tracker (hassas, yavaş hareket için ideal)
    """
    
    # OpenCV sürümüne göre tracker fabrika fonksiyonlarını ayarla
    _TRACKER_FACTORIES = {
        'CSRT':  ('TrackerCSRT_create',  'TrackerMIL_create'),
        'KCF':   ('TrackerKCF_create',   'TrackerMIL_create'),
        'MIL':   ('TrackerMIL_create',   None),
    }
    
    @staticmethod
    def _get_tracker_factory(preferred='CSRT'):
        """OpenCV sürümüne uygun tracker factory'yi döndürür."""
        # Eski API (< 4.5.1)
        old_names = {'CSRT': 'TrackerCSRT_create', 'MIL': 'TrackerMIL_create',
                     'KCF': 'TrackerKCF_create'}
        # Yeni API (>= 4.5.1)
        new_names = {'CSRT': ('TrackerMIL_create',), 'MIL': ('TrackerMIL_create',),
                     'KCF': ('TrackerMIL_create',)}
        
        # Önce tercih edilen tracker'ı dene
        for name in [old_names.get(preferred, ''), 'TrackerMIL_create',
                     'TrackerCSRT_create', 'TrackerKCF_create']:
            factory = getattr(cv2, name, None)
            if factory is not None:
                return factory
        
        # Son çare: genel Tracker
        return None
    
    TRACKER_TYPES = {}  # Çalışma zamanında doldurulacak
    
    def __init__(self, tracker_type='CSRT'):
        self.tracker = None
        self.tracker_type = tracker_type
        self.bbox = None           # (x, y, w, h) piksel cinsinden
        self.center = None         # (cx, cy) piksel cinsinden
        self.is_tracking = False
        self.track_lost = False
        
        # İzleme geçmişi
        self.positions = []        # [(cx, cy), ...]
        self.timestamps = []       # [t, ...]
        self.frame_count = 0
        
        # Arka plan çıkarma
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=50, varThreshold=25, detectShadows=False
        )
        self.bg_initialized = False
        
        # ROI (ilgi bölgesi) - tüp alanı
        self.roi = None            # (x, y, w, h)
        
        # Arama bölgesi - tüp kenarlarının yaklaşık konumu
        self.search_margin = 30   # piksel
        
        # Parçacık boyut filtresi
        self.min_area_px = 30
        self.max_area_px = 50000
        self.circularity_threshold = 0.4
        
        # Kalman filtresi (gürültüyü azaltmak için)
        self.kalman = self._create_kalman()
        self.kalman_initialized = False
    
    def _create_kalman(self):
        """4 durum değişkeni (x, y, vx, vy), 2 ölçüm (x, y)"""
        kf = cv2.KalmanFilter(4, 2)
        kf.measurementMatrix = np.array([[1, 0, 0, 0],
                                          [0, 1, 0, 0]], np.float32)
        kf.transitionMatrix = np.array([[1, 0, 1, 0],
                                         [0, 1, 0, 1],
                                         [0, 0, 1, 0],
                                         [0, 0, 0, 1]], np.float32)
        kf.processNoiseCov = np.eye(4, dtype=np.float32) * 0.03
        kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * 1.0
        kf.errorCovPost = np.eye(4, dtype=np.float32)
        return kf
    
    def set_roi(self, x, y, w, h):
        """İlgi bölgesini ayarla (tüp içi bölge)."""
        self.roi = (int(x), int(y), int(w), int(h))
    
    def set_size_filter(self, min_area_px, max_area_px):
        """Parçacık boyut filtrelerini ayarla."""
        self.min_area_px = min_area_px
        self.max_area_px = max_area_px
    
    def initialize_tracker(self, frame, bbox):
        """
        Verilen bounding box ile tracker'ı başlat.
        bbox: (x, y, w, h)
        """
        if self.tracker is not None:
            self.tracker = None
        
        try:
            factory = self._get_tracker_factory(self.tracker_type)
            if factory:
                self.tracker = factory()
            else:
                raise RuntimeError("Tracker bulunamadı")
        except Exception:
            factory = getattr(cv2, 'TrackerMIL_create', None)
            if factory:
                self.tracker = factory()
            else:
                return False
        
        success = self.tracker.init(frame, bbox)
        
        if success:
            self.bbox = bbox
            cx = int(bbox[0] + bbox[2] / 2)
            cy = int(bbox[1] + bbox[3] / 2)
            self.center = (cx, cy)
            self.is_tracking = True
            self.track_lost = False
            
            # Kalman'ı başlat
            self.kalman.statePre = np.array([[cx], [cy], [0], [0]], np.float32)
            self.kalman.statePost = np.array([[cx], [cy], [0], [0]], np.float32)
            self.kalman_initialized = True
        
        return success
    
    def update(self, frame, timestamp=None):
        """
        Yeni kareyi işle ve parçacığı güncelle.
        
        Returns: (success, center_px, bbox) 
            center_px: (cx, cy) Kalman filtreli merkez
            bbox: (x, y, w, h) takip kutusu
        """
        if timestamp is None:
            timestamp = time.time()
        
        self.frame_count += 1
        
        if not self.is_tracking or self.tracker is None:
            return False, None, None
        
        success, bbox = self.tracker.update(frame)
        
        if success:
            x, y, w, h = [int(v) for v in bbox]
            self.bbox = (x, y, w, h)
            cx = x + w // 2
            cy = y + h // 2
            
            # Kalman güncellemesi
            if self.kalman_initialized:
                pred = self.kalman.predict()
                meas = np.array([[np.float32(cx)], [np.float32(cy)]])
                corrected = self.kalman.correct(meas)
                cx_k = int(corrected[0])
                cy_k = int(corrected[1])
            else:
                cx_k, cy_k = cx, cy
            
            self.center = (cx_k, cy_k)
            self.track_lost = False
            
            self.positions.append((cx_k, cy_k))
            self.timestamps.append(timestamp)
            
            return True, (cx_k, cy_k), (x, y, w, h)
        else:
            self.track_lost = True
            # Kalman tahmini kullan
            if self.kalman_initialized:
                pred = self.kalman.predict()
                cx_k = int(pred[0])
                cy_k = int(pred[1])
                self.center = (cx_k, cy_k)
                return False, (cx_k, cy_k), self.bbox
            
            return False, None, None
    
    def auto_detect(self, frame):
        """
        Arka plan çıkarma ve kontur analizi ile parçacığı otomatik tespit et.
        
        Returns: [(bbox, score), ...] - tespit edilen adaylar
        """
        # ROI uygula
        if self.roi:
            rx, ry, rw, rh = self.roi
            work_frame = frame[ry:ry+rh, rx:rx+rw]
            offset = (rx, ry)
        else:
            work_frame = frame
            offset = (0, 0)
        
        # Gri tonlamaya çevir
        gray = cv2.cvtColor(work_frame, cv2.COLOR_BGR2GRAY) if len(work_frame.shape) == 3 else work_frame.copy()
        
        # Gaussian blur ile gürültü azalt
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        candidates = []
        
        # Yöntem 1: Arka plan çıkarma
        fg_mask = self.bg_subtractor.apply(blurred)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_clean = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        fg_clean = cv2.morphologyEx(fg_clean, cv2.MORPH_CLOSE, kernel)
        
        contours_bg, _ = cv2.findContours(fg_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for cnt in contours_bg:
            area = cv2.contourArea(cnt)
            if self.min_area_px <= area <= self.max_area_px:
                score = self._score_contour(cnt, area, gray)
                if score > 0:
                    x, y, w, h = cv2.boundingRect(cnt)
                    # Offset ekle
                    x += offset[0]
                    y += offset[1]
                    candidates.append(((x, y, w, h), score))
        
        # Yöntem 2: Eşikleme (arka plan yoksa)
        if not candidates or not self.bg_initialized:
            _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            thresh_clean = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
            contours_th, _ = cv2.findContours(thresh_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for cnt in contours_th:
                area = cv2.contourArea(cnt)
                if self.min_area_px <= area <= self.max_area_px:
                    score = self._score_contour(cnt, area, gray)
                    if score > 0.3:
                        x, y, w, h = cv2.boundingRect(cnt)
                        x += offset[0]
                        y += offset[1]
                        candidates.append(((x, y, w, h), score * 0.8))
        
        self.bg_initialized = True
        
        # Skora göre sırala
        candidates.sort(key=lambda c: c[1], reverse=True)
        return candidates[:5]  # En iyi 5 adayı döndür
    
    def _score_contour(self, contour, area, gray_frame):
        """Konturun parçacık olma ihtimalini puanlar (0-1)."""
        if area < self.min_area_px:
            return 0
        
        # Dairesellık kontrolü: 4π*A / P²
        perimeter = cv2.arcLength(contour, True)
        if perimeter < 1:
            return 0
        
        circularity = 4 * np.pi * area / (perimeter ** 2)
        if circularity < self.circularity_threshold:
            return 0
        
        # En-boy oranı (küre için ~1)
        x, y, w, h = cv2.boundingRect(contour)
        aspect = min(w, h) / max(w, h) if max(w, h) > 0 else 0
        if aspect < 0.4:
            return 0
        
        # Yuvarlak nesne skoru
        score = circularity * 0.6 + aspect * 0.4
        return score
    
    def reset(self):
        """Tüm takip geçmişini sıfırla."""
        self.tracker = None
        self.bbox = None
        self.center = None
        self.is_tracking = False
        self.track_lost = False
        self.positions = []
        self.timestamps = []
        self.frame_count = 0
        self.bg_initialized = False
        self.kalman_initialized = False
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=50, varThreshold=25, detectShadows=False
        )
        self.kalman = self._create_kalman()
    
    def draw_overlay(self, frame, calibrator=None, show_trajectory=True):
        """
        Takip sonuçlarını frame üzerine çiz.
        
        Returns: annotated frame
        """
        output = frame.copy()
        
        # Bounding box
        if self.bbox and self.is_tracking:
            x, y, w, h = self.bbox
            color = (0, 255, 0) if not self.track_lost else (0, 165, 255)
            cv2.rectangle(output, (x, y), (x + w, y + h), color, 2)
        
        # Merkez noktası
        if self.center:
            cx, cy = self.center
            cv2.circle(output, (cx, cy), 4, (0, 255, 255), -1)
            cv2.circle(output, (cx, cy), 8, (0, 255, 255), 1)
        
        # Yörünge çizgisi
        if show_trajectory and len(self.positions) > 1:
            pts = np.array(self.positions[-100:], dtype=np.int32)  # Son 100 nokta
            for i in range(1, len(pts)):
                alpha = i / len(pts)
                color_intensity = int(255 * alpha)
                cv2.line(output, tuple(pts[i-1]), tuple(pts[i]),
                         (0, color_intensity, 255 - color_intensity), 2)
        
        # ROI sınırı
        if self.roi:
            rx, ry, rw, rh = self.roi
            cv2.rectangle(output, (rx, ry), (rx + rw, ry + rh), (255, 100, 0), 1)
            cv2.putText(output, "ROI", (rx + 5, ry + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 100, 0), 1)
        
        # Durum metni
        status_color = (0, 255, 0) if (self.is_tracking and not self.track_lost) else (0, 0, 255)
        if self.is_tracking and not self.track_lost:
            status = f"TAKIP AKTIF | {len(self.positions)} nokta"
        elif self.track_lost:
            status = "TAKIP KAYBI - Yeniden aranıyor..."
        else:
            status = "Bekleniyor..."
        
        cv2.putText(output, status, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
        
        return output
    
    def get_tracking_summary(self):
        """Takip özetini döndür."""
        return {
            'total_points': len(self.positions),
            'positions': self.positions.copy(),
            'timestamps': self.timestamps.copy(),
            'duration': (self.timestamps[-1] - self.timestamps[0]) if len(self.timestamps) > 1 else 0,
            'is_tracking': self.is_tracking,
            'track_lost': self.track_lost,
        }
