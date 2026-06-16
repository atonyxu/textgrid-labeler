import json
import os as _os
import tkinter as tk
from tkinter import messagebox
import textgrid
import copy
from typing import List, Optional

from .audio import AudioData
from .ui import UIBuilder
from .file_ops import FileOperationsMixin
from .view import ViewManagerMixin
from .drawing import DrawingMixin
from .events import EventHandlerMixin
from .playback import PlaybackMixin
from .search import SearchMixin


class TextGridLabeler(
    UIBuilder,
    FileOperationsMixin,
    ViewManagerMixin,
    DrawingMixin,
    EventHandlerMixin,
    PlaybackMixin,
    SearchMixin,
    tk.Tk,
):
    def __init__(self, filepath: str = ""):
        tk.Tk.__init__(self)
        self.title("TextGrid Labeler")
        self.geometry("1200x700")
        self.minsize(800, 500)
        try:
            self.state("zoomed")
        except tk.TclError:
            w = self.winfo_screenwidth()
            h = self.winfo_screenheight()
            self.geometry(f"{w}x{h}+0+0")

        if filepath and _os.path.exists(filepath):
            self.after(10, self._load_textgrid, filepath)

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

        # List selection
        self.selected_idx: int = -1

        # Ruler
        self.ruler_w = 28

        # Undo/redo
        self.undo_stack: List[str] = []
        self.redo_stack: List[str] = []

        # Recent files
        self.recent_files: List[str] = []
        self._recent_limit = 10
        self._load_recent()

        # Drag state
        self.dragging = False
        self.drag_boundary_time: float = 0.0
        self.drag_min_time: float = 0.0
        self.drag_max_time: float = 0.0

        # Hover time (tracked for keyboard shortcuts)
        self.hover_time: Optional[float] = None

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

    def set_status(self, text: str):
        self.status_bar.config(text=text)

    def _recent_dir(self) -> str:
        d = _os.path.join(_os.path.expanduser("~"), ".textgrid-labeler")
        _os.makedirs(d, exist_ok=True)
        return d

    def _recent_path(self) -> str:
        return _os.path.join(self._recent_dir(), "recent.json")

    def _load_recent(self):
        p = self._recent_path()
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            self.recent_files = [e for e in data if _os.path.exists(e)][:self._recent_limit]
        except Exception:
            self.recent_files = []

    def _save_recent(self):
        p = self._recent_path()
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(self.recent_files, f, ensure_ascii=False)
        except Exception:
            pass

    def _add_recent(self, path: str):
        if not path:
            return
        self.recent_files = [e for e in self.recent_files if e != path]
        self.recent_files.insert(0, path)
        self.recent_files = self.recent_files[:self._recent_limit]
        self._save_recent()
        self._update_recent_menu()

    def _show_help(self):
        import os as _os
        help_path = _os.path.join(_os.path.dirname(__file__), "HELP.txt")
        try:
            with open(help_path, encoding="utf-8") as f:
                text = f.read()
        except Exception:
            text = "Help file not found."
        from tkinter.scrolledtext import ScrolledText
        win = tk.Toplevel(self)
        win.title("User Guide - TextGrid Labeler")
        win.geometry("620x560")
        win.minsize(480, 400)
        win.transient(self)
        win.grab_set()
        txt = ScrolledText(win, wrap=tk.WORD, font=("Consolas", 10),
                           padx=12, pady=12, bg="#fafafa", fg="#222")
        txt.pack(fill=tk.BOTH, expand=True)
        txt.insert(tk.END, text)
        txt.config(state=tk.DISABLED)
        btn = tk.Button(win, text="Close", command=win.destroy,
                        font=("Segoe UI", 10))
        btn.pack(pady=(0, 10))

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
