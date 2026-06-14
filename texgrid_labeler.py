import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import wave
import numpy as np
import os
import subprocess
import threading
import io
import tempfile
import platform
import textgrid
from typing import List, Optional, Tuple


# ─── Cross-platform Audio Playback ──────────────────────────────────────────

class AudioPlayer:
    @staticmethod
    def play_wav_data(wav_data: bytes):
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.write(wav_data)
        tmp_name = tmp.name
        tmp.close()

        def _play_and_clean():
            try:
                system = platform.system()
                if system == "Windows":
                    import winsound
                    winsound.PlaySound(tmp_name, winsound.SND_FILENAME | winsound.SND_ASYNC)
                elif system == "Darwin":
                    subprocess.Popen(["afplay", tmp_name],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    for cmd in ["paplay", "aplay", "ffplay", "play"]:
                        try:
                            subprocess.run([cmd, "--version"],
                                           capture_output=True, timeout=1)
                            subprocess.Popen([cmd, tmp_name],
                                             stdout=subprocess.DEVNULL,
                                             stderr=subprocess.DEVNULL)
                            break
                        except (FileNotFoundError, subprocess.TimeoutExpired):
                            continue
                cleanup_after = 5.0
                threading.Timer(cleanup_after, lambda: AudioPlayer._cleanup(tmp_name)).start()
            except Exception as e:
                print(f"Playback error: {e}")

        threading.Thread(target=_play_and_clean, daemon=True).start()

    @staticmethod
    def _cleanup(path: str):
        try:
            os.unlink(path)
        except:
            pass


# ─── Audio Data Handler ─────────────────────────────────────────────────────

class AudioData:
    def __init__(self, filepath: str = ""):
        self.filepath = filepath
        self.sample_rate = 0
        self.n_channels = 0
        self.sample_width = 0
        self.n_frames = 0
        self.duration = 0.0
        self.max_possible = 1.0
        self.samples: Optional[np.ndarray] = None
        if filepath:
            self.load(filepath)

    def load(self, filepath: str):
        self.filepath = filepath
        with wave.open(filepath, "rb") as wf:
            self.sample_rate = wf.getframerate()
            self.n_channels = wf.getnchannels()
            self.sample_width = wf.getsampwidth()
            self.n_frames = wf.getnframes()
            self.duration = self.n_frames / self.sample_rate
            self.max_possible = 2 ** (8 * self.sample_width - 1)
            raw = wf.readframes(self.n_frames)
            dtype = np.int16 if self.sample_width == 2 else np.int32 if self.sample_width == 4 else np.int8
            self.samples = np.frombuffer(raw, dtype=dtype).astype(np.float32)
            if self.n_channels > 1:
                self.samples = self.samples.reshape(-1, self.n_channels).mean(axis=1)

    def is_loaded(self) -> bool:
        return self.samples is not None and len(self.samples) > 0

    def get_section(self, start_time: float, end_time: float) -> Optional[np.ndarray]:
        if not self.is_loaded():
            return None
        start_frame = int(start_time * self.sample_rate)
        end_frame = int(end_time * self.sample_rate)
        start_frame = max(0, min(start_frame, self.n_frames - 1))
        end_frame = max(start_frame + 1, min(end_frame, self.n_frames))
        return self.samples[start_frame:end_frame]

    def play(self, start_time: float, end_time: float):
        section = self.get_section(start_time, end_time)
        if section is None or len(section) == 0:
            return
        self._play_array(section)

    def _play_array(self, samples: np.ndarray):
        samples = np.clip(samples, -32768, 32767).astype(np.int16)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(samples.tobytes())

        AudioPlayer.play_wav_data(buf.getvalue())


# ─── Main Application ───────────────────────────────────────────────────────

class TextGridLabeler(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TextGrid Labeler")
        self.geometry("1200x700")
        self.minsize(800, 500)

        # Data
        self.textgrid: Optional[textgrid.TextGrid] = None
        self.textgrid_path: str = ""
        self.audio_data = AudioData()
        self.current_tier_index: int = 0
        self.modified = False

        # View state
        self.visible_start = 0.0
        self.visible_duration = 5.0

        # Search state
        self.search_results: List[int] = []
        self.search_index: int = -1
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._on_search_changed())

        # Drag state
        self.dragging = False
        self.drag_boundary_time: float = 0.0
        self.drag_min_time: float = 0.0
        self.drag_max_time: float = 0.0

        # Playback cursor state
        import time as _time
        self._time = _time
        self.play_cursor_time: Optional[float] = None
        self.play_cursor_start: float = 0.0
        self.play_cursor_end: float = 0.0
        self.play_cursor_wall: float = 0.0
        self.play_cursor_after_id: Optional[str] = None

        # Colors
        self.bg_color = "#1e1e1e"
        self.fg_color = "#d4d4d4"
        self.wave_color = "#4fc3f7"
        self.line_color = "#ff4444"
        self.label_bg = "#2d2d2d"
        self.search_hl = "#ffcc00"
        self.status_bg = "#007acc"

        self._build_ui()
        self._bind_events()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─── UI Build ─────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_menu()
        self._build_toolbar()
        self._build_canvases()
        self._build_scrollbar()
        self._build_statusbar()

    def _build_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open TextGrid", command=self._open_textgrid, accelerator="Ctrl+O")
        file_menu.add_command(label="Open WAV", command=self._open_wav, accelerator="Ctrl+W")
        file_menu.add_separator()
        file_menu.add_command(label="Save TextGrid", command=self._save_textgrid, accelerator="Ctrl+S")
        file_menu.add_command(label="Save as New TextGrid", command=self._save_as_textgrid, accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)
        menubar.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.bind_all("<Control-o>", lambda e: self._open_textgrid())
        self.bind_all("<Control-w>", lambda e: self._open_wav())
        self.bind_all("<Control-s>", lambda e: self._save_textgrid())
        self.bind_all("<Control-Shift-S>", lambda e: self._save_as_textgrid())
        self.bind_all("<Control-Shift-s>", lambda e: self._save_as_textgrid())

    def _build_toolbar(self):
        toolbar = tk.Frame(self, bg=self.bg_color, height=40)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=0, pady=0)
        toolbar.pack_propagate(False)

        left_frame = tk.Frame(toolbar, bg=self.bg_color)
        left_frame.pack(side=tk.LEFT, padx=8, pady=4)

        tk.Label(left_frame, text="Layer:", bg=self.bg_color, fg=self.fg_color,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 4))

        self.layer_var = tk.StringVar()
        self.layer_combo = ttk.Combobox(left_frame, textvariable=self.layer_var,
                                         state="readonly", width=22, font=("Segoe UI", 10))
        self.layer_combo.pack(side=tk.LEFT, padx=(0, 4))
        self.layer_combo.bind("<<ComboboxSelected>>", self._on_layer_changed)

        search_frame = tk.Frame(toolbar, bg=self.bg_color)
        search_frame.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=20, pady=4)

        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                                      font=("Segoe UI", 10),
                                      bg="#3c3c3c", fg=self.fg_color,
                                      insertbackground=self.fg_color,
                                      relief=tk.FLAT, bd=2)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=2)
        self.search_entry.bind("<Return>", lambda e: self._search_next())

        right_frame = tk.Frame(toolbar, bg=self.bg_color)
        right_frame.pack(side=tk.RIGHT, padx=8, pady=4)

        self.btn_prev = tk.Button(right_frame, text="\u25c0", width=3,
                                   font=("Segoe UI", 10),
                                   bg="#3c3c3c", fg=self.fg_color,
                                   relief=tk.FLAT, activebackground="#555",
                                   command=self._search_prev)
        self.btn_prev.pack(side=tk.LEFT, padx=1)

        self.btn_next = tk.Button(right_frame, text="\u25b6", width=3,
                                   font=("Segoe UI", 10),
                                   bg="#3c3c3c", fg=self.fg_color,
                                   relief=tk.FLAT, activebackground="#555",
                                   command=self._search_next)
        self.btn_next.pack(side=tk.LEFT, padx=1)

        self.search_count_label = tk.Label(right_frame, text="", bg=self.bg_color,
                                            fg=self.search_hl, font=("Segoe UI", 9))
        self.search_count_label.pack(side=tk.LEFT, padx=(4, 0))

    def _build_canvases(self):
        main_frame = tk.Frame(self, bg=self.bg_color)
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.annot_canvas = tk.Canvas(main_frame, bg=self.label_bg,
                                       height=40, highlightthickness=0)
        self.annot_canvas.pack(side=tk.TOP, fill=tk.X)

        self.ruler_canvas = tk.Canvas(main_frame, bg="#252526",
                                       height=22, highlightthickness=0)
        self.ruler_canvas.pack(side=tk.TOP, fill=tk.X)

        self.wave_canvas = tk.Canvas(main_frame, bg=self.bg_color,
                                      highlightthickness=0)
        self.wave_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def _build_scrollbar(self):
        scroll_frame = tk.Frame(self, bg=self.bg_color)
        scroll_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(2, 6))

        self.time_label = tk.Label(scroll_frame, text="0.000s / 0.000s",
                                    bg=self.bg_color, fg=self.fg_color,
                                    font=("Consolas", 9))
        self.time_label.pack(side=tk.LEFT, padx=(0, 8))

        self.scrollbar = ttk.Scrollbar(scroll_frame, orient=tk.HORIZONTAL,
                                        command=self._on_scrollbar)
        self.scrollbar.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _build_statusbar(self):
        self.status_bar = tk.Label(self, text="Ready",
                                    bg=self.status_bg, fg="white",
                                    font=("Segoe UI", 9),
                                    anchor=tk.W, padx=8)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    # ─── Event Bindings ──────────────────────────────────────────────────

    def _bind_events(self):
        self.wave_canvas.bind("<Button-1>", self._on_canvas_click)
        self.wave_canvas.bind("<Button-3>", self._on_canvas_right_click)
        self.wave_canvas.bind("<Double-Button-1>", self._on_canvas_double_click)
        self.wave_canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.wave_canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

        self.annot_canvas.bind("<Double-Button-1>", self._on_annot_double_click)

        self.wave_canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.wave_canvas.bind("<Control-MouseWheel>", self._on_ctrl_mousewheel)
        self.annot_canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.annot_canvas.bind("<Control-MouseWheel>", self._on_ctrl_mousewheel)

        self.wave_canvas.bind("<Configure>", self._on_resize)

    # ─── File Operations ─────────────────────────────────────────────────

    def _open_textgrid(self):
        path = filedialog.askopenfilename(
            title="Open TextGrid",
            filetypes=[("TextGrid files", "*.TextGrid *.textgrid"),
                       ("All files", "*.*")]
        )
        if not path:
            return
        try:
            self.textgrid = textgrid.TextGrid.fromFile(path)
            self.textgrid_path = path
            self.modified = False

            wav_path = os.path.splitext(path)[0] + ".wav"
            if os.path.exists(wav_path):
                self.audio_data.load(wav_path)
                self.set_status(f"Auto-loaded WAV: {os.path.basename(wav_path)}")

            self._on_data_loaded()
            self.set_status(f"Opened: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open TextGrid:\n{e}")
            import traceback
            traceback.print_exc()

    def _open_wav(self):
        path = filedialog.askopenfilename(
            title="Open WAV",
            filetypes=[("WAV files", "*.wav"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            self.audio_data.load(path)
            if self.textgrid:
                self.visible_duration = min(5.0, self.audio_data.duration)
            self._update_view()
            self.set_status(f"Loaded WAV: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open WAV:\n{e}")

    def _save_textgrid(self):
        if not self.textgrid:
            messagebox.showinfo("Info", "No TextGrid file to save.")
            return
        if not self.textgrid_path:
            self._save_as_textgrid()
            return
        try:
            self.textgrid.write(self.textgrid_path)
            self.modified = False
            self.set_status(f"Saved: {os.path.basename(self.textgrid_path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save TextGrid:\n{e}")

    def _save_as_textgrid(self):
        if not self.textgrid:
            messagebox.showinfo("Info", "No TextGrid file to save.")
            return
        path = filedialog.asksaveasfilename(
            title="Save TextGrid As",
            defaultextension=".TextGrid",
            filetypes=[("TextGrid files", "*.TextGrid")]
        )
        if not path:
            return
        try:
            self.textgrid.write(path)
            self.textgrid_path = path
            self.modified = False
            self.set_status(f"Saved as: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save TextGrid:\n{e}")

    # ─── Data and View Management ────────────────────────────────────────

    def _on_data_loaded(self):
        if not self.textgrid:
            return

        total_dur = self.textgrid.maxTime
        if self.audio_data.is_loaded():
            total_dur = max(total_dur, self.audio_data.duration)

        if total_dur > 0:
            self.visible_duration = min(5.0, total_dur)
            self.visible_start = 0.0

        tier_names = [f"{t.name} ({type(t).__name__})" for t in self.textgrid.tiers]
        self.layer_combo["values"] = tier_names
        if tier_names:
            self.current_tier_index = 0
            self.layer_var.set(tier_names[0])

        self._update_scrollbar()
        self._update_view()

    def _update_view(self):
        self._draw_annotation_bar()
        self._draw_ruler()
        self._draw_waveform()
        self._draw_playback_line()
        self._update_time_label()
        self._update_scrollbar()

    def _on_layer_changed(self, event=None):
        idx = self.layer_combo.current()
        if idx >= 0:
            self.current_tier_index = idx
            self.search_results = []
            self.search_index = -1
            self._update_search_display(redraw=False)
            self._update_view()
            self.set_status(f"Selected layer: {self.layer_combo.get()}")

    def _on_resize(self, event=None):
        self._update_view()

    def _update_scrollbar(self):
        total = self._get_total_duration()
        if total <= 0:
            self.scrollbar.set(0, 1)
            return
        frac_start = self.visible_start / total
        frac_width = self.visible_duration / total
        self.scrollbar.set(frac_start, frac_start + frac_width)

    def _on_scrollbar(self, *args):
        total = self._get_total_duration()
        if total <= 0:
            return
        if args[0] == "moveto":
            frac = float(args[1])
            self.visible_start = frac * total
        elif args[0] == "scroll":
            direction = int(args[1])
            step = self.visible_duration * 0.2
            if args[2] == "pages":
                step *= 5
            self.visible_start += direction * step
        self._clamp_view()
        self._update_view()

    def _clamp_view(self):
        total = self._get_total_duration()
        if total <= 0:
            self.visible_start = 0
            self.visible_duration = 5.0
            return
        if self.visible_duration > total:
            self.visible_duration = total
            self.visible_start = 0
        self.visible_start = max(0, min(self.visible_start, total - self.visible_duration))

    def _get_total_duration(self) -> float:
        total = 0.0
        if self.textgrid:
            total = max(total, self.textgrid.maxTime)
        if self.audio_data.is_loaded():
            total = max(total, self.audio_data.duration)
        return total

    def _update_time_label(self):
        total = self._get_total_duration()
        end_t = min(self.visible_start + self.visible_duration, total)
        self.time_label.config(
            text=f"{self.visible_start:.3f}s - {end_t:.3f}s / {total:.3f}s"
        )

    # ─── Drawing ─────────────────────────────────────────────────────────

    def _get_current_tier(self):
        if not self.textgrid:
            return None
        if 0 <= self.current_tier_index < len(self.textgrid.tiers):
            return self.textgrid.tiers[self.current_tier_index]
        return None

    def _draw_annotation_bar(self):
        self.annot_canvas.delete("all")
        tier = self._get_current_tier()
        if not tier or not hasattr(tier, "intervals"):
            return

        w = self.annot_canvas.winfo_width()
        if w <= 1:
            w = 400
        h = self.annot_canvas.winfo_height()
        vis_end = self.visible_start + self.visible_duration

        for i, interval in enumerate(tier.intervals):
            if interval.maxTime <= self.visible_start or interval.minTime >= vis_end:
                continue

            x1 = int((interval.minTime - self.visible_start) / self.visible_duration * w)
            x2 = int((interval.maxTime - self.visible_start) / self.visible_duration * w)

            is_search_match = i in self.search_results if self.search_results else False
            is_current_search = False
            if is_search_match and self.search_index >= 0:
                idx = self.search_index % len(self.search_results)
                is_current_search = (i == self.search_results[idx])

            fill_color = "#4a4020" if is_current_search else ("#353535" if not is_search_match else "#3a3a3a")

            self.annot_canvas.create_rectangle(x1, 0, x2, h,
                                                fill=fill_color,
                                                outline="#555", width=1)

            if x2 - x1 > 10:
                display_text = interval.mark if interval.mark else "(sil)"
                self.annot_canvas.create_text(
                    (x1 + x2) / 2, h / 2,
                    text=display_text,
                    fill=self.search_hl,
                    font=("Segoe UI", 12, "bold"),
                    width=max(10, x2 - x1 - 4),
                    anchor=tk.CENTER
                )

    def _draw_ruler(self):
        self.ruler_canvas.delete("all")
        w = self.ruler_canvas.winfo_width()
        if w <= 1:
            w = 400
        h = self.ruler_canvas.winfo_height()
        total = self._get_total_duration()
        if total <= 0:
            return

        vis_end = self.visible_start + self.visible_duration

        tick_spacing = self._nice_number(self.visible_duration / 10)
        t = np.ceil(self.visible_start / tick_spacing) * tick_spacing
        while t <= vis_end:
            x = int((t - self.visible_start) / self.visible_duration * w)
            if 0 <= x <= w:
                self.ruler_canvas.create_line(x, 0, x, h, fill="#666", width=1)
                self.ruler_canvas.create_text(x + 2, h / 2,
                                               text=f"{t:.3f}s",
                                               fill=self.fg_color,
                                               font=("Consolas", 8),
                                               anchor=tk.W)
            t += tick_spacing

    def _draw_waveform(self):
        self.wave_canvas.delete("all")
        w = self.wave_canvas.winfo_width()
        h = self.wave_canvas.winfo_height()
        if w <= 1 or h <= 1:
            return

        if self.audio_data.is_loaded():
            self._draw_waveform_data(w, h)
        else:
            mid = h / 2
            self.wave_canvas.create_text(w / 2, mid,
                                          text="No audio loaded. Open a WAV file to view waveform.",
                                          fill="#666", font=("Segoe UI", 12))

        if self.textgrid:
            self._draw_annotation_lines(w, h)

    def _draw_waveform_data(self, w: int, h: int):
        vis_end = self.visible_start + self.visible_duration
        sr = self.audio_data.sample_rate
        total_samples = len(self.audio_data.samples)

        start_idx = int(self.visible_start * sr)
        end_idx = int(vis_end * sr)
        start_idx = max(0, min(start_idx, total_samples - 1))
        end_idx = max(start_idx + 1, min(end_idx, total_samples))

        chunk = self.audio_data.samples[start_idx:end_idx]
        if len(chunk) == 0:
            return

        mid = h / 2
        self.wave_canvas.create_line(0, mid, w, mid, fill="#333", width=1)

        n_points = min(len(chunk), w * 2)
        if n_points < 2:
            return

        indices = np.linspace(0, len(chunk) - 1, n_points).astype(np.intp)
        downsampled = chunk[indices]

        norm = downsampled / self.audio_data.max_possible * (h / 2 - 4)

        coords = []
        for i in range(n_points):
            x = (i / (n_points - 1)) * w
            coords.append(x)
            coords.append(mid - norm[i])

        self.wave_canvas.create_line(*coords, fill=self.wave_color, width=1)

    def _draw_annotation_lines(self, w: int, h: int):
        tier = self._get_current_tier()
        if not tier:
            return

        vis_end = self.visible_start + self.visible_duration

        if hasattr(tier, "intervals"):
            boundaries = set()
            for interval in tier.intervals:
                boundaries.add(interval.minTime)
                boundaries.add(interval.maxTime)
            boundaries = sorted(b for b in boundaries if self.visible_start <= b <= vis_end)

            for t in boundaries:
                x = int((t - self.visible_start) / self.visible_duration * w)
                if 0 <= x <= w:
                    highlight = False
                    if self.search_results and self.search_index >= 0:
                        sidx = self.search_results[self.search_index % len(self.search_results)]
                        interval = tier.intervals[sidx]
                        if abs(t - interval.minTime) < 0.001 or abs(t - interval.maxTime) < 0.001:
                            highlight = True

                    color = self.search_hl if highlight else self.line_color
                    line_w = 2 if highlight else 1
                    self.wave_canvas.create_line(x, 0, x, h,
                                                  fill=color, width=line_w,
                                                  tags=("annot_line",))
                    self.wave_canvas.create_polygon(
                        x - 4, 0, x + 4, 0, x, 6,
                        fill=color, outline=color, tags=("annot_line",)
                    )
        elif hasattr(tier, "points"):
            for pt in tier.points:
                if self.visible_start <= pt.time <= vis_end:
                    x = int((pt.time - self.visible_start) / self.visible_duration * w)
                    if 0 <= x <= w:
                        self.wave_canvas.create_line(x, 0, x, h,
                                                      fill=self.line_color,
                                                      width=1)

    # ─── Mouse Events ────────────────────────────────────────────────────

    def _pixel_to_time(self, px: int) -> float:
        w = self.wave_canvas.winfo_width()
        if w <= 0:
            return self.visible_start
        return self.visible_start + (px / w) * self.visible_duration

    def _get_all_boundaries(self, tier) -> List[float]:
        boundaries = set()
        for interval in tier.intervals:
            boundaries.add(interval.minTime)
            boundaries.add(interval.maxTime)
        return sorted(boundaries)

    def _find_boundary_constraints(self, bound_time: float, tier) -> Tuple[float, float]:
        boundaries = self._get_all_boundaries(tier)
        try:
            pos = boundaries.index(bound_time)
            lo = boundaries[pos - 1] if pos > 0 else tier.minTime
            hi = boundaries[pos + 1] if pos < len(boundaries) - 1 else tier.maxTime
            return lo, hi
        except ValueError:
            return tier.minTime, tier.maxTime

    def _find_nearest_boundary(self, time: float, max_dist: float = 0.05) -> Tuple[float, bool]:
        tier = self._get_current_tier()
        if not tier or not hasattr(tier, "intervals"):
            return 0.0, False

        boundaries = self._get_all_boundaries(tier)
        nearest = None
        nearest_dist = max_dist

        for b in boundaries:
            d = abs(time - b)
            if d < nearest_dist:
                nearest_dist = d
                nearest = b

        if nearest is not None:
            return nearest, True
        return 0.0, False

    def _find_interval_at_time(self, time: float) -> int:
        tier = self._get_current_tier()
        if not tier or not hasattr(tier, "intervals"):
            return -1
        for i, interval in enumerate(tier.intervals):
            if interval.minTime <= time < interval.maxTime:
                return i
        if tier.intervals and abs(time - tier.intervals[-1].maxTime) < 0.001:
            return len(tier.intervals) - 1
        return -1

    def _on_canvas_click(self, event):
        if not self.textgrid:
            return
        click_time = self._pixel_to_time(event.x)
        tier = self._get_current_tier()
        if not tier or not hasattr(tier, "intervals"):
            return

        bound_time, found = self._find_nearest_boundary(click_time, max_dist=0.05)
        if found:
            min_t, max_t = self._find_boundary_constraints(bound_time, tier)
            self.dragging = True
            self.drag_boundary_time = bound_time
            self.drag_min_time = min_t
            self.drag_max_time = max_t

    def _on_canvas_right_click(self, event):
        if not self.textgrid:
            return
        click_time = self._pixel_to_time(event.x)
        tier = self._get_current_tier()
        if not tier or not hasattr(tier, "intervals"):
            return

        idx = self._find_interval_at_time(click_time)
        if idx >= 0 and self.audio_data.is_loaded():
            interval = tier.intervals[idx]
            self.audio_data.play(interval.minTime, interval.maxTime)
            self._start_playback_cursor(interval.minTime, interval.maxTime)
            self.set_status(f"Playing: [{interval.minTime:.3f}s - {interval.maxTime:.3f}s] {interval.mark}")

    def _on_canvas_double_click(self, event):
        if not self.textgrid:
            return
        click_time = self._pixel_to_time(event.x)
        tier = self._get_current_tier()
        if not tier or not hasattr(tier, "intervals"):
            return

        _, found = self._find_nearest_boundary(click_time, max_dist=0.03)
        if found:
            return

        interval_idx = self._find_interval_at_time(click_time)
        if interval_idx < 0:
            return

        interval = tier.intervals[interval_idx]
        new_text = simpledialog.askstring(
            "New Annotation",
            f"Enter label for new annotation at {click_time:.3f}s:",
            initialvalue=interval.mark,
            parent=self
        )
        if new_text is not None:
            self._add_annotation_boundary(interval_idx, click_time, new_text)

    def _on_canvas_drag(self, event):
        if not self.dragging:
            return

        click_time = self._pixel_to_time(event.x)
        new_time = max(self.drag_min_time, min(self.drag_max_time, click_time))

        tier = self._get_current_tier()
        if not tier or not hasattr(tier, "intervals"):
            return

        for interval in tier.intervals:
            if abs(interval.minTime - self.drag_boundary_time) < 0.001:
                interval.minTime = new_time
            if abs(interval.maxTime - self.drag_boundary_time) < 0.001:
                interval.maxTime = new_time

        self.drag_boundary_time = new_time
        self.modified = True
        self._update_view()

    def _on_canvas_release(self, event):
        if self.dragging:
            self.dragging = False
            self.set_status("Boundary updated")

    def _on_annot_double_click(self, event):
        if not self.textgrid:
            return
        w = self.annot_canvas.winfo_width()
        if w <= 0:
            return
        click_time = self.visible_start + (event.x / w) * self.visible_duration
        tier = self._get_current_tier()
        if not tier or not hasattr(tier, "intervals"):
            return

        idx = self._find_interval_at_time(click_time)
        if idx < 0:
            return

        interval = tier.intervals[idx]
        new_text = simpledialog.askstring(
            "Edit Label",
            f"Edit label for interval [{interval.minTime:.3f}s - {interval.maxTime:.3f}s]:",
            initialvalue=interval.mark,
            parent=self
        )
        if new_text is not None:
            interval.mark = new_text
            self.modified = True
            self._update_view()
            self.set_status(f"Label updated: {new_text}")

    # ─── Playback Cursor ─────────────────────────────────────────────

    def _start_playback_cursor(self, start_time: float, end_time: float):
        self._stop_playback_cursor()
        self.play_cursor_start = start_time
        self.play_cursor_end = end_time
        self.play_cursor_wall = self._time.perf_counter()
        self.play_cursor_time = start_time
        self._draw_playback_line()
        self._tick_playback_cursor()

    def _tick_playback_cursor(self):
        if self.play_cursor_time is None:
            return
        elapsed = self._time.perf_counter() - self.play_cursor_wall
        current = self.play_cursor_start + elapsed
        if current >= self.play_cursor_end:
            self._stop_playback_cursor()
            return
        self.play_cursor_time = current
        self._draw_playback_line()
        self.play_cursor_after_id = self.after(50, self._tick_playback_cursor)

    def _stop_playback_cursor(self):
        if self.play_cursor_after_id is not None:
            self.after_cancel(self.play_cursor_after_id)
        self.play_cursor_after_id = None
        self.play_cursor_time = None
        self._draw_playback_line()

    def _draw_playback_line(self):
        self.wave_canvas.delete("play_cursor")
        if self.play_cursor_time is None:
            return
        w = self.wave_canvas.winfo_width()
        h = self.wave_canvas.winfo_height()
        if w <= 1 or h <= 1:
            return
        vis_end = self.visible_start + self.visible_duration
        if self.play_cursor_time < self.visible_start or self.play_cursor_time > vis_end:
            return
        x = int((self.play_cursor_time - self.visible_start) / self.visible_duration * w)
        self.wave_canvas.create_line(x, 0, x, h, fill="#44ff44", width=2, tags=("play_cursor",))

    def _add_annotation_boundary(self, interval_idx: int, time: float, text: str = ""):
        tier = self._get_current_tier()
        if not tier or not hasattr(tier, "intervals"):
            return

        interval = tier.intervals[interval_idx]
        if time <= interval.minTime or time >= interval.maxTime:
            return

        if not text:
            text = interval.mark
        old_xmax = interval.maxTime
        interval.maxTime = time

        new_interval = textgrid.Interval(minTime=time, maxTime=old_xmax, mark=text)
        tier.intervals.insert(interval_idx + 1, new_interval)

        self.modified = True
        self._update_view()
        self.set_status(f"Added boundary at {time:.3f}s")

    # ─── Mouse Wheel ─────────────────────────────────────────────────────

    def _on_mousewheel(self, event):
        delta = event.delta / 120
        step = self.visible_duration * 0.15 * delta
        self.visible_start += step
        self._clamp_view()
        self._update_view()

    def _on_ctrl_mousewheel(self, event):
        delta = event.delta / 120
        factor = 1.0 - delta * 0.12
        factor = max(0.5, min(2.0, factor))

        new_duration = self.visible_duration * factor
        total = self._get_total_duration()
        new_duration = max(0.1, min(new_duration, total if total > 0 else 100))

        w = self.wave_canvas.winfo_width()
        mouse_frac = event.x / w if w > 0 else 0.5
        mouse_frac = max(0, min(1, mouse_frac))

        center_time = self.visible_start + mouse_frac * self.visible_duration
        new_start = center_time - mouse_frac * new_duration
        if new_start < 0:
            new_start = 0
        if new_start + new_duration > total:
            new_start = max(0, total - new_duration)
        self.visible_start = new_start
        self.visible_duration = new_duration

        self._update_view()

    # ─── Search ──────────────────────────────────────────────────────────

    def _on_search_changed(self):
        self._do_search()

    def _do_search(self):
        if not self.textgrid:
            self.search_results = []
            self.search_index = -1
            self._update_search_display()
            return

        query = self.search_var.get().strip().lower()
        if not query:
            self.search_results = []
            self.search_index = -1
            self._update_search_display()
            return

        tier = self._get_current_tier()
        if not tier or not hasattr(tier, "intervals"):
            self.search_results = []
            self.search_index = -1
            self._update_search_display()
            return

        results = []
        for i, interval in enumerate(tier.intervals):
            if query in interval.mark.lower():
                results.append(i)

        self.search_results = results
        if self.search_results:
            self.search_index = 0
            self._scroll_to_result(self.search_results[0])
        else:
            self.search_index = -1

        self._update_search_display()

    def _search_next(self):
        if not self.search_results:
            return
        self.search_index = (self.search_index + 1) % len(self.search_results)
        self._scroll_to_result(self.search_results[self.search_index])
        self._update_search_display()

    def _search_prev(self):
        if not self.search_results:
            return
        self.search_index = (self.search_index - 1) % len(self.search_results)
        self._scroll_to_result(self.search_results[self.search_index])
        self._update_search_display()

    def _scroll_to_result(self, interval_idx: int):
        tier = self._get_current_tier()
        if not tier or interval_idx >= len(tier.intervals):
            return
        interval = tier.intervals[interval_idx]
        center = (interval.minTime + interval.maxTime) / 2
        self.visible_start = center - self.visible_duration / 2
        self._clamp_view()
        self._update_view()

    def _update_search_display(self, redraw=True):
        n = len(self.search_results)
        if n == 0:
            self.search_count_label.config(text="")
        else:
            current = self.search_index % n if self.search_index >= 0 else 0
            self.search_count_label.config(text=f"{current + 1}/{n}")

        if redraw:
            self._update_view()

    # ─── Utilities ───────────────────────────────────────────────────────

    def _nice_number(self, x: float) -> float:
        if x == 0:
            return 1
        exp = np.floor(np.log10(x))
        frac = x / (10 ** exp)
        if frac < 1.5:
            nice = 1.0
        elif frac < 3.5:
            nice = 2.0
        elif frac < 7.5:
            nice = 5.0
        else:
            nice = 10.0
        return nice * (10 ** exp)

    def set_status(self, text: str):
        self.status_bar.config(text=text)

    def _show_about(self):
        messagebox.showinfo("About TextGrid Labeler",
                            "TextGrid Labeler v1.0\n\n"
                            "A tool for viewing and annotating TextGrid files.\n"
                            "Built with Python + Tkinter + textgrid library.")

    def _on_close(self):
        self._stop_playback_cursor()
        if self.modified:
            result = messagebox.askyesnocancel("Unsaved Changes",
                                                "You have unsaved changes. Save before closing?")
            if result is None:
                return
            if result:
                self._save_textgrid()
                if self.modified:
                    return
        self.destroy()

    def run(self):
        self.mainloop()


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = TextGridLabeler()
    app.run()
