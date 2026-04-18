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

        # Kaynak ayarları placeholder — radio butonlarının hemen altı
        self._src_slot = tk.Frame(p, bg=PANEL_BG)
        self._src_slot.pack(fill="x")

        # ── Kamera container ──────────────────────────────────────────────
        self.live_container = tk.Frame(self._src_slot, bg=PANEL_BG)

        self.live_frame = tk.LabelFrame(self.live_container,
                                         text=" Kamera Ayarları ",
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

        self.cam_btn = tk.Button(self.live_container,
                                  text="🔌  Kamerayı Başlat",
                                  command=self._toggle_camera, font=FONT_LABEL,
                                  bg=SUCCESS, fg="white", relief="flat", cursor="hand2")
        self.cam_btn.pack(fill="x", padx=8, pady=2)
        tk.Button(self.live_container, text="⚙  Gelişmiş Kamera Ayarları",
                  command=self._open_settings, font=FONT_LABEL,
                  bg=ACCENT, fg=TEXT_LIGHT, relief="flat", cursor="hand2"
                  ).pack(fill="x", padx=8, pady=2)

        # ── Video container ──────────────────────────────────────────────
        self.video_container = tk.Frame(self._src_slot, bg=PANEL_BG)

        self.video_frame_ui = tk.LabelFrame(self.video_container,
                                             text=" Video Dosyası ",
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
        self.calib_lbl = tk.Label(p, text="Kalibrasyon yok", bg=PANEL_BG,
                                   fg=TEXT_DIM, font=FONT_MONO,
                                   wraplength=260, justify="left")
        self.calib_lbl.pack(padx=8, pady=4, anchor="w")

        # ── Deney parametreleri ──────────────────────────────────────────
        self._sec(p, "🧪 DENEY PARAMETRELERİ")

        # Sıvı seçimi
        tk.Label(p, text="Sıvı:", bg=PANEL_BG, fg=TEXT_DIM,
                 font=FONT_LABEL).pack(anchor="w", padx=8, pady=(4, 0))
        fluid_row = tk.Frame(p, bg=PANEL_BG)
        fluid_row.pack(fill="x", padx=8, pady=2)
        fluids = [
            ("Mısır Şurubu", 1380.0, 5.0),
            ("Gliserin",     1260.0, 1.41),
            ("Su",            998.0, 0.001),
        ]
        for name, rho, mu in fluids:
            tk.Button(fluid_row, text=name, font=("Segoe UI", 8),
                      bg=ACCENT, fg=TEXT_LIGHT, relief="flat",
                      command=lambda r=rho, m=mu, n=name: self._set_fluid(r, m, n)
                      ).pack(side="left", padx=2)

        self._ent(p, "Yoğunluk (kg/m³):", self.fluid_density)
        self._ent(p, "Viskozite (Pa·s):", self.fluid_viscosity)

        # Cisim malzemesi
        tk.Label(p, text="Cisim:", bg=PANEL_BG, fg=TEXT_DIM,
                 font=FONT_LABEL).pack(anchor="w", padx=8, pady=(4, 0))
        mat_row = tk.Frame(p, bg=PANEL_BG)
        mat_row.pack(fill="x", padx=8, pady=2)
        materials = [
            ("Pirinç",    8500.0),
            ("Cam",       2500.0),
            ("Alüminyum", 2700.0),
            ("Çelik",     7800.0),
        ]
        for name, rho in materials:
            tk.Button(mat_row, text=name, font=("Segoe UI", 8),
                      bg=ACCENT, fg=TEXT_LIGHT, relief="flat",
                      command=lambda r=rho, n=name: self._set_material(r, n)
                      ).pack(side="left", padx=2)

        self._ent(p, "Yoğunluk (kg/m³):", self.particle_density)

        # Cisim çapı
        dia_row = tk.Frame(p, bg=PANEL_BG)
        dia_row.pack(fill="x", padx=8, pady=2)
        tk.Label(dia_row, text="Çap:", width=4, anchor="w",
                 bg=PANEL_BG, fg=TEXT_DIM, font=FONT_LABEL).pack(side="left")
        for d in [1, 2, 3, 4, 5, 6]:
            tk.Button(dia_row, text=f"{d}", font=("Segoe UI", 8),
                      bg=ACCENT, fg=TEXT_LIGHT, relief="flat", width=2,
                      command=lambda dd=d: self._set_diameter(dd)
                      ).pack(side="left", padx=1)
        tk.Label(dia_row, text="mm", bg=PANEL_BG, fg=TEXT_DIM,
                 font=FONT_LABEL).pack(side="left", padx=2)

        # Boru iç çapı
        pipe_row = tk.Frame(p, bg=PANEL_BG)
        pipe_row.pack(fill="x", padx=8, pady=2)
        tk.Label(pipe_row, text="Boru iç Ø:", width=9, anchor="w",
                 bg=PANEL_BG, fg=TEXT_DIM, font=FONT_LABEL).pack(side="left")
        for d in [45, 95]:
            tk.Button(pipe_row, text=f"{d}mm", font=("Segoe UI", 8),
                      bg=ACCENT, fg=TEXT_LIGHT, relief="flat",
                      command=lambda dd=d: self._set_pipe(dd)
                      ).pack(side="left", padx=2)

        tk.Checkbutton(p, text="Duvar düzeltmesi uygula",
                       variable=self.apply_wall_corr,
                       bg=PANEL_BG, fg=TEXT_LIGHT, selectcolor=ACCENT,
                       activebackground=PANEL_BG, font=FONT_LABEL
                       ).pack(anchor="w", padx=8, pady=2)

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

        # ── Alt kontrol: kayıt + dışa aktarma ──────────────────────────
        ctrl = tk.Frame(parent, bg=ACCENT, height=36)
        ctrl.pack(fill="x", side="bottom")
        ctrl.pack_propagate(False)
        self.rec_btn = tk.Button(ctrl, text="⏺  Kayıt", font=FONT_LABEL,
                                  bg=HIGHLIGHT, fg="white", relief="flat",
                                  command=self._toggle_record)
        self.rec_btn.pack(side="left", padx=8, pady=4)
        self.play_rec_btn = tk.Button(ctrl, text="▶ İzle", font=FONT_LABEL,
                                       bg=ACCENT, fg=TEXT_LIGHT, relief="flat",
                                       command=self._play_recording, state="disabled")
        self.play_rec_btn.pack(side="left", padx=2, pady=4)
        self.save_rec_btn = tk.Button(ctrl, text="💾 Videoyu Kaydet", font=FONT_LABEL,
                                       bg=ACCENT, fg=TEXT_LIGHT, relief="flat",
                                       command=self._save_recording, state="disabled")
        self.save_rec_btn.pack(side="left", padx=2, pady=4)
        for txt, cmd in [("📸 Görüntü", self._screenshot),
                         ("📊 Grafik",   self._show_plot),
                         ("💾 Sonuçlar", self._export)]:
            tk.Button(ctrl, text=txt, font=FONT_LABEL, bg=ACCENT, fg=TEXT_LIGHT,
                      relief="flat", command=cmd).pack(side="left", padx=2, pady=4)
        self.fps_lbl = tk.Label(ctrl, text="FPS: --", font=FONT_MONO,
                                 bg=ACCENT, fg=TEXT_DIM)
        self.fps_lbl.pack(side="right", padx=12)
        self.frame_lbl = tk.Label(ctrl, text="Kare: --", font=FONT_MONO,
                                   bg=ACCENT, fg=TEXT_DIM)
        self.frame_lbl.pack(side="right", padx=8)

        # ── Oynatma kontrol çubuğu (İzle modunda görünür) ────────────
        self.playback_bar = tk.Frame(parent, bg=ACCENT, height=36)
        # Başlangıçta gizli — _play_recording açar
        self.playback_bar.pack_propagate(False)
        self.pb_play_btn = tk.Button(self.playback_bar, text="▶", font=FONT_LABEL,
                                      bg=ACCENT, fg=TEXT_LIGHT, relief="flat", width=3,
                                      command=self._pb_toggle_play)
        self.pb_play_btn.pack(side="left", padx=4, pady=4)
        self.pb_slider = tk.Scale(self.playback_bar, from_=0, to=100,
                                   orient="horizontal", showvalue=False,
                                   bg=ACCENT, fg=TEXT_LIGHT, troughcolor=HIGHLIGHT,
                                   highlightthickness=0,
                                   command=self._pb_on_seek)
        self.pb_slider.pack(side="left", fill="x", expand=True, padx=4, pady=4)
        self.pb_lbl = tk.Label(self.playback_bar, text="0 / 0", font=FONT_MONO,
                                bg=ACCENT, fg=TEXT_DIM)
        self.pb_lbl.pack(side="right", padx=8)
        tk.Button(self.playback_bar, text="✕ Kapat", font=FONT_LABEL,
                  bg=ACCENT, fg=TEXT_LIGHT, relief="flat",
                  command=self._pb_close).pack(side="right", padx=4, pady=4)

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

        # ── Hesaplama sonuçları ──────────────────────────────────────────
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
            self.video_container.pack_forget()
            self.live_container.pack(fill="x")
        else:
            # Kamerayı durdur
            if self.camera is not None and self.camera.is_open:
                self._stop_live()
            self.live_container.pack_forget()
            self.video_container.pack(fill="x")
