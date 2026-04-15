"""
ui/settings_mixin.py — Gelişmiş kamera ayarları penceresi (mixin)
ROI / FPS / Gain / White Balance — canlı önizleme ile doğrulama
"""

import tkinter as tk
from tkinter import ttk
import cv2
from PIL import Image, ImageTk

from ui.theme import (DARK_BG, PANEL_BG, ACCENT, HIGHLIGHT, TEXT_LIGHT,
                      TEXT_DIM, SUCCESS, WARNING, FONT_MONO, FONT_LABEL,
                      FONT_HEAD, FONT_TITLE)

# Sol panel içindeki scale widget genişliği
_SCALE_LEN = 160


class SettingsMixin:

    # ── Teorik FPS tahmini ────────────────────────────────────────────────────
    _BASE_FPS = 227.7        # ölçülen: 1440×1080 @ 1ms
    _FULL_H   = 1080
    _USB3_BW  = 400_000_000  # byte/s efektif

    def _est_fps(self, w, h, exposure_us=None):
        if h <= 0:
            return 0.0
        readout   = self._BASE_FPS * self._FULL_H / h
        usb3      = self._USB3_BW / max(w * h, 1)
        practical = min(readout, usb3)
        if exposure_us and exposure_us > 0:
            practical = min(practical, 1_000_000 / exposure_us)
        return practical

    # ── Ana pencere ───────────────────────────────────────────────────────────

    def _open_settings(self):
        if hasattr(self, '_settings_win') and self._settings_win.winfo_exists():
            self._settings_win.lift()
            return

        from camera_interface import BaslerCamera
        cam       = self.camera
        is_basler = isinstance(cam, BaslerCamera) and cam.is_open

        win = tk.Toplevel(self.root)
        win.title("Kamera Ayarları — acA1440-220uc")
        win.configure(bg=DARK_BG)
        win.geometry("1060x680")
        win.resizable(True, True)
        self._settings_win    = win
        self._settings_preview_id = None

        # ── Başlık ────────────────────────────────────────────────────────────
        hdr = tk.Frame(win, bg=ACCENT, height=40)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⚙  Gelişmiş Kamera Ayarları",
                 font=FONT_TITLE, bg=ACCENT, fg=TEXT_LIGHT
                 ).pack(side="left", padx=14, pady=6)
        tk.Label(hdr,
                 text="✓ Basler bağlı" if is_basler else "⚠  Basler bağlı değil",
                 font=FONT_LABEL, bg=ACCENT,
                 fg=SUCCESS if is_basler else WARNING
                 ).pack(side="right", padx=14)

        # ── Alt çubuk (body'den ÖNCE pack edilmeli) ───────────────────────────
        footer = tk.Frame(win, bg=ACCENT, height=36)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        tk.Button(footer, text="Kapat", font=FONT_LABEL,
                  bg=HIGHLIGHT, fg="white", relief="flat",
                  command=lambda: self._close_settings(win)
                  ).pack(side="right", padx=10, pady=4)
        tk.Button(footer, text="↺  Yenile", font=FONT_LABEL,
                  bg=ACCENT, fg=TEXT_LIGHT, relief="flat",
                  command=lambda: self._refresh_si(cam)
                  ).pack(side="right", padx=4, pady=4)

        # ── Gövde ─────────────────────────────────────────────────────────────
        body = tk.Frame(win, bg=DARK_BG)
        body.pack(fill="both", expand=True, padx=6, pady=4)

        # Sol: kaydırılabilir ayarlar paneli
        left_outer = tk.Frame(body, bg=PANEL_BG, width=480)
        left_outer.pack(side="left", fill="y", padx=(0, 4))
        left_outer.pack_propagate(False)

        cv_s = tk.Canvas(left_outer, bg=PANEL_BG, highlightthickness=0)
        sb_s = ttk.Scrollbar(left_outer, orient="vertical", command=cv_s.yview)
        sf   = tk.Frame(cv_s, bg=PANEL_BG)

        # İç frame genişliğini canvas genişliğine kilitle (kırpılma önlemi)
        def _on_canvas_resize(e):
            cv_s.itemconfig(_win_id, width=e.width)
        _win_id = cv_s.create_window((0, 0), window=sf, anchor="nw")
        cv_s.bind("<Configure>", _on_canvas_resize)
        sf.bind("<Configure>", lambda e: cv_s.configure(
            scrollregion=cv_s.bbox("all")))
        cv_s.configure(yscrollcommand=sb_s.set)
        sb_s.pack(side="right", fill="y")
        cv_s.pack(side="left", fill="both", expand=True)

        # Mouse tekerleği ile kaydırma
        def _on_mousewheel(e):
            cv_s.yview_scroll(int(-1 * (e.delta / 120)), "units")
        sf.bind_all("<MouseWheel>", _on_mousewheel)
        win.bind("<Destroy>", lambda e: sf.unbind_all("<MouseWheel>"))

        # Sağ: canlı önizleme
        right = tk.Frame(body, bg=PANEL_BG)
        right.pack(side="right", fill="both", expand=True)

        self._settings_sec(right, "📷 CANLI ÖNİZLEME")
        preview_canvas = tk.Canvas(right, bg="#0a0a0a")
        preview_canvas.pack(fill="both", expand=True, padx=6, pady=4)

        info_frame = tk.Frame(right, bg=PANEL_BG)
        info_frame.pack(fill="x", padx=6, pady=(0, 6))

        self._si_fps  = tk.StringVar(value="Sonuç FPS : --")
        self._si_fmt  = tk.StringVar(value="Format    : --")
        self._si_roi  = tk.StringVar(value="ROI       : --")
        self._si_gain = tk.StringVar(value="Gain      : --")
        self._si_wb   = tk.StringVar(value="WB        : --")
        self._si_temp = tk.StringVar(value="Sıcaklık  : --")
        for var, fg in [(self._si_fps, SUCCESS), (self._si_fmt, WARNING),
                        (self._si_roi, TEXT_LIGHT),
                        (self._si_gain, TEXT_LIGHT), (self._si_wb, TEXT_LIGHT),
                        (self._si_temp, TEXT_DIM)]:
            tk.Label(info_frame, textvariable=var, bg=PANEL_BG, fg=fg,
                     font=FONT_MONO, anchor="w").pack(fill="x")

        # ── Ayar bölümleri (kaydırılabilir sol panele) ────────────────────────
        for title, builder in [
            ("⚡ HIZLI PRESETLER",    lambda: self._build_quick_presets_section(sf, cam, is_basler)),
            ("🔄 GÖRÜNTÜ DÖNDÜRME",  lambda: self._build_rotation_section(sf)),
            ("📐 ROI",                lambda: self._build_roi_section(sf, cam, is_basler)),
            ("⏱ FPS",                lambda: self._build_fps_section(sf, cam, is_basler)),
            ("📶 GAIN  (0 – 36 dB)", lambda: self._build_gain_section(sf, cam, is_basler)),
            ("🎨 WHITE BALANCE",     lambda: self._build_wb_section(sf, cam, is_basler)),
        ]:
            self._settings_sec(sf, title)
            try:
                builder()
            except Exception as _e:
                tk.Label(sf, text=f"⚠ Bölüm yüklenemedi: {_e}",
                         bg=PANEL_BG, fg=WARNING,
                         font=FONT_MONO, wraplength=420
                         ).pack(padx=8, anchor="w", pady=4)

        # ── Başlangıç + döngü ─────────────────────────────────────────────────
        if is_basler:
            self._refresh_si(cam)
        self._settings_preview_loop(win, preview_canvas, cam)
        win.protocol("WM_DELETE_WINDOW", lambda: self._close_settings(win))

    # ── ROI ───────────────────────────────────────────────────────────────────

    def _build_roi_section(self, parent, cam, is_basler):
        if is_basler:
            ox, oy, w, h = cam.get_roi()
            w_max  = cam.camera.Width.GetMax()
            h_max  = cam.camera.Height.GetMax()
            ox_max = cam.camera.OffsetX.GetMax()
            oy_max = cam.camera.OffsetY.GetMax()
            try:    exp_us = cam.camera.ExposureTime.GetValue()
            except: exp_us = 1000.0
        else:
            ox, oy, w, h = 0, 0, 1440, 1080
            w_max, h_max, ox_max, oy_max = 1448, 1084, 16, 8
            exp_us = 1000.0

        v_ox = tk.IntVar(value=ox)
        v_oy = tk.IntVar(value=oy)
        v_w  = tk.IntVar(value=w)
        v_h  = tk.IntVar(value=h)

        tk.Label(parent,
                 text=f"Sensör: 1456×1088 px  |  Max aktif: {w_max}×{h_max}",
                 bg=PANEL_BG, fg=TEXT_DIM, font=FONT_MONO
                 ).pack(padx=8, anchor="w")

        # Anlık FPS tahmini
        est_var = tk.StringVar(
            value=f"Tahmini Max FPS: {self._est_fps(w, h, exp_us):.0f}")
        est_lbl = tk.Label(parent, textvariable=est_var,
                           bg=PANEL_BG, fg=WARNING, font=FONT_MONO)
        est_lbl.pack(padx=8, anchor="w", pady=(0, 2))

        def _update_est(*_):
            try:
                fps   = self._est_fps(v_w.get(), v_h.get(), exp_us)
                color = SUCCESS if fps > 400 else (WARNING if fps > 200 else TEXT_DIM)
                est_var.set(f"Tahmini Max FPS: {fps:.0f}")
                est_lbl.configure(fg=color)
            except Exception:
                pass

        v_w.trace_add("write", _update_est)
        v_h.trace_add("write", _update_est)

        for lbl, var, mn, mx, inc in [
            ("OffsetX (px):",   v_ox, 0,   ox_max, 4),
            ("OffsetY (px):",   v_oy, 0,   oy_max, 2),
            ("Genişlik (px):",  v_w,  4,   w_max,  4),
            ("Yükseklik (px):", v_h,  2,   h_max,  2),
        ]:
            row = tk.Frame(parent, bg=PANEL_BG)
            row.pack(fill="x", padx=8, pady=1)
            tk.Label(row, text=lbl, width=15, anchor="w",
                     bg=PANEL_BG, fg=TEXT_DIM, font=FONT_LABEL).pack(side="left")
            tk.Spinbox(row, textvariable=var, from_=mn, to=mx, increment=inc,
                       width=7, bg="#0d0d1a", fg=TEXT_LIGHT, font=FONT_MONO,
                       buttonbackground=ACCENT, relief="flat",
                       state="normal" if is_basler else "disabled"
                       ).pack(side="right")

        # Preset butonları
        tk.Label(parent, text="Hızlı presetler (kamera 90° → yükseklik = yatay):",
                 bg=PANEL_BG, fg=TEXT_DIM, font=FONT_MONO
                 ).pack(padx=8, anchor="w", pady=(6, 1))

        preset_row = tk.Frame(parent, bg=PANEL_BG)
        preset_row.pack(fill="x", padx=8, pady=2)

        def _set_preset(pox, poy, pw, ph):
            v_ox.set(pox); v_oy.set(poy)
            v_w.set(pw);   v_h.set(ph)

        for name, pox, poy, pw, ph in [
            ("Tam\n228 fps",      0,   0,   1440, 1080),
            ("÷2\n~455 fps",      0, 270,   1440,  540),
            ("÷4\n~911 fps",      0, 405,   1440,  270),
            ("×5\n~1000 fps",     0, 440,   1440,  200),
        ]:
            tk.Button(preset_row, text=name, font=("Segoe UI", 8),
                      bg=ACCENT, fg=TEXT_LIGHT, relief="flat",
                      justify="center", width=9,
                      command=lambda a=pox, b=poy, c=pw, d=ph: _set_preset(a, b, c, d),
                      state="normal" if is_basler else "disabled"
                      ).pack(side="left", padx=2, pady=1)

        # Uygula / Sıfırla
        btn_row = tk.Frame(parent, bg=PANEL_BG)
        btn_row.pack(fill="x", padx=8, pady=4)

        def _apply_roi():
            ok, msg = cam.set_roi(v_ox.get(), v_oy.get(), v_w.get(), v_h.get())
            self._log(msg)
            self._refresh_si(cam)

        def _reset_roi():
            cam.reset_roi()
            v_ox.set(0); v_oy.set(0)
            v_w.set(w_max); v_h.set(h_max)
            self._log("ROI sıfırlandı")
            self._refresh_si(cam)

        st = "normal" if is_basler else "disabled"
        tk.Button(btn_row, text="✓  Uygula", font=FONT_LABEL,
                  bg=SUCCESS, fg=DARK_BG, relief="flat",
                  command=_apply_roi, state=st).pack(side="left", padx=4)
        tk.Button(btn_row, text="⟲  Tam Sensör", font=FONT_LABEL,
                  bg=ACCENT, fg=TEXT_LIGHT, relief="flat",
                  command=_reset_roi, state=st).pack(side="left", padx=4)

    # ── FPS ───────────────────────────────────────────────────────────────────

    def _build_fps_section(self, parent, cam, is_basler):
        fps_en  = cam.camera.AcquisitionFrameRateEnable.GetValue() if is_basler else False
        fps_val = cam.camera.AcquisitionFrameRate.GetValue()        if is_basler else 100.0
        fps_max = min(cam.camera.AcquisitionFrameRate.GetMax(), 1000.0) if is_basler else 1000.0

        v_en  = tk.BooleanVar(value=fps_en)
        v_fps = tk.DoubleVar(value=fps_val)

        en_row = tk.Frame(parent, bg=PANEL_BG)
        en_row.pack(fill="x", padx=8, pady=2)

        def _on_enable():
            if not is_basler:
                return
            cam.camera.AcquisitionFrameRateEnable.SetValue(v_en.get())
            fps_sl.configure(state="normal" if v_en.get() else "disabled")
            self._refresh_si(cam)

        tk.Checkbutton(en_row, text="FPS Sınırlamasını Etkinleştir",
                       variable=v_en, command=_on_enable,
                       bg=PANEL_BG, fg=TEXT_LIGHT, selectcolor=ACCENT,
                       activebackground=PANEL_BG, font=FONT_LABEL,
                       state="normal" if is_basler else "disabled"
                       ).pack(side="left")

        tk.Label(en_row, text="(kapalı = max hız)",
                 bg=PANEL_BG, fg=TEXT_DIM, font=FONT_MONO).pack(side="left", padx=6)

        sl_row = tk.Frame(parent, bg=PANEL_BG)
        sl_row.pack(fill="x", padx=8, pady=2)
        tk.Label(sl_row, text="FPS:", width=8, anchor="w",
                 bg=PANEL_BG, fg=TEXT_DIM, font=FONT_LABEL).pack(side="left")
        fps_lbl = tk.Label(sl_row, text=f"{fps_val:.0f}", width=6,
                           bg=PANEL_BG, fg=SUCCESS, font=FONT_MONO)
        fps_lbl.pack(side="right")

        _deb = [None]

        def _on_fps(v):
            fps_lbl.configure(text=f"{float(v):.0f}")
            if _deb[0]:
                sl_row.after_cancel(_deb[0])
            def _apply():
                if is_basler:
                    cam.set_fps(v_fps.get())
                    self._refresh_si(cam)
            _deb[0] = sl_row.after(300, _apply)

        fps_sl = tk.Scale(sl_row, variable=v_fps,
                          from_=1, to=min(int(fps_max), 1000),
                          orient="horizontal", resolution=1,
                          bg=PANEL_BG, fg=TEXT_LIGHT, troughcolor=ACCENT,
                          highlightthickness=0, length=_SCALE_LEN,
                          command=_on_fps,
                          state="normal" if (is_basler and fps_en) else "disabled")
        fps_sl.pack(side="right", padx=4)

        # Preset'in FPS slider'ını güncelleyebilmesi için referans sakla
        self._sf_fps_var    = v_fps
        self._sf_fps_en_var = v_en
        self._sf_fps_lbl    = fps_lbl
        self._sf_fps_slider = fps_sl

    # ── Gain ──────────────────────────────────────────────────────────────────

    def _build_gain_section(self, parent, cam, is_basler):
        gain_auto = "Off"
        gain_val  = 0.0
        if is_basler:
            try: gain_auto = cam.camera.GainAuto.GetValue()
            except Exception: pass
            try: gain_val  = cam.camera.Gain.GetValue()
            except Exception: pass

        v_auto = tk.StringVar(value=gain_auto)
        v_gain = tk.DoubleVar(value=gain_val)

        auto_row = tk.Frame(parent, bg=PANEL_BG)
        auto_row.pack(fill="x", padx=8, pady=2)
        tk.Label(auto_row, text="Mod:", width=8, anchor="w",
                 bg=PANEL_BG, fg=TEXT_DIM, font=FONT_LABEL).pack(side="left")

        gain_sl_ref = [None]
        gain_lbl_ref = [None]

        def _poll_gain_once():
            """'Bir Kez' modu bitince slider'ı gerçek değere güncelle."""
            top = parent.winfo_toplevel()
            if not top.winfo_exists() or not is_basler:
                return
            try:
                if cam.camera.GainAuto.GetValue() == "Once":
                    top.after(250, _poll_gain_once)
                    return
                new_g = cam.camera.Gain.GetValue()
                v_gain.set(round(new_g, 1))
                if gain_lbl_ref[0]:
                    gain_lbl_ref[0].configure(text=f"{new_g:.1f}")
                v_auto.set("Off")
                if gain_sl_ref[0]:
                    gain_sl_ref[0].configure(state="normal")
                self._refresh_si(cam)
            except Exception:
                pass

        def _on_auto():
            if not is_basler:
                return
            mode = v_auto.get()
            cam.set_gain_auto(mode)
            if gain_sl_ref[0]:
                gain_sl_ref[0].configure(
                    state="normal" if mode == "Off" else "disabled")
            self._refresh_si(cam)
            if mode == "Once":
                top = parent.winfo_toplevel()
                top.after(250, _poll_gain_once)

        for txt, val in [("Manuel", "Off"), ("Bir Kez", "Once"), ("Sürekli", "Continuous")]:
            tk.Radiobutton(auto_row, text=txt, variable=v_auto, value=val,
                           command=_on_auto, bg=PANEL_BG, fg=TEXT_LIGHT,
                           selectcolor=ACCENT, activebackground=PANEL_BG,
                           font=FONT_LABEL,
                           state="normal" if is_basler else "disabled"
                           ).pack(side="left", padx=4)

        sl_row = tk.Frame(parent, bg=PANEL_BG)
        sl_row.pack(fill="x", padx=8, pady=2)
        tk.Label(sl_row, text="Gain (dB):", width=10, anchor="w",
                 bg=PANEL_BG, fg=TEXT_DIM, font=FONT_LABEL).pack(side="left")
        gain_lbl = tk.Label(sl_row, text=f"{gain_val:.1f}", width=6,
                            bg=PANEL_BG, fg=SUCCESS, font=FONT_MONO)
        gain_lbl.pack(side="right")
        gain_lbl_ref[0] = gain_lbl

        _deb = [None]

        def _on_gain(v):
            gain_lbl.configure(text=f"{float(v):.1f}")
            if _deb[0]:
                sl_row.after_cancel(_deb[0])
            def _apply():
                if is_basler:
                    cam.set_gain(v_gain.get())
                    self._refresh_si(cam)
            _deb[0] = sl_row.after(300, _apply)

        sl_state = "normal" if (is_basler and gain_auto == "Off") else "disabled"
        gain_sl = tk.Scale(sl_row, variable=v_gain,
                           from_=0, to=36, orient="horizontal", resolution=0.5,
                           bg=PANEL_BG, fg=TEXT_LIGHT, troughcolor=ACCENT,
                           highlightthickness=0, length=_SCALE_LEN,
                           command=_on_gain, state=sl_state)
        gain_sl.pack(side="right", padx=4)
        gain_sl_ref[0] = gain_sl

    # ── White Balance ─────────────────────────────────────────────────────────

    def _build_wb_section(self, parent, cam, is_basler):
        wb_auto = "Continuous"
        wb_r, wb_g, wb_b = 1.0, 1.067, 7.576
        if is_basler:
            try: wb_auto = cam.camera.BalanceWhiteAuto.GetValue()
            except Exception: pass
            try:
                cam.camera.BalanceRatioSelector.SetValue("Red")
                wb_r = cam.camera.BalanceRatio.GetValue()
                cam.camera.BalanceRatioSelector.SetValue("Green")
                wb_g = cam.camera.BalanceRatio.GetValue()
                cam.camera.BalanceRatioSelector.SetValue("Blue")
                wb_b = cam.camera.BalanceRatio.GetValue()
            except Exception: pass

        v_auto = tk.StringVar(value=wb_auto)
        v_r    = tk.DoubleVar(value=wb_r)
        v_g    = tk.DoubleVar(value=wb_g)
        v_b    = tk.DoubleVar(value=wb_b)

        auto_row = tk.Frame(parent, bg=PANEL_BG)
        auto_row.pack(fill="x", padx=8, pady=2)
        tk.Label(auto_row, text="Mod:", width=8, anchor="w",
                 bg=PANEL_BG, fg=TEXT_DIM, font=FONT_LABEL).pack(side="left")

        ch_sliders = []   # slider widget'ları
        ch_labels  = []   # (DoubleVar, Label) çiftleri — polling için

        def _apply_wb_values(new_r, new_g, new_b):
            """Slider değişkenlerini ve etiketleri güncelle (polling sonrası)."""
            v_r.set(round(new_r, 3))
            v_g.set(round(new_g, 3))
            v_b.set(round(new_b, 3))
            for (vv, lbl), val in zip(ch_labels, [new_r, new_g, new_b]):
                lbl.configure(text=f"{val:.3f}")

        def _poll_wb_once():
            """'Bir Kez' modu bitince slider'ları gerçek değere güncelle."""
            top = parent.winfo_toplevel()
            if not top.winfo_exists() or not is_basler:
                return
            try:
                if cam.camera.BalanceWhiteAuto.GetValue() == "Once":
                    top.after(250, _poll_wb_once)   # Henüz bitmedi, tekrar bak
                    return
                # Otomatik ayar tamamlandı — yeni değerleri oku
                cam.camera.BalanceRatioSelector.SetValue("Red")
                new_r = cam.camera.BalanceRatio.GetValue()
                cam.camera.BalanceRatioSelector.SetValue("Green")
                new_g = cam.camera.BalanceRatio.GetValue()
                cam.camera.BalanceRatioSelector.SetValue("Blue")
                new_b = cam.camera.BalanceRatio.GetValue()
                _apply_wb_values(new_r, new_g, new_b)
                v_auto.set("Off")               # Radyo düğmesini Manuel'e al
                for sl in ch_sliders:
                    sl.configure(state="normal")
                self._refresh_si(cam)
            except Exception:
                pass

        def _on_auto():
            if not is_basler:
                return
            mode = v_auto.get()
            cam.set_wb_auto(mode)
            # Slider durumunu moda göre ayarla
            # Sürekli: kilitle (sliderlar hareket etmez, değerleri bekleme)
            # Bir Kez:  kilitle, tamamlanınca aç ve güncelle
            # Manuel:   aç
            st = "normal" if mode == "Off" else "disabled"
            for sl in ch_sliders:
                sl.configure(state=st)
            self._refresh_si(cam)
            if mode == "Once":
                top = parent.winfo_toplevel()
                top.after(250, _poll_wb_once)   # Tamamlanmayı bekle

        for txt, val in [("Manuel", "Off"), ("Bir Kez", "Once"), ("Sürekli", "Continuous")]:
            tk.Radiobutton(auto_row, text=txt, variable=v_auto, value=val,
                           command=_on_auto, bg=PANEL_BG, fg=TEXT_LIGHT,
                           selectcolor=ACCENT, activebackground=PANEL_BG,
                           font=FONT_LABEL,
                           state="normal" if is_basler else "disabled"
                           ).pack(side="left", padx=4)

        _deb = [None]

        def _on_ch(v=None):
            if _deb[0]:
                parent.after_cancel(_deb[0])
            def _apply():
                if is_basler:
                    cam.set_white_balance(v_r.get(), v_g.get(), v_b.get())
                    self._refresh_si(cam)
            _deb[0] = parent.after(300, _apply)

        sl_state = "normal" if (is_basler and wb_auto == "Off") else "disabled"

        for lbl_txt, var, init, fg_col in [
            ("Red:",   v_r, wb_r, "#ff6b6b"),
            ("Green:", v_g, wb_g, "#4ecca3"),
            ("Blue:",  v_b, wb_b, "#6baaff"),
        ]:
            row = tk.Frame(parent, bg=PANEL_BG)
            row.pack(fill="x", padx=8, pady=1)
            tk.Label(row, text=lbl_txt, width=8, anchor="w",
                     bg=PANEL_BG, fg=fg_col, font=FONT_LABEL).pack(side="left")
            val_lbl = tk.Label(row, text=f"{init:.3f}", width=6,
                               bg=PANEL_BG, fg=fg_col, font=FONT_MONO)
            val_lbl.pack(side="right")
            ch_labels.append((var, val_lbl))

            def _make_cmd(lbl_ref):
                def _cmd(v):
                    lbl_ref.configure(text=f"{float(v):.3f}")
                    _on_ch()
                return _cmd

            sl = tk.Scale(row, variable=var,
                          from_=0, to=16, orient="horizontal", resolution=0.01,
                          bg=PANEL_BG, fg=TEXT_LIGHT, troughcolor=ACCENT,
                          highlightthickness=0, length=_SCALE_LEN,
                          command=_make_cmd(val_lbl),
                          state=sl_state)
            sl.pack(side="right", padx=4)
            ch_sliders.append(sl)

        # Alt boşluk
        tk.Frame(parent, bg=PANEL_BG, height=10).pack()

    # ── Canlı önizleme döngüsü ────────────────────────────────────────────────

    def _settings_preview_loop(self, win, canvas, cam):
        tick = [0]

        def _tick():
            if not win.winfo_exists():
                return
            tick[0] += 1
            if tick[0] >= 7:   # ~1 sn'de bir bilgi yenile
                tick[0] = 0
                self._refresh_si(cam)
            try:
                with self.frame_lock:
                    frame = (self.latest_frame.copy()
                             if self.latest_frame is not None else None)

                if frame is not None:
                    # Hardware ROI bilgisini görüntü üzerinde metin olarak göster.
                    # latest_frame zaten hardware ROI + software rotation sonrası
                    # geldiğinden kamera koordinatlarıyla dikdörtgen çizmek yanlış
                    # olur; bunun yerine sağ üst köşeye bilgi etiketi basılır.
                    from camera_interface import BaslerCamera
                    if isinstance(cam, BaslerCamera) and cam.is_open:
                        try:
                            ox, oy, w, h = cam.get_roi()
                            fh, fw = frame.shape[:2]
                            # Tam sensör değilse HW ROI aktif — bilgi yaz
                            full_w, full_h = 1448, 1084
                            if w < full_w - 8 or h < full_h - 8:
                                rot = self.rotation_code.get()
                                rot_txt = {0:"0°",1:"90°CW",2:"180°",3:"90°CCW"}.get(rot,"")
                                label = f"HW ROI {w}x{h} @({ox},{oy})  [{rot_txt}]"
                                cv2.putText(frame, label,
                                            (4, 16),
                                            cv2.FONT_HERSHEY_SIMPLEX,
                                            0.45, (0, 255, 255), 1,
                                            cv2.LINE_AA)
                        except Exception:
                            pass

                    cw = canvas.winfo_width()  or 480
                    ch = canvas.winfo_height() or 360
                    fh, fw = frame.shape[:2]
                    sc  = min(cw / fw, ch / fh)
                    nw  = int(fw * sc)
                    nh  = int(fh * sc)
                    res = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LINEAR)
                    rgb = cv2.cvtColor(res, cv2.COLOR_BGR2RGB)
                    ph  = ImageTk.PhotoImage(Image.fromarray(rgb))
                    xo  = (cw - nw) // 2
                    yo  = (ch - nh) // 2
                    canvas.delete("all")
                    canvas.create_image(xo, yo, anchor="nw", image=ph)
                    canvas._ph = ph
                else:
                    canvas.delete("all")
                    canvas.create_text(
                        (canvas.winfo_width() or 480) // 2,
                        (canvas.winfo_height() or 360) // 2,
                        text="Görüntü yok — önce kamera/video başlatın",
                        fill=TEXT_DIM, font=FONT_LABEL)
            except Exception:
                pass

            self._settings_preview_id = win.after(150, _tick)

        _tick()

    # ── Bilgi yenileme ────────────────────────────────────────────────────────

    def _refresh_si(self, cam):
        from camera_interface import BaslerCamera
        if not isinstance(cam, BaslerCamera) or not cam.is_open:
            return
        s = cam.get_settings()
        try:
            fps = s.get('resulting_fps', 0)
            en  = s.get('fps_enable', False)
            self._si_fps.set(
                f"Sonuç FPS : {fps:.1f}  [{'sınırlı' if en else 'max'}]")
        except Exception: pass
        try:
            fmt = s.get('pixel_format', '--')
            bw  = {'BGR8':3,'RGB8':3,'YUV422_8':2}.get(fmt, 1)
            self._si_fmt.set(f"Format    : {fmt}  ({bw} byte/px)")
        except Exception: pass
        try:
            ox, oy, w, h = s.get('roi', (0, 0, 1440, 1080))
            self._si_roi.set(f"ROI       : {w}×{h}  offset ({ox},{oy})")
        except Exception: pass
        try:
            g  = s.get('gain', 0.0)
            ga = s.get('gain_auto', '--')
            self._si_gain.set(f"Gain      : {g:.1f} dB  [{ga}]")
        except Exception: pass
        try:
            wba = s.get('wb_auto', '--')
            wb  = s.get('wb', {})
            r = wb.get('red', 0); g = wb.get('green', 0); b = wb.get('blue', 0)
            self._si_wb.set(f"WB        : [{wba}] R{r:.2f} G{g:.2f} B{b:.2f}")
        except Exception: pass
        try:
            t = s.get('temperature', 0)
            self._si_temp.set(f"Sıcaklık  : {t:.1f} °C")
        except Exception: pass

    # ── Kapatma ───────────────────────────────────────────────────────────────

    def _close_settings(self, win):
        if self._settings_preview_id:
            try:
                win.after_cancel(self._settings_preview_id)
            except Exception:
                pass
            self._settings_preview_id = None
        try:
            win.destroy()
        except Exception:
            pass

    # ── Hızlı Presetler ──────────────────────────────────────────────────────

    def _build_quick_presets_section(self, parent, cam, is_basler):
        """Bir tıkla birden fazla ayarı uygulayan preset butonları."""

        presets = [
            {
                "name":  "🏎  800 FPS\nDeney Modu",
                "desc":  "90°CW  |  1440×270 (merkez)  |  800 FPS",
                "apply": lambda: self._preset_800fps(cam, is_basler),
            },
        ]

        for p in presets:
            card = tk.Frame(parent, bg=ACCENT, relief="flat")
            card.pack(fill="x", padx=8, pady=4)

            tk.Label(card, text=p["desc"], bg=ACCENT, fg=TEXT_LIGHT,
                     font=FONT_MONO, anchor="w").pack(side="left", padx=10, pady=6)

            tk.Button(card, text=p["name"], font=FONT_LABEL,
                      bg=SUCCESS, fg=DARK_BG, relief="flat",
                      justify="center",
                      command=p["apply"],
                      state="normal" if is_basler else "disabled",
                      cursor="hand2"
                      ).pack(side="right", padx=8, pady=6)

        if not is_basler:
            tk.Label(parent,
                     text="Preset uygulamak icin Basler kamera bagli ve baslatilmis olmali.",
                     bg=PANEL_BG, fg=WARNING, font=FONT_MONO, wraplength=420
                     ).pack(padx=8, anchor="w", pady=2)

    def _preset_800fps(self, cam, is_basler):
        """800 FPS deney preseti — TEK durdur/ayarla/başlat döngüsü.
        Format → ROI → FPS hepsi kamera durdukken set edilir, sonra başlatılır.
        """
        import time, threading

        # 1. Döndürme (yazılım)
        self.rotation_code.set(1)
        self._log("Preset: 90°CW döndürme ayarlandı")

        if not is_basler:
            self._log("Preset: Kamera yok — sadece döndürme uygulandı.")
            return

        # 2. Kamerayı durdur
        was_running = cam._running
        cam._running = False
        try:
            if cam.camera.IsGrabbing():
                cam.camera.StopGrabbing()
        except Exception:
            pass
        time.sleep(0.25)
        while not cam._queue.empty():
            try: cam._queue.get_nowait()
            except Exception: break

        # 3. Piksel formatı: en düşük bant genişliği (1 byte/piksel)
        #    BGR8 = 3 byte → USB3'te 1440×270 için maks ~308 fps
        #    BayerRG8/Mono8 = 1 byte → maks ~900+ fps
        try:
            available = list(cam.camera.PixelFormat.Symbolics)
            self._log(f"Preset: Desteklenen formatlar: {available}")
            fmt_set = None
            for fmt in ["BayerRG8", "BayerGB8", "BayerBG8", "Mono8"]:
                if fmt in available:
                    cam.camera.PixelFormat.SetValue(fmt)
                    fmt_set = fmt
                    break
            self._log(f"Preset: Piksel format → {fmt_set or 'değiştirilemedi (BGR8 kalıyor)'}")
        except Exception as e:
            self._log(f"Preset: Format hatası: {e}")

        # 4. Hardware ROI: 1440×roi_height, dikey merkez
        try:
            cam.camera.OffsetX.SetValue(0)
            cam.camera.OffsetY.SetValue(0)
            roi_h = self.cam_roi_height.get()
            w = 1440
            h = (int(roi_h) // 2) * 2
            h = max(2, min(h, cam.camera.Height.GetMax()))
            cam.camera.Width.SetValue(w)
            cam.camera.Height.SetValue(h)
            sensor_h = cam.camera.SensorHeight.GetValue()
            oy = ((sensor_h - h) // 2 // 2) * 2   # inc=2'ye yuvarla
            cam.camera.OffsetY.SetValue(oy)
            self._log(f"Preset: HW ROI → {w}×{h} @(0,{oy})")
        except Exception as e:
            self._log(f"Preset: ROI hatası: {e}")

        # 5. FPS sınırı (kamera durdukken GetMax doğru değeri döner)
        try:
            cam.camera.AcquisitionFrameRateEnable.SetValue(True)
            fps_max = cam.camera.AcquisitionFrameRate.GetMax()
            target  = min(800.0, fps_max)
            cam.camera.AcquisitionFrameRate.SetValue(target)
            self._log(f"Preset: FPS → {target:.0f}  (donanım maks={fps_max:.1f})")
        except Exception as e:
            self._log(f"Preset: FPS hatası: {e}")

        # 6. Kamerayı yeniden başlat
        if was_running:
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

        # Gelişmiş ayarlar penceresi açıksa FPS bölümündeki slider'ı güncelle
        try:
            if hasattr(self, '_sf_fps_en_var'):
                self._sf_fps_en_var.set(True)
                self._sf_fps_var.set(target)
                self._sf_fps_lbl.configure(text=f"{target:.0f}")
                self._sf_fps_slider.configure(state="normal")
        except Exception:
            pass

        self._refresh_si(cam)
        self._log("Preset tamamlandı: 90°CW | 1440×270 HW ROI | 800 FPS")

    # ── Döndürme ─────────────────────────────────────────────────────────────

    def _build_rotation_section(self, parent):
        """0° / 90° CW / 90° CCW / 180° seçim butonları."""
        desc = tk.Label(
            parent,
            text="Kamera 90° fiziksel olarak döndürüldüyse yazılım döndürmesi uygular.\n"
                 "Döndürme undistort'tan sonra, takipten önce uygulanır.",
            bg=PANEL_BG, fg=TEXT_DIM, font=FONT_MONO,
            justify="left", wraplength=420)
        desc.pack(padx=8, anchor="w", pady=(2, 4))

        btn_frame = tk.Frame(parent, bg=PANEL_BG)
        btn_frame.pack(fill="x", padx=8, pady=2)

        # (etiket, rotation_code değeri, cv2 karşılığı açıklaması)
        options = [
            ("0°\n(Kapalı)",        0),
            ("90° ↷\n(Saat Yönü)",  1),
            ("180°\n(Ters Çevir)",  2),
            ("90° ↶\n(Saat Tersi)", 3),
        ]

        for lbl, code in options:
            tk.Radiobutton(
                btn_frame,
                text=lbl,
                variable=self.rotation_code,
                value=code,
                bg=PANEL_BG, fg=TEXT_LIGHT,
                selectcolor=ACCENT,
                activebackground=PANEL_BG,
                font=("Segoe UI", 8),
                justify="center",
                indicatoron=0,           # düğme görünümü
                width=10, relief="flat",
            ).pack(side="left", padx=3, pady=2)

        # Anlık durum etiketi
        rot_names = {0: "Döndürme yok", 1: "90° Saat Yönünde",
                     2: "180°", 3: "90° Saat Yönü Tersine"}

        status_var = tk.StringVar(
            value=f"Seçili: {rot_names.get(self.rotation_code.get(), '--')}")
        status_lbl = tk.Label(parent, textvariable=status_var,
                              bg=PANEL_BG, fg=SUCCESS, font=FONT_MONO)
        status_lbl.pack(padx=8, anchor="w", pady=(2, 4))

        def _on_change(*_):
            status_var.set(
                f"Seçili: {rot_names.get(self.rotation_code.get(), '--')}")

        self.rotation_code.trace_add("write", _on_change)

    # ── Yardımcı ──────────────────────────────────────────────────────────────

    def _settings_sec(self, p, title):
        f = tk.Frame(p, bg=ACCENT, height=24)
        f.pack(fill="x", pady=(8, 2))
        f.pack_propagate(False)
        tk.Label(f, text=title, bg=ACCENT, fg=TEXT_LIGHT,
                 font=FONT_HEAD).pack(side="left", padx=10, pady=3)
