"""
calibration.py - Kırılma ve geometrik bozulma kalibrasyon modülü
Silindirik cam tüpün içindeki sıvıdan kaynaklanan optik kırılmayı düzeltir.
"""
import numpy as np
import cv2
import json
import os
import pickle
from datetime import datetime


class RefractionCalibrator:
    """
    Silindirik tüp + sıvı kırılma bozulmasını düzelten kalibratör.
    
    Kullanım:
    1. Kalibrasyon grid'i (satranç tahtası veya nokta grid) tüp içine yerleştirilir.
    2. Birkaç görüntü alınır.
    3. Bozulma haritası hesaplanır ve kaydedilir.
    4. Sonraki kullanımlarda düzeltme otomatik uygulanır.
    """
    
    def __init__(self):
        self.camera_matrix = None
        self.dist_coeffs = None
        self.map1 = None
        self.map2 = None
        self.is_calibrated = False
        self.calibration_info = {}
        
        # Geometrik ölçek: piksel başına mm
        self.px_per_mm = 1.0
        self.scale_calibrated = False
        
        # Manuel kırılma düzeltme parametresi (silindirik lens modeli)
        self.refraction_lut = None  # Look-up table: görünen_y -> gerçek_y
        
    def calibrate_from_checkerboard(self, images, board_size=(9, 6), square_size_mm=5.0):
        """
        Satranç tahtası görüntülerinden kamera kalibrasyonu ve bozulma düzeltme.
        
        images: BGR numpy array listesi
        board_size: iç köşe sayısı (sütun, satır)
        square_size_mm: kare büyüklüğü mm cinsinden
        
        Returns: (success, rms_error)
        """
        objp = np.zeros((board_size[0] * board_size[1], 3), np.float32)
        objp[:, :2] = np.mgrid[0:board_size[0], 0:board_size[1]].T.reshape(-1, 2)
        objp *= square_size_mm
        
        obj_points = []
        img_points = []
        
        img_size = None
        
        for img in images:
            if img is None:
                continue
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
            img_size = (gray.shape[1], gray.shape[0])
            
            flags = cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE
            ret, corners = cv2.findChessboardCorners(gray, board_size, flags)
            
            if ret:
                # Alt-piksel hassasiyeti
                criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
                corners_refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
                
                obj_points.append(objp)
                img_points.append(corners_refined)
        
        if len(obj_points) < 3:
            return False, "Yeterli kalibrasyon görüntüsü bulunamadı (en az 3 gerekli)"
        
        ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
            obj_points, img_points, img_size, None, None
        )
        
        if ret:
            self.camera_matrix = mtx
            self.dist_coeffs = dist
            self.map1, self.map2 = cv2.initUndistortRectifyMap(
                mtx, dist, None, mtx, img_size, cv2.CV_16SC2
            )
            self.is_calibrated = True
            self.calibration_info = {
                'method': 'checkerboard',
                'board_size': board_size,
                'square_size_mm': square_size_mm,
                'num_images': len(obj_points),
                'rms_error': ret,
                'date': datetime.now().isoformat()
            }
            return True, f"Kalibrasyon başarılı. RMS hata: {ret:.4f} piksel"
        
        return False, "Kalibrasyon başarısız"
    
    def calibrate_scale_from_reference(self, img, line_start, line_end, real_length_mm):
        """
        Bilinen uzunluktaki bir referanstan piksel/mm ölçeği hesaplar.
        Kullanıcı iki nokta işaretler ve gerçek uzunluğu girer.
        
        img: görüntü
        line_start, line_end: (x, y) koordinatları
        real_length_mm: gerçek mesafe mm cinsinden
        
        Returns: px_per_mm
        """
        dx = line_end[0] - line_start[0]
        dy = line_end[1] - line_start[1]
        length_px = np.sqrt(dx**2 + dy**2)
        
        if real_length_mm <= 0 or length_px <= 0:
            return self.px_per_mm
        
        self.px_per_mm = length_px / real_length_mm
        self.scale_calibrated = True
        self.calibration_info['px_per_mm'] = self.px_per_mm
        self.calibration_info['scale_date'] = datetime.now().isoformat()
        
        return self.px_per_mm
    
    def set_manual_scale(self, px_per_mm):
        """Manuel piksel/mm değeri ayarla."""
        self.px_per_mm = px_per_mm
        self.scale_calibrated = True
        self.calibration_info['px_per_mm'] = px_per_mm
    
    def calibrate_refraction_from_grid(self, img, grid_points_apparent, grid_points_real_mm):
        """
        Silindirik sıvı kırılmasını manuel nokta eşleştirmesiyle kalibre eder.
        
        grid_points_apparent: [(x_px, y_px), ...] kameradan görünen noktalar
        grid_points_real_mm: [(x_mm, y_mm), ...] gerçek fiziksel noktalar
        
        Bu metod, silindirik yüzeyden kaynaklanan y-eksenindeki kırılmayı 
        LUT (look-up table) olarak saklar.
        """
        if len(grid_points_apparent) < 4:
            return False, "En az 4 nokta gerekli"
        
        apparent_y = np.array([p[1] for p in grid_points_apparent], dtype=np.float64)
        real_y_px = np.array([p[1] * self.px_per_mm for p in grid_points_real_mm], dtype=np.float64)
        
        # Polinom fit ile düzeltme eğrisi
        if len(apparent_y) >= 4:
            coeffs = np.polyfit(apparent_y, real_y_px, 3)
        else:
            coeffs = np.polyfit(apparent_y, real_y_px, 1)
        
        self.refraction_poly = coeffs
        self.is_calibrated = True
        self.calibration_info['refraction_method'] = 'polynomial_lut'
        self.calibration_info['refraction_poly'] = coeffs.tolist()
        
        return True, f"Kırılma kalibrasyonu tamam ({len(grid_points_apparent)} nokta)"
    
    def correct_position(self, x_px, y_px):
        """
        Ham piksel koordinatını düzeltilmiş koordinata dönüştürür.
        Hem bozulma düzeltmesi hem kırılma düzeltmesi uygular.
        
        Returns: (x_corrected_px, y_corrected_px)
        """
        x_c, y_c = x_px, y_px
        
        # 1. Kamera bozulma düzeltmesi (lens distortion)
        if self.is_calibrated and self.camera_matrix is not None:
            pts = np.array([[[x_px, y_px]]], dtype=np.float32)
            undistorted = cv2.undistortPoints(pts, self.camera_matrix, self.dist_coeffs, P=self.camera_matrix)
            x_c = undistorted[0][0][0]
            y_c = undistorted[0][0][1]
        
        # 2. Silindirik kırılma düzeltmesi
        if hasattr(self, 'refraction_poly') and self.refraction_poly is not None:
            y_c = np.polyval(self.refraction_poly, y_c)
        
        return x_c, y_c
    
    def undistort_frame(self, frame):
        """Tüm kareye bozulma düzeltmesi uygular."""
        if not self.is_calibrated or self.map1 is None:
            return frame
        return cv2.remap(frame, self.map1, self.map2, cv2.INTER_LINEAR)
    
    def px_to_mm(self, px_value):
        """Piksel uzunluğunu mm'ye çevirir."""
        return px_value / self.px_per_mm
    
    def mm_to_px(self, mm_value):
        """mm uzunluğunu piksele çevirir."""
        return mm_value * self.px_per_mm
    
    def save(self, filepath):
        """Kalibrasyon verilerini dosyaya kaydeder."""
        data = {
            'camera_matrix': self.camera_matrix.tolist() if self.camera_matrix is not None else None,
            'dist_coeffs': self.dist_coeffs.tolist() if self.dist_coeffs is not None else None,
            'px_per_mm': self.px_per_mm,
            'scale_calibrated': self.scale_calibrated,
            'is_calibrated': self.is_calibrated,
            'calibration_info': self.calibration_info,
            'refraction_poly': getattr(self, 'refraction_poly', np.array([])).tolist() if hasattr(self, 'refraction_poly') else None
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    
    def load(self, filepath):
        """Kalibrasyon verilerini dosyadan yükler."""
        if not os.path.exists(filepath):
            return False
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        if data.get('camera_matrix'):
            self.camera_matrix = np.array(data['camera_matrix'])
        if data.get('dist_coeffs'):
            self.dist_coeffs = np.array(data['dist_coeffs'])
        
        self.px_per_mm = data.get('px_per_mm', 1.0)
        self.scale_calibrated = data.get('scale_calibrated', False)
        self.is_calibrated = data.get('is_calibrated', False)
        self.calibration_info = data.get('calibration_info', {})
        
        if data.get('refraction_poly'):
            self.refraction_poly = np.array(data['refraction_poly'])
        
        # Undistort haritalarını yeniden oluştur
        if self.camera_matrix is not None and self.dist_coeffs is not None:
            # Boyutu bilmiyoruz, ilk frame geldiğinde oluşturulacak
            pass
        
        return True
    
    def rebuild_maps(self, frame_size):
        """Undistort haritalarını belirli bir frame boyutu için yeniden oluştur."""
        if self.camera_matrix is not None and self.dist_coeffs is not None:
            self.map1, self.map2 = cv2.initUndistortRectifyMap(
                self.camera_matrix, self.dist_coeffs, None,
                self.camera_matrix, frame_size, cv2.CV_16SC2
            )
    
    def get_status_text(self):
        """Kalibrasyon durumunu metin olarak döndürür."""
        lines = []
        if self.is_calibrated:
            lines.append("✓ Lens bozulma kalibrasyonu: Aktif")
            if self.calibration_info.get('rms_error'):
                lines.append(f"  RMS Hata: {self.calibration_info['rms_error']:.4f} px")
        else:
            lines.append("✗ Lens bozulma kalibrasyonu: Pasif")
        
        if self.scale_calibrated:
            lines.append(f"✓ Ölçek: {self.px_per_mm:.3f} px/mm")
        else:
            lines.append("✗ Ölçek kalibrasyonu: Pasif (varsayılan 1 px/mm)")
        
        if hasattr(self, 'refraction_poly'):
            lines.append("✓ Kırılma düzeltmesi: Aktif")
        else:
            lines.append("✗ Kırılma düzeltmesi: Pasif")
        
        return "\n".join(lines)
