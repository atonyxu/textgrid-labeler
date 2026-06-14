class SearchMixin:
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
