"""
ui/tracking_mixin.py — Silüet tabanlı ölçüm başlatma/durdurma/sıfırlama (mixin)
"""

from tkinter import messagebox
from ui.theme import SUCCESS, HIGHLIGHT


class TrackingMixin:

    def _toggle_measurement(self):
        """Ölçümü başlat / durdur toggle."""
        if self.detector is None:
            messagebox.showwarning("Uyarı", "Dedektör başlatılmamış.")
            return

        if self.detector.is_active:
            # Durdur
            self.detector.is_active = False
            self.measure_btn.configure(text="▶  Ölçümü Başlat", bg=SUCCESS)
            n = len(self.detector.positions)
            self._log(f"Ölçüm durduruldu — {n} nokta kaydedildi.")
        else:
            # Parametre kontrolü
            missing = []
            if not self._fluid_selected:
                missing.append("Sıvı seçilmedi")
            if not self._material_selected:
                missing.append("Cisim malzemesi seçilmedi")
            if not self._diameter_selected:
                missing.append("Cisim çapı seçilmedi")
            if missing:
                messagebox.showwarning("Eksik Parametre",
                                       "\n".join(missing))
                return

            # Başlat
            self.detector.reset()
            self.detector.is_active = True
            self.speed_var.set("-- mm/s")
            self.vel_cv.delete("all")
            self.measure_btn.configure(text="⏹  Ölçümü Durdur", bg=HIGHLIGHT)
            self._log("Ölçüm başlatıldı — cismi serbest bırakın.")

    def _reset_tracking(self):
        if self.detector is not None:
            self.detector.reset()
        self.measure_btn.configure(text="▶  Ölçümü Başlat", bg=SUCCESS)
        self.speed_var.set("-- mm/s")
        self.vel_cv.delete("all")
        self._log("Ölçüm sıfırlandı.")

    def _set_threshold(self, value):
        """Tespit parlaklık eşiğini ayarla."""
        if self.detector is not None:
            self.detector.threshold = value

    def _set_min_area(self, value):
        if self.detector is not None:
            self.detector.min_area = value

    # ── Ölçüm bölgesi dikdörtgen seçimi ─────────────────────────────────────

    def _start_rect_select(self):
        self._rect_select_step = 1
        self._rect_first_pt = None
        self._log("Bölge seçimi: sol üst köşeye tıklayın.")

    def _on_rect_click(self, fx, fy):
        if self._rect_select_step == 1:
            self._rect_first_pt = (fx, fy)
            self._rect_select_step = 2
            self._log(f"Sol üst köşe: ({fx}, {fy}) — şimdi sağ alt köşeye tıklayın.")
        elif self._rect_select_step == 2:
            x1, y1 = self._rect_first_pt
            x2, y2 = fx, fy
            self._meas_rect = (min(x1, x2), min(y1, y2),
                               max(x1, x2), max(y1, y2))
            self._rect_select_step = 0
            self._rect_first_pt = None
            r = self._meas_rect
            self._log(f"Ölçüm bölgesi: ({r[0]},{r[1]}) – ({r[2]},{r[3]})")

    def _clear_rect(self):
        self._meas_rect = None
        self._rect_select_step = 0
        self._rect_first_pt = None
        self._log("Ölçüm bölgesi kaldırıldı.")
