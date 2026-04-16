"""
ui/export_mixin.py — Video kayıt, izleme, kaydetme ve veri dışa aktarma (mixin)

Akış: Kayıt → belleğe biriktir → Durdur → İzle (ileri/geri/pause) → Videoyu Kaydet
"""

import json
import os
import threading
import time

import cv2
from tkinter import filedialog, messagebox

from camera_interface import BaslerCamera
from ui.theme import HIGHLIGHT, SUCCESS


class ExportMixin:

    # ── Kayıt başlat / durdur ────────────────────────────────────────────────

    def _toggle_record(self):
        if not self.is_recording:
            self._start_record()
        else:
            self._stop_record()

    def _start_record(self):
        cam = self.camera
        if cam is None or not cam.is_open:
            messagebox.showwarning("Uyarı", "Kamera aktif değil.")
            return
        cam.start_recording()
        self.is_recording = True
        self.rec_btn.configure(text="⏹  Durdur", bg="#cc0000")
        self.play_rec_btn.configure(state="disabled")
        self.save_rec_btn.configure(state="disabled")
        self._log("Kayıt başladı.")

    def _stop_record(self):
        self.is_recording = False
        cam = self.camera
        count = 0
        if cam is not None:
            count = cam.stop_recording()
        self.rec_btn.configure(text="⏺  Kayıt", bg=HIGHLIGHT)
        self._log(f"Kayıt durduruldu — {count} frame.")
        if count > 0:
            self.play_rec_btn.configure(state="normal")
            self.save_rec_btn.configure(state="normal")

    # ── Kaydı izle (bellekten, ileri/geri/pause) ─────────────────────────────

    def _play_recording(self):
        cam = self.camera
        if cam is None:
            messagebox.showwarning("Uyarı", "Kayıt bulunamadı.")
            return
        frames = getattr(cam, '_rec_frames', [])
        if not frames:
            messagebox.showwarning("Uyarı", "Bellekte kayıt yok.")
            return

        # Mevcut döngüyü durdur
        self._signal_stop()
        time.sleep(0.1)

        # Playback state
        self._pb_frames = frames
        self._pb_idx = 0
        self._pb_playing = False
        self._pb_fps = cam.grab_fps if cam.grab_fps > 0 else 30.0

        # Slider ayarla
        self.pb_slider.configure(to=len(frames) - 1)
        self.pb_slider.set(0)
        self.pb_play_btn.configure(text="▶")
        self.pb_lbl.configure(text=f"0 / {len(frames)}")

        # Oynatma çubuğunu göster
        self.playback_bar.pack(fill="x", side="bottom", before=self.canvas)

        # İlk frame'i göster
        self._pb_show_frame(0)
        self._log(f"Kayıt izleniyor: {len(frames)} frame")

    def _pb_toggle_play(self):
        """Oynat / Duraklat."""
        if not hasattr(self, '_pb_frames') or not self._pb_frames:
            return
        if self._pb_playing:
            self._pb_playing = False
            self.pb_play_btn.configure(text="▶")
        else:
            self._pb_playing = True
            self.pb_play_btn.configure(text="⏸")
            threading.Thread(target=self._pb_play_loop, daemon=True).start()

    def _pb_play_loop(self):
        """Arka planda frame'leri sırayla göster."""
        frames = self._pb_frames
        fps = min(self._pb_fps, 60.0)   # ekran için max 60 FPS
        interval = 1.0 / max(fps, 1)
        while self._pb_playing and self._pb_idx < len(frames):
            t0 = time.time()
            idx = self._pb_idx
            self.root.after(0, self._pb_show_frame, idx)
            self.root.after(0, self.pb_slider.set, idx)
            self._pb_idx += 1
            rem = interval - (time.time() - t0)
            if rem > 0:
                time.sleep(rem)
        self._pb_playing = False
        self.root.after(0, self.pb_play_btn.configure, {"text": "▶"})

    def _pb_on_seek(self, val):
        """Slider ile frame'e atla."""
        if not hasattr(self, '_pb_frames') or not self._pb_frames:
            return
        idx = int(float(val))
        self._pb_idx = idx
        if not self._pb_playing:
            self._pb_show_frame(idx)

    def _pb_show_frame(self, idx):
        """Belirtilen frame'i canvas'ta göster."""
        frames = self._pb_frames
        if idx < 0 or idx >= len(frames):
            return
        frame = frames[idx]
        self.pb_lbl.configure(text=f"{idx + 1} / {len(frames)}")
        # latest_frame güncelle (tespit için)
        with self.frame_lock:
            self.latest_frame = frame.copy()
            self.latest_annotated = frame.copy()
        self._show_frame(frame)

    def _pb_close(self):
        """Oynatma modunu kapat."""
        self._pb_playing = False
        self._pb_frames = []
        self.playback_bar.pack_forget()

    # ── Videoyu dosyaya kaydet ────────────────────────────────────────────────

    def _save_recording(self):
        cam = self.camera
        frames = getattr(cam, '_rec_frames', []) if cam else []
        if not frames:
            messagebox.showwarning("Uyarı", "Bellekte kayıt yok.")
            return

        path = filedialog.asksaveasfilename(
            title="Videoyu Kaydet",
            defaultextension=".avi",
            filetypes=[("AVI", "*.avi"), ("MP4", "*.mp4")])
        if not path:
            return

        fps = cam.grab_fps if cam.grab_fps > 0 else 800.0
        count = cam.save_recording(path, fps)
        self._log(f"Video kaydedildi: {count} frame → {os.path.basename(path)}")

    # ── Ekran görüntüsü ──────────────────────────────────────────────────────

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

    # ── Sonuç dışa aktarma ───────────────────────────────────────────────────

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
