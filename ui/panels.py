"""
ui/panels.py — Sol / Orta / Sağ panel inşa metodları (mixin)
"""

import tkinter as tk
from tkinter import ttk
from ui.theme import (DARK_BG, PANEL_BG, ACCENT, HIGHLIGHT, TEXT_LIGHT,
                      TEXT_DIM, SUCCESS, WARNING, FONT_MONO, FONT_LABEL,
                      FONT_HEAD, FONT_TITLE)


class PanelsMixin:

    # ── Ana çerçeve ──────────────────────────────────────────────────────────

    def _build_ui(self):
        tf = tk.Frame(self.root, bg=ACCENT, height=50)
        tf.pack(fill="x")
        tk.Label(tf, text="⚗  Sürüklenme Katsayısı Ölçüm Sistemi",
                 font=FONT_TITLE, bg=ACCENT, fg=TEXT_LIGHT
                 ).pack(side="left", padx=20, pady=10)
        tk.Label(tf, text="Basler acA 1440-220uc  |  Terminal Hız Metodu",
                 font=FONT_LABEL, bg=ACCENT, fg=TEXT_DIM
                 ).pack(side="right", padx=20)

        main = tk.Frame(self.root, bg=DARK_BG)
        main.pack(fill="both", expand=True, padx=5, pady=5)

        left = tk.Frame(main, bg=PANEL_BG, width=295)
        left.pack(side="left", fill="y", padx=(0, 4))
        left.pack_propagate(False)
        self._build_left(left)

        center = tk.Frame(main, bg=DARK_BG)
        center.pack(side="left", fill="both", expand=True, padx=2)
        self._build_center(center)

        right = tk.Frame(main, bg=PANEL_BG, width=335)
        right.pack(side="right", fill="y", padx=(4, 0))
        right.pack_propagate(False)
        self._build_right(right)

    # ── Sol panel ────────────────────────────────────────────────────────────

    def _build_left(self, parent):
        cv = tk.Canvas(parent, bg=PANEL_BG, highlightthickness=0)
        sb = ttk.Scrollbar(parent, orient="vertical", command=cv.yview)
        sf = tk.Frame(cv, bg=PANEL_BG)
        sf.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.create_window((0, 0), window=sf, anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        p = sf

        # Kaynak seçimi
        self._sec(p, "📡 KAYNAK SEÇİMİ")
        r = tk.Frame(p, bg=PANEL_BG)
        r.pack(fill="x", padx=8, pady=4)
        for txt, val in [("Canlı Kamera", "live"), ("Video Dosyası", "video")]:
            tk.Radiobutton(
                r, text=txt, variable=self.source_mode, value=val,
                bg=PANEL_BG, fg=TEXT_LIGHT, selectcolor=ACCENT,
                activebackground=PANEL_BG, font=FONT_LABEL,
                command=self._on_src_change
            ).pack(side="left")

        # Kamera ayarları
        self.live_frame = tk.LabelFrame(p, text=" Kamera Ayarları ",
                                         bg=PANEL_BG, fg=TEXT_DIM, font=FONT_LABEL)
        self.live_frame.pack(fill="x", padx=8, pady=4)
        self._slider(self.live_frame, "Exposure (μs):", self.cam_exposure, 100, 10000,
                     lambda v: self._set_exposure(int(float(v))))
        roi_row = tk.Frame(self.live_frame, bg=PANEL_BG)
        roi_row.pack(fill="x", padx=5, pady=2)
        tk.Label(roi_row, text="ROI:", width=5, anchor="w",
                 bg=PANEL_BG, fg=TEXT_DIM, font=FONT_LABEL).pack(side="left")
        for h_val in [270, 220, 180, 150]:
            tk.Button(roi_row, text=str(h_val), font=FONT_LABEL,
                      bg=ACCENT, fg=TEXT_LIGHT, relief="flat", width=4,
                      command=lambda hv=h_val: self._apply_roi_height(hv)
                      ).pack(side="left", padx=2)

        self.cam_btn = tk.Button(p, text="🔌  Kamerayı Başlat",
                                  command=self._toggle_camera, font=FONT_LABEL,
                                  bg=SUCCESS, fg="white", relief="flat", cursor="hand2")
        self.cam_btn.pack(fill="x", padx=8, pady=2)
        tk.Button(p, text="⚙  Gelişmiş Kamera Ayarları",
                  command=self._open_settings, font=FONT_LABEL,
                  bg=ACCENT, fg=TEXT_LIGHT, relief="flat", cursor="hand2"
                  ).pack(fill="x", padx=8, pady=2)

        # Video dosyası
        self.video_frame_ui = tk.LabelFrame(p, text=" Video Dosyası ",
                                             bg=PANEL_BG, fg=TEXT_DIM, font=FONT_LABEL)
        self.video_frame_ui.pack(fill="x", padx=8, pady=4)
        self.video_path_var = tk.StringVar(value="Dosya seçilmedi")
        tk.Label(self.video_frame_ui, textvariable=self.video_path_var,
                 bg=PANEL_BG, fg=TEXT_DIM, font=FONT_MONO, wraplength=220
                 ).pack(padx=5, pady=3)
        self._btn(self.video_frame_ui, "📂  Video Dosyası Seç", self._select_video)
        pr = tk.Frame(self.video_frame_ui, bg=PANEL_BG)
        pr.pack(fill="x", padx=5, pady=3)
        self.play_btn = tk.Button(pr, text="▶ Oynat", font=FONT_LABEL,
                                   bg=ACCENT, fg=TEXT_LIGHT, relief="flat",
                                   command=self._toggle_play)
        self.play_btn.pack(side="left", padx=2)
        tk.Button(pr, text="⏹ Sıfırla", font=FONT_LABEL, bg=ACCENT, fg=TEXT_LIGHT,
                  relief="flat", command=self._reset_video).pack(side="left", padx=2)
        self.vid_status = tk.StringVar(value="Hazır")
        tk.Label(self.video_frame_ui, textvariable=self.vid_status,
                 bg=PANEL_BG, fg=TEXT_DIM, font=FONT_MONO).pack(pady=2)

        self._on_src_change()

        # Kalibrasyon
        self._sec(p, "📐 KALİBRASYON")
        self._btn(p, "📏  Kalibrasyon (Nokta Seçimi)", self._start_combined_calib, WARNING)
        self._btn(p, "♟  Satranç Tahtası Kalibrasyonu",  self._checkerboard_calib)
        cr = tk.Frame(p, bg=PANEL_BG)
        cr.pack(fill="x", padx=8, pady=2)
        self._bsm(cr, "💾 Kaydet", self._save_calibration)
        self._bsm(cr, "📂 Yükle",  self._load_calibration)
        self.calib_lbl = tk.Label(p, text="Kalibrasyon yok", bg=PANEL_BG,
                                   fg=TEXT_DIM, font=FONT_MONO,
                                   wraplength=260, justify="left")
        self.calib_lbl.pack(padx=8, pady=4, anchor="w")

        # Takip
        self._sec(p, "🎯 TAKİP")
        self._slider(p, "Parlaklık Eşiği:", self.detect_threshold, 10, 250,
                     lambda v: self._set_threshold(int(float(v))))
        self.measure_btn = tk.Button(
            p, text="▶  Ölçümü Başlat", command=self._toggle_measurement,
            font=FONT_LABEL, bg=SUCCESS, fg="white", relief="flat",
            activebackground=HIGHLIGHT, cursor="hand2")
        self.measure_btn.pack(fill="x", padx=8, pady=2)
        self._btn(p, "⏹  Ölçümü Sıfırla", self._reset_tracking)

    # ── Orta panel ───────────────────────────────────────────────────────────

    def _build_center(self, parent):
        self.canvas = tk.Canvas(parent, bg="#0a0a0a", cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Button-3>", self._on_rclick)

        ctrl = tk.Frame(parent, bg=ACCENT, height=36)
        ctrl.pack(fill="x", side="bottom")
        ctrl.pack_propagate(False)
        self.rec_btn = tk.Button(ctrl, text="⏺  Kayıt", font=FONT_LABEL,
                                  bg=HIGHLIGHT, fg="white", relief="flat",
                                  command=self._toggle_record)
        self.rec_btn.pack(side="left", padx=8, pady=4)
        for txt, cmd in [("📸 Ekran Görüntüsü", self._screenshot),
                         ("📊 Sonuç Grafiği",   self._show_plot),
                         ("💾 Sonuçları Kaydet", self._export)]:
            tk.Button(ctrl, text=txt, font=FONT_LABEL, bg=ACCENT, fg=TEXT_LIGHT,
                      relief="flat", command=cmd).pack(side="left", padx=4, pady=4)
        self.fps_lbl = tk.Label(ctrl, text="FPS: --", font=FONT_MONO,
                                 bg=ACCENT, fg=TEXT_DIM)
        self.fps_lbl.pack(side="right", padx=12)
        self.frame_lbl = tk.Label(ctrl, text="Kare: --", font=FONT_MONO,
                                   bg=ACCENT, fg=TEXT_DIM)
        self.frame_lbl.pack(side="right", padx=8)

    # ── Sağ panel ────────────────────────────────────────────────────────────

    def _build_right(self, parent):
        self._sec(parent, "📋 SİSTEM GÜNLÜĞÜ")
        lf = tk.Frame(parent, bg=PANEL_BG)
        lf.pack(fill="x", padx=5, pady=2)
        ls = ttk.Scrollbar(lf)
        ls.pack(side="right", fill="y")
        self.log_text = tk.Text(lf, height=8, bg="#0d0d1a", fg=SUCCESS,
                                 font=FONT_MONO, yscrollcommand=ls.set,
                                 state="disabled", wrap="word", relief="flat")
        self.log_text.pack(fill="x")
        ls.config(command=self.log_text.yview)

        self._sec(parent, "📊 HESAPLAMA SONUÇLARI")
        self.rl = {}
        for label, key, unit in [
            ("Terminal Hız",    "v_terminal",   "mm/s"),
            ("(Duvar Düz.)",    "v_corrected",  "mm/s"),
            ("Stokes Tahm.",    "v_stokes",     "mm/s"),
            ("Reynolds Sayısı", "Re",           ""),
            ("C_d (Ölçülen)",   "Cd",           ""),
            ("C_d (Stokes)",    "Cd_stokes",    ""),
            ("C_d (Ampirik)",   "Cd_empirical", ""),
            ("Hata (Stokes)",   "err_stokes",   "%"),
            ("Hata (Ampirik)",  "err_emp",      "%"),
            ("Akış Rejimi",     "regime",       ""),
        ]:
            row = tk.Frame(parent, bg=PANEL_BG)
            row.pack(fill="x", padx=8, pady=1)
            tk.Label(row, text=f"{label}:", width=17, anchor="w",
                     bg=PANEL_BG, fg=TEXT_DIM, font=FONT_LABEL).pack(side="left")
            vl = tk.Label(row, text="--", anchor="e",
                          bg=PANEL_BG, fg=TEXT_LIGHT, font=FONT_MONO)
            vl.pack(side="right")
            if unit:
                tk.Label(row, text=unit, width=5, anchor="w",
                         bg=PANEL_BG, fg=TEXT_DIM, font=FONT_MONO).pack(side="right")
            self.rl[key] = vl

        self._sec(parent, "⚡ ANLIK HIZ")
        self.speed_var = tk.StringVar(value="-- mm/s")
        tk.Label(parent, textvariable=self.speed_var,
                 font=("Consolas", 18, "bold"), bg=PANEL_BG, fg=SUCCESS).pack(pady=6)
        self.vel_cv = tk.Canvas(parent, bg="#0a0a0a", height=120)
        self.vel_cv.pack(fill="x", padx=5, pady=4)

        self._btn(parent, "🧮  C_d Hesapla",     self._calculate_cd, SUCCESS)
        self._btn(parent, "🗑  Geçmişi Temizle", self._clear_history, HIGHLIGHT)

        self._sec(parent, "📁 GEÇMİŞ DENEMELER")
        hf = tk.Frame(parent, bg=PANEL_BG)
        hf.pack(fill="both", expand=True, padx=5, pady=2)
        hs = ttk.Scrollbar(hf, orient="vertical")
        hs.pack(side="right", fill="y")
        hsx = ttk.Scrollbar(hf, orient="horizontal")
        hsx.pack(side="bottom", fill="x")
        self.hist = tk.Listbox(hf, bg="#0d0d1a", fg=TEXT_LIGHT, font=FONT_MONO,
                                yscrollcommand=hs.set, xscrollcommand=hsx.set,
                                selectbackground=ACCENT, relief="flat")
        self.hist.pack(fill="both", expand=True)
        hs.config(command=self.hist.yview)
        hsx.config(command=self.hist.xview)

    # ── Kaynak değişimi ──────────────────────────────────────────────────────

    def _on_src_change(self):
        if self.source_mode.get() == "live":
            self.live_frame.pack(fill="x", padx=8, pady=4)
            self.video_frame_ui.pack_forget()
        else:
            self.live_frame.pack_forget()
            self.video_frame_ui.pack(fill="x", padx=8, pady=4)
