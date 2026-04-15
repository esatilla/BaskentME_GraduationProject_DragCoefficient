"""
ui/widget_helpers.py — Yeniden kullanılabilir Tkinter widget fabrika metodları (mixin)
"""

import tkinter as tk
from ui.theme import (PANEL_BG, ACCENT, HIGHLIGHT, TEXT_LIGHT, TEXT_DIM,
                      WARNING, DARK_BG, FONT_LABEL, FONT_HEAD, FONT_MONO)


class WidgetHelpersMixin:

    def _sec(self, p, title):
        """Başlık çubuğu bölümü."""
        f = tk.Frame(p, bg=ACCENT, height=26)
        f.pack(fill="x", pady=(8, 2))
        tk.Label(f, text=title, bg=ACCENT, fg=TEXT_LIGHT,
                 font=FONT_HEAD).pack(side="left", padx=10, pady=4)

    def _btn(self, p, text, cmd, bg=None):
        """Tam genişlik düğme."""
        bg = bg or ACCENT
        tk.Button(
            p, text=text, command=cmd, font=FONT_LABEL,
            bg=bg, fg="white" if bg != WARNING else DARK_BG,
            relief="flat", activebackground=HIGHLIGHT, cursor="hand2"
        ).pack(fill="x", padx=8, pady=2)

    def _bsm(self, p, text, cmd):
        """Küçük yan düğme."""
        tk.Button(
            p, text=text, command=cmd, font=("Segoe UI", 8),
            bg=ACCENT, fg=TEXT_LIGHT, relief="flat", cursor="hand2"
        ).pack(side="left", padx=3, pady=2)

    def _ent(self, p, label, var):
        """Etiket + giriş alanı satırı."""
        row = tk.Frame(p, bg=PANEL_BG)
        row.pack(fill="x", padx=8, pady=2)
        tk.Label(row, text=label, bg=PANEL_BG, fg=TEXT_DIM,
                 font=FONT_LABEL, width=22, anchor="w").pack(side="left")
        tk.Entry(row, textvariable=var, width=10, bg="#0d0d1a",
                 fg=TEXT_LIGHT, font=FONT_MONO, relief="flat",
                 insertbackground=TEXT_LIGHT).pack(side="right")

    def _slider(self, p, label, var, lo, hi, cmd):
        """Etiket + kaydırıcı satırı."""
        row = tk.Frame(p, bg=PANEL_BG)
        row.pack(fill="x", padx=5, pady=2)
        tk.Label(row, text=label, bg=PANEL_BG, fg=TEXT_DIM,
                 font=FONT_LABEL, width=16, anchor="w").pack(side="left")
        tk.Scale(
            row, variable=var, from_=lo, to=hi, orient="horizontal",
            bg=PANEL_BG, fg=TEXT_LIGHT, troughcolor=ACCENT,
            highlightthickness=0, command=cmd,
            font=("Segoe UI", 7), length=120
        ).pack(side="right")
