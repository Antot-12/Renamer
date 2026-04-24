"""Main application UI and logic."""

from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List, Optional
from pathlib import Path

# Try to import drag-and-drop support (may not work on all platforms)
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except (ImportError, RuntimeError):
    DND_AVAILABLE = False
    TkinterDnD = None
    DND_FILES = None

import ttkbootstrap as tb
from PIL import Image, ImageTk, UnidentifiedImageError

from renamer.constants import (
    AUDIO, IMG, DOC, VID, ARC, PRESENTATION, CODE, TEXT, GAME, SUPPORTED,
    TYPE_EMOJI, MAX_FILES, MAX_PREVIEW_SIZE, MAX_PREVIEW_MEMORY, MAX_LOG_LINES,
)
from renamer.metadata import sanitize, bytes_to_human_readable, extract_metadata, get_audio_tags
from renamer.file_ops import (
    FileEntry, AppState, collect_files, is_duplicate_name,
    check_for_duplicate_destinations, FileOperationWorker,
)

# Dark Neon Cyan Theme Colors
COLORS = {
    "bg_dark": "#0a0a0a",
    "bg_main": "#0d0d0d",
    "bg_secondary": "#151515",
    "bg_input": "#1a1a1a",
    "bg_hover": "#202020",
    "cyan": "#00ffff",
    "cyan_dark": "#00cccc",
    "cyan_glow": "#00ffff",
    "cyan_dim": "#008888",
    "text": "#e0e0e0",
    "text_dim": "#888888",
    "success": "#00ff88",
    "error": "#ff4466",
    "warning": "#ffaa00",
}


class Settings:
    """Налаштування програми з збереженням."""

    DEFAULT_SETTINGS = {
        "auto_select_all": True,
        "confirm_rename": False,
        "confirm_large_batch": True,
        "large_batch_threshold": 100,
        "auto_remove_after_rename": True,
        "show_notifications": True,
        "default_template": "Оригінал",
        "default_mode": "move",
        "ask_metadata_audio": False,
        "use_original_name_fallback": True,
    }

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path.home() / ".renamer_config.json"
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.load()

    def load(self) -> None:
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.settings.update(loaded)
        except (json.JSONDecodeError, IOError):
            pass

    def save(self) -> None:
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except IOError:
            pass

    def get(self, key: str, default=None):
        return self.settings.get(key, default)

    def set(self, key: str, value) -> None:
        self.settings[key] = value
        self.save()


