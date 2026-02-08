# ui.py
from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import numpy as np
import sounddevice as sd

from presets import Params, save_preset, load_preset
from audio_io import load_audio, export_wav
from engine import render


APP_TITLE = "Warpocalypse"
DEFAULT_GEOMETRY = "980x640"


class WarpocalypseApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.geometry(DEFAULT_GEOMETRY)

        self.params = Params()

        self.src_path: str | None = None
        self.src_audio: np.ndarray | None = None
        self.src_sr: int | None = None

        self.out_audio: np.ndarray | None = None
        self.out_sr: int | None = None
        self.out_segments: int = 0

        self._play_lock = threading.Lock()
        self._is_playing = False

        self._build_ui()

    def run(self) -> None:
        self.root.mainloop()

    # ---------------- UI ----------------

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        left = ttk.Frame(self.root, padding=10)
        left.grid(row=0, column=0, sticky="nsw")
        left.columnconfigure(0, weight=1)

        right = ttk.Frame(self.root, padding=10)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)

        # --- Left: fichiers + presets
        ttk.Label(left, text="Fichier").grid(row=0, column=0, sticky="w")

        btn_load = ttk.Button(left, text="Charger…", command=self._on_load)
        btn_load.grid(row=1, column=0, sticky="ew", pady=(6, 0))

        self.lbl_file = ttk.Label(left, text="Aucun fichier chargé.", wraplength=260)
        self.lbl_file.grid(row=2, column=0, sticky="w", pady=(6, 12))

        ttk.Separator(left).grid(row=3, column=0, sticky="ew", pady=10)

        ttk.Label(left, text="Preset").grid(row=4, column=0, sticky="w")
        row_preset = ttk.Frame(left)
        row_preset.grid(row=5, column=0, sticky="ew", pady=(6, 0))
        row_preset.columnconfigure(0, weight=1)
        row_preset.columnconfigure(1, weight=1)

        ttk.Button(row_preset, text="Charger preset…", command=self._on_load_preset).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(row_preset, text="Sauver preset…", command=self._on_save_preset).grid(row=0, column=1, sticky="ew")

        ttk.Separator(left).grid(row=6, column=0, sticky="ew", pady=10)

        # --- Left: paramètres
        ttk.Label(left, text="Paramètres").grid(row=7, column=0, sticky="w")

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

        ttk.Separator(left).grid(row=17, column=0, sticky="ew", pady=10)

        # --- Left: actions
        ttk.Button(left, text="Randomize (nouvelle seed)", command=self._on_randomize_seed).grid(row=18, column=0, sticky="ew")
        ttk.Button(left, text="Rendre (apply)", command=self._on_render).grid(row=19, column=0, sticky="ew", pady=(6, 0))

        row_act = ttk.Frame(left)
        row_act.grid(row=20, column=0, sticky="ew", pady=(10, 0))
        row_act.columnconfigure(0, weight=1)
        row_act.columnconfigure(1, weight=1)

        ttk.Button(row_act, text="Preview", command=self._on_preview).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(row_act, text="Stop", command=self._on_stop).grid(row=0, column=1, sticky="ew")

        ttk.Button(left, text="Exporter WAV…", command=self._on_export).grid(row=21, column=0, sticky="ew", pady=(10, 0))

        # --- Right: infos + waveform
        self.lbl_info = ttk.Label(right, text="Chargez un fichier pour commencer.", wraplength=620)
        self.lbl_info.grid(row=0, column=0, sticky="w")

        self.canvas = tk.Canvas(right, height=240, bg="black", highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky="ew", pady=(10, 10))
        self.canvas.bind("<Configure>", lambda _e: self._redraw_waveform())

        self.txt_log = tk.Text(right, height=12, wrap="word")
        self.txt_log.grid(row=2, column=0, sticky="nsew")
        self.txt_log.configure(state="disabled")

    def _add_scale(self, parent: ttk.Frame, label: str, var: tk.DoubleVar, a: float, b: float, row: int) -> None:
        frm = ttk.Frame(parent)
        frm.grid(row=row, column=0, sticky="ew", pady=3)
        frm.columnconfigure(1, weight=1)
        ttk.Label(frm, text=label, width=14).grid(row=0, column=0, sticky="w")
        s = ttk.Scale(frm, from_=a, to=b, variable=var, orient="horizontal")
        s.grid(row=0, column=1, sticky="ew", padx=(6, 0))

    def _add_spin(self, parent: ttk.Frame, label: str, var: tk.IntVar, a: int, b: int, row: int) -> None:
        frm = ttk.Frame(parent)
        frm.grid(row=row, column=0, sticky="ew", pady=3)
        frm.columnconfigure(1, weight=1)
        ttk.Label(frm, text=label, width=14).grid(row=0, column=0, sticky="w")
        sp = ttk.Spinbox(frm, from_=a, to=b, textvariable=var, increment=1, width=10)
        sp.grid(row=0, column=1, sticky="w", padx=(6, 0))

    def _add_spin_float(self, parent: ttk.Frame, label: str, var: tk.DoubleVar, a: float, b: float, row: int) -> None:
        frm = ttk.Frame(parent)
        frm.grid(row=row, column=0, sticky="ew", pady=3)
        frm.columnconfigure(1, weight=1)
        ttk.Label(frm, text=label, width=14).grid(row=0, column=0, sticky="w")
        sp = ttk.Spinbox(frm, from_=a, to=b, textvariable=var, increment=0.5, width=10)
        sp.grid(row=0, column=1, sticky="w", padx=(6, 0))

    # ---------------- Logic ----------------

    def _log(self, msg: str) -> None:
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", msg + "\n")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

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

    def _on_randomize_seed(self) -> None:
        # nouvelle seed (mais affichée, donc reproductible)
        import random
        new_seed = random.randint(0, 2_000_000_000)
        self.var_seed.set(new_seed)
        self._log(f"Seed -> {new_seed}")

    def _on_render(self) -> None:
        if self.src_audio is None or self.src_sr is None:
            messagebox.showinfo("Information", "Veuillez charger un fichier audio avant de rendre.")
            return

        self._sync_params_from_ui()

        try:
            res = render(self.src_audio, self.src_sr, self.params)
        except Exception as e:
            messagebox.showerror("Erreur", f"Le rendu a échoué.\n\nDétail : {e}")
            return

        self.out_audio = res.audio
        self.out_sr = self.src_sr
        self.out_segments = res.segments_count

        self.lbl_info.configure(
            text=f"Rendu prêt — segments: {self.out_segments} — durée: {len(self.out_audio)/self.out_sr:.2f} s — seed: {self.params.seed}"
        )
        self._log(f"Rendu OK: {self.out_segments} segments, seed={self.params.seed}")
        self._redraw_waveform()

    def _on_preview(self) -> None:
        audio, sr = self._get_preview_buffer()
        if audio is None or sr is None:
            return

        def _play() -> None:
            with self._play_lock:
                self._is_playing = True
            try:
                sd.stop()
                sd.play(audio, sr, blocking=True)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Erreur", f"Lecture audio impossible.\n\nDétail : {e}"))
            finally:
                with self._play_lock:
                    self._is_playing = False

        threading.Thread(target=_play, daemon=True).start()
        self._log("Preview: lecture lancée.")

    def _on_stop(self) -> None:
        sd.stop()
        self._log("Stop: lecture arrêtée.")

    def _get_preview_buffer(self) -> tuple[np.ndarray | None, int | None]:
        if self.src_audio is None or self.src_sr is None:
            messagebox.showinfo("Information", "Veuillez charger un fichier audio avant de pré-écouter.")
            return None, None

        if self.out_audio is not None and self.out_sr is not None:
            return self.out_audio, self.out_sr

        # Si pas rendu, on lit l'original
        return self.src_audio, self.src_sr

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

        # downsample à la largeur du canvas
        n = len(audio)
        step = max(1, n // w)
        reduced = audio[::step]

        mid = h // 2
        scale = (h * 0.45)

        # trace en vert pâle (mais sans dépendances; Tkinter gère la couleur)
        x_prev = 0
        y_prev = mid
        for x, v in enumerate(reduced[:w]):
            y = int(mid - float(v) * scale)
            self.canvas.create_line(x_prev, y_prev, x, y, fill="#9BE7A2")
            x_prev, y_prev = x, y

        dur = n / sr
        self.canvas.create_text(10, 10, anchor="nw", fill="white", text=f"{dur:.2f}s — {sr}Hz")

    def _draw_center_text(self, text: str) -> None:
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        self.canvas.create_text(w//2, h//2, fill="white", text=text)
