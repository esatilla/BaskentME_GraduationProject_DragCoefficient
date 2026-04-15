"""
ui/source_mixin.py — Kamera / video kaynağı yönetimi (mixin)
"""

import os
import threading
import time

from tkinter import filedialog, messagebox

from camera_interface import BaslerCamera, VideoFileSource
from ui.theme import SUCCESS, HIGHLIGHT


class SourceMixin:

    # ── Durdur ───────────────────────────────────────────────────────────────

    def _signal_stop(self):
        """Mevcut döngüye dur sinyali gönder; join() ÇAĞIRMA."""
        self.stop_event.set()

    # ── Canlı kamera toggle ──────────────────────────────────────────────────

    def _toggle_camera(self):
        """Kamera başlat / durdur toggle."""
        if self.camera is not None and self.camera.is_open:
            self._stop_live()
        else:
            self._start_live()

    def _start_live(self):
        """Kamera başlatmayı arka plan thread'inde yap — UI donmaz."""
        self.cam_btn.configure(state="disabled", text="⏳  Bağlanıyor…")
        self._signal_stop()

        # Eski kamerayı kapat (yeniden başlatma durumu)
        old_cam = self.camera
        self.camera = None
        if old_cam is not None:
            try:
                old_cam.close()
            except Exception:
                pass

        def _open_camera():
            time.sleep(0.3)
            try:
                cam = BaslerCamera()
                success, msg = cam.open()
            except Exception as e:
                success, msg, cam = False, str(e), None

            if not success:
                def _show_err():
                    messagebox.showerror("Kamera Hatası", msg)
                    self.cam_btn.configure(state="normal",
                                           text="🔌  Kamerayı Başlat",
                                           bg=SUCCESS)
                self.root.after(0, _show_err)
                return

            self.camera = cam

            # Grab başlamadan önce deney modunu uygula (background thread — UI donmaz)
            if isinstance(cam, BaslerCamera):
                roi_h = self.cam_roi_height.get()
                exp_msgs = cam.configure_experiment_mode(roi_height=roi_h)
                for m in exp_msgs:
                    self.root.after(0, self._log, f"Deney modu: {m}")
                # Grab callback: her frame'de tespit
                cam.set_frame_callback(self._on_grab_frame)

            cam.start_capture()
            self.root.after(0, self._log, msg)
            self.root.after(0, self._on_camera_ready)

        threading.Thread(target=_open_camera, daemon=True).start()

    def _on_camera_ready(self):
        """Kamera hazır → döngüyü başlat (ANA THREAD)."""
        self.cam_btn.configure(state="normal",
                               text="⏹  Kamerayı Durdur", bg=HIGHLIGHT)
        self.stop_event.clear()
        self._launch_loop('camera')

    def _stop_live(self):
        """Kamerayı durdur ve kapat."""
        self._signal_stop()
        cam = self.camera
        self.camera = None
        if cam is not None:
            try:
                cam.close()
            except Exception:
                pass
        self.cam_btn.configure(state="normal",
                               text="🔌  Kamerayı Başlat", bg=SUCCESS)
        self._log("Kamera durduruldu.")

    # ── Canlı ROI değiştirme ─────────────────────────────────────────────────

    def _apply_roi_height(self, h_val):
        """Kamera açıkken ROI yüksekliğini değiştir — grab durdur/ayarla/başlat."""
        self.cam_roi_height.set(h_val)
        cam = self.camera
        if cam is None or not cam.is_open:
            self._log(f"ROI → {h_val} (kamera başlayınca uygulanacak)")
            return

        def _do():
            # Grab durdur
            cam._running = False
            try:
                if cam.camera.IsGrabbing():
                    cam.camera.StopGrabbing()
            except Exception:
                pass
            time.sleep(0.15)
            # ROI ayarla
            try:
                cam.camera.OffsetX.SetValue(0)
                cam.camera.OffsetY.SetValue(0)
                h = (int(h_val) // 2) * 2
                h = max(2, min(h, cam.camera.Height.GetMax()))
                cam.camera.Width.SetValue(1440)
                cam.camera.Height.SetValue(h)
                sensor_h = cam.camera.SensorHeight.GetValue()
                oy = ((sensor_h - h) // 2 // 2) * 2
                cam.camera.OffsetY.SetValue(oy)
                self.root.after(0, self._log,
                                f"ROI → 1440x{h} @(0,{oy})")
            except Exception as e:
                self.root.after(0, self._log, f"ROI hatası: {e}")
            # FPS yeniden ayarla (ROI değişince max FPS değişir)
            try:
                fps_max = cam.camera.AcquisitionFrameRate.GetMax()
                target = min(800.0, fps_max)
                cam.camera.AcquisitionFrameRate.SetValue(target)
                self.root.after(0, self._log,
                                f"FPS → {target:.0f}")
            except Exception:
                pass
            # Grab yeniden başlat
            pylon = cam._pylon
            for strategy in [pylon.GrabStrategy_LatestImageOnly,
                             pylon.GrabStrategy_OneByOne]:
                try:
                    cam.camera.StartGrabbing(strategy)
                    break
                except Exception:
                    continue
            cam._running = True
            cam._thread = threading.Thread(target=cam._grab_loop, daemon=True)
            cam._thread.start()

        threading.Thread(target=_do, daemon=True).start()

    # ── Video dosyası ─────────────────────────────────────────────────────────

    def _select_video(self):
        path = filedialog.askopenfilename(
            title="Video Dosyası Seç",
            filetypes=[("Video", "*.mp4 *.avi *.mov *.mkv *.mts"), ("Tümü", "*.*")])
        if not path:
            return
        self._signal_stop()

        def _open():
            time.sleep(0.2)
            vs = VideoFileSource()
            ok, msg = vs.open(path)
            if ok:
                self.video_source = vs
                fn = os.path.basename(path)
                self.root.after(0, self.video_path_var.set,
                                fn[:35] + "…" if len(fn) > 35 else fn)
                self.root.after(0, self._log, msg)
                self.root.after(0, self._on_video_ready)
            else:
                self.root.after(0, self._log, f"Video hatası: {msg}")
                self.root.after(0, messagebox.showerror, "Video Hatası", msg)

        threading.Thread(target=_open, daemon=True).start()

    def _on_video_ready(self):
        self.stop_event.clear()
        self._launch_loop('video')

    def _toggle_play(self):
        if self.video_source:
            if self.video_source.paused:
                self.video_source.resume()
                self.play_btn.configure(text="⏸ Duraklat")
            else:
                self.video_source.pause()
                self.play_btn.configure(text="▶ Oynat")

    def _reset_video(self):
        if self.video_source:
            self.video_source.seek(0)
            self.video_source.resume()
            self.play_btn.configure(text="⏸ Duraklat")
            self._reset_tracking()

    # ── Kamera ayarları ───────────────────────────────────────────────────────

    def _set_exposure(self, us):
        if self.camera and hasattr(self.camera, 'set_exposure'):
            try:
                self.camera.set_exposure(us)
            except Exception:
                pass

    def _set_fps(self, fps):
        if self.camera and hasattr(self.camera, 'set_fps'):
            try:
                self.camera.set_fps(fps)
            except Exception:
                pass
