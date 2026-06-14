class ViewManagerMixin:
    def _on_data_loaded(self):
        if not self.textgrid:
            return

        self.selected_idx = -1
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
        self._populate_annotation_list()

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
            self.selected_idx = -1
            self._update_search_display(redraw=False)
            self._update_view()
            self._populate_annotation_list()
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

    def _populate_annotation_list(self):
        for item in self.annot_tree.get_children():
            self.annot_tree.delete(item)

        tier = self._get_current_tier()
        if not tier or not hasattr(tier, "intervals"):
            return

        query = self.search_var.get().strip().lower()

        for i, interval in enumerate(tier.intervals):
            if query and query not in interval.mark.lower():
                continue
            dur_ms = (interval.maxTime - interval.minTime) * 1000
            self.annot_tree.insert("", "end", iid=str(i),
                                   values=(interval.mark or "(sil)",
                                           f"{interval.minTime:.3f}",
                                           f"{dur_ms:.0f}"))

    def _on_annotation_selected(self, event):
        sel = self.annot_tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        tier = self._get_current_tier()
        if not tier or idx >= len(tier.intervals):
            return
        interval = tier.intervals[idx]
        center = (interval.minTime + interval.maxTime) / 2
        self.visible_start = center - self.visible_duration / 2
        self._clamp_view()
        self.selected_idx = idx

        if self.search_results:
            try:
                self.search_index = self.search_results.index(idx)
            except ValueError:
                self.search_results = [idx]
                self.search_index = 0
                self._populate_annotation_list()
                self.annot_tree.selection_set(str(idx))
        else:
            self.search_results = [idx]
            self.search_index = 0

        self._update_search_display(redraw=False)
        self._update_view()
