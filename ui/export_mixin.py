"""
ui/export_mixin.py — Video kayıt, ekran görüntüsü ve veri dışa aktarma (mixin)
"""

import json

import cv2
from tkinter import filedialog, messagebox

from ui.theme import HIGHLIGHT


class ExportMixin:

    def _toggle_record(self):
        if not self.is_recording:
            path = filedialog.asksaveasfilename(
                title="Video Kaydet",
                defaultextension=".avi",
                filetypes=[("AVI", "*.avi"), ("MP4", "*.mp4")])
            if not path:
                return
            with self.frame_lock:
                f = self.latest_annotated
            if f is None:
                messagebox.showwarning("Uyarı", "Kamera aktif değil.")
                return
            h, w = f.shape[:2]
            fc = (cv2.VideoWriter_fourcc(*'XVID') if path.endswith('.avi')
                  else cv2.VideoWriter_fourcc(*'mp4v'))
            self.record_writer = cv2.VideoWriter(path, fc, 30.0, (w, h))
            self.record_path  = path
            self.is_recording = True
            self.rec_btn.configure(text="⏹  Kaydı Durdur", bg="#cc0000")
            self._log(f"Kayıt başladı: {path}")
        else:
            self.is_recording = False
            if self.record_writer:
                self.record_writer.release()
                self.record_writer = None
            self.rec_btn.configure(text="⏺  Kayıt", bg=HIGHLIGHT)
            self._log(f"Kayıt durduruldu: {self.record_path}")

    def _screenshot(self):
        with self.frame_lock:
            f = self.latest_annotated
        if f is None:
            return
        p = filedialog.asksaveasfilename(
            title="Ekran Görüntüsü",
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")])
        if p:
            cv2.imwrite(p, f)
            self._log(f"Ekran görüntüsü: {p}")

    def _export(self):
        if not self.results:
            messagebox.showwarning("Veri Yok", "Henüz hesaplanmış sonuç yok.")
            return
        p = filedialog.asksaveasfilename(
            title="Sonuçları Kaydet",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("CSV", "*.csv")])
        if not p:
            return
        if p.endswith('.json'):
            with open(p, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
        elif p.endswith('.csv'):
            import csv
            with open(p, 'w', newline='', encoding='utf-8') as f:
                w2 = csv.DictWriter(f, fieldnames=self.results[0].keys())
                w2.writeheader()
                w2.writerows(self.results)
        self._log(f"Sonuçlar kaydedildi: {p}")

    def _clear_history(self):
        if messagebox.askyesno("Onay", "Tüm geçmiş silinsin mi?"):
            self.results.clear()
            self.hist.delete(0, "end")
            self._reset_tracking()
            self._log("Geçmiş temizlendi.")
