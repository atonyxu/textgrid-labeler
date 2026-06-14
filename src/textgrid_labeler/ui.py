import tkinter as tk
from tkinter import ttk


class UIBuilder:
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

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Undo", command=self._undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Redo", command=self._redo, accelerator="Ctrl+Y")
        menubar.add_cascade(label="Edit", menu=edit_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.bind_all("<Control-o>", lambda e: self._open_textgrid())
        self.bind_all("<Control-w>", lambda e: self._open_wav())
        self.bind_all("<Control-s>", lambda e: self._save_textgrid())
        self.bind_all("<Control-Shift-S>", lambda e: self._save_as_textgrid())
        self.bind_all("<Control-Shift-s>", lambda e: self._save_as_textgrid())
        self.bind_all("<Control-z>", lambda e: self._undo())
        self.bind_all("<Control-Z>", lambda e: self._undo())
        self.bind_all("<Control-y>", lambda e: self._redo())
        self.bind_all("<Control-Y>", lambda e: self._redo())

    def _build_toolbar(self):
        toolbar = tk.Frame(self, height=40)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=0, pady=0)
        toolbar.pack_propagate(False)

        left_frame = tk.Frame(toolbar)
        left_frame.pack(side=tk.LEFT, padx=8, pady=4)

        tk.Label(left_frame, text="Layer:",
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 4))

        self.layer_var = tk.StringVar()
        self.layer_combo = ttk.Combobox(left_frame, textvariable=self.layer_var,
                                         state="readonly", width=22, font=("Segoe UI", 10))
        self.layer_combo.pack(side=tk.LEFT, padx=(0, 4))
        self.layer_combo.bind("<<ComboboxSelected>>", self._on_layer_changed)

        search_frame = tk.Frame(toolbar)
        search_frame.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=20, pady=4)

        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                                      font=("Segoe UI", 10))
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=2)
        self.search_entry.bind("<Return>", lambda e: self._do_search())

        right_frame = tk.Frame(toolbar)
        right_frame.pack(side=tk.RIGHT, padx=8, pady=4)

        self.btn_prev = tk.Button(right_frame, text="\u25c0", width=3,
                                   font=("Segoe UI", 10),
                                   command=self._search_prev)
        self.btn_prev.pack(side=tk.LEFT, padx=1)

        self.btn_next = tk.Button(right_frame, text="\u25b6", width=3,
                                   font=("Segoe UI", 10),
                                   command=self._search_next)
        self.btn_next.pack(side=tk.LEFT, padx=1)

        self.search_count_label = tk.Label(right_frame, text="",
                                            font=("Segoe UI", 9))
        self.search_count_label.pack(side=tk.LEFT, padx=(4, 0))

    def _build_canvases(self):
        main_frame = tk.Frame(self, bg=self.bg_color)
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        wave_frame = tk.Frame(main_frame, bg=self.bg_color)
        wave_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.annot_canvas = tk.Canvas(wave_frame, bg=self.label_bg,
                                       height=40, highlightthickness=0)
        self.annot_canvas.pack(side=tk.TOP, fill=tk.X)

        self.ruler_canvas = tk.Canvas(wave_frame, bg="#252526",
                                       height=22, highlightthickness=0)
        self.ruler_canvas.pack(side=tk.TOP, fill=tk.X)

        self.wave_canvas = tk.Canvas(wave_frame, bg=self.bg_color,
                                      highlightthickness=0)
        self.wave_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self._build_annotation_list(main_frame)

    def _build_annotation_list(self, parent):
        panel = tk.Frame(parent, width=180, bg="#f0f0f0")
        panel.pack(side=tk.RIGHT, fill=tk.Y)
        panel.pack_propagate(False)

        header = tk.Frame(panel, bg="#e0e0e0")
        header.pack(side=tk.TOP, fill=tk.X)

        tk.Label(header, text="Annotations", font=("Segoe UI", 10, "bold"),
                 bg="#e0e0e0").pack(side=tk.LEFT, padx=8, pady=4)

        columns = ("label", "start", "dur")
        self.annot_tree = ttk.Treeview(panel, columns=columns, show="headings",
                                        height=12)
        self.annot_tree.heading("label", text="Label")
        self.annot_tree.heading("start", text="Start (s)")
        self.annot_tree.heading("dur", text="Dur (ms)")
        self.annot_tree.column("label", width=80, minwidth=60)
        self.annot_tree.column("start", width=50, minwidth=40)
        self.annot_tree.column("dur", width=45, minwidth=40)
        self.annot_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(panel, orient=tk.VERTICAL, command=self.annot_tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.annot_tree.configure(yscrollcommand=scroll.set)

        self.annot_tree.bind("<<TreeviewSelect>>", self._on_annotation_selected)

    def _build_scrollbar(self):
        scroll_frame = tk.Frame(self)
        scroll_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(2, 6))

        self.time_label = tk.Label(scroll_frame, text="0.000s / 0.000s",
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
