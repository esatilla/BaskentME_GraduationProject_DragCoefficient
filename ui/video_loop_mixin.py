"""
ui/video_loop_mixin.py — Arka plan video döngüsü ve görüntü gösterimi (mixin)
"""

import threading
import time

import cv2
import numpy as np
from PIL import Image, ImageTk

from physics import calculate_segment_velocities
from ui.theme import SUCCESS, TEXT_DIM


class VideoLoopMixin:

    # ── Döngü yönetimi ───────────────────────────────────────────────────────

    def _signal_stop(self):
        """Mevcut döngüye dur sinyali gönder; join() ÇAĞIRMA."""
        self.stop_event.set()

    def _launch_loop(self, source):
        self._loop_id += 1
        my_id = self._loop_id
        threading.Thread(target=self._video_loop,
                          args=(source, my_id), daemon=True).start()

    # ── Ana döngü (BACKGROUND THREAD) ───────────────────────────────────────

    def _video_loop(self, source, my_id):
        """
        stop_event veya loop_id değişince durur.

        Kamera modunda: tespit grab callback'te 800 FPS hızında yapılır,
        bu döngü sadece son frame'i ekrana ~30 FPS gösterir.
        Video modunda: eski davranış (her frame tespit + gösterim).
        """
        display_fps  = 0.0

        while not self.stop_event.is_set() and self._loop_id == my_id:
            t0 = time.time()

            if source == 'camera':
                cam = self.camera
                if cam is None:
                    time.sleep(0.02); continue

                # Ekran kuyruğundan son frame'i al
                try:
                    frame, ts = cam._queue.get(timeout=0.15)
                except Exception:
                    continue

                frame = self._preprocess(frame)

                # Son tespit sonucunu al (grab callback tarafından güncellenir)
                pos = self._last_det_pos
                cnt = self._last_det_cnt
                display_fps = cam.grab_fps

                self._display_frame(frame, pos, cnt, display_fps, source)
                self.root.after(0, self._upd_bar, display_fps,
                                self.detector.frame_count)

                # Ekran hızını sınırla (~30 FPS)
                elapsed = time.time() - t0
                rem = (1.0 / 30.0) - elapsed
                if rem > 0:
                    time.sleep(rem)

            else:
                # ── Video dosyası modu ──────────────────────────────────────
                vs = self.video_source
                if vs is None:
                    time.sleep(0.02); continue
                if vs.paused:
                    time.sleep(0.05); continue
                try:
                    ok, raw_frame, ts = vs.read()
                except Exception as e:
                    self.root.after(0, self._log, f"Okuma hatası: {e}")
                    time.sleep(0.1); continue
                if not ok or raw_frame is None:
                    self.root.after(0, self._log, "Video sona erdi.")
                    break

                frame = self._preprocess(raw_frame)

                pos, cnt = None, None
                try:
                    pos, cnt = self.detector.detect(frame, ts)
                except Exception as e:
                    self.root.after(0, self._log, f"Tespit hatası: {e}")

                display_fps = vs.fps or 30
                self._display_frame(frame, pos, cnt, display_fps, source)

                fc = self.detector.frame_count
                self.root.after(0, self._upd_bar, display_fps, fc)
                try:
                    p  = int(vs.progress * 100)
                    tt = vs.current_time_s
                    self.root.after(0, self.vid_status.set,
                                    f"{p}%  |  {tt:.1f}s")
                except Exception:
                    pass

                # Hız sınırlama (video)
                try:
                    target = 1.0 / max((vs.fps or 30), 1)
                    rem = target - (time.time() - t0)
                    if rem > 0:
                        time.sleep(rem)
                except Exception:
                    pass

        self.root.after(0, self._log, "Döngü durdu.")

    # ── Grab callback: her frame'de tespit (800 FPS, grab thread) ────────────

    def _on_grab_frame(self, raw_gray, ts):
        """BaslerCamera grab thread'inden çağrılır — HER frame için.
        raw_gray: BayerRG8 ham veri (tek kanal, cvtColor gereksiz).
        Döndürme yapılmaz, koordinatlar dönüştürülür. Morfoloji atlanır."""
        try:
            pos = self.detector.detect_fast(raw_gray, ts, self._rotation_transform)
            self._last_det_pos = pos
            self._last_det_cnt = None
        except Exception:
            pass

    @staticmethod
    def _rot90cw(cx, cy, h, w):
        """90° CW döndürme koordinat dönüşümü."""
        return h - 1 - cy, cx

    @staticmethod
    def _rot180(cx, cy, h, w):
        return w - 1 - cx, h - 1 - cy

    @staticmethod
    def _rot90ccw(cx, cy, h, w):
        return cy, w - 1 - cx

    @property
    def _rotation_transform(self):
        """Aktif döndürme koduna göre koordinat dönüşüm fonksiyonu."""
        try:
            rc = self.rotation_code.get()
        except Exception:
            return None
        if rc == 1:
            return self._rot90cw
        elif rc == 2:
            return self._rot180
        elif rc == 3:
            return self._rot90ccw
        return None

    # ── Yardımcı: frame ön işleme ───────────────────────────────────────────

    def _preprocess(self, frame):
        """Kalibrasyon düzeltme + döndürme."""
        try:
            if self.calibrator.is_calibrated and self.calibrator.map1 is not None:
                frame = self.calibrator.undistort_frame(frame)
        except Exception:
            pass
        try:
            rc = self.rotation_code.get()
            if rc == 1:
                frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
            elif rc == 2:
                frame = cv2.rotate(frame, cv2.ROTATE_180)
            elif rc == 3:
                frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        except Exception:
            pass
        return frame

    # ── Yardımcı: görüntü göster + overlay ──────────────────────────────────

    def _display_frame(self, frame, pos, cnt, display_fps, source):
        """Overlay çiz, kayıt yap, ekrana gönder."""
        annotated = frame.copy()

        v_lbl = None
        if pos is not None:
            try:
                if self.detector.is_active and len(self.detector.positions) > 1:
                    segs = calculate_segment_velocities(
                        self.detector.positions,
                        self.detector.timestamps,
                        self.calibrator.px_per_mm)
                    if segs:
                        last_v = segs[-1]['v_mm_s']
                        v_lbl  = f"{last_v:.1f} mm/s"
                        dists  = [s['cum_dist_mm'] / 10.0 for s in segs]
                        vels   = [s['v_mm_s'] for s in segs]
                        self.root.after(0, self._upd_speed, last_v)
                        self.root.after(0, self._draw_vel, dists, vels)
                annotated = self.detector.draw_overlay(annotated, pos, cnt, v_lbl)
            except Exception:
                pass

        # Kalibrasyon modu işaretleri
        try:
            cm  = self._calib_mode
            pts = list(self.calib_points)
            if cm == "combined" and pts:
                for i, pt in enumerate(pts):
                    cv2.circle(annotated, pt, 5, (0, 255, 255), -1)
                    cv2.putText(annotated, str(i + 1),
                                (pt[0] + 8, pt[1] - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                if len(pts) >= 2:
                    for i in range(len(pts) - 1):
                        cv2.line(annotated, pts[i], pts[i + 1], (0, 255, 255), 1)
                cv2.putText(annotated, f"Nokta: {len(pts)} (min 5)",
                            (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        except Exception:
            pass

        # Bilgi metni
        try:
            h, w = annotated.shape[:2]
            cv2.putText(annotated, f"FPS:{display_fps:.0f}  {w}x{h}",
                        (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (70, 70, 70), 1)
        except Exception:
            pass

        # Kayıt
        try:
            if self.is_recording and self.record_writer:
                self.record_writer.write(annotated)
        except Exception:
            pass

        # Frame paylaş
        try:
            ann_c = annotated.copy()
            frm_c = frame.copy()
            with self.frame_lock:
                self.latest_frame     = frm_c
                self.latest_annotated = ann_c
            self.root.after(0, self._show_frame, ann_c)
        except Exception:
            pass

    # ── Görüntü gösterimi (ANA THREAD) ───────────────────────────────────────

    def _show_frame(self, frame):
        try:
            cw = self.canvas.winfo_width()
            ch = self.canvas.winfo_height()
            if cw < 10 or ch < 10:
                return
            h, w = frame.shape[:2]
            sc = min(cw / w, ch / h)
            nw, nh = int(w * sc), int(h * sc)
            res = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LINEAR)
            rgb = cv2.cvtColor(res, cv2.COLOR_BGR2RGB)
            ph  = ImageTk.PhotoImage(Image.fromarray(rgb))
            xo  = (cw - nw) // 2
            yo  = (ch - nh) // 2
            self.canvas.delete("all")
            self.canvas.create_image(xo, yo, anchor="nw", image=ph)
            self.canvas._ph = ph          # GC koruması
            self.canvas._sc = sc
            self.canvas._of = (xo, yo)
            self.canvas._fs = (w, h)
        except Exception:
            pass

    def _upd_bar(self, fps, fc):
        try:
            self.fps_lbl.configure(text=f"FPS: {fps:.1f}")
            self.frame_lbl.configure(text=f"Kare: {fc}")
        except Exception:
            pass

    def _upd_speed(self, v):
        try:
            self.speed_var.set(f"{v:.1f} mm/s")
        except Exception:
            pass

    # ── Thread-safe log ──────────────────────────────────────────────────────

    def _log(self, message):
        def _write():
            import time as _t
            ts = _t.strftime("%H:%M:%S")
            self.log_text.configure(state="normal")
            self.log_text.insert("end", f"[{ts}] {message}\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.root.after(0, _write)

    def _check_pypylon(self):
        try:
            import pypylon  # noqa: F401
            return "✓ pypylon bulundu – Basler kamera kullanılabilir"
        except ImportError:
            return "✗ pypylon yok – Yalnızca video dosyası kullanılabilir"
