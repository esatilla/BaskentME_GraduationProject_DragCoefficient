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
