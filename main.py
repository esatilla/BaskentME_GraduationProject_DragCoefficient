"""
main.py — Sürüklenme Katsayısı Ölçüm Sistemi
Basler acA 1440-220uc  |  Ana thread hiçbir zaman bloke olmaz
"""

import tkinter as tk
import threading

import matplotlib
matplotlib.use('Agg')

from calibration import RefractionCalibrator
from detector import SilhouetteDetector

from ui.theme import DARK_BG
from ui.widget_helpers import WidgetHelpersMixin
from ui.panels import PanelsMixin
from ui.video_loop_mixin import VideoLoopMixin
from ui.source_mixin import SourceMixin
from ui.calibration_mixin import CalibrationMixin
from ui.tracking_mixin import TrackingMixin
from ui.results_mixin import ResultsMixin
from ui.export_mixin import ExportMixin
from ui.settings_mixin import SettingsMixin


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
    def __init__(self, root):
        self.root = root
        self.root.title("Sürüklenme Katsayısı Ölçüm Sistemi  |  Basler acA 1440-220uc")
        self.root.geometry("1500x900")
        self.root.configure(bg=DARK_BG)
        self.root.resizable(True, True)

        # Alt sistemler
        self.calibrator   = RefractionCalibrator()
        self.detector     = SilhouetteDetector(threshold=80)
        self.camera       = None
        self.video_source = None

        # Kaynak modu
        self.source_mode = tk.StringVar(value="live")

        # Durum bayrakları
        self.is_running   = False
        self.is_recording = False
        self.record_writer = None
        self.record_path   = None

        # Kalibrasyon durumu (ana thread'e ait; thread sadece okur)
        self._calib_mode  = "idle"
        self.calib_points = []

        # Deney parametreleri (varsayılan 0 = seçilmedi)
        self.particle_diameter = tk.DoubleVar(value=0.0)
        self.particle_density  = tk.DoubleVar(value=0.0)
        self.fluid_density     = tk.DoubleVar(value=0.0)
        self.fluid_viscosity   = tk.DoubleVar(value=0.0)
        self.cylinder_diameter = tk.DoubleVar(value=45.0)
        self.apply_wall_corr   = tk.BooleanVar(value=True)
        self._fluid_selected    = False
        self._material_selected = False
        self._diameter_selected = False

        # Görüntü döndürme — varsayılan: 90°CW (deney modu)
        self.rotation_code = tk.IntVar(value=1)

        # Kamera ayarları
        self.cam_exposure  = tk.IntVar(value=1000)
        self.cam_fps       = tk.IntVar(value=100)
        self.cam_roi_height = tk.IntVar(value=270)   # ROI yüksekliği (px)

        # Tespit eşiği (0–255; altındaki pikseller = nesne)
        self.detect_threshold = tk.IntVar(value=80)

        # Sonuç geçmişi
        self.results = []

        # Thread güvenliği
        self._loop_id         = 0
        self.stop_event       = threading.Event()
        self.frame_lock       = threading.Lock()
        self.latest_frame     = None
        self.latest_annotated = None
        self._last_det_pos    = None   # son tespit pozisyonu (grab callback)
        self._last_det_cnt    = None   # son tespit konturu (grab callback)

        self._build_ui()
        self._log("Sistem hazır.")
        self._log(self._check_pypylon())
        self._auto_load_calib()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)


    def _on_close(self):
        self._signal_stop()
        try:
            if self.camera:
                self.camera.close()
        except Exception:
            pass
        try:
            if self.video_source:
                self.video_source.close()
        except Exception:
            pass
        try:
            if self.is_recording and self.record_writer:
                self.record_writer.release()
        except Exception:
            pass
        self.root.destroy()


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    DragCoefficientApp(root)
    root.mainloop()
