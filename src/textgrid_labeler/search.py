class SearchMixin:
    def _do_search(self):
        if not self.textgrid:
            self.search_results = []
            self.search_index = -1
            self._update_search_display()
            self._populate_annotation_list()
            return

        query = self.search_var.get().strip().lower()
        if not query:
            self.search_results = []
            self.search_index = -1
            self._update_search_display()
            self._populate_annotation_list()
            return

        tier = self._get_current_tier()
        if not tier or not hasattr(tier, "intervals"):
            self.search_results = []
            self.search_index = -1
            self._update_search_display()
            self._populate_annotation_list()
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
        self._populate_annotation_list()

    def _search_next(self):
        if not self.search_results:
            return
        self.search_index = (self.search_index + 1) % len(self.search_results)
        idx = self.search_results[self.search_index]
        self._scroll_to_result(idx)
        self.annot_tree.selection_set(str(idx))
        self.annot_tree.see(str(idx))
        self._update_search_display()

    def _search_prev(self):
        if not self.search_results:
            return
        self.search_index = (self.search_index - 1) % len(self.search_results)
        idx = self.search_results[self.search_index]
        self._scroll_to_result(idx)
        self.annot_tree.selection_set(str(idx))
        self.annot_tree.see(str(idx))
        self._update_search_display()

    def _scroll_to_result(self, interval_idx: int):
        tier = self._get_current_tier()
        if not tier or interval_idx >= len(tier.intervals):
            return
        interval = tier.intervals[interval_idx]
        center = (interval.minTime + interval.maxTime) / 2
        self.visible_start = center - self.visible_duration / 2
        self._clamp_view()
        self.selected_idx = interval_idx
        self._update_view()

    def _update_search_display(self, redraw=True):
        n = len(self.search_results)
        if n == 0:
            self.search_count_label.config(text="")
        else:
            pos = self.search_index if 0 <= self.search_index < n else 0
            self.search_count_label.config(text=f"{pos + 1}/{n}")

        if redraw:
            self._update_view()
