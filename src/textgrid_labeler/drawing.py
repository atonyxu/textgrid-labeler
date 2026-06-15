import tkinter as tk

import math


class DrawingMixin:
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

            is_selected = (i == self.selected_idx)

            if is_current_search or is_selected:
                fill_color = "#4a4020"
            elif is_search_match:
                fill_color = "#3a3a3a"
            else:
                fill_color = "#353535"

            self.annot_canvas.create_rectangle(x1, 0, x2, h,
                                                fill=fill_color,
                                                outline="#555", width=1)

            if x2 - x1 > 10:
                display_text = interval.mark if interval.mark else "(sil)"
                text_color = self.search_hl if (is_current_search or is_selected) else self.fg_color
                self.annot_canvas.create_text(
                    (x1 + x2) / 2, h / 2,
                    text=display_text,
                    fill=text_color,
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
        t = math.ceil(self.visible_start / tick_spacing) * tick_spacing
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

        self._draw_db_ruler(w, h, self.ruler_w)

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
        max_ampl = h / 2 - 4

        n_pixels = w
        if n_pixels < 2 or len(chunk) < 2:
            self.wave_canvas.create_line(0, mid, w, mid, fill="#333", width=1)
            return

        samples_per_pixel = len(chunk) / n_pixels

        fg = (0x4f, 0xc3, 0xf7)
        bg = (0x1e, 0x1e, 0x1e)

        raw = bytearray([bg[0], bg[1], bg[2]]) * (w * h)

        for x in range(n_pixels):
            lo = int(x * samples_per_pixel)
            hi = int((x + 1) * samples_per_pixel)
            if hi <= lo:
                hi = lo + 1
            if hi > len(chunk):
                hi = len(chunk)
            column = chunk[lo:hi]
            col_min = min(column)
            col_max = max(column)
            y1 = int(mid - col_max * max_ampl)
            y2 = int(mid - col_min * max_ampl)
            if y1 > y2:
                y1, y2 = y2, y1
            if y1 < 0:
                y1 = 0
            if y2 >= h:
                y2 = h - 1
            for y in range(y1, y2 + 1):
                i = (y * w + x) * 3
                raw[i] = fg[0]
                raw[i + 1] = fg[1]
                raw[i + 2] = fg[2]

        ppm = b"P6\n" + str(w).encode() + b" " + str(h).encode() + b"\n255\n" + bytes(raw)
        self._wave_photo = tk.PhotoImage(data=ppm)
        self.wave_canvas.create_image(0, 0, image=self._wave_photo, anchor=tk.NW, tags=("wave_img",))
        self.wave_canvas.create_line(0, mid, w, mid, fill="#333", width=1)

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
                    if self.selected_idx >= 0 and self.selected_idx < len(tier.intervals):
                        interval = tier.intervals[self.selected_idx]
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

    def _draw_db_ruler(self, w: int, h: int, ruler_w: int):
        if ruler_w <= 4:
            return

        mid = h / 2
        ruler_x = w - ruler_w

        self.wave_canvas.create_rectangle(ruler_x, 0, w, h, fill=self.bg_color, outline="")
        self.wave_canvas.create_line(ruler_x, 0, ruler_x, h, fill="#444", width=1)

        self.wave_canvas.create_text(
            ruler_x + ruler_w // 2, 2,
            text="dB", fill="#888",
            font=("Consolas", 8), anchor=tk.N
        )

        db_levels = [0, -1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -12, -18, -24, -48]
        labeled = {-3, -6, -9, -12, -18, -24, -48}

        for db in db_levels:
            ratio = 10 ** (db / 20)
            y_offset = ratio * (h / 2 - 4)

            for sign in (+1, -1):
                y = mid + sign * y_offset
                if 0 <= y <= h:
                    tick_len = 6 if db == 0 else (4 if db in labeled else 2)
                    self.wave_canvas.create_line(
                        ruler_x - tick_len, y, ruler_x, y,
                        fill="#ddd" if db == 0 else "#555", width=1
                    )

            label_y = mid - y_offset
            if 0 <= label_y <= h and db in labeled:
                self.wave_canvas.create_text(
                    ruler_x + 4, label_y,
                    text=str(db),
                    fill="#ddd" if db == 0 else self.fg_color,
                    font=("Consolas", 8), anchor=tk.W
                )

    def _nice_number(self, x: float) -> float:
        if x == 0:
            return 1
        exp = math.floor(math.log10(x))
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
