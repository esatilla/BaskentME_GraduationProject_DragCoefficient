"""
ui/results_mixin.py — Cd hesaplama, sonuç gösterimi ve grafik (mixin)
"""

import time

import tkinter as tk
from tkinter import messagebox

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image, ImageTk

from physics import (calculate_segment_velocities, detect_terminal_velocity,
                     calculate_drag_coefficient, apply_wall_correction,
                     detrend_segment_velocities)
from ui.theme import (DARK_BG, PANEL_BG, TEXT_LIGHT, TEXT_DIM,
                      SUCCESS, WARNING, HIGHLIGHT)


class ResultsMixin:

    # ── Cd hesaplama ─────────────────────────────────────────────────────────

    def _calculate_cd(self):
        s = self.detector.get_tracking_summary()

        positions  = s['positions']
        timestamps = s['timestamps']

        # Bölge filtresi
        rect = self._meas_rect
        if rect is not None:
            x1, y1, x2, y2 = rect
            filtered = [(p, t) for p, t in zip(positions, timestamps)
                        if x1 <= p[0] <= x2 and y1 <= p[1] <= y2]
            if filtered:
                positions, timestamps = zip(*filtered)
                positions  = list(positions)
                timestamps = list(timestamps)
            else:
                positions, timestamps = [], []

        if len(positions) < 5:
            messagebox.showwarning("Yetersiz Veri", "Bölge içinde en az 5 nokta gerekli.")
            return

        segs = calculate_segment_velocities(
            positions, timestamps, self.calibrator.px_per_mm)
        if len(segs) < 2:
            messagebox.showwarning(
                "Yetersiz Segment",
                "En az 2 segment (2×1 cm) gerekli — cismi daha uzun mesafede bırakın.")
            return

        if self.detrend_velocity.get() and len(segs) >= 3:
            segs = detrend_segment_velocities(segs)
            self._log("Nem gradyanı düzeltmesi uygulandı.")

        vels   = [seg['v_mm_s'] for seg in segs]
        t_mids = [(seg['t_start'] + seg['t_end']) / 2.0 for seg in segs]

        vt, _ = detect_terminal_velocity(
            np.array(t_mids), np.array(vels), min_stable_points=3)
        if vt is None:
            messagebox.showwarning(
                "Terminal Hıza Ulaşılamadı",
                "Terminal hıza ulaşılamadı.\n"
                "Cismin daha uzun süre düşmesini bekleyin.")
            self._log("Terminal hıza ulaşılamadı.")
            return

        vc, wk = vt, 1.0
        if self.apply_wall_corr.get():
            vc, wk = apply_wall_correction(vt, self.particle_diameter.get(),
                                            self.cylinder_diameter.get())

        res = calculate_drag_coefficient(vc,
                                         self.particle_diameter.get(),
                                         self.particle_density.get(),
                                         self.fluid_density.get(),
                                         self.fluid_viscosity.get())
        if res is None:
            messagebox.showerror("Hesaplama Hatası",
                                  "Geçersiz parametreler – değerleri kontrol edin.")
            return

        self._show_results(res, vt, vc)
        self._last_segs = segs
        self._last_vt   = vt

        entry = {
            'time':        time.strftime("%H:%M:%S"),
            'v_terminal':  vt,
            'v_corrected': vc,
            'Cd':          res['Cd'],
            'Re':          res['Re'],
            'diameter_mm': self.particle_diameter.get(),
            'rho_p':       self.particle_density.get(),
            'mu':          self.fluid_viscosity.get(),
            'wall_factor': wk,
            'points':      s['total_points'],
            'duration_s':  s['duration'],
            'segments':    len(segs),
        }
        self.results.append(entry)
        lbl = (f"[{entry['time']}]  v={vc:.1f}mm/s  "
               f"Cd={res['Cd']:.4f}  Re={res['Re']:.3f}  ({len(segs)} seg)")
        self.hist.insert(tk.END, lbl)
        self.hist.see(tk.END)
        self._log(f"✓ Cd={res['Cd']:.4f}  Re={res['Re']:.4f}  {res['regime']}")

    def _show_results(self, res, vt, vc):
        def f(v, d=4):
            return f"{v:.{d}f}" if v is not None else "--"

        def ec(e):
            return SUCCESS if e and e < 5 else (WARNING if e and e < 15 else HIGHLIGHT)

        self.rl['v_terminal'].configure(text=f(vt, 2),              fg=TEXT_LIGHT)
        self.rl['v_corrected'].configure(text=f(vc, 2),             fg=SUCCESS)
        self.rl['v_stokes'].configure(text=f(res['v_stokes'], 2),   fg=TEXT_DIM)
        self.rl['Re'].configure(text=f(res['Re'], 4),                fg=TEXT_LIGHT)
        self.rl['Cd'].configure(text=f(res['Cd'], 4),                fg=SUCCESS)
        self.rl['Cd_stokes'].configure(text=f(res['Cd_stokes'], 4),      fg=TEXT_DIM)
        self.rl['Cd_empirical'].configure(text=f(res['Cd_empirical'], 4), fg=TEXT_DIM)
        es = res['error_stokes_pct']
        ee = res['error_empirical_pct']
        self.rl['err_stokes'].configure(text=f(es, 1) if es else "--", fg=ec(es))
        self.rl['err_emp'].configure(text=f(ee, 1) if ee else "--",    fg=ec(ee))
        self.rl['regime'].configure(text=res['regime'], fg=WARNING)

    def _clear_history(self):
        self.results.clear()
        self.hist.delete(0, tk.END)
        self._log("Geçmiş temizlendi.")

    # ── Deney parametresi preset'leri ────────────────────────────────────────

    # (fluid_name, temp_°C) → (ρ kg/m³, μ Pa·s)
    _FLUID_TABLE = {
        ("Gliserin",     15): (1264.0, 2.330),
        ("Gliserin",     20): (1261.0, 1.412),
        ("Gliserin",     25): (1258.0, 0.934),
        ("Gliserin",     30): (1255.0, 0.629),
        ("Su",           15): (999.1,  0.001139),
        ("Su",           20): (998.2,  0.001002),
        ("Su",           25): (997.0,  0.000891),
        ("Su",           30): (995.7,  0.000798),
        ("Mısır Şurubu", 15): (1385.0, 8.0),
        ("Mısır Şurubu", 20): (1382.0, 5.5),
        ("Mısır Şurubu", 25): (1380.0, 4.0),
        ("Mısır Şurubu", 30): (1377.0, 3.0),
    }

    def _set_fluid(self, rho, mu, name):
        self._selected_fluid_name = name
        t = self.fluid_temp.get()
        props = self._FLUID_TABLE.get((name, t))
        if props:
            rho, mu = props
        self.fluid_density.set(rho)
        self.fluid_viscosity.set(mu)
        self._fluid_selected = True
        self._log(f"Sıvı: {name}  (ρ={rho} kg/m³, μ={mu} Pa·s, @{t}°C)")

    def _set_temp(self, t):
        self.fluid_temp.set(t)
        name = self._selected_fluid_name
        if name:
            props = self._FLUID_TABLE.get((name, t))
            if props:
                rho, mu = props
                self.fluid_density.set(rho)
                self.fluid_viscosity.set(mu)
                self._log(f"Sıcaklık: {t}°C → {name}  (ρ={rho} kg/m³, μ={mu} Pa·s)")
            else:
                self._log(f"Sıcaklık: {t}°C  ({name} için tablo verisi yok)")
        else:
            self._log(f"Sıcaklık: {t}°C  (önce sıvı seçin)")

    def _set_material(self, rho, name):
        self.particle_density.set(rho)
        self._material_selected = True
        self._log(f"Cisim: {name}  (ρ={rho} kg/m³)")

    def _set_diameter(self, d):
        self.particle_diameter.set(float(d))
        self._diameter_selected = True
        self._log(f"Cisim çapı: {d} mm")

    def _set_pipe(self, d):
        self.cylinder_diameter.set(float(d))
        self._log(f"Boru iç çapı: {d} mm")

    # ── Lineer regresyon grafiği ────────────────────────────────────────────

    def _open_regression(self):
        segs = getattr(self, '_last_segs', None)
        vt   = getattr(self, '_last_vt', None)
        if not segs or vt is None:
            messagebox.showwarning("Veri Yok",
                                   "Önce Cd hesaplaması yapın.")
            return
        self._show_velocity_regression(segs, vt)

    def _show_velocity_regression(self, segs, vt):
        from scipy.stats import linregress

        cum_dist = np.array([s['cum_dist_mm'] / 10.0 for s in segs])
        vels     = np.array([s['v_mm_s'] for s in segs])
        t_mids   = np.array([(s['t_start'] + s['t_end']) / 2.0 for s in segs])
        t_rel    = t_mids - t_mids[0]

        slope, intercept, r_value, _, _ = linregress(t_rel, vels)
        r2 = r_value ** 2
        fit_line = slope * t_rel + intercept

        fig, axes = plt.subplots(1, 2, figsize=(12, 5), facecolor='#1a1a2e')
        for ax in axes:
            ax.set_facecolor('#0d0d1a')
            ax.tick_params(colors='#8892a4')
            for sp in ['bottom', 'left']:
                ax.spines[sp].set_color('#8892a4')
            for sp in ['top', 'right']:
                ax.spines[sp].set_visible(False)

        ax1 = axes[0]
        ax1.scatter(t_rel, vels, color='#4ecca3', s=40, zorder=3, label='Segment Hızı')
        ax1.plot(t_rel, fit_line, color='#e94560', lw=2, ls='--',
                 label=f'Regresyon (R²={r2:.4f})')
        ax1.axhline(vt, color='#f0c040', lw=1.5, ls=':',
                    label=f'Terminal: {vt:.1f} mm/s')
        ax1.set_xlabel('Zaman (s)', color='#8892a4')
        ax1.set_ylabel('Hız (mm/s)', color='#8892a4')
        ax1.set_title('Hız – Zaman  (Lineer Regresyon)', color='#eaeaea')
        ax1.legend(facecolor='#16213e', labelcolor='#eaeaea', fontsize=8)
        ax1.grid(alpha=0.2, color='#8892a4')

        slope_d, intercept_d, r_d, _, _ = linregress(cum_dist, vels)
        fit_d = slope_d * cum_dist + intercept_d

        ax2 = axes[1]
        ax2.scatter(cum_dist, vels, color='#4ecca3', s=40, zorder=3, label='Segment Hızı')
        ax2.plot(cum_dist, fit_d, color='#e94560', lw=2, ls='--',
                 label=f'Regresyon (R²={r_d**2:.4f})')
        ax2.axhline(vt, color='#f0c040', lw=1.5, ls=':',
                    label=f'Terminal: {vt:.1f} mm/s')
        ax2.set_xlabel('Mesafe (cm)', color='#8892a4')
        ax2.set_ylabel('Hız (mm/s)', color='#8892a4')
        ax2.set_title('Hız – Mesafe  (Lineer Regresyon)', color='#eaeaea')
        ax2.legend(facecolor='#16213e', labelcolor='#eaeaea', fontsize=8)
        ax2.grid(alpha=0.2, color='#8892a4')

        info = (f"Eğim: {slope:.2f} mm/s²   Kesişim: {intercept:.1f} mm/s   "
                f"R²: {r2:.4f}   Terminal Hız: {vt:.1f} mm/s")
        fig.text(0.5, 0.01, info, ha='center', color='#8892a4', fontsize=9)
        plt.tight_layout(rect=[0, 0.04, 1, 1])

        import io
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, facecolor=fig.get_facecolor())
        plt.close(fig)
        buf.seek(0)
        img = Image.open(buf)
        ph  = ImageTk.PhotoImage(img)

        pw = tk.Toplevel(self.root)
        pw.title("Hız Analizi — Lineer Regresyon")
        pw.configure(bg=DARK_BG)
        lbl = tk.Label(pw, image=ph, bg=DARK_BG)
        lbl.image = ph
        lbl.pack(padx=10, pady=10)

    # ── Mini hız grafiği (mesafe–hız) ────────────────────────────────────────

    def _draw_vel(self, dists_cm, vels):
        """dists_cm: birikimli mesafe (cm), vels: segment ort. hız (mm/s)."""
        try:
            dists_cm = np.asarray(dists_cm, float)
            vels     = np.asarray(vels,     float)
            cw = self.vel_cv.winfo_width()
            ch = self.vel_cv.winfo_height()
            if cw < 10 or ch < 10 or len(vels) < 2:
                return
            self.vel_cv.delete("all")
            self.vel_cv.create_rectangle(0, 0, cw, ch, fill="#0a0a0a", outline="")
            pad = 15
            pw, ph = cw - 2 * pad, ch - 2 * pad
            vm  = max(0, float(np.min(vels)) * 0.9)
            vx  = float(np.max(vels)) * 1.1 + 0.1
            dm  = float(dists_cm[0])
            dx  = float(dists_cm[-1])
            if dx <= dm or vx <= vm:
                return

            def tc(d, v):
                return (int(pad + (d - dm) / (dx - dm) * pw),
                        int(ch - pad - (v - vm) / (vx - vm) * ph))

            pts = []
            for d, v in zip(dists_cm, vels):
                pts.extend(tc(d, v))
            if len(pts) >= 4:
                self.vel_cv.create_line(*pts, fill=SUCCESS, width=2, smooth=True)
            for d, v in zip(dists_cm, vels):
                x, y = tc(d, v)
                self.vel_cv.create_oval(x - 3, y - 3, x + 3, y + 3,
                                         fill=SUCCESS, outline="")
            self.vel_cv.create_text(pad,      ch - 4, text=f"{dm:.0f}cm",
                                     fill=TEXT_DIM, anchor="sw", font=("Consolas", 7))
            self.vel_cv.create_text(cw - pad, ch - 4, text=f"{dx:.0f}cm",
                                     fill=TEXT_DIM, anchor="se", font=("Consolas", 7))
            self.vel_cv.create_text(pad,      pad,    text=f"{vx:.0f}",
                                     fill=TEXT_DIM, anchor="nw", font=("Consolas", 7))
        except Exception:
            pass

    # ── Analiz grafiği penceresi ──────────────────────────────────────────────

    def _show_plot(self):
        s = self.detector.get_tracking_summary()
        positions  = s['positions']
        timestamps = s['timestamps']
        rect = self._meas_rect
        if rect is not None:
            x1, y1, x2, y2 = rect
            filtered = [(p, t) for p, t in zip(positions, timestamps)
                        if x1 <= p[0] <= x2 and y1 <= p[1] <= y2]
            if filtered:
                positions, timestamps = zip(*filtered)
                positions  = list(positions)
                timestamps = list(timestamps)
            else:
                positions, timestamps = [], []
        if len(positions) < 5:
            messagebox.showwarning("Veri Yok", "Bölge içinde yeterli veri yok.")
            return
        segs = calculate_segment_velocities(
            positions, timestamps, self.calibrator.px_per_mm)
        if len(segs) < 2:
            messagebox.showwarning("Veri Yok", "En az 2 segment (2×5 cm) gerekli.")
            return

        if self.detrend_velocity.get() and len(segs) >= 3:
            segs = detrend_segment_velocities(segs)

        cum_dists_cm = [seg['cum_dist_mm'] / 10.0 for seg in segs]
        vels         = [seg['v_mm_s'] for seg in segs]
        t_mids       = [(seg['t_start'] + seg['t_end']) / 2.0 for seg in segs]

        fig, axes = plt.subplots(2, 1, figsize=(10, 7), facecolor='#1a1a2e')
        for ax in axes:
            ax.set_facecolor('#0d0d1a')
            ax.tick_params(colors='#8892a4')
            for sp in ['bottom', 'left']:
                ax.spines[sp].set_color('#8892a4')
            for sp in ['top', 'right']:
                ax.spines[sp].set_visible(False)

        axes[0].plot(cum_dists_cm, vels, 'o-', color='#4ecca3', lw=2, ms=6,
                     label='Segment Ort. Hız')
        vt, _ = detect_terminal_velocity(
            np.array(t_mids), np.array(vels), min_stable_points=3)
        if vt:
            axes[0].axhline(vt, color='#e94560', ls='--', lw=1.5,
                            label=f'Terminal: {vt:.1f} mm/s')
        axes[0].set_xlabel('Mesafe (cm)', color='#8892a4')
        axes[0].set_ylabel('Hız (mm/s)', color='#8892a4')
        axes[0].set_title('Hız – Mesafe  (1 cm Segmentler)', color='#eaeaea')
        axes[0].legend(facecolor='#16213e', labelcolor='#eaeaea')
        axes[0].grid(alpha=0.2, color='#8892a4')

        pm = max(self.calibrator.px_per_mm, 1e-6)
        xs = [p[0] / pm for p in s['positions']]
        ys = [p[1] / pm for p in s['positions']]
        sc = axes[1].scatter(xs, ys, c=s['timestamps'], cmap='plasma', s=10)
        axes[1].set_xlabel('X (mm)', color='#8892a4')
        axes[1].set_ylabel('Y (mm)', color='#8892a4')
        axes[1].set_title('Cisim Yörüngesi', color='#eaeaea')
        axes[1].invert_yaxis()
        cb = fig.colorbar(sc, ax=axes[1])
        cb.ax.tick_params(colors='#8892a4')
        cb.set_label('Zaman (s)', color='#8892a4')
        plt.tight_layout()

        import io
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, facecolor=fig.get_facecolor())
        plt.close(fig)
        buf.seek(0)
        img = Image.open(buf)
        ph  = ImageTk.PhotoImage(img)

        pw = tk.Toplevel(self.root)
        pw.title("Analiz Grafikleri")
        pw.configure(bg=DARK_BG)
        lbl = tk.Label(pw, image=ph, bg=DARK_BG)
        lbl.image = ph
        lbl.pack(padx=10, pady=10)
