# ui.py
from __future__ import annotations

import os
import sys
import math
import threading
import tkinter as tk
import random

# --- Pillow (images UI) ---
try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None

from tkinter import ttk, filedialog, messagebox
from tkinter import font as tkfont

import numpy as np
import sounddevice as sd

from presets import Params, save_preset, load_preset
from audio_io import load_audio, export_wav, get_ffmpeg_status_short
from engine import render

APP_NAME = "Warpocalypse"
APP_VERSION = "1.1.8"

APP_TITLE = f"{APP_NAME} v{APP_VERSION}"
DEFAULT_GEOMETRY = "1000x740"

# --- Bibli de thèmes (issus de Garage) ---
THEMES = {
    # ===== Thèmes sombres (sobres / quotidiens) =====
    "[Sombre] Midnight Garage": dict(
        BG="#151515", PANEL="#1F1F1F", FIELD="#2A2A2A",
        FG="#EAEAEA", FIELD_FG="#F0F0F0", ACCENT="#FF9800"
    ),
    "[Sombre] AIR-KLM Night flight": dict(
        BG="#0B1E2D", PANEL="#102A3D", FIELD="#16384F",
        FG="#EAF6FF", FIELD_FG="#FFFFFF", ACCENT="#00A1DE"
    ),
    "[Sombre] Café Serré": dict(
        BG="#1B120C", PANEL="#2A1C14", FIELD="#3A281D",
        FG="#F2E6D8", FIELD_FG="#FFF4E6", ACCENT="#C28E5C"
    ),
    "[Sombre] Matrix Déjà Vu": dict(
        BG="#000A00", PANEL="#001F00", FIELD="#003300",
        FG="#00FF66", FIELD_FG="#66FF99", ACCENT="#00FF00"
    ),
    "[Sombre] Miami Vice 1987": dict(
        BG="#14002E", PANEL="#2B0057", FIELD="#004D4D",
        FG="#FFF0FF", FIELD_FG="#FFFFFF", ACCENT="#00FFD5"
    ),
    "[Sombre] Cyber Licorne": dict(
        BG="#1A0026", PANEL="#2E004F", FIELD="#3D0066",
        FG="#F6E7FF", FIELD_FG="#FFFFFF", ACCENT="#FF2CF7"
    ),
    # ===== Thèmes clairs =====
    "[Clair] AIR-KLM Day flight": dict(
        BG="#EAF6FF", PANEL="#D6EEF9", FIELD="#FFFFFF",
        FG="#0B2A3F", FIELD_FG="#0B2A3F", ACCENT="#00A1DE"
    ),
    "[Clair] Matin Brumeux": dict(
        BG="#E6E7E8", PANEL="#D4D7DB", FIELD="#FFFFFF",
        FG="#1E1F22", FIELD_FG="#1E1F22", ACCENT="#6B7C93"
    ),
    "[Clair] Latte Vanille": dict(
        BG="#FAF6F1", PANEL="#EFE6DC", FIELD="#FFFFFF",
        FG="#3D2E22", FIELD_FG="#3D2E22", ACCENT="#D8B892"
    ),
    "[Clair] Miellerie La Divette": dict(
        BG="#E6B65C", PANEL="#F5E6CC", FIELD="#FFFFFF",
        FG="#50371A", FIELD_FG="#50371A", ACCENT="#F2B705"
    ),
    # ===== Thèmes Pouêt-Pouêt =====
    "[Pouêt] Chewing-gum Océan": dict(
        BG="#00A6C8", PANEL="#0083A1", FIELD="#00C7B7",
        FG="#082026", FIELD_FG="#082026", ACCENT="#FF4FD8"
    ),
    "[Pouêt] Pamplemousse": dict(
        BG="#FF4A1C", PANEL="#E63B10", FIELD="#FF7A00",
        FG="#1A0B00", FIELD_FG="#1A0B00", ACCENT="#00E5FF"
    ),
    "[Pouêt] Raisin Toxique": dict(
        BG="#7A00FF", PANEL="#5B00C9", FIELD="#B000FF",
        FG="#0F001A", FIELD_FG="#0F001A", ACCENT="#39FF14"
    ),
    "[Pouêt] Citron qui pique": dict(
        BG="#FFF200", PANEL="#E6D800", FIELD="#FFF7A6",
        FG="#1A1A00", FIELD_FG="#1A1A00", ACCENT="#0066FF"
    ),
    "[Pouêt] Barbie Apocalypse": dict(
        BG="#FF1493", PANEL="#004D40", FIELD="#1B5E20",
        FG="#E8FFF8", FIELD_FG="#FFFFFF", ACCENT="#FFEB3B"
    ),
    "[Pouêt] Compagnie Créole": dict(
        BG="#8B3A1A", PANEL="#F2C94C", FIELD="#FFFFFF",
        FG="#5A2E0C", FIELD_FG="#5A2E0C", ACCENT="#8B3A1A"
    ),
}

WARP_STRETCH_SPAN_MAX = 0.60   # 0..1 -> 1±span
WARP_PITCH_RANGE_MAX_ST = 12.0 # demi-tons


# ---------------- UI widgets ----------------

