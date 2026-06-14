import os
from tkinter import filedialog, messagebox

import textgrid


class FileOperationsMixin:
    @staticmethod
    def _find_wav(textgrid_path: str) -> str:
        base = os.path.splitext(os.path.basename(textgrid_path))[0]
        tg_dir = os.path.dirname(textgrid_path)
        parent_dir = os.path.dirname(tg_dir)

        candidates = [
            os.path.join(tg_dir, base + ".wav"),
            os.path.join(parent_dir, base + ".wav"),
        ]
        for sub in ("wav", "wavs", "WAV", "WAVS"):
            candidates.append(os.path.join(parent_dir, sub, base + ".wav"))

        for c in candidates:
            if os.path.exists(c):
                return c
        return ""

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
            self.undo_stack.clear()
            self.redo_stack.clear()

            wav_path = self._find_wav(path)
            if wav_path:
                self.audio_data.load(wav_path)
                self.set_status(f"Auto-loaded WAV: {os.path.basename(wav_path)}")

            self._add_recent(path)
            self._on_data_loaded()
            self.set_status(f"Opened: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open TextGrid:\n{e}")
            import traceback
            traceback.print_exc()

    def _open_recent(self, path: str):
        if not os.path.exists(path):
            self.recent_files = [e for e in self.recent_files if e != path]
            self._save_recent()
            self._update_recent_menu()
            messagebox.showinfo("File Not Found", f"The file no longer exists:\n{path}")
            return
        try:
            self.textgrid = textgrid.TextGrid.fromFile(path)
            self.textgrid_path = path
            self.modified = False
            self.undo_stack.clear()
            self.redo_stack.clear()

            wav_path = self._find_wav(path)
            if wav_path:
                self.audio_data.load(wav_path)
                self.set_status(f"Auto-loaded WAV: {os.path.basename(wav_path)}")

            self._add_recent(path)
            self._on_data_loaded()
            self.set_status(f"Opened: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open TextGrid:\n{e}")

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
