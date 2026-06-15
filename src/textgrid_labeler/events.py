from tkinter import simpledialog, messagebox
from typing import List, Tuple

import textgrid
import copy


class EventHandlerMixin:
    def _pixel_to_time(self, px: int) -> float:
        w = self.wave_canvas.winfo_width()
        if w <= 0:
            return self.visible_start
        effective_w = w - self.ruler_w
        px = max(0, min(px, effective_w - 1))
        return self.visible_start + (px / effective_w) * self.visible_duration

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

    def _save_state(self):
        if self.textgrid is None:
            return
        self.undo_stack.append(copy.deepcopy(self.textgrid))
        self.redo_stack.clear()
        if len(self.undo_stack) > 100:
            self.undo_stack.pop(0)
        return

    def _undo(self):
        if not self.undo_stack:
            return
        self.redo_stack.append(copy.deepcopy(self.textgrid))
        self.textgrid = self.undo_stack.pop()
        self.modified = True
        self.search_results = []
        self.search_index = -1
        self.selected_idx = -1
        self._update_search_display(redraw=False)
        self._update_view()
        self._populate_annotation_list()
        self.set_status("Undo")

    def _redo(self):
        if not self.redo_stack:
            return
        self.undo_stack.append(copy.deepcopy(self.textgrid))
        self.textgrid = self.redo_stack.pop()
        self.modified = True
        self.search_results = []
        self.search_index = -1
        self.selected_idx = -1
        self._update_search_display(redraw=False)
        self._update_view()
        self._populate_annotation_list()
        self.set_status("Redo")

    def _on_canvas_motion(self, event):
        x = event.x
        h = self.wave_canvas.winfo_height()
        items = self.wave_canvas.find_withtag("cursor")
        if items:
            self.wave_canvas.coords(items[0], x, 0, x, h)
        else:
            self.wave_canvas.create_line(x, 0, x, h, fill="#ffcc00", dash=(3, 3), width=1, tags=("cursor",))
        self.wave_canvas.tag_raise("cursor")

    def _on_canvas_leave(self, event):
        self.wave_canvas.delete("cursor")

    def _on_canvas_click(self, event):
        if not self.textgrid:
            return
        click_time = self._pixel_to_time(event.x)
        tier = self._get_current_tier()
        if not tier or not hasattr(tier, "intervals"):
            return

        bound_time, found = self._find_nearest_boundary(click_time, max_dist=0.05)
        if found:
            self._save_state()
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

        bound_time, found = self._find_nearest_boundary(click_time, max_dist=0.03)
        if found:
            if bound_time <= tier.minTime or bound_time >= tier.maxTime:
                return
            for i, iv in enumerate(tier.intervals):
                if abs(iv.maxTime - bound_time) < 0.001:
                    if not messagebox.askyesno("Delete Boundary",
                                               f"Delete boundary at {bound_time:.3f}s and merge intervals?"):
                        return
                    self._save_state()
                    right = tier.intervals[i + 1]
                    iv.maxTime = right.maxTime
                    del tier.intervals[i + 1]
                    self.modified = True
                    self.selected_idx = -1
                    self._update_view()
                    self._populate_annotation_list()
                    self.set_status(f"Deleted boundary at {bound_time:.3f}s")
                    return
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
            self._populate_annotation_list()
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
        if new_text is not None and new_text != interval.mark:
            self._save_state()
            interval.mark = new_text
            self.modified = True
            self.selected_idx = -1
            self._update_view()
            self._populate_annotation_list()
            self.set_status(f"Label updated: {new_text}")

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

    def _add_annotation_boundary(self, interval_idx: int, time: float, text: str = ""):
        tier = self._get_current_tier()
        if not tier or not hasattr(tier, "intervals"):
            return

        interval = tier.intervals[interval_idx]
        if time <= interval.minTime or time >= interval.maxTime:
            return

        if not text:
            text = interval.mark
        self._save_state()
        old_xmax = interval.maxTime
        interval.maxTime = time

        new_interval = textgrid.Interval(minTime=time, maxTime=old_xmax, mark=text)
        tier.intervals.insert(interval_idx + 1, new_interval)

        self.modified = True
        self._update_view()
        self._populate_annotation_list()
        self.set_status(f"Added boundary at {time:.3f}s")