class RotaryKnobCanvas(tk.Canvas):
    """Cadran rotatif (dial + graduation + aiguille) sur Canvas.
    Le label et la valeur sont gérés par un widget conteneur (RotaryKnob).
    """
    def __init__(
        self,
        parent: tk.Misc,
        var: tk.Variable,
        from_: float,
        to: float,
        step: float = 0.01,
        size: int = 78,
        theme: dict[str, str] | None = None,
    ) -> None:
        # ttk.Frame ne supporte pas forcément -background (TclError). On récupère un fond cohérent.
        try:
            _bg = parent.cget("background")
        except tk.TclError:
            _bg = ""
            try:
                style = ttk.Style()
                _bg = style.lookup(parent.winfo_class(), "background") or style.lookup("TFrame", "background")
            except Exception:
                _bg = ""
            if not _bg:
                try:
                    _bg = parent.winfo_toplevel().cget("bg")
                except Exception:
                    _bg = "black"

        self._theme = theme or {}
        panel_bg = (theme.get("PANEL") if theme else _bg)

        super().__init__(
            parent,
            width=size,
            height=size,
            highlightthickness=0,
            bg=panel_bg,
        )

        self._var = var
        self._from = float(from_)
        self._to = float(to)
        self._step = float(step)
        self._size = int(size)
        self._r = (self._size // 2) - 6
        self._cx = self._size // 2
        self._cy = self._size // 2

        self._col_bg = self._theme.get("PANEL", self.cget("bg"))
        self._col_dial = self._theme.get("FIELD", "#202020")
        self._col_outline = self._theme.get("FG", "#888888")
        self._col_accent = self._theme.get("ACCENT", "#9BE7A2")

        self._drag_y: int | None = None
        self._drag_start_val: float = float(self._get_value())

        self._needle_id = None

        self._draw_static()
        self._redraw_dynamic()

        # Interactions
        self.bind("<Button-1>", self._on_down)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_up)

        # Molette (Windows/macOS) + Linux (Button-4/5)
        self.bind("<MouseWheel>", self._on_wheel)
        self.bind("<Button-4>", lambda _e: self._nudge(+self._step))
        self.bind("<Button-5>", lambda _e: self._nudge(-self._step))

        # Update quand la variable change
        try:
            self._var.trace_add("write", lambda *_: self._redraw_dynamic())
        except Exception:
            pass

    def set_theme(self, theme: dict[str, str] | None) -> None:
        self._theme = theme or {}
        self._col_bg = self._theme.get("PANEL", self.cget("bg"))
        self._col_dial = self._theme.get("FIELD", "#202020")
        self._col_outline = self._theme.get("FG", "#888888")
        self._col_accent = self._theme.get("ACCENT", "#9BE7A2")
        try:
            self.configure(bg=self._theme.get("PANEL", self.cget("bg")))
        except Exception:
            pass
        self._draw_static()
        self._redraw_dynamic()

    def _draw_static(self) -> None:
        self.delete("all")

        # Dial (cercle)
        self.create_oval(
            self._cx - self._r,
            self._cy - self._r,
            self._cx + self._r,
            self._cy + self._r,
            outline=self._col_outline,
            width=2,
            fill=self._col_dial,
        )

        # Graduation (petits traits) -135° -> +135°
        n_ticks = 11
        for i in range(n_ticks):
            t = i / (n_ticks - 1) if n_ticks > 1 else 0.0
            ang = math.radians(-135.0 + 270.0 * t)
            r1 = self._r - 2
            r2 = self._r - 10
            x1 = self._cx + int(math.cos(ang) * r1)
            y1 = self._cy + int(math.sin(ang) * r1)
            x2 = self._cx + int(math.cos(ang) * r2)
            y2 = self._cy + int(math.sin(ang) * r2)
            self.create_line(x1, y1, x2, y2, fill=self._col_outline, width=2, capstyle="round")

    def _get_value(self) -> float:
        try:
            return float(self._var.get())
        except Exception:
            return float(self._from)

    def _set_value(self, v: float) -> None:
        v = float(np.clip(v, self._from, self._to))
        if self._step > 0:
            v = round(v / self._step) * self._step
        if abs(v) < 1e-12:
            v = 0.0
        self._var.set(v)

    def _value_to_angle(self, v: float) -> float:
        t = 0.0
        if self._to != self._from:
            t = (v - self._from) / (self._to - self._from)
        t = float(np.clip(t, 0.0, 1.0))
        return (-135.0 + 270.0 * t)

    def _redraw_dynamic(self) -> None:
        v = float(self._get_value())
        angle = np.deg2rad(self._value_to_angle(v))
        x2 = self._cx + int(np.cos(angle) * (self._r - 8))
        y2 = self._cy + int(np.sin(angle) * (self._r - 8))

        if self._needle_id is not None:
            self.delete(self._needle_id)
        self._needle_id = self.create_line(
            self._cx, self._cy, x2, y2,
            fill=self._col_accent, width=3, capstyle="round"
        )

    def _on_down(self, e: tk.Event) -> None:
        self._drag_y = int(e.y)
        self._drag_start_val = float(self._get_value())

    def _on_drag(self, e: tk.Event) -> None:
        if self._drag_y is None:
            return
        dy = int(self._drag_y) - int(e.y)
        span = (self._to - self._from)
        if span <= 0:
            return
        delta = (dy / 120.0) * span
        self._set_value(self._drag_start_val + delta)

    def _on_up(self, _e: tk.Event) -> None:
        self._drag_y = None

    def _nudge(self, delta: float) -> None:
        self._set_value(float(self._get_value()) + float(delta))

    def _on_wheel(self, e: tk.Event) -> None:
        d = float(getattr(e, "delta", 0.0))
        if d == 0.0:
            return
        self._nudge(self._step if d > 0 else -self._step)


class RotaryKnob(ttk.Frame):
    """Potard complet: Canvas + label + valeur (TTK labels).
    Avantage: plus de clipping de texte car les labels ne sont plus dans le Canvas.
    """
    def __init__(
        self,
        parent: tk.Misc,
        label: str,
        var: tk.Variable,
        from_: float,
        to: float,
        step: float = 0.01,
        size: int = 78,
        theme: dict[str, str] | None = None,
    ) -> None:
        super().__init__(parent, style="Panel.TFrame")
        self._label_text = label
        self._var = var
        self._theme = theme or {}

        self.canvas = RotaryKnobCanvas(self, var, from_, to, step=step, size=size, theme=theme)
        self.canvas.grid(row=0, column=0, sticky="n", padx=2, pady=(0, 0))

        self.lbl_name = ttk.Label(self, text=label, style="Panel.TLabel")
        self.lbl_name.grid(row=1, column=0, sticky="n", pady=(2, 0))

        self.lbl_value = ttk.Label(self, text="", style="Panel.TLabel")
        self.lbl_value.grid(row=2, column=0, sticky="n", pady=(0, 0))

        self.columnconfigure(0, weight=1)

        self._update_value_text()

        try:
            self._var.trace_add("write", lambda *_: self._update_value_text())
        except Exception:
            pass

    def _update_value_text(self) -> None:
        try:
            v = float(self._var.get())
        except Exception:
            v = 0.0
        self.lbl_value.configure(text=f"{v:.2f}")

    def set_theme(self, theme: dict[str, str] | None) -> None:
        self._theme = theme or {}
        try:
            self.configure(style="Panel.TFrame")
        except Exception:
            pass
        self.canvas.set_theme(theme)
        # Les labels sont stylés via ttk.Style; ici on ne force rien.


# ---------------- Application ----------------

class WarpocalypseApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.geometry(DEFAULT_GEOMETRY)
        try:
            self.root.minsize(980, 680)
        except Exception:
            pass

        # Style / Thèmes
        self._style = ttk.Style()
        try:
            self._style.theme_use("clam")
        except Exception:
            pass

        self.var_theme = tk.StringVar()
        self.theme: dict[str, str] = {}
        self._choose_random_theme()

        self.params = Params()

        # Widgets dépendants du thème
        self._knob_widgets: list[RotaryKnob] = []
        self._col_accent = self.theme.get("ACCENT", "#9BE7A2")

        # Audio
        self.src_path: str | None = None
        self.src_audio: np.ndarray | None = None
        self.src_sr: int | None = None

        self.out_audio: np.ndarray | None = None
        self.out_sr: int | None = None
        self.out_segments: int = 0

        self._play_lock = threading.Lock()
        self._is_playing = False
        # Anti-segfault PortAudio: arrêt demandé via Event, stop exécuté dans le thread audio
        self._stop_request = threading.Event()
        self._play_thread: threading.Thread | None = None

        # --- AIDE overlay (affiché au démarrage) ---
        self.var_show_help = tk.BooleanVar(value=True)
        self._help_text_widget: tk.Text | None = None
        self._help_content: str | None = None

        # Splash image (warpocalypse.png)
        self._splash_label: tk.Label | None = None
        self._splash_image: object | None = None

        # Mode Loop (toggle)
        self.var_loop_mode = tk.BooleanVar(value=False)

        # Loop selection (sur waveform) : fractions [0..1]
        self._loop_start_frac: float = 0.0
        self._loop_end_frac: float = 1.0
        self._loop_drag: str | None = None  # "start" | "end" | None
        self._loop_pad_px: int = 10  # distance de saisie des poignées

        self.chk_loop_mode: ttk.Checkbutton | None = None

        self._build_ui()
        self.lbl_ffmpeg.configure(text=get_ffmpeg_status_short())
        self._load_splash_image()
        self._apply_splash_layer()
        self._render_help_overlay()
        self._update_help_visibility()
    def _choose_random_theme(self) -> None:
        names = list(THEMES.keys())
        if not names:
            self.var_theme.set("")
            self.theme = {}
            return
        name = random.choice(names)
        self.var_theme.set(name)
        self._apply_theme(name)

    def _apply_theme(self, name: str) -> None:
        theme = THEMES.get(name) or {}
        self.theme = theme

        bg = theme.get("BG", "#101010")
        panel = theme.get("PANEL", "#1A1A1A")
        field = theme.get("FIELD", "#222222")
        fg = theme.get("FG", "#EAEAEA")
        field_fg = theme.get("FIELD_FG", fg)
        accent = theme.get("ACCENT", "#00A1DE")
        self._col_accent = accent

        # Tk background (root)
        try:
            self.root.configure(bg=bg)
        except Exception:
            pass

        # TTK styles
        s = self._style
        s.configure(".", background=bg, foreground=fg)
        s.configure("TFrame", background=bg)
        s.configure("Panel.TFrame", background=panel)

        s.configure("TLabel", background=bg, foreground=fg)
        s.configure("Panel.TLabel", background=panel, foreground=fg)

        s.configure("Panel.TCheckbutton", background=panel, foreground=fg)
        s.map(
            "Panel.TCheckbutton",
            background=[("active", panel)],
            foreground=[("disabled", "#777777")],
        )

        s.configure("TButton", background=panel, foreground=fg)
        s.map("TButton",
              background=[("active", field), ("pressed", field)],
              foreground=[("disabled", "#777777")])

        s.configure("TScale", background=panel)
        s.configure("Horizontal.TScale", background=panel)

        s.configure("TEntry", fieldbackground=field, foreground=field_fg)
        s.configure("TCombobox", fieldbackground=field, foreground=field_fg, background=panel)
        s.map("TCombobox",
              fieldbackground=[("readonly", field)],
              foreground=[("readonly", field_fg)])

        s.configure("TSpinbox", fieldbackground=field, foreground=field_fg, background=panel)
        s.configure("TSeparator", background=bg)

        # Widgets Tk (waveform canvas)
        if hasattr(self, "canvas"):
            try:
                self.canvas.configure(bg=field)
            except Exception:
                pass
            try:
                self._redraw_waveform()
            except Exception:
                pass

        # Potards
        for k in getattr(self, "_knob_widgets", []):
            try:
                k.set_theme(theme)
            except Exception:
                pass

        # Aide: s'assurer que l'overlay est au bon niveau
        try:
            self._update_help_visibility()
        except Exception:
            pass

    def _on_theme_change(self, _e: object = None) -> None:
        name = str(self.var_theme.get())
        if name in THEMES:
            self._apply_theme(name)

    def run(self) -> None:
        self.root.mainloop()

    # ---------------- UI ----------------

    def _build_ui(self) -> None:
        # Topbar: thème + (petit) transport
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        topbar = ttk.Frame(self.root, padding=(10, 6), style="Panel.TFrame")
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.columnconfigure(0, weight=1)

        # Statut ffmpeg/ffprobe à gauche (compact)
        frm_diag = ttk.Frame(topbar, style="Panel.TFrame")
        frm_diag.grid(row=0, column=0, sticky="w")

        self.lbl_ffmpeg = ttk.Label(
            frm_diag,
            text=get_ffmpeg_status_short(),
            style="Panel.TLabel",
        )
        self.lbl_ffmpeg.grid(row=0, column=0, sticky="w")



        # Thème à droite
        frm_theme = ttk.Frame(topbar, style="Panel.TFrame")
        frm_theme.grid(row=0, column=1, sticky="e")
        ttk.Label(frm_theme, text="Thème :", style="Panel.TLabel").grid(row=0, column=0, sticky="e", padx=(0, 6))
        self.cmb_theme = ttk.Combobox(
            frm_theme,
            values=list(THEMES.keys()),
            textvariable=self.var_theme,
            state="readonly",
            width=28,
        )
        self.cmb_theme.grid(row=0, column=1, sticky="e")
        self.cmb_theme.bind("<<ComboboxSelected>>", self._on_theme_change)

        # PanedWindow: gauche (contrôles) / droite (signal)
        pw = ttk.Panedwindow(self.root, orient="horizontal")
        pw.grid(row=1, column=0, sticky="nsew")

        left = ttk.Frame(pw, padding=10, style="Panel.TFrame")
        right = ttk.Frame(pw, padding=10, style="Panel.TFrame")
        pw.add(left, weight=0)
        pw.add(right, weight=1)

        # --- LEFT (compact, sans couper les boutons) ---
        left.columnconfigure(0, weight=1)

        # (Titre "Fichier" supprimé)
        ttk.Button(left, text="Chargez un fichier audio", command=self._on_load).grid(row=1, column=0, sticky="ew", pady=(6, 0))

        self.lbl_file = ttk.Label(left, text="Aucun fichier chargé.", wraplength=260, style="Panel.TLabel")
        self.lbl_file.grid(row=2, column=0, sticky="w", pady=(6, 10))

        ttk.Separator(left).grid(row=3, column=0, sticky="ew", pady=8)

        # (Titre "Preset" supprimé)
        row_preset = ttk.Frame(left, style="Panel.TFrame")
        row_preset.grid(row=5, column=0, sticky="ew", pady=(6, 0))
        row_preset.columnconfigure(0, weight=1)
        row_preset.columnconfigure(1, weight=1)
        ttk.Button(row_preset, text="Charger…", command=self._on_load_preset).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(row_preset, text="Sauver…", command=self._on_save_preset).grid(row=0, column=1, sticky="ew")

        ttk.Separator(left).grid(row=6, column=0, sticky="ew", pady=8)

        ttk.Label(left, text="Paramètres", style="Panel.TLabel").grid(row=7, column=0, sticky="w")

        self.var_seed = tk.IntVar(value=self.params.seed)
        self._add_spin(left, "Seed", self.var_seed, 0, 2_000_000_000, row=8)

        self.var_grain_min = tk.IntVar(value=self.params.grain_ms_min)
        self.var_grain_max = tk.IntVar(value=self.params.grain_ms_max)
        self._add_spin(left, "Grain min (ms)", self.var_grain_min, 10, 5000, row=9)
        self._add_spin(left, "Grain max (ms)", self.var_grain_max, 10, 5000, row=10)

        self.var_shuffle = tk.DoubleVar(value=self.params.shuffle_amount)
        self._add_scale(left, "Shuffle", self.var_shuffle, 0.0, 1.0, row=11)

        self.var_keep = tk.DoubleVar(value=self.params.keep_original_ratio)
        self._add_scale(left, "Garder original", self.var_keep, 0.0, 1.0, row=12)

        self.var_rev = tk.DoubleVar(value=self.params.reverse_prob)
        self._add_scale(left, "Reverse prob", self.var_rev, 0.0, 1.0, row=13)

        self.var_gain_min = tk.DoubleVar(value=self.params.gain_db_min)
        self.var_gain_max = tk.DoubleVar(value=self.params.gain_db_max)
        self._add_spin_float(left, "Gain min (dB)", self.var_gain_min, -60.0, 60.0, row=14)
        self._add_spin_float(left, "Gain max (dB)", self.var_gain_max, -60.0, 60.0, row=15)

        self.var_intensity = tk.DoubleVar(value=self.params.intensity)
        self._add_scale(left, "Intensité", self.var_intensity, 0.0, 2.0, row=16)

        ttk.Separator(left).grid(row=17, column=0, sticky="ew", pady=8)

        # Actions en bas à gauche (compact)
        act = ttk.Frame(left, style="Panel.TFrame")
        act.grid(row=18, column=0, sticky="ew")
        act.columnconfigure(0, weight=1)
        act.columnconfigure(1, weight=1)

        ttk.Button(act, text="Randomize", command=self._on_randomize_seed).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.btn_render = ttk.Button(act, text="Rendre", command=self._on_render)
        self.btn_render.grid(row=0, column=1, sticky="ew")

        act2 = ttk.Frame(left, style="Panel.TFrame")
        act2.grid(row=19, column=0, sticky="ew", pady=(6, 0))
        act2.columnconfigure(0, weight=1)
        act2.columnconfigure(1, weight=1)
        ttk.Button(act2, text="Preview", command=self._on_preview).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(act2, text="Stop", command=self._on_stop).grid(row=0, column=1, sticky="ew")        # Mode Loop (case à cocher) - même largeur que Export
        self.chk_loop_mode = ttk.Checkbutton(
            left,
            text="Mode Loop",
            variable=self.var_loop_mode,
            command=self._on_loop_mode_changed,
            style="Panel.TCheckbutton",
        )
        self.chk_loop_mode.grid(row=20, column=0, sticky="ew", pady=(8, 0))

        ttk.Button(left, text="Exporter fichier entier…", command=self._on_export).grid(row=21, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(left, text="Exporter loop…", command=self._on_export_loop).grid(row=22, column=0, sticky="ew", pady=(6, 0))


        # --- RIGHT (waveform + potards + infos) ---
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        # Ligne "info" + toggle aide (en haut à droite)
        row_info = ttk.Frame(right, style="Panel.TFrame")
        row_info.grid(row=0, column=0, sticky="ew")
        row_info.columnconfigure(0, weight=1)

        self.lbl_info = ttk.Label(row_info, text="", wraplength=740, style="Panel.TLabel")
        self.lbl_info.grid(row=0, column=0, sticky="w")

        help_controls = ttk.Frame(row_info, style="Panel.TFrame")
        help_controls.grid(row=0, column=1, sticky="e")

        # Case cochée par défaut + "?" à côté
        chk_help = ttk.Checkbutton(
            help_controls,
            variable=self.var_show_help,
            command=self._update_help_visibility,
        )
        chk_help.grid(row=0, column=0, padx=(0, 4))
        ttk.Label(help_controls, text="?", style="Panel.TLabel").grid(row=0, column=1)

        # Conteneur waveform + overlay aide
        wave_container = ttk.Frame(right, style="Panel.TFrame")
        wave_container.grid(row=1, column=0, sticky="nsew", pady=(10, 10))
        wave_container.columnconfigure(0, weight=1)
        wave_container.rowconfigure(0, weight=1)

        # Waveform (hauteur divisée par 2 : 280 -> 140)
        self.canvas = tk.Canvas(
            wave_container,
            height=140,
            bg=self.theme.get("FIELD", "black"),
            highlightthickness=0,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", lambda _e: self._redraw_waveform())

        self.canvas.bind("<Button-1>", self._on_canvas_down)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_up)

        # Splash (warpocalypse.png) : couche au-dessus de la waveform
        self._splash_label = tk.Label(
            wave_container,
            bg=self.theme.get("FIELD", "black"),
            borderwidth=0,
            highlightthickness=0,
        )
        self._splash_label.grid(row=0, column=0, sticky="nsew")

        # Overlay AIDE (fond noir, texte blanc, police 14)
        self._help_text_widget = tk.Text(
            wave_container,
            wrap="word",
            bg="black",
            fg="white",
            insertbackground="white",
            borderwidth=0,
            highlightthickness=0,
        )
        self._help_text_widget.grid(row=0, column=0, sticky="nsew")

        help_font = tkfont.Font(family="Helvetica", size=14)
        self._help_text_widget.configure(font=help_font)
        self._help_text_widget.configure(state="disabled")

        # Charger assets/AIDE.md (lecture ici, rendu via _render_help_overlay)
        help_path = os.path.join(self._assets_dir(), "AIDE.md")
        content: str | None = None
        if os.path.isfile(help_path):
            try:
                with open(help_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                content = None

        self._help_content = content



        # Rendu initial de l'aide (texte centré + image si dispo)
        try:
            self._render_help_overlay()
        except Exception:
            pass
        # Potards (dans une barre dédiée, toujours visible)
        knobs_bar = ttk.Frame(right, style="Panel.TFrame")
        knobs_bar.grid(row=2, column=0, sticky="ew")
        for c in range(4):
            knobs_bar.columnconfigure(c, weight=1, uniform="knobs")

        # Variables UI Warp (4 potards)
        self.var_warp_amount = tk.DoubleVar(value=float(self.params.warp_amount))
        self.var_warp_stretch_range = tk.DoubleVar(value=0.0)  # 0..1 -> 1±span
        self.var_warp_pitch_range = tk.DoubleVar(value=0.0)    # 0..12 st
        self.var_warp_prob = tk.DoubleVar(value=float((self.params.warp_stretch_prob + self.params.warp_pitch_prob) / 2.0))

        self._push_warp_ranges_to_ui()

        k_warp = RotaryKnob(knobs_bar, "Warp", self.var_warp_amount, 0.0, 1.0, step=0.01, theme=self.theme)
        k_warp.grid(row=0, column=0, sticky="n", padx=8)
        self._knob_widgets.append(k_warp)

        k_stretch = RotaryKnob(knobs_bar, "Stretch", self.var_warp_stretch_range, 0.0, 1.0, step=0.01, theme=self.theme)
        k_stretch.grid(row=0, column=1, sticky="n", padx=8)
        self._knob_widgets.append(k_stretch)

        k_pitch = RotaryKnob(knobs_bar, "Pitch", self.var_warp_pitch_range, 0.0, WARP_PITCH_RANGE_MAX_ST, step=0.25, theme=self.theme)
        k_pitch.grid(row=0, column=2, sticky="n", padx=8)
        self._knob_widgets.append(k_pitch)

        k_prob = RotaryKnob(knobs_bar, "Prob", self.var_warp_prob, 0.0, 1.0, step=0.01, theme=self.theme)
        k_prob.grid(row=0, column=3, sticky="n", padx=8)
        self._knob_widgets.append(k_prob)

        # Applique le thème courant
        self._apply_theme(str(self.var_theme.get()))
        # Afficher l'aide au démarrage (checkbox cochée par défaut)
        self._update_help_visibility()

    def _assets_dir(self) -> str:
        """Retourne le dossier assets/ en dev ET en build (PyInstaller/AppImage/tar.gz)."""
        candidates: list[str] = []

        # 1) PyInstaller (onefile) : extraction temporaire
        meipass = getattr(sys, "_MEIPASS", None)
        if isinstance(meipass, str) and meipass:
            candidates.append(os.path.join(meipass, "assets"))

        # 2) À côté de l'exécutable (PyInstaller onedir / AppImage)
        try:
            exe_dir = os.path.dirname(os.path.abspath(sys.executable))
            candidates.append(os.path.join(exe_dir, "assets"))
        except Exception:
            pass

        # 3) À côté du fichier ui.py (dev ou bundle onedir)
        candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets"))

        for p in candidates:
            if os.path.isdir(p):
                return p

        # Fallback (chemin attendu en dev)
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


    def _load_splash_image(self) -> None:
        """Charge assets/warpocalypse.png via Pillow (si disponible)."""
        self._splash_image = None
        if Image is None or ImageTk is None:
            return

        splash_path = os.path.join(self._assets_dir(), "warpocalypse.png")
        if not os.path.isfile(splash_path):
            return

        try:
            img = Image.open(splash_path).convert("RGBA")
            max_w = 640
            w, h = img.size
            if w > max_w and w > 0:
                ratio = max_w / float(w)
                img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
            self._splash_image = ImageTk.PhotoImage(img)
        except Exception:
            self._splash_image = None

    def _apply_splash_layer(self) -> None:
        """Applique la splash au label (si présent)."""
        if self._splash_label is None or self._splash_image is None:
            return
        try:
            self._splash_label.configure(image=self._splash_image)
            self._splash_label.image = self._splash_image
        except Exception:
            pass

    def _render_help_overlay(self) -> None:
        """Met à jour le contenu de l'aide (image + texte centré)."""
        if self._help_text_widget is None:
            return

        content = self._help_content
        if not content:
            content = (
                "AIDE.md introuvable.\n\n"
                "Créer le fichier : assets/AIDE.md\n"
                "Puis relancer l'application.\n"
            )

        try:
            self._help_text_widget.configure(state="normal")
            self._help_text_widget.delete("1.0", "end")

            if self._splash_image is not None:
                try:
                    self._help_text_widget.image_create("end", image=self._splash_image)
                    self._help_text_widget._header_image = self._splash_image
                    self._help_text_widget.insert("end", "\n\n")
                except Exception:
                    pass

            self._help_text_widget.insert("end", content)
            self._help_text_widget.tag_configure("center", justify="center")
            self._help_text_widget.tag_add("center", "1.0", "end")
            self._help_text_widget.configure(state="disabled")
        except Exception:
            try:
                self._help_text_widget.configure(state="disabled")
            except Exception:
                pass

    def _update_help_visibility(self) -> None:
        """Gère les couches : aide / splash / waveform.

        - Si l'aide est cochée : l'overlay d'aide passe au-dessus.
        - Si l'aide est décochée :
            - s'il n'y a PAS d'audio chargé : on montre la splash (warpocalypse.png)
            - s'il y a un audio : on montre la waveform (la splash passe en dessous)
        """
        if self._help_text_widget is None:
            return

        show_help = bool(self.var_show_help.get())

        if show_help:
            try:
                self._help_text_widget.lift()
            except Exception:
                pass
            return

        # Aide masquée
        try:
            self._help_text_widget.lower()
        except Exception:
            pass

        has_audio = (self.src_audio is not None) or (self.out_audio is not None)

        # Quand un audio est chargé, la waveform doit être visible (splash en dessous).
        if self._splash_label is not None:
            try:
                if has_audio:
                    self._splash_label.lower()
                else:
                    self._splash_label.lift()
            except Exception:
                pass
    # ---------------- Mode Loop ----------------

    def _on_loop_mode_changed(self) -> None:
        """Callback du mode loop (case à cocher)."""
        if bool(self.var_loop_mode.get()):
            try:
                self._ensure_default_loop()
            except Exception:
                pass
        self._redraw_waveform()
        self._log(f"Mode Loop -> {bool(self.var_loop_mode.get())}")



    def _loop_has_audio(self) -> bool:
        return (self.src_audio is not None and self.src_sr is not None) or (self.out_audio is not None and self.out_sr is not None)

    def _loop_has_valid_selection(self) -> bool:
        if not self._loop_has_audio():
            return False
        if self._loop_end_frac <= self._loop_start_frac:
            return False
        # durée mini ~80 ms
        audio, sr = self._get_preview_buffer(raw=True)
        if audio is None or sr is None or len(audio) == 0:
            return False
        dur = len(audio) / float(sr)
        seg = (self._loop_end_frac - self._loop_start_frac) * dur
        return seg >= 0.08

    def _loop_frac_from_x(self, x: int) -> float:
        w = max(1, int(self.canvas.winfo_width()))
        return float(max(0.0, min(1.0, float(x) / float(w))))

    def _loop_x_from_frac(self, f: float) -> int:
        w = max(1, int(self.canvas.winfo_width()))
        return int(max(0.0, min(1.0, float(f))) * w)

    def _on_canvas_down(self, e: tk.Event) -> None:
        if not bool(self.var_loop_mode.get()):
            return
        if not self._loop_has_audio():
            return

        x = int(getattr(e, "x", 0))
        xs = self._loop_x_from_frac(self._loop_start_frac)
        xe = self._loop_x_from_frac(self._loop_end_frac)

        if abs(x - xs) <= self._loop_pad_px:
            self._loop_drag = "start"
        elif abs(x - xe) <= self._loop_pad_px:
            self._loop_drag = "end"
        else:
            # prendre la poignée la plus proche
            self._loop_drag = "start" if abs(x - xs) <= abs(x - xe) else "end"

        self._on_canvas_drag(e)

    def _on_canvas_drag(self, e: tk.Event) -> None:
        if not bool(self.var_loop_mode.get()):
            return
        if self._loop_drag not in ("start", "end"):
            return
        if not self._loop_has_audio():
            return

        f = self._loop_frac_from_x(int(getattr(e, "x", 0)))
        min_gap = 0.002  # évite start==end

        if self._loop_drag == "start":
            self._loop_start_frac = float(max(0.0, min(self._loop_end_frac - min_gap, f)))
        else:
            self._loop_end_frac = float(min(1.0, max(self._loop_start_frac + min_gap, f)))

        self._redraw_waveform()

    def _on_canvas_up(self, _e: tk.Event) -> None:
        self._loop_drag = None

    def _apply_loop_to_buffer(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """Découpe le buffer selon la sélection loop si Mode Loop actif."""
        if not bool(self.var_loop_mode.get()):
            return audio
        if not self._loop_has_valid_selection():
            return audio

        n = len(audio)
        start = int(round(self._loop_start_frac * n))
        end = int(round(self._loop_end_frac * n))
        start = max(0, min(n - 1, start))
        end = max(start + 1, min(n, end))
        return audio[start:end]

    def _ensure_default_loop(self) -> None:
        """Initialise une sélection loop raisonnable à l'activation."""
        if not self._loop_has_audio():
            self._loop_start_frac = 0.0
            self._loop_end_frac = 1.0
            return
        audio, sr = self._get_preview_buffer(raw=True)
        if audio is None or sr is None or len(audio) == 0:
            self._loop_start_frac = 0.0
            self._loop_end_frac = 1.0
            return
        dur = len(audio) / float(sr)
        end_s = min(1.5, max(0.25, dur * 0.15))
        self._loop_start_frac = 0.0
        self._loop_end_frac = float(max(0.01, min(1.0, end_s / dur))) if dur > 0 else 1.0

    # ---- helpers UI ----

    def _add_scale(self, parent: ttk.Frame, label: str, var: tk.DoubleVar, a: float, b: float, row: int) -> None:
        frm = ttk.Frame(parent, style="Panel.TFrame")
        frm.grid(row=row, column=0, sticky="ew", pady=3)
        frm.columnconfigure(1, weight=1)
        ttk.Label(frm, text=label, width=14, style="Panel.TLabel").grid(row=0, column=0, sticky="w")
        s = ttk.Scale(frm, from_=a, to=b, variable=var, orient="horizontal")
        s.grid(row=0, column=1, sticky="ew", padx=(6, 0))

    def _add_spin(self, parent: ttk.Frame, label: str, var: tk.IntVar, a: int, b: int, row: int) -> None:
        frm = ttk.Frame(parent, style="Panel.TFrame")
        frm.grid(row=row, column=0, sticky="ew", pady=3)
        frm.columnconfigure(1, weight=1)
        ttk.Label(frm, text=label, width=14, style="Panel.TLabel").grid(row=0, column=0, sticky="w")
        sp = ttk.Spinbox(frm, from_=a, to=b, textvariable=var, increment=1, width=10)
        sp.grid(row=0, column=1, sticky="w", padx=(6, 0))

    def _add_spin_float(self, parent: ttk.Frame, label: str, var: tk.DoubleVar, a: float, b: float, row: int) -> None:
        frm = ttk.Frame(parent, style="Panel.TFrame")
        frm.grid(row=row, column=0, sticky="ew", pady=3)
        frm.columnconfigure(1, weight=1)
        ttk.Label(frm, text=label, width=14, style="Panel.TLabel").grid(row=0, column=0, sticky="w")
        sp = ttk.Spinbox(frm, from_=a, to=b, textvariable=var, increment=0.5, width=10)
        sp.grid(row=0, column=1, sticky="w", padx=(6, 0))

    # ---------------- Logic ----------------

    def _log(self, msg: str) -> None:
        # Journal supprimé (volontaire).
        pass

    def _sync_params_from_ui(self) -> None:
        self.params.seed = int(self.var_seed.get())
        self.params.grain_ms_min = int(self.var_grain_min.get())
        self.params.grain_ms_max = int(self.var_grain_max.get())
        self.params.shuffle_amount = float(self.var_shuffle.get())
        self.params.keep_original_ratio = float(self.var_keep.get())
        self.params.reverse_prob = float(self.var_rev.get())
        self.params.gain_db_min = float(self.var_gain_min.get())
        self.params.gain_db_max = float(self.var_gain_max.get())
        self.params.intensity = float(self.var_intensity.get())

        # --- Warp (potards à droite) ---
        try:
            self.params.warp_amount = float(self.var_warp_amount.get())

            r = float(self.var_warp_stretch_range.get())
            r = float(np.clip(r, 0.0, 1.0))
            span = r * WARP_STRETCH_SPAN_MAX
            self.params.warp_stretch_min = float(max(0.05, 1.0 - span))
            self.params.warp_stretch_max = float(max(self.params.warp_stretch_min, 1.0 + span))

            pr = float(self.var_warp_pitch_range.get())
            pr = float(np.clip(pr, 0.0, WARP_PITCH_RANGE_MAX_ST))
            self.params.warp_pitch_min_st = float(-pr)
            self.params.warp_pitch_max_st = float(pr)

            p = float(self.var_warp_prob.get())
            p = float(np.clip(p, 0.0, 1.0))
            self.params.warp_stretch_prob = float(p)
            self.params.warp_pitch_prob = float(p)
        except Exception:
            pass

    def _push_params_to_ui(self) -> None:
        self.var_seed.set(int(self.params.seed))
        self.var_grain_min.set(int(self.params.grain_ms_min))
        self.var_grain_max.set(int(self.params.grain_ms_max))
        self.var_shuffle.set(float(self.params.shuffle_amount))
        self.var_keep.set(float(self.params.keep_original_ratio))
        self.var_rev.set(float(self.params.reverse_prob))
        self.var_gain_min.set(float(self.params.gain_db_min))
        self.var_gain_max.set(float(self.params.gain_db_max))
        self.var_intensity.set(float(self.params.intensity))

        try:
            self.var_warp_amount.set(float(self.params.warp_amount))
            self.var_warp_prob.set(float((self.params.warp_stretch_prob + self.params.warp_pitch_prob) / 2.0))
            self._push_warp_ranges_to_ui()
        except Exception:
            pass

    def _push_warp_ranges_to_ui(self) -> None:
        # Stretch
        try:
            mn = float(getattr(self.params, "warp_stretch_min", 1.0))
            mx = float(getattr(self.params, "warp_stretch_max", 1.0))
            span = max(0.0, max(1.0 - mn, mx - 1.0))
            r = 0.0 if WARP_STRETCH_SPAN_MAX <= 0 else (span / WARP_STRETCH_SPAN_MAX)
            self.var_warp_stretch_range.set(float(np.clip(r, 0.0, 1.0)))
        except Exception:
            pass

        # Pitch
        try:
            pmin = float(getattr(self.params, "warp_pitch_min_st", 0.0))
            pmax = float(getattr(self.params, "warp_pitch_max_st", 0.0))
            pr = max(abs(pmin), abs(pmax))
            self.var_warp_pitch_range.set(float(np.clip(pr, 0.0, WARP_PITCH_RANGE_MAX_ST)))
        except Exception:
            pass

    def _on_load(self) -> None:
        path = filedialog.askopenfilename(
            title="Choisir un fichier audio",
            filetypes=[
                ("Audio", "*.wav *.wave *.mp3 *.flac *.ogg *.aiff *.aif *.m4a"),
                ("WAV", "*.wav *.wave"),
                ("Tous les fichiers", "*.*"),
            ],
        )
        if not path:
            return

        try:
            audio, sr = load_audio(path)
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger ce fichier.\n\nDétail : {e}")
            return

        self.src_path = path
        self.src_audio = audio
        self.src_sr = sr

        self.out_audio = None
        self.out_sr = None
        self.out_segments = 0

        self.lbl_file.configure(text=os.path.basename(path))
        self.lbl_info.configure(text=f"Chargé : {os.path.basename(path)} — {sr} Hz — {len(audio)/sr:.2f} s (mono)")
        self._log(f"Chargement OK: {path}")
        self._redraw_waveform()
        self.lbl_ffmpeg.configure(text=get_ffmpeg_status_short())

        # Quand un son est chargé : afficher la forme d'onde (masquer l'aide)
        try:
            self.var_show_help.set(False)
            self._update_help_visibility()
            try:
                self._redraw_waveform()
            except Exception:
                pass
        except Exception:
            pass


    def _on_randomize_seed(self) -> None:
        new_seed = random.randint(0, 2_000_000_000)
        self.var_seed.set(new_seed)
        self._log(f"Seed -> {new_seed}")

    def _on_render(self) -> None:
        if self.src_audio is None or self.src_sr is None:
            messagebox.showinfo("Information", "Veuillez charger un fichier audio avant de rendre.")
            return

        # Évite les doubles clics
        try:
            if getattr(self, "_render_busy", False):
                return
        except Exception:
            pass

        self._render_busy = True

        # UI: désactiver le bouton pendant le rendu
        try:
            self.btn_render.configure(text="Rendu…", state="disabled")
        except Exception:
            pass

        # Récupère les paramètres dans le thread UI (safe)
        self._sync_params_from_ui()

        # Si Warp activé : vérifier dépendances AVANT de lancer le thread (safe pour messagebox)
        if float(np.clip(getattr(self.params, "warp_amount", 0.0), 0.0, 1.0)) > 0.0:
            try:
                from warp_engine import ensure_warp_deps_available
                ensure_warp_deps_available()
            except Exception as e:
                self._render_busy = False
                try:
                    self.btn_render.configure(text="Rendre", state="normal")
                except Exception:
                    pass
                messagebox.showerror("Warp", f"Warp activé, mais dépendances manquantes ou invalides.\n\nDétail : {e}")
                return

        # Worker (thread)
        def _worker(audio: np.ndarray, sr: int, params: Params) -> None:
            try:
                res = render(audio, sr, params)
                # Retour UI thread
                self.root.after(0, lambda: self._on_render_done(res))
            except Exception as e:
                self.root.after(0, lambda: self._on_render_failed(e))

        threading.Thread(
            target=_worker,
            args=(self.src_audio, self.src_sr, self.params),
            daemon=True,
        ).start()

    def _on_render_done(self, res) -> None:
        # res vient de engine.render()
        try:
            self.out_audio = res.audio
            self.out_sr = self.src_sr
            self.out_segments = res.segments_count

            self.lbl_info.configure(
                text=f"Rendu prêt — segments: {self.out_segments} — durée: {len(self.out_audio)/self.out_sr:.2f} s — seed: {self.params.seed}"
            )
            self._redraw_waveform()
        finally:
            self._render_busy = False
            try:
                self.btn_render.configure(text="Rendre", state="normal")
            except Exception:
                pass

    def _on_render_failed(self, e: Exception) -> None:
        try:
            messagebox.showerror("Erreur", f"Le rendu a échoué.\n\nDétail : {e}")
        finally:
            self._render_busy = False
            try:
                self.btn_render.configure(text="Rendre", state="normal")
            except Exception:
                pass

    def _on_preview(self) -> None:
        audio, sr = self._get_preview_buffer()
        if audio is None or sr is None:
            return

        # Empêche double lecture
        with self._play_lock:
            if self._is_playing:
                return
            self._is_playing = True

        self._stop_request.clear()

        loop_enabled = bool(self.var_loop_mode.get()) and self._loop_has_valid_selection()

        def _play_worker(buf: np.ndarray, samplerate: int, loop_on: bool) -> None:
            try:
                while True:
                    if self._stop_request.is_set():
                        break

                    sd.play(buf, samplerate, blocking=False)

                    # Attendre fin OU stop demandé
                    while True:
                        if self._stop_request.is_set():
                            break
                        try:
                            stream = sd.get_stream()
                            active = bool(getattr(stream, "active", False)) if stream is not None else False
                        except Exception:
                            active = False
                        if not active:
                            break
                        sd.sleep(30)

                    # IMPORTANT : stop exécuté dans le MÊME thread que play()
                    try:
                        sd.stop()
                    except Exception:
                        pass

                    if not loop_on or self._stop_request.is_set():
                        break

            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Erreur", f"Lecture audio impossible.\n\nDétail : {e}"))
            finally:
                with self._play_lock:
                    self._is_playing = False

        self._play_thread = threading.Thread(
            target=_play_worker,
            args=(audio, sr, loop_enabled),
            daemon=True,
        )
        self._play_thread.start()
        self._log("Preview: lecture lancée.")


    def _on_stop(self) -> None:
        # Ne pas appeler sd.stop() depuis Tkinter (segfault observé)
        self._stop_request.set()
        self._log("Stop: arrêt demandé.")

    def _get_preview_buffer(self, raw: bool = False) -> tuple[np.ndarray | None, int | None]:
        if self.src_audio is None or self.src_sr is None:
            messagebox.showinfo("Information", "Veuillez charger un fichier audio avant de pré-écouter.")
            return None, None

        # Buffer de base : rendu si dispo, sinon source
        if self.out_audio is not None and self.out_sr is not None:
            buf = self.out_audio
            sr = self.out_sr
        else:
            buf = self.src_audio
            sr = self.src_sr

        # Appliquer la sélection loop uniquement si raw=False
        if not raw and buf is not None and sr is not None:
            try:
                buf = self._apply_loop_to_buffer(buf, sr)
            except Exception:
                pass

        return buf, sr


    def _on_export(self) -> None:
        if self.out_audio is None or self.out_sr is None:
            messagebox.showinfo("Information", "Veuillez rendre (apply) avant d’exporter.")
            return

        path = filedialog.asksaveasfilename(
            title="Exporter en WAV",
            defaultextension=".wav",
            filetypes=[("WAV", "*.wav")],
        )
        if not path:
            return

        try:
            export_wav(path, self.out_audio, self.out_sr)
        except Exception as e:
            messagebox.showerror("Erreur", f"Export impossible.\n\nDétail : {e}")
            return

        messagebox.showinfo("Export", "Le fichier a été exporté en WAV.")
        self._log(f"Export OK: {path}")

    def _on_export_loop(self) -> None:
        # Il faut au moins un buffer dispo (rendu ou source)
        if self.src_audio is None or self.src_sr is None:
            messagebox.showinfo("Information", "Veuillez charger un fichier audio avant d’exporter une loop.")
            return

        if not bool(self.var_loop_mode.get()):
            messagebox.showinfo("Information", "Veuillez activer le Mode Loop et définir une sélection avant d’exporter.")
            return

        if not self._loop_has_valid_selection():
            messagebox.showinfo("Information", "Sélection de loop invalide ou trop courte. Ajustez les poignées sur la forme d’onde.")
            return

        # Buffer de base : rendu si dispo, sinon source
        if self.out_audio is not None and self.out_sr is not None:
            base = self.out_audio
            sr = self.out_sr
        else:
            base = self.src_audio
            sr = self.src_sr

        # Découpe selon la sélection loop
        try:
            seg = self._apply_loop_to_buffer(base, sr)
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d’extraire la loop.\n\nDétail : {e}")
            return

        path = filedialog.asksaveasfilename(
            title="Exporter la loop en WAV",
            defaultextension=".wav",
            filetypes=[("WAV", "*.wav")],
        )
        if not path:
            return

        try:
            export_wav(path, seg, sr)
        except Exception as e:
            messagebox.showerror("Erreur", f"Export loop impossible.\n\nDétail : {e}")
            return

        messagebox.showinfo("Export", "La loop a été exportée en WAV.")
        self._log(f"Export loop OK: {path}")


    def _on_save_preset(self) -> None:
        self._sync_params_from_ui()
        path = filedialog.asksaveasfilename(
            title="Sauver le preset",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        try:
            save_preset(path, self.params)
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de sauvegarder le preset.\n\nDétail : {e}")
            return
        messagebox.showinfo("Preset", "Le preset a été sauvegardé.")
        self._log(f"Preset sauvegardé: {path}")

    def _on_load_preset(self) -> None:
        path = filedialog.askopenfilename(
            title="Charger un preset",
            filetypes=[("JSON", "*.json"), ("Tous les fichiers", "*.*")],
        )
        if not path:
            return
        try:
            self.params = load_preset(path)
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger le preset.\n\nDétail : {e}")
            return
        self._push_params_to_ui()
        messagebox.showinfo("Preset", "Le preset a été chargé.")
        self._log(f"Preset chargé: {path}")

    # ---------------- Waveform ----------------

    def _redraw_waveform(self) -> None:
        self.canvas.delete("all")

        audio = None
        sr = None
        if self.out_audio is not None and self.out_sr is not None:
            audio = self.out_audio
            sr = self.out_sr
        elif self.src_audio is not None and self.src_sr is not None:
            audio = self.src_audio
            sr = self.src_sr

        if audio is None or sr is None or len(audio) == 0:
            self._draw_center_text("Aucun signal")
            return

        w = max(1, self.canvas.winfo_width())
        h = max(1, self.canvas.winfo_height())

        n = len(audio)
        step = max(1, n // w)
        reduced = audio[::step]

        mid = h // 2
        scale = (h * 0.45)

        x_prev = 0
        y_prev = mid
        for x, v in enumerate(reduced[:w]):
            y = int(mid - float(v) * scale)
            self.canvas.create_line(x_prev, y_prev, x, y, fill=self._col_accent)
            x_prev, y_prev = x, y

        dur = n / sr
        self.canvas.create_text(10, 10, anchor="nw", fill="white", text=f"{dur:.2f}s — {sr}Hz")

        # Traits de sélection (début/fin) si Mode Loop activé
        if bool(self.var_loop_mode.get()) and self._loop_has_audio():
            xs = self._loop_x_from_frac(self._loop_start_frac)
            xe = self._loop_x_from_frac(self._loop_end_frac)
            if xe < xs:
                xs, xe = xe, xs

            # Zone sélectionnée (voile léger)
            try:
                self.canvas.create_rectangle(xs, 0, xe, h, fill="", outline="", stipple="gray50", tags="loop")
            except Exception:
                pass

            # Poignées: noir + liseré blanc (visibles sur tous thèmes)
            self.canvas.create_line(xs, 0, xs, h, fill="white", width=4, tags="loop")
            self.canvas.create_line(xs, 0, xs, h, fill="black", width=2, tags="loop")
            self.canvas.create_line(xe, 0, xe, h, fill="white", width=4, tags="loop")
            self.canvas.create_line(xe, 0, xe, h, fill="black", width=2, tags="loop")

            try:
                seg = max(0.0, (self._loop_end_frac - self._loop_start_frac) * float(dur))
                self.canvas.create_text(10, 28, anchor="nw", fill="white", text=f"Loop: {seg:.2f}s", tags="loop")
            except Exception:
                pass


    def _draw_center_text(self, text: str) -> None:
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        self.canvas.create_text(w // 2, h // 2, fill="white", text=text)
