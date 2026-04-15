"""
ui/calibration_mixin.py — Kalibrasyon UI metodları (mixin)

Birleşik kalibrasyon: kullanıcı en az 5 nokta seçer, ardından her ardışık
nokta çifti arasındaki gerçek mesafeyi (mm) girer. Bu verilerden hem ölçek
(px/mm) hem kırılma düzeltmesi (polinom) hesaplanır.

Tıklamada zoom penceresi açılır — alt-piksel hassasiyetinde nokta seçimi.
"""

import os
import tkinter as tk
import threading

import numpy as np
import cv2
from PIL import Image, ImageTk
from tkinter import filedialog, messagebox, simpledialog

from ui.theme import DARK_BG, PANEL_BG, ACCENT, TEXT_LIGHT, FONT_LABEL

# Otomatik kalibrasyon dosyası — proje dizininde
_AUTO_CALIB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                "calibration_auto.json")


class CalibrationMixin:

    # ── Birleşik kalibrasyon ─────────────────────────────────────────────────

    def _start_combined_calib(self):
        """Ölçek + kırılma kalibrasyonunu başlat: en az 5 nokta seçilecek."""
        self._calib_mode  = "combined"
        self.calib_points = []
        self._log("KALİBRASYON: Görüntüde en az 5 referans noktasına tıklayın. "
                  "Sağ tık = geri al.")
        messagebox.showinfo(
            "Kalibrasyon",
            "Düşey eksen boyunca bilinen aralıklarla\n"
            "en az 5 referans noktasına tıklayın.\n\n"
            "Noktaları sırayla (yukarıdan aşağıya) seçin.\n"
            "Sağ tık ile son noktayı geri alabilirsiniz.")

    def _finish_combined_calib(self):
        """Seçilen noktalardan ölçek + kırılma hesapla."""
        pts = self.calib_points
        n = len(pts)

        # Her ardışık çift için gerçek mesafeyi sor
        real_dists = []
        for i in range(n - 1):
            p1, p2 = pts[i], pts[i + 1]
            px_dist = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
            ans = simpledialog.askfloat(
                f"Mesafe {i+1}→{i+2}",
                f"Nokta {i+1} → Nokta {i+2} arası\n"
                f"(piksel: {px_dist:.1f})\n\n"
                f"Gerçek mesafe (mm):",
                initialvalue=10.0)
            if ans is None or ans <= 0:
                messagebox.showwarning("İptal", "Kalibrasyon iptal edildi.")
                self._calib_mode  = "idle"
                self.calib_points = []
                return
            real_dists.append(ans)

        # ── Ölçek hesapla: tüm çiftlerin ortalaması ────────────────────────
        px_dists = []
        for i in range(n - 1):
            p1, p2 = pts[i], pts[i + 1]
            px_dists.append(np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2))

        scales = [pd / rd for pd, rd in zip(px_dists, real_dists)]
        avg_scale = float(np.mean(scales))
        self.calibrator.px_per_mm = avg_scale
        self.calibrator.scale_calibrated = True
        self.calibrator.calibration_info['px_per_mm'] = avg_scale

        self._log(f"Ölçek: {avg_scale:.3f} px/mm  ({1000/avg_scale:.2f} μm/px)")

        # ── Kırılma düzeltmesi: polinom fit ─────────────────────────────────
        # Kümülatif gerçek mesafeler (mm) → piksel y koordinatları
        cum_real = [0.0]
        for rd in real_dists:
            cum_real.append(cum_real[-1] + rd)

        # Görünen y koordinatları (piksel)
        apparent_y = np.array([p[1] for p in pts], dtype=np.float64)
        # Beklenen y (ölçekle çarpılmış gerçek kümülatif mesafeler + başlangıç ofseti)
        real_y_px = np.array(cum_real, dtype=np.float64) * avg_scale + apparent_y[0]

        if n >= 5:
            coeffs = np.polyfit(apparent_y, real_y_px, min(3, n - 2))
            self.calibrator.refraction_poly = coeffs
            self.calibrator.is_calibrated = True
            self.calibrator.calibration_info['refraction_method'] = 'polynomial_lut'
            self.calibrator.calibration_info['refraction_poly'] = coeffs.tolist()

            # Sapma bilgisi
            predicted = np.polyval(coeffs, apparent_y)
            max_err = float(np.max(np.abs(predicted - real_y_px)))
            self._log(f"Kırılma düzeltmesi: {n} nokta, maks hata {max_err:.1f} px")
        else:
            self._log("Kırılma düzeltmesi atlandı (5+ nokta gerekli)")

        self._calib_mode  = "idle"
        self.calib_points = []
        self._upd_calib()
        self._auto_save_calib()

    # ── Satranç tahtası ──────────────────────────────────────────────────────

    def _checkerboard_calib(self):
        paths = filedialog.askopenfilenames(
            title="Satranç Tahtası Görüntüleri (min 3)",
            filetypes=[("Görüntü", "*.jpg *.jpeg *.png *.bmp"), ("Tümü", "*.*")])
        if len(paths) < 3:
            messagebox.showwarning("Az Görüntü", "En az 3 görüntü seçin.")
            return
        bw = simpledialog.askinteger("Board", "İç köşe Yatay:", initialvalue=9)
        bh = simpledialog.askinteger("Board", "İç köşe Dikey:",  initialvalue=6)
        sq = simpledialog.askfloat("Board", "Kare boyutu (mm):", initialvalue=5.0)
        if not all([bw, bh, sq]):
            return
        imgs = [cv2.imread(p) for p in paths]
        imgs = [x for x in imgs if x is not None]
        self._log(f"Satranç tahtası kalibrasyonu ({len(imgs)} görüntü)…")

        def _do():
            ok, msg = self.calibrator.calibrate_from_checkerboard(imgs, (bw, bh), sq)
            self.root.after(0, self._log, f"Kalibrasyon: {msg}")
            self.root.after(0, self._upd_calib)
            if ok:
                self.root.after(0, self._auto_save_calib)

        threading.Thread(target=_do, daemon=True).start()

    # ── Kaydet / Yükle ───────────────────────────────────────────────────────

    def _save_calibration(self):
        p = filedialog.asksaveasfilename(title="Kalibrasyonu Kaydet",
                                          defaultextension=".json",
                                          filetypes=[("JSON", "*.json")])
        if p:
            self.calibrator.save(p)
            self._log(f"Kalibrasyon kaydedildi: {p}")

    def _load_calibration(self):
        p = filedialog.askopenfilename(title="Kalibrasyon Yükle",
                                        filetypes=[("JSON", "*.json")])
        if p:
            if self.calibrator.load(p):
                self._log(f"Kalibrasyon yüklendi: {p}")
                self._upd_calib()
            else:
                messagebox.showerror("Hata", "Kalibrasyon dosyası okunamadı.")

    def _upd_calib(self):
        self.calib_lbl.configure(text=self.calibrator.get_status_text())

    def _auto_save_calib(self):
        """Kalibrasyonu otomatik dosyaya kaydet."""
        try:
            self.calibrator.save(_AUTO_CALIB_PATH)
            self._log(f"Kalibrasyon otomatik kaydedildi.")
        except Exception:
            pass

    def _auto_load_calib(self):
        """Uygulama açılışında son kalibrasyonu yükle."""
        if os.path.exists(_AUTO_CALIB_PATH):
            if self.calibrator.load(_AUTO_CALIB_PATH):
                self._log("Son kalibrasyon yüklendi.")
                self._upd_calib()

    # ── Canvas tıklama ────────────────────────────────────────────────────────

    def _cv2fr(self, cx, cy):
        """Canvas piksel koordinatını orijinal frame koordinatına çevir."""
        if not hasattr(self.canvas, '_sc'):
            return cx, cy
        sc = self.canvas._sc
        ox, oy = self.canvas._of
        return int((cx - ox) / sc), int((cy - oy) / sc)

    def _on_click(self, ev):
        fx, fy = self._cv2fr(ev.x, ev.y)
        m = self._calib_mode

        if m == "combined":
            # Zoom penceresi aç — hassas nokta seçimi
            self._open_zoom(fx, fy)

    def _on_rclick(self, ev):
        if self.calib_points:
            removed = self.calib_points.pop()
            self._log(f"Geri alındı: {removed}")

    # ── Zoom penceresi ───────────────────────────────────────────────────────

    _ZOOM_CROP = 60     # orijinal frame'den ±60 piksel kırp
    _ZOOM_SCALE = 6     # 6× büyütme

    def _open_zoom(self, cx, cy):
        """Tıklanan noktanın etrafında zoom penceresi aç.
        Kullanıcı zoom görüntüsünde tıklayarak hassas konum seçer."""
        with self.frame_lock:
            src = self.latest_frame
        if src is None:
            # Frame yoksa direkt kaydet
            self._confirm_calib_point(cx, cy)
            return

        h, w = src.shape[:2]
        r = self._ZOOM_CROP
        # Kırpma sınırları
        x1 = max(0, cx - r)
        y1 = max(0, cy - r)
        x2 = min(w, cx + r)
        y2 = min(h, cy + r)
        crop = src[y1:y2, x1:x2].copy()

        if crop.size == 0:
            self._confirm_calib_point(cx, cy)
            return

        sc = self._ZOOM_SCALE
        zoomed = cv2.resize(crop, (crop.shape[1] * sc, crop.shape[0] * sc),
                            interpolation=cv2.INTER_NEAREST)

        # Çapraz nişangah çiz (merkez)
        zh, zw = zoomed.shape[:2]
        center_zx = (cx - x1) * sc + sc // 2
        center_zy = (cy - y1) * sc + sc // 2
        cv2.line(zoomed, (center_zx - 20, center_zy), (center_zx + 20, center_zy),
                 (0, 255, 255), 1)
        cv2.line(zoomed, (center_zx, center_zy - 20), (center_zx, center_zy + 20),
                 (0, 255, 255), 1)

        # Toplevel pencere
        top = tk.Toplevel(self.root)
        top.title(f"Zoom — Nokta {len(self.calib_points) + 1}")
        top.configure(bg=DARK_BG)
        top.attributes("-topmost", True)
        top.resizable(False, False)

        tk.Label(top, text="Tıklayarak noktayı seçin  |  ESC = iptal",
                 bg=DARK_BG, fg=TEXT_LIGHT, font=FONT_LABEL).pack(pady=4)

        rgb = cv2.cvtColor(zoomed, cv2.COLOR_BGR2RGB)
        ph = ImageTk.PhotoImage(Image.fromarray(rgb))

        zcanvas = tk.Canvas(top, width=zw, height=zh, bg="#000",
                            cursor="crosshair")
        zcanvas.pack(padx=8, pady=(0, 8))
        zcanvas.create_image(0, 0, anchor="nw", image=ph)
        zcanvas._ph = ph

        def _on_zoom_click(ev):
            # Zoom pikselini orijinal frame pikseline çevir
            orig_x = x1 + ev.x / sc
            orig_y = y1 + ev.y / sc
            orig_x = int(round(orig_x))
            orig_y = int(round(orig_y))
            top.destroy()
            self._confirm_calib_point(orig_x, orig_y)

        def _on_escape(ev):
            top.destroy()

        zcanvas.bind("<Button-1>", _on_zoom_click)
        top.bind("<Escape>", _on_escape)
        top.focus_force()

    def _confirm_calib_point(self, fx, fy):
        """Kalibrasyon noktasını onayla ve kaydet."""
        self.calib_points.append((fx, fy))
        n = len(self.calib_points)
        self._log(f"Kalibrasyon noktası {n}: ({fx}, {fy})")
        if n >= 5:
            if messagebox.askyesno(
                    "Tamamla",
                    f"{n} nokta seçildi.\n"
                    f"Kalibrasyonu tamamlamak istiyor musunuz?\n\n"
                    f"Daha fazla nokta eklemek için 'Hayır'a basın."):
                self._finish_combined_calib()
