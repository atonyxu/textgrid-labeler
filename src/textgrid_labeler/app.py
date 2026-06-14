import tkinter as tk
from tkinter import messagebox
import textgrid
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
    def __init__(self):
        tk.Tk.__init__(self)
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

        # List selection
        self.selected_idx: int = -1

        # Ruler
        self.ruler_w = 28

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
