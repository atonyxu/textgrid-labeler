from typing import Optional


class PlaybackMixin:
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