class RenamerApp:
    """Головний клас програми для GUI."""

    TEMPLATES = {
        "Оригінал": lambda a, t, i, ext: t + ext if t else "",
        "Виконавець - Назва": lambda a, t, i, ext: f"{a} - {t}{ext}" if a and t else (t + ext if t else ""),
        "Назва (Виконавець)": lambda a, t, i, ext: f"{t} ({a}){ext}" if a and t else (t + ext if t else ""),
        "## - Назва": lambda a, t, i, ext: f"{i:02d} - {t}{ext}" if t else "",
        "### - Назва": lambda a, t, i, ext: f"{i:03d} - {t}{ext}" if t else "",
        "ВЕЛИКІ ЛІТЕРИ": lambda a, t, i, ext: (t.upper() + ext) if t else "",
        "малі літери": lambda a, t, i, ext: (t.lower() + ext) if t else "",
    }

    def __init__(self) -> None:
        self.settings = Settings()
        self.state = AppState()
        self._preview_references: List[ImageTk.PhotoImage] = []
        self._log_line_count = 0
        self._operation_worker: Optional[FileOperationWorker] = None

        self._setup_root()
        self._setup_variables()
        self._setup_notebook()
        self._setup_main_page()
        self._setup_settings_page()
        self._setup_bindings()

    def _setup_root(self) -> None:
        """Ініціалізація головного вікна з темною неоновою темою."""
        if DND_AVAILABLE:
            try:
                self.root = TkinterDnD.Tk()
                self.dnd_enabled = True
            except RuntimeError:
                self.root = tk.Tk()
                self.dnd_enabled = False
        else:
            self.root = tk.Tk()
            self.dnd_enabled = False

        self.root.title("🔄 Перейменувач файлів")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)
        self.root.configure(bg=COLORS["bg_main"])

        # Initialize ttkbootstrap with cyborg theme and override colors
        self.style = tb.Style("cyborg")

        # Override the theme colors to use cyan
        self.style.colors.primary = COLORS["cyan"]
        self.style.colors.secondary = COLORS["cyan_dim"]
        self.style.colors.info = COLORS["cyan"]
        self.style.colors.success = COLORS["success"]
        self.style.colors.warning = COLORS["warning"]
        self.style.colors.danger = COLORS["error"]

        # Configure custom styles
        self._configure_styles()

    def _configure_styles(self) -> None:
        """Налаштування стилів для темної неонової теми."""
        s = self.style

        # General
        s.configure(".", background=COLORS["bg_main"], foreground=COLORS["cyan"])

        # Notebook (tabs)
        s.configure("TNotebook", background=COLORS["bg_main"], borderwidth=0)
        s.configure("TNotebook.Tab",
                    background=COLORS["bg_secondary"],
                    foreground=COLORS["cyan"],
                    padding=[25, 12],
                    font=("Segoe UI", 11, "bold"))
        s.map("TNotebook.Tab",
              background=[("selected", COLORS["bg_main"]), ("active", COLORS["bg_hover"])],
              foreground=[("selected", COLORS["cyan_glow"])])

        # Treeview
        s.configure("Treeview",
                    background=COLORS["bg_input"],
                    foreground=COLORS["cyan"],
                    fieldbackground=COLORS["bg_input"],
                    font=("Consolas", 10),
                    rowheight=32)
        s.configure("Treeview.Heading",
                    background=COLORS["bg_secondary"],
                    foreground=COLORS["cyan"],
                    font=("Segoe UI", 10, "bold"))
        s.map("Treeview",
              background=[("selected", COLORS["cyan_dim"])],
              foreground=[("selected", "#ffffff")])

        # Labels
        s.configure("TLabel", background=COLORS["bg_main"], foreground=COLORS["cyan"])
        s.configure("Cyan.TLabel", foreground=COLORS["cyan"], font=("Segoe UI", 10))
        s.configure("Title.TLabel", foreground=COLORS["cyan_glow"], font=("Segoe UI", 18, "bold"))
        s.configure("Dim.TLabel", foreground=COLORS["text_dim"])

        # LabelFrame
        s.configure("TLabelframe", background=COLORS["bg_main"])
        s.configure("TLabelframe.Label",
                    background=COLORS["bg_main"],
                    foreground=COLORS["cyan"],
                    font=("Segoe UI", 10, "bold"))

        # Custom Cyan Button (solid)
        s.configure("Cyan.TButton",
                    background=COLORS["cyan_dim"],
                    foreground="#000000",
                    font=("Segoe UI", 10, "bold"),
                    padding=[12, 6])
        s.map("Cyan.TButton",
              background=[("active", COLORS["cyan"]), ("pressed", COLORS["cyan_dark"])],
              foreground=[("active", "#000000")])

        # Outline Cyan Button
        s.configure("CyanOutline.TButton",
                    background=COLORS["bg_main"],
                    foreground=COLORS["cyan"],
                    font=("Segoe UI", 10),
                    padding=[12, 6])
        s.map("CyanOutline.TButton",
              background=[("active", COLORS["cyan_dim"])],
              foreground=[("active", "#000000")])

        # Success Button (green)
        s.configure("Success.TButton",
                    background=COLORS["success"],
                    foreground="#000000",
                    font=("Segoe UI", 10, "bold"),
                    padding=[12, 6])
        s.map("Success.TButton",
              background=[("active", "#00ff99")],
              foreground=[("active", "#000000")])

        # Danger Button (red)
        s.configure("Danger.TButton",
                    background=COLORS["error"],
                    foreground="#ffffff",
                    font=("Segoe UI", 10),
                    padding=[12, 6])
        s.map("Danger.TButton",
              background=[("active", "#ff6688")],
              foreground=[("active", "#000000")])

        # Scale/Slider
        s.configure("Cyan.Horizontal.TScale",
                    background=COLORS["bg_main"],
                    troughcolor=COLORS["bg_input"])

        # Checkbutton - cyan style
        s.configure("Cyan.TCheckbutton",
                    background=COLORS["bg_main"],
                    foreground=COLORS["cyan"],
                    font=("Segoe UI", 10))
        s.map("Cyan.TCheckbutton",
              foreground=[("active", COLORS["cyan_glow"])])

        # Radiobutton - cyan style
        s.configure("Cyan.TRadiobutton",
                    background=COLORS["bg_main"],
                    foreground=COLORS["cyan"],
                    font=("Segoe UI", 10))
        s.map("Cyan.TRadiobutton",
              foreground=[("active", COLORS["cyan_glow"])])

        # Combobox
        s.configure("TCombobox",
                    fieldbackground=COLORS["bg_input"],
                    background=COLORS["bg_input"],
                    foreground=COLORS["cyan"])

        # Entry
        s.configure("TEntry",
                    fieldbackground=COLORS["bg_input"],
                    foreground=COLORS["cyan"])

    def _setup_variables(self) -> None:
        """Ініціалізація змінних tkinter."""
        self.tmpl_var = tk.StringVar(value=self.settings.get("default_template", "Оригінал"))
        self.pre_var = tk.StringVar()
        self.suf_var = tk.StringVar()
        self.find_var = tk.StringVar()
        self.repl_var = tk.StringVar()
        self.copy_var = tk.BooleanVar(value=self.settings.get("default_mode") == "copy")
        self.tgt_var = tk.StringVar()
        self.count_var = tk.StringVar(value="Вибрано: 0/0")
        self.context_idx = tk.IntVar(value=-1)
        self.status_var = tk.StringVar(value="✨ Готово до роботи")

        # Settings variables
        self.auto_select_var = tk.BooleanVar(value=self.settings.get("auto_select_all"))
        self.confirm_rename_var = tk.BooleanVar(value=self.settings.get("confirm_rename"))
        self.confirm_large_var = tk.BooleanVar(value=self.settings.get("confirm_large_batch"))
        self.large_threshold_var = tk.IntVar(value=self.settings.get("large_batch_threshold"))
        self.auto_remove_var = tk.BooleanVar(value=self.settings.get("auto_remove_after_rename"))
        self.show_notif_var = tk.BooleanVar(value=self.settings.get("show_notifications"))
        self.ask_metadata_var = tk.BooleanVar(value=self.settings.get("ask_metadata_audio"))
        self.use_fallback_var = tk.BooleanVar(value=self.settings.get("use_original_name_fallback"))
        self.default_tmpl_var = tk.StringVar(value=self.settings.get("default_template", "Оригінал"))

    def _setup_notebook(self) -> None:
        """Створення вкладок."""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        self.main_frame = tk.Frame(self.notebook, bg=COLORS["bg_main"])
        self.settings_frame = tk.Frame(self.notebook, bg=COLORS["bg_main"])

        self.notebook.add(self.main_frame, text="  📁 Файли  ")
        self.notebook.add(self.settings_frame, text="  ⚙️ Налаштування  ")

    def _create_cyan_button(self, parent, text: str, command, width: int = 14, style: str = "solid") -> tb.Button:
        """Створити кнопку з неоновим cyan стилем."""
        style_map = {
            "solid": "info",
            "outline": "info-outline",
            "success": "success",
            "danger": "danger-outline",
        }
        bootstyle = style_map.get(style, "info")
        return tb.Button(parent, text=text, command=command, width=width, bootstyle=bootstyle)

    def _setup_main_page(self) -> None:
        """Налаштування головної сторінки."""
        # Toolbar
        toolbar = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        toolbar.pack(fill=tk.X, padx=10, pady=(10, 5))

        # File buttons
        btn_frame = tk.Frame(toolbar, bg=COLORS["bg_main"])
        btn_frame.pack(side=tk.LEFT)

        self._create_cyan_button(btn_frame, "📄 Додати файли", self._add_files, 14, "solid").pack(side=tk.LEFT, padx=(0, 5))
        self._create_cyan_button(btn_frame, "📁 Додати папку", self._add_folder, 14, "solid").pack(side=tk.LEFT, padx=(0, 15))
        self._create_cyan_button(btn_frame, "✓ Вибрати все", self._select_all, 12, "outline").pack(side=tk.LEFT, padx=2)
        self._create_cyan_button(btn_frame, "✗ Зняти вибір", self._deselect_all, 12, "outline").pack(side=tk.LEFT, padx=2)
        self._create_cyan_button(btn_frame, "🗑 Очистити", self._clear_all, 10, "danger").pack(side=tk.LEFT, padx=(15, 0))

        # Counter
        tk.Label(toolbar, textvariable=self.count_var,
                 font=("Segoe UI", 12, "bold"), fg=COLORS["cyan"],
                 bg=COLORS["bg_main"]).pack(side=tk.RIGHT, padx=10)

        # Template settings frame
        tmpl_frame = tk.LabelFrame(self.main_frame, text=" Налаштування перейменування ",
                                   bg=COLORS["bg_main"], fg=COLORS["cyan"],
                                   font=("Segoe UI", 10, "bold"))
        tmpl_frame.pack(fill=tk.X, padx=10, pady=8)

        inner = tk.Frame(tmpl_frame, bg=COLORS["bg_main"])
        inner.pack(fill=tk.X, padx=15, pady=12)

        # Row 1
        row1 = tk.Frame(inner, bg=COLORS["bg_main"])
        row1.pack(fill=tk.X, pady=(0, 10))

        tk.Label(row1, text="Шаблон:", bg=COLORS["bg_main"], fg=COLORS["cyan"],
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)
        tmpl_combo = ttk.Combobox(row1, textvariable=self.tmpl_var,
                                   values=list(self.TEMPLATES.keys()), width=20, state="readonly")
        tmpl_combo.pack(side=tk.LEFT, padx=(5, 25))
        tmpl_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_names())

        tk.Label(row1, text="Префікс:", bg=COLORS["bg_main"], fg=COLORS["cyan"],
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)
        pre_entry = tk.Entry(row1, textvariable=self.pre_var, width=12,
                             bg=COLORS["bg_input"], fg=COLORS["cyan"],
                             insertbackground=COLORS["cyan"], relief="flat", font=("Consolas", 10))
        pre_entry.pack(side=tk.LEFT, padx=(5, 25))
        pre_entry.bind("<KeyRelease>", lambda e: self._refresh_names())

        tk.Label(row1, text="Суфікс:", bg=COLORS["bg_main"], fg=COLORS["cyan"],
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)
        suf_entry = tk.Entry(row1, textvariable=self.suf_var, width=12,
                             bg=COLORS["bg_input"], fg=COLORS["cyan"],
                             insertbackground=COLORS["cyan"], relief="flat", font=("Consolas", 10))
        suf_entry.pack(side=tk.LEFT, padx=(5, 0))
        suf_entry.bind("<KeyRelease>", lambda e: self._refresh_names())

        # Row 2
        row2 = tk.Frame(inner, bg=COLORS["bg_main"])
        row2.pack(fill=tk.X)

        tk.Label(row2, text="Знайти:", bg=COLORS["bg_main"], fg=COLORS["cyan"],
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)
        find_entry = tk.Entry(row2, textvariable=self.find_var, width=12,
                              bg=COLORS["bg_input"], fg=COLORS["cyan"],
                              insertbackground=COLORS["cyan"], relief="flat", font=("Consolas", 10))
        find_entry.pack(side=tk.LEFT, padx=(5, 15))
        find_entry.bind("<KeyRelease>", lambda e: self._refresh_names())

        tk.Label(row2, text="Замінити:", bg=COLORS["bg_main"], fg=COLORS["cyan"],
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)
        repl_entry = tk.Entry(row2, textvariable=self.repl_var, width=12,
                              bg=COLORS["bg_input"], fg=COLORS["cyan"],
                              insertbackground=COLORS["cyan"], relief="flat", font=("Consolas", 10))
        repl_entry.pack(side=tk.LEFT, padx=(5, 25))
        repl_entry.bind("<KeyRelease>", lambda e: self._refresh_names())

        tb.Checkbutton(row2, text="Копіювати (не переміщати)",
                       variable=self.copy_var, bootstyle="info").pack(side=tk.LEFT, padx=(0, 25))

        self._create_cyan_button(row2, "📂 Цільова папка", self._choose_target, 14, "outline").pack(side=tk.LEFT)

        tk.Label(row2, textvariable=self.tgt_var, bg=COLORS["bg_main"],
                 fg=COLORS["text_dim"], font=("Segoe UI", 9),
                 anchor="w", width=30).pack(side=tk.LEFT, padx=(10, 0))

        # Treeview
        self._setup_treeview()

        # Action bar
        action_bar = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        action_bar.pack(fill=tk.X, padx=10, pady=12)

        self._create_cyan_button(action_bar, "🚀 ПЕРЕЙМЕНУВАТИ", self._rename_selected, 18, "success").pack(side=tk.LEFT, padx=(0, 10))
        self._create_cyan_button(action_bar, "🔄 Оновити імена", self._refresh_names, 14, "outline").pack(side=tk.LEFT)

        # Status bar
        status_bar = tk.Frame(self.main_frame, bg=COLORS["bg_secondary"])
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Label(status_bar, textvariable=self.status_var, bg=COLORS["bg_secondary"],
                 fg=COLORS["cyan_dim"], font=("Segoe UI", 9), anchor="w",
                 padx=15, pady=8).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Log
        self._setup_log_area()

    def _setup_treeview(self) -> None:
        """Створення таблиці файлів."""
        tree_frame = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        cols = ("✓", "№", "Тип", "Стара назва", "Нова назва", "Розмір", "Інфо")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="extended")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        col_widths = {"✓": 40, "№": 50, "Тип": 50, "Стара назва": 280,
                      "Нова назва": 280, "Розмір": 100, "Інфо": 120}
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=col_widths.get(c, 100), anchor="w")

        if self.dnd_enabled:
            self.tree.drop_target_register(DND_FILES)

        # Context menu
        self.row_menu = tk.Menu(self.root, tearoff=0, bg=COLORS["bg_secondary"],
                                 fg=COLORS["cyan"], activebackground=COLORS["cyan_dim"],
                                 activeforeground="#000000")
        self.row_menu.add_command(label="✏️ Редагувати ім'я", command=self._edit_name)
        self.row_menu.add_command(label="👁 Перегляд", command=self._preview_selected)
        self.row_menu.add_separator()
        self.row_menu.add_command(label="❌ Видалити вибране", command=self._delete_selected)

    def _setup_log_area(self) -> None:
        """Створення області логу."""
        log_frame = tk.LabelFrame(self.main_frame, text=" Журнал ",
                                   bg=COLORS["bg_main"], fg=COLORS["cyan"],
                                   font=("Segoe UI", 9))
        log_frame.pack(fill=tk.X, padx=10, pady=(0, 8))

        self.log_box = tk.Text(log_frame, height=4, fg=COLORS["cyan"],
                                bg=COLORS["bg_input"], font=("Consolas", 9),
                                state="disabled", wrap=tk.WORD, relief="flat")
        self.log_box.pack(fill=tk.X, padx=8, pady=8)

    def _setup_settings_page(self) -> None:
        """Налаштування сторінки параметрів."""
        # Scrollable container
        canvas = tk.Canvas(self.settings_frame, bg=COLORS["bg_main"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.settings_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=COLORS["bg_main"])

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=20)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Enable mouse wheel scrolling (works with touchpad on Mac/Windows/Linux)
        def _on_mousewheel(event):
            # Mac uses event.delta directly (positive = scroll up)
            # Windows uses event.delta / 120
            # Linux uses Button-4/5
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")
            elif event.delta:
                # Mac: delta is larger, around 1-5 per scroll
                # Windows: delta is 120 per notch
                if abs(event.delta) > 100:
                    # Windows
                    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                else:
                    # Mac - smaller delta values
                    canvas.yview_scroll(int(-1 * event.delta), "units")

        # Bind only when mouse is over settings frame
        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            canvas.bind_all("<Button-4>", _on_mousewheel)
            canvas.bind_all("<Button-5>", _on_mousewheel)

        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)
        scrollable_frame.bind("<Enter>", _bind_mousewheel)
        scrollable_frame.bind("<Leave>", _unbind_mousewheel)

        # Store canvas reference for cleanup
        self._settings_canvas = canvas

        container = scrollable_frame

        # Title
        tk.Label(container, text="⚙️ Налаштування", font=("Segoe UI", 22, "bold"),
                 bg=COLORS["bg_main"], fg=COLORS["cyan_glow"]).pack(anchor="w", pady=(0, 25))

        # Settings groups
        self._create_settings_group(container, "📂 Вибір файлів", [
            ("Автоматично вибирати всі файли при додаванні", self.auto_select_var),
            ("Використовувати оригінальну назву як запасний варіант", self.use_fallback_var),
        ])

        self._create_settings_group(container, "❓ Підтвердження", [
            ("Запитувати підтвердження перед кожним перейменуванням", self.confirm_rename_var),
            ("Підтверджувати лише для великих пакетів", self.confirm_large_var),
        ])

        # Threshold slider
        threshold_frame = tk.LabelFrame(container, text=" 📊 Поріг великого пакету ",
                                         bg=COLORS["bg_main"], fg=COLORS["cyan"],
                                         font=("Segoe UI", 10, "bold"))
        threshold_frame.pack(fill=tk.X, pady=12)

        slider_inner = tk.Frame(threshold_frame, bg=COLORS["bg_main"])
        slider_inner.pack(fill=tk.X, padx=20, pady=15)

        self.threshold_label = tk.Label(slider_inner,
                                         text=f"{self.large_threshold_var.get()} файлів",
                                         bg=COLORS["bg_main"], fg=COLORS["cyan_glow"],
                                         font=("Segoe UI", 14, "bold"))
        self.threshold_label.pack(anchor="w")

        def update_threshold(val):
            int_val = int(float(val))
            self.large_threshold_var.set(int_val)
            self.threshold_label.config(text=f"{int_val} файлів")

        # Use ttk.Scale with cyan style
        threshold_scale = ttk.Scale(slider_inner, from_=10, to=500,
                                    variable=self.large_threshold_var,
                                    orient=tk.HORIZONTAL, length=400,
                                    command=update_threshold,
                                    style="Cyan.Horizontal.TScale")
        threshold_scale.pack(anchor="w", pady=(10, 0))

        # Bind mouse wheel for touchpad scrolling on the scale
        def scale_scroll(event):
            current = self.large_threshold_var.get()
            if event.delta > 0 or event.num == 4:
                new_val = min(500, current + 10)
            else:
                new_val = max(10, current - 10)
            self.large_threshold_var.set(new_val)
            update_threshold(new_val)

        threshold_scale.bind("<MouseWheel>", scale_scroll)
        threshold_scale.bind("<Button-4>", scale_scroll)
        threshold_scale.bind("<Button-5>", scale_scroll)

        self._create_settings_group(container, "✅ Після перейменування", [
            ("Видаляти файли зі списку після успішного перейменування", self.auto_remove_var),
            ("Показувати сповіщення про завершення", self.show_notif_var),
        ])

        self._create_settings_group(container, "🎵 Аудіофайли", [
            ("Запитувати виконавця/назву, якщо немає в метаданих", self.ask_metadata_var),
        ])

        # Default template
        tmpl_group = tk.LabelFrame(container, text=" 📝 Шаблон за замовчуванням ",
                                    bg=COLORS["bg_main"], fg=COLORS["cyan"],
                                    font=("Segoe UI", 10, "bold"))
        tmpl_group.pack(fill=tk.X, pady=12)

        tmpl_inner = tk.Frame(tmpl_group, bg=COLORS["bg_main"])
        tmpl_inner.pack(fill=tk.X, padx=20, pady=15)

        for tmpl_name in list(self.TEMPLATES.keys()):
            rb = tb.Radiobutton(tmpl_inner, text=tmpl_name, variable=self.default_tmpl_var,
                                value=tmpl_name, bootstyle="info")
            rb.pack(anchor="w", pady=4)

        # Save/Reset buttons
        btn_frame = tk.Frame(container, bg=COLORS["bg_main"])
        btn_frame.pack(fill=tk.X, pady=30)

        self._create_cyan_button(btn_frame, "💾 Зберегти налаштування", self._save_settings, 22, "success").pack(side=tk.LEFT)
        self._create_cyan_button(btn_frame, "↩️ Скинути до стандартних", self._reset_settings, 22, "danger").pack(side=tk.LEFT, padx=15)

    def _create_settings_group(self, parent, title: str, options: list) -> None:
        """Створення групи налаштувань."""
        group = tk.LabelFrame(parent, text=f" {title} ", bg=COLORS["bg_main"],
                               fg=COLORS["cyan"], font=("Segoe UI", 10, "bold"))
        group.pack(fill=tk.X, pady=12)

        inner = tk.Frame(group, bg=COLORS["bg_main"])
        inner.pack(fill=tk.X, padx=20, pady=15)

        for label, var in options:
            cb = tb.Checkbutton(inner, text=label, variable=var, bootstyle="info")
            cb.pack(anchor="w", pady=6)

    def _save_settings(self) -> None:
        """Зберегти всі налаштування."""
        self.settings.set("auto_select_all", self.auto_select_var.get())
        self.settings.set("confirm_rename", self.confirm_rename_var.get())
        self.settings.set("confirm_large_batch", self.confirm_large_var.get())
        self.settings.set("large_batch_threshold", self.large_threshold_var.get())
        self.settings.set("auto_remove_after_rename", self.auto_remove_var.get())
        self.settings.set("show_notifications", self.show_notif_var.get())
        self.settings.set("ask_metadata_audio", self.ask_metadata_var.get())
        self.settings.set("use_original_name_fallback", self.use_fallback_var.get())
        self.settings.set("default_template", self.default_tmpl_var.get())
        self.settings.set("default_mode", "copy" if self.copy_var.get() else "move")

        self._set_status("✅ Налаштування збережено!")
        if self.show_notif_var.get():
            messagebox.showinfo("Успіх", "Налаштування успішно збережено!")

    def _reset_settings(self) -> None:
        """Скинути налаштування до стандартних."""
        if not messagebox.askyesno("Підтвердження", "Скинути всі налаштування до стандартних?"):
            return

        self.settings.settings = Settings.DEFAULT_SETTINGS.copy()
        self.settings.save()

        self.auto_select_var.set(True)
        self.confirm_rename_var.set(False)
        self.confirm_large_var.set(True)
        self.large_threshold_var.set(100)
        self.auto_remove_var.set(True)
        self.show_notif_var.set(True)
        self.ask_metadata_var.set(False)
        self.use_fallback_var.set(True)
        self.default_tmpl_var.set("Оригінал")
        self.threshold_label.config(text="100 файлів")

        self._set_status("✅ Налаштування скинуто!")

    def _setup_bindings(self) -> None:
        """Налаштування прив'язок подій."""
        self.tree.bind("<Button-1>", self._on_click)
        self.tree.bind("<Double-Button-1>", self._on_double_click)
        self.tree.bind("<Delete>", self._delete_selected)
        self.tree.bind("<Button-3>", self._on_context)
        if self.dnd_enabled:
            self.tree.dnd_bind("<<Drop>>", self._on_drop)
        self.root.bind("<Control-a>", lambda e: self._select_all())
        self.root.bind("<Control-d>", lambda e: self._deselect_all())

    # ========== File Operations ==========

    def _template_name(self, artist: str, title: str, idx: int, ext: str) -> str:
        tmpl = self.tmpl_var.get()
        template_func = self.TEMPLATES.get(tmpl, self.TEMPLATES["Оригінал"])
        base = template_func(artist, title, idx, "")
        if not base:
            base = title or "unnamed"
        prefix = self.pre_var.get()
        suffix = self.suf_var.get()
        base = prefix + base + suffix
        find_text = self.find_var.get()
        replace_text = self.repl_var.get()
        if find_text:
            base = base.replace(find_text, replace_text)
        return sanitize(base) + ext

    def _get_file_type(self, ext: str) -> str:
        if ext in AUDIO: return TYPE_EMOJI["audio"]
        elif ext in IMG: return TYPE_EMOJI["image"]
        elif ext in DOC: return TYPE_EMOJI["document"]
        elif ext in VID: return TYPE_EMOJI["video"]
        elif ext in ARC: return TYPE_EMOJI["archive"]
        elif ext in PRESENTATION: return TYPE_EMOJI["presentation"]
        elif ext in CODE: return TYPE_EMOJI["code"]
        elif ext in TEXT: return TYPE_EMOJI["text"]
        elif ext in GAME: return TYPE_EMOJI["game"]
        return "📁"

    def _insert_row(self, entry: FileEntry) -> None:
        idx = len(self.state.entries) - 1
        self.tree.insert("", "end", iid=idx, values=(
            "✔" if entry.selected.get() else "", idx + 1, entry.file_type,
            entry.original, entry.new_name, bytes_to_human_readable(entry.size), entry.info
        ))

    def _refresh_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for i, entry in enumerate(self.state.entries):
            self.tree.insert("", "end", iid=i, values=(
                "✔" if entry.selected.get() else "", i + 1, entry.file_type,
                entry.original, entry.new_name, bytes_to_human_readable(entry.size), entry.info
            ))

    def _refresh_names(self, event=None) -> None:
        for i, entry in enumerate(self.state.entries):
            title = sanitize(os.path.splitext(entry.original)[0])
            artist = ""
            if entry.ext in AUDIO:
                try:
                    artist, tag_title, _, _ = get_audio_tags(entry.path)
                    if tag_title: title = sanitize(tag_title)
                    artist = sanitize(artist) if artist else ""
                except Exception:
                    pass
            entry.new_name = self._template_name(artist, title, i + 1, entry.ext)
            self.tree.set(i, "Нова назва", entry.new_name)
        self._set_status(f"🔄 Оновлено імена для {len(self.state.entries)} файлів")

    def _update_counter(self) -> None:
        total = len(self.state.entries)
        selected = self.state.count_selected()
        self.count_var.set(f"Вибрано: {selected}/{total}")

    def _set_status(self, message: str) -> None:
        self.status_var.set(message)

    # ========== Event Handlers ==========

    def _on_click(self, event: tk.Event) -> None:
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell": return
        col = self.tree.identify_column(event.x)
        item = self.tree.identify_row(event.y)
        if not item: return
        idx = int(item)
        if idx >= len(self.state.entries): return
        if col == "#1":
            entry = self.state.entries[idx]
            entry.selected.set(not entry.selected.get())
            self.tree.set(idx, "✓", "✔" if entry.selected.get() else "")
            self._update_counter()

    def _on_double_click(self, event: tk.Event) -> None:
        item = self.tree.identify_row(event.y)
        if not item: return
        col = self.tree.identify_column(event.x)
        idx = int(item)
        if idx >= len(self.state.entries): return
        entry = self.state.entries[idx]
        if col == "#5":
            self._edit_name_at(idx)
        elif entry.ext in IMG:
            self._preview_image(entry)

    def _on_context(self, event: tk.Event) -> None:
        row = self.tree.identify_row(event.y)
        if row:
            self.context_idx.set(int(row))
            self.tree.selection_set(row)
            self.row_menu.tk_popup(event.x_root, event.y_root)

    def _on_drop(self, event: tk.Event) -> None:
        paths = self.root.tk.splitlist(event.data)
        self._add_files(list(paths))

    # ========== File Management ==========

    def _add_files(self, paths: Optional[List[str]] = None) -> None:
        if paths is None:
            paths = list(filedialog.askopenfilenames(
                title="Виберіть файли",
                filetypes=[("Всі підтримувані", " ".join(f"*{ext}" for ext in SUPPORTED)), ("Всі файли", "*.*")]
            ))
        if paths: self._process_paths(paths)

    def _add_folder(self) -> None:
        folder = filedialog.askdirectory(title="Виберіть папку")
        if folder: self._process_paths([folder])

    def _process_paths(self, paths: List[str]) -> None:
        if self.state.is_at_limit():
            messagebox.showwarning("Ліміт", f"Досягнуто максимум файлів ({MAX_FILES})")
            return

        start_idx = len(self.state.entries) + 1
        added_count = 0
        remaining = self.state.get_remaining_capacity()
        auto_select = self.auto_select_var.get()

        for filepath in collect_files(paths):
            if added_count >= remaining: break
            filepath = os.path.abspath(filepath)
            if filepath in self.state.path_set or not os.path.isfile(filepath): continue
            ext = os.path.splitext(filepath)[1].lower()
            if ext not in SUPPORTED: continue

            filename = os.path.basename(filepath)
            directory = os.path.dirname(filepath)

            try:
                artist, title, info, size = extract_metadata(filepath, ext)
            except (FileNotFoundError, PermissionError):
                continue

            artist = sanitize(artist) if artist else ""
            title = sanitize(title) if title else ""
            if not title and self.use_fallback_var.get():
                title = sanitize(os.path.splitext(filename)[0])
            if not title: continue

            new_name = self._template_name(artist, title, start_idx + added_count, ext)
            file_type = self._get_file_type(ext)

            entry = FileEntry(
                path=filepath, original=filename, directory=directory,
                new_name=new_name, ext=ext, file_type=file_type,
                selected=tk.BooleanVar(value=auto_select), size=size, info=info,
            )

            if self.state.add_entry(entry):
                self._insert_row(entry)
                added_count += 1

        self._update_counter()
        self._set_status(f"✅ Додано {added_count} файлів")

    def _select_all(self) -> None:
        for i, entry in enumerate(self.state.entries):
            entry.selected.set(True)
            self.tree.set(i, "✓", "✔")
        self._update_counter()

    def _deselect_all(self) -> None:
        for i, entry in enumerate(self.state.entries):
            entry.selected.set(False)
            self.tree.set(i, "✓", "")
        self._update_counter()

    def _delete_selected(self, event=None) -> None:
        selection = list(self.tree.selection())
        if not selection: return
        indices = sorted([int(i) for i in selection], reverse=True)
        for i in indices:
            if 0 <= i < len(self.state.entries):
                entry = self.state.entries[i]
                self.state.path_set.discard(entry.path)
                self.state.entries.pop(i)
        self._refresh_tree()
        self._update_counter()

    def _clear_all(self) -> None:
        if not self.state.entries: return
        self.tree.delete(*self.tree.get_children())
        self.state.clear()
        self._update_counter()
        self._set_status("🗑 Список очищено")

    def _edit_name(self) -> None:
        idx = self.context_idx.get()
        if idx >= 0: self._edit_name_at(idx)

    def _edit_name_at(self, idx: int) -> None:
        if idx < 0 or idx >= len(self.state.entries): return
        entry = self.state.entries[idx]
        base = os.path.splitext(entry.new_name)[0]

        editor = tk.Toplevel(self.root)
        editor.title("Редагувати ім'я")
        editor.geometry("450x130")
        editor.configure(bg=COLORS["bg_main"])
        editor.transient(self.root)
        editor.grab_set()

        tk.Label(editor, text="Нова назва (без розширення):", bg=COLORS["bg_main"],
                 fg=COLORS["cyan"], font=("Segoe UI", 10)).pack(pady=(20, 8))

        name_var = tk.StringVar(value=base)
        name_entry = tk.Entry(editor, textvariable=name_var, width=50,
                              bg=COLORS["bg_input"], fg=COLORS["cyan"],
                              font=("Consolas", 11), insertbackground=COLORS["cyan"], relief="flat")
        name_entry.pack(pady=5, padx=20)
        name_entry.select_range(0, tk.END)
        name_entry.focus()

        def save():
            new_base = sanitize(name_var.get())
            if new_base:
                entry.new_name = new_base + entry.ext
                self.tree.set(idx, "Нова назва", entry.new_name)
            editor.destroy()

        name_entry.bind("<Return>", lambda e: save())
        name_entry.bind("<Escape>", lambda e: editor.destroy())

        btn_frame = tk.Frame(editor, bg=COLORS["bg_main"])
        btn_frame.pack(pady=12)
        self._create_cyan_button(btn_frame, "Зберегти", save, 10, "success").pack(side=tk.LEFT, padx=5)
        self._create_cyan_button(btn_frame, "Скасувати", editor.destroy, 10, "outline").pack(side=tk.LEFT)

    def _preview_selected(self) -> None:
        idx = self.context_idx.get()
        if idx >= 0 and idx < len(self.state.entries):
            entry = self.state.entries[idx]
            if entry.ext in IMG: self._preview_image(entry)

    def _preview_image(self, entry: FileEntry) -> None:
        try:
            file_size = os.path.getsize(entry.path)
            if file_size > MAX_PREVIEW_MEMORY:
                messagebox.showwarning("Попередження", "Файл завеликий для перегляду")
                return

            with Image.open(entry.path) as img:
                w, h = img.size
                scale = min(800 / w, 600 / h, 1)
                if scale < 1:
                    img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
                img_copy = img.copy()

            top = tk.Toplevel(self.root)
            top.title(f"Перегляд: {entry.original}")
            top.configure(bg=COLORS["bg_main"])

            imgtk = ImageTk.PhotoImage(img_copy)
            self._preview_references.append(imgtk)

            label = tk.Label(top, image=imgtk, bg=COLORS["bg_main"])
            label.image = imgtk
            label.pack(padx=15, pady=15)

            def on_close():
                if imgtk in self._preview_references:
                    self._preview_references.remove(imgtk)
                top.destroy()

            top.protocol("WM_DELETE_WINDOW", on_close)
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося переглянути: {e}")

    # ========== Rename Operation ==========

    def _rename_selected(self) -> None:
        selected = self.state.get_selected()
        if not selected:
            messagebox.showinfo("Інформація", "Немає вибраних файлів")
            return

        if self.confirm_rename_var.get():
            if not messagebox.askyesno("Підтвердження", f"Перейменувати {len(selected)} файлів?"):
                return
        elif self.confirm_large_var.get() and len(selected) > self.large_threshold_var.get():
            if not messagebox.askyesno("Підтвердження", f"Перейменувати {len(selected)} файлів?"):
                return

        if check_for_duplicate_destinations(self.state.entries, self.state.target_dir):
            messagebox.showerror("Помилка", "Виявлено однакові імена призначення!")
            return

        success_count = 0
        error_count = 0
        success_entries = []

        def on_success(entry: FileEntry) -> None:
            nonlocal success_count
            success_count += 1
            success_entries.append(entry)
            self.root.after(0, lambda: self._log(f"✅ {entry.original} → {entry.new_name}"))

        def on_error(entry: FileEntry, error: str) -> None:
            nonlocal error_count
            error_count += 1
            self.root.after(0, lambda: self._log(f"❌ {entry.original}: {error}"))

        def on_complete() -> None:
            self.root.after(0, lambda: self._on_rename_complete(success_count, error_count, success_entries))

        self._set_status(f"⏳ Перейменування {len(selected)} файлів...")

        self._operation_worker = FileOperationWorker(
            entries=selected, target_dir=self.state.target_dir,
            copy_mode=self.copy_var.get(), on_success=on_success,
            on_error=on_error, on_complete=on_complete,
        )
        self._operation_worker.start()

    def _on_rename_complete(self, success: int, errors: int, entries: list) -> None:
        self._set_status(f"✅ Завершено: {success} успішно, {errors} помилок")

        if self.auto_remove_var.get() and entries:
            for entry in entries:
                if entry in self.state.entries:
                    idx = self.state.entries.index(entry)
                    self.state.path_set.discard(entry.path)
                    self.state.entries.pop(idx)
            self._refresh_tree()

        self._update_counter()

        if self.show_notif_var.get():
            messagebox.showinfo("Завершено", f"✅ Перейменовано: {success}\n❌ Помилок: {errors}")

    def _choose_target(self) -> None:
        directory = filedialog.askdirectory(title="Виберіть цільову папку")
        if directory:
            self.state.target_dir = directory
            self.tgt_var.set(directory if len(directory) < 35 else "..." + directory[-32:])
        else:
            self.state.target_dir = None
            self.tgt_var.set("")

    def _log(self, message: str) -> None:
        self.log_box.config(state="normal")
        if self._log_line_count >= MAX_LOG_LINES:
            self.log_box.delete("1.0", "2.0")
        else:
            self._log_line_count += 1
        self.log_box.insert(tk.END, message + "\n")
        self.log_box.config(state="disabled")
        self.log_box.see(tk.END)

    def run(self) -> None:
        """Запустити програму."""
        self.root.mainloop()


def main() -> None:
    app = RenamerApp()
    app.run()


if __name__ == "__main__":
    main()
