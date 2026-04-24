"""Main application UI and logic."""

from __future__ import annotations

import ctypes
import json
import os
import platform
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
from PIL import Image, ImageTk

from renamer.constants import (
    AUDIO, IMG, DOC, VID, ARC, PRESENTATION, CODE, TEXT, GAME, SUPPORTED,
    TYPE_EMOJI, MAX_FILES, MAX_PREVIEW_MEMORY, MAX_LOG_LINES,
)
from renamer.metadata import sanitize, bytes_to_human_readable, extract_metadata, get_audio_tags
from renamer.file_ops import (
    FileEntry, AppState, collect_files,
    check_for_duplicate_destinations, FileOperationWorker,
)

# Enable DPI awareness on Windows
if platform.system() == "Windows":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

# Dark theme with cyan accents - improved readability
COLORS = {
    "bg_dark": "#0d0d0d",
    "bg_main": "#121212",
    "bg_secondary": "#1a1a1a",
    "bg_input": "#252525",
    "bg_hover": "#2a2a2a",
    "cyan": "#00e5ff",
    "cyan_dark": "#00b8d4",
    "cyan_dim": "#0097a7",
    "text": "#ffffff",
    "text_secondary": "#b0b0b0",
    "text_dim": "#707070",
    "success": "#4caf50",
    "error": "#f44336",
    "warning": "#ff9800",
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

    # Audio templates (with artist/title)
    AUDIO_TEMPLATES = {
        "Оригінал": lambda a, t, i, ext: t + ext if t else "",
        "Виконавець - Назва": lambda a, t, i, ext: f"{a} - {t}{ext}" if a and t else (t + ext if t else ""),
        "Назва (Виконавець)": lambda a, t, i, ext: f"{t} ({a}){ext}" if a and t else (t + ext if t else ""),
        "## - Назва": lambda a, t, i, ext: f"{i:02d} - {t}{ext}" if t else "",
        "## - Виконавець - Назва": lambda a, t, i, ext: f"{i:02d} - {a} - {t}{ext}" if a and t else "",
    }

    # File templates (no artist)
    FILE_TEMPLATES = {
        "Оригінал": lambda t, i, ext: t + ext if t else "",
        "## - Назва": lambda t, i, ext: f"{i:02d} - {t}{ext}" if t else "",
        "### - Назва": lambda t, i, ext: f"{i:03d} - {t}{ext}" if t else "",
        "ВЕЛИКІ ЛІТЕРИ": lambda t, i, ext: (t.upper() + ext) if t else "",
        "малі літери": lambda t, i, ext: (t.lower() + ext) if t else "",
        "Назва_без_пробілів": lambda t, i, ext: (t.replace(" ", "_") + ext) if t else "",
    }

    def __init__(self) -> None:
        self.settings = Settings()
        self.music_state = AppState()
        self.files_state = AppState()
        self._preview_references: List[ImageTk.PhotoImage] = []
        self._log_line_count = 0
        self._operation_worker: Optional[FileOperationWorker] = None

        self._setup_root()
        self._setup_variables()
        self._configure_styles()
        self._setup_notebook()
        self._setup_music_page()
        self._setup_files_page()
        self._setup_settings_page()

    def _setup_root(self) -> None:
        """Ініціалізація головного вікна."""
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

        self.root.title("Перейменувач файлів")
        self.root.geometry("1280x850")
        self.root.minsize(1000, 700)
        self.root.configure(bg=COLORS["bg_main"])

        # Initialize ttkbootstrap
        self.style = tb.Style("darkly")

    def _configure_styles(self) -> None:
        """Налаштування стилів."""
        s = self.style

        # Notebook tabs
        s.configure("TNotebook", background=COLORS["bg_main"])
        s.configure("TNotebook.Tab",
                    background=COLORS["bg_secondary"],
                    foreground=COLORS["text"],
                    padding=[20, 10],
                    font=("Segoe UI", 11))
        s.map("TNotebook.Tab",
              background=[("selected", COLORS["cyan_dim"])],
              foreground=[("selected", COLORS["text"])])

        # Treeview
        s.configure("Treeview",
                    background=COLORS["bg_input"],
                    foreground=COLORS["text"],
                    fieldbackground=COLORS["bg_input"],
                    font=("Segoe UI", 10),
                    rowheight=28)
        s.configure("Treeview.Heading",
                    background=COLORS["bg_secondary"],
                    foreground=COLORS["cyan"],
                    font=("Segoe UI", 10, "bold"))
        s.map("Treeview",
              background=[("selected", COLORS["cyan_dim"])],
              foreground=[("selected", COLORS["text"])])

        # Labels
        s.configure("TLabel", background=COLORS["bg_main"], foreground=COLORS["text"])
        s.configure("Accent.TLabel", foreground=COLORS["cyan"], font=("Segoe UI", 10, "bold"))

        # LabelFrame
        s.configure("TLabelframe", background=COLORS["bg_main"])
        s.configure("TLabelframe.Label",
                    background=COLORS["bg_main"],
                    foreground=COLORS["cyan"],
                    font=("Segoe UI", 10, "bold"))

        # Combobox
        s.configure("TCombobox", padding=5)

    def _setup_variables(self) -> None:
        """Ініціалізація змінних tkinter."""
        # Music tab
        self.music_tmpl_var = tk.StringVar(value="Виконавець - Назва")
        self.music_pre_var = tk.StringVar()
        self.music_suf_var = tk.StringVar()
        self.music_find_var = tk.StringVar()
        self.music_repl_var = tk.StringVar()
        self.music_copy_var = tk.BooleanVar(value=False)
        self.music_tgt_var = tk.StringVar()
        self.music_count_var = tk.StringVar(value="0 / 0")

        # Files tab
        self.files_tmpl_var = tk.StringVar(value="Оригінал")
        self.files_pre_var = tk.StringVar()
        self.files_suf_var = tk.StringVar()
        self.files_find_var = tk.StringVar()
        self.files_repl_var = tk.StringVar()
        self.files_copy_var = tk.BooleanVar(value=False)
        self.files_tgt_var = tk.StringVar()
        self.files_count_var = tk.StringVar(value="0 / 0")

        # Settings
        self.auto_select_var = tk.BooleanVar(value=self.settings.get("auto_select_all"))
        self.confirm_rename_var = tk.BooleanVar(value=self.settings.get("confirm_rename"))
        self.confirm_large_var = tk.BooleanVar(value=self.settings.get("confirm_large_batch"))
        self.large_threshold_var = tk.IntVar(value=self.settings.get("large_batch_threshold"))
        self.auto_remove_var = tk.BooleanVar(value=self.settings.get("auto_remove_after_rename"))
        self.show_notif_var = tk.BooleanVar(value=self.settings.get("show_notifications"))
        self.use_fallback_var = tk.BooleanVar(value=self.settings.get("use_original_name_fallback"))

        self.status_var = tk.StringVar(value="Готово")

    def _setup_notebook(self) -> None:
        """Створення вкладок."""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.music_frame = tk.Frame(self.notebook, bg=COLORS["bg_main"])
        self.files_frame = tk.Frame(self.notebook, bg=COLORS["bg_main"])
        self.settings_frame = tk.Frame(self.notebook, bg=COLORS["bg_main"])

        self.notebook.add(self.music_frame, text="  🎵 Музика  ")
        self.notebook.add(self.files_frame, text="  📁 Файли  ")
        self.notebook.add(self.settings_frame, text="  ⚙️ Налаштування  ")

    def _create_button(self, parent, text: str, command, style: str = "primary") -> tb.Button:
        """Створити кнопку."""
        style_map = {
            "primary": "info",
            "secondary": "secondary",
            "success": "success",
            "danger": "danger",
            "outline": "info-outline",
        }
        return tb.Button(parent, text=text, command=command, bootstyle=style_map.get(style, "info"))

    def _setup_music_page(self) -> None:
        """Сторінка для музичних файлів."""
        # Header
        header = tk.Frame(self.music_frame, bg=COLORS["bg_main"])
        header.pack(fill=tk.X, padx=15, pady=(15, 10))

        tk.Label(header, text="🎵 Перейменування музики", font=("Segoe UI", 16, "bold"),
                 bg=COLORS["bg_main"], fg=COLORS["cyan"]).pack(side=tk.LEFT)

        tk.Label(header, textvariable=self.music_count_var, font=("Segoe UI", 12),
                 bg=COLORS["bg_main"], fg=COLORS["text_secondary"]).pack(side=tk.RIGHT)

        # Buttons
        btn_frame = tk.Frame(self.music_frame, bg=COLORS["bg_main"])
        btn_frame.pack(fill=tk.X, padx=15, pady=5)

        self._create_button(btn_frame, "➕ Додати файли",
                           lambda: self._add_files_to(self.music_state, self.music_tree, AUDIO, self._refresh_music),
                           "primary").pack(side=tk.LEFT, padx=(0, 5))
        self._create_button(btn_frame, "📁 Додати папку",
                           lambda: self._add_folder_to(self.music_state, self.music_tree, AUDIO, self._refresh_music),
                           "primary").pack(side=tk.LEFT, padx=(0, 15))
        self._create_button(btn_frame, "✓ Все", lambda: self._select_all_in(self.music_state, self.music_tree),
                           "outline").pack(side=tk.LEFT, padx=2)
        self._create_button(btn_frame, "✗ Нічого", lambda: self._deselect_all_in(self.music_state, self.music_tree),
                           "outline").pack(side=tk.LEFT, padx=2)
        self._create_button(btn_frame, "🗑 Очистити", lambda: self._clear_all_in(self.music_state, self.music_tree),
                           "danger").pack(side=tk.LEFT, padx=(15, 0))

        # Template settings
        tmpl_frame = tk.LabelFrame(self.music_frame, text=" Шаблон перейменування ",
                                    bg=COLORS["bg_main"], fg=COLORS["cyan"], font=("Segoe UI", 10, "bold"))
        tmpl_frame.pack(fill=tk.X, padx=15, pady=10)

        inner = tk.Frame(tmpl_frame, bg=COLORS["bg_main"])
        inner.pack(fill=tk.X, padx=15, pady=12)

        # Row 1
        row1 = tk.Frame(inner, bg=COLORS["bg_main"])
        row1.pack(fill=tk.X, pady=(0, 8))

        tk.Label(row1, text="Шаблон:", bg=COLORS["bg_main"], fg=COLORS["text"],
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)
        music_combo = ttk.Combobox(row1, textvariable=self.music_tmpl_var,
                                    values=list(self.AUDIO_TEMPLATES.keys()), width=25, state="readonly")
        music_combo.pack(side=tk.LEFT, padx=(8, 20))
        music_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_music())

        tk.Label(row1, text="Префікс:", bg=COLORS["bg_main"], fg=COLORS["text"],
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)
        ttk.Entry(row1, textvariable=self.music_pre_var, width=15).pack(side=tk.LEFT, padx=(8, 20))

        tk.Label(row1, text="Суфікс:", bg=COLORS["bg_main"], fg=COLORS["text"],
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)
        ttk.Entry(row1, textvariable=self.music_suf_var, width=15).pack(side=tk.LEFT, padx=8)

        # Row 2
        row2 = tk.Frame(inner, bg=COLORS["bg_main"])
        row2.pack(fill=tk.X)

        tk.Label(row2, text="Знайти:", bg=COLORS["bg_main"], fg=COLORS["text"],
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.music_find_var, width=15).pack(side=tk.LEFT, padx=(8, 20))

        tk.Label(row2, text="Замінити:", bg=COLORS["bg_main"], fg=COLORS["text"],
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.music_repl_var, width=15).pack(side=tk.LEFT, padx=(8, 20))

        tb.Checkbutton(row2, text="Копіювати", variable=self.music_copy_var,
                       bootstyle="round-toggle").pack(side=tk.LEFT, padx=(0, 15))

        self._create_button(row2, "📂 Ціль", lambda: self._choose_target(self.music_state, self.music_tgt_var),
                           "outline").pack(side=tk.LEFT)
        tk.Label(row2, textvariable=self.music_tgt_var, bg=COLORS["bg_main"],
                 fg=COLORS["text_dim"], font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=8)

        # Treeview
        self.music_tree = self._create_treeview(self.music_frame, self.music_state, AUDIO, self._refresh_music)

        # Actions
        action_frame = tk.Frame(self.music_frame, bg=COLORS["bg_main"])
        action_frame.pack(fill=tk.X, padx=15, pady=10)

        self._create_button(action_frame, "🚀 ПЕРЕЙМЕНУВАТИ",
                           lambda: self._rename_selected(self.music_state, self.music_tree, self.music_copy_var, self._refresh_music),
                           "success").pack(side=tk.LEFT, padx=(0, 10))
        self._create_button(action_frame, "🔄 Оновити", self._refresh_music, "outline").pack(side=tk.LEFT)

        # Status
        status = tk.Frame(self.music_frame, bg=COLORS["bg_secondary"])
        status.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Label(status, textvariable=self.status_var, bg=COLORS["bg_secondary"],
                 fg=COLORS["text_secondary"], font=("Segoe UI", 9), pady=8).pack(side=tk.LEFT, padx=15)

    def _setup_files_page(self) -> None:
        """Сторінка для загальних файлів."""
        # Header
        header = tk.Frame(self.files_frame, bg=COLORS["bg_main"])
        header.pack(fill=tk.X, padx=15, pady=(15, 10))

        tk.Label(header, text="📁 Перейменування файлів", font=("Segoe UI", 16, "bold"),
                 bg=COLORS["bg_main"], fg=COLORS["cyan"]).pack(side=tk.LEFT)

        tk.Label(header, textvariable=self.files_count_var, font=("Segoe UI", 12),
                 bg=COLORS["bg_main"], fg=COLORS["text_secondary"]).pack(side=tk.RIGHT)

        # Buttons
        btn_frame = tk.Frame(self.files_frame, bg=COLORS["bg_main"])
        btn_frame.pack(fill=tk.X, padx=15, pady=5)

        self._create_button(btn_frame, "➕ Додати файли",
                           lambda: self._add_files_to(self.files_state, self.files_tree, SUPPORTED, self._refresh_files),
                           "primary").pack(side=tk.LEFT, padx=(0, 5))
        self._create_button(btn_frame, "📁 Додати папку",
                           lambda: self._add_folder_to(self.files_state, self.files_tree, SUPPORTED, self._refresh_files),
                           "primary").pack(side=tk.LEFT, padx=(0, 15))
        self._create_button(btn_frame, "✓ Все", lambda: self._select_all_in(self.files_state, self.files_tree),
                           "outline").pack(side=tk.LEFT, padx=2)
        self._create_button(btn_frame, "✗ Нічого", lambda: self._deselect_all_in(self.files_state, self.files_tree),
                           "outline").pack(side=tk.LEFT, padx=2)
        self._create_button(btn_frame, "🗑 Очистити", lambda: self._clear_all_in(self.files_state, self.files_tree),
                           "danger").pack(side=tk.LEFT, padx=(15, 0))

        # Template settings
        tmpl_frame = tk.LabelFrame(self.files_frame, text=" Шаблон перейменування ",
                                    bg=COLORS["bg_main"], fg=COLORS["cyan"], font=("Segoe UI", 10, "bold"))
        tmpl_frame.pack(fill=tk.X, padx=15, pady=10)

        inner = tk.Frame(tmpl_frame, bg=COLORS["bg_main"])
        inner.pack(fill=tk.X, padx=15, pady=12)

        # Row 1
        row1 = tk.Frame(inner, bg=COLORS["bg_main"])
        row1.pack(fill=tk.X, pady=(0, 8))

        tk.Label(row1, text="Шаблон:", bg=COLORS["bg_main"], fg=COLORS["text"],
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)
        files_combo = ttk.Combobox(row1, textvariable=self.files_tmpl_var,
                                    values=list(self.FILE_TEMPLATES.keys()), width=25, state="readonly")
        files_combo.pack(side=tk.LEFT, padx=(8, 20))
        files_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_files())

        tk.Label(row1, text="Префікс:", bg=COLORS["bg_main"], fg=COLORS["text"],
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)
        ttk.Entry(row1, textvariable=self.files_pre_var, width=15).pack(side=tk.LEFT, padx=(8, 20))

        tk.Label(row1, text="Суфікс:", bg=COLORS["bg_main"], fg=COLORS["text"],
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)
        ttk.Entry(row1, textvariable=self.files_suf_var, width=15).pack(side=tk.LEFT, padx=8)

        # Row 2
        row2 = tk.Frame(inner, bg=COLORS["bg_main"])
        row2.pack(fill=tk.X)

        tk.Label(row2, text="Знайти:", bg=COLORS["bg_main"], fg=COLORS["text"],
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.files_find_var, width=15).pack(side=tk.LEFT, padx=(8, 20))

        tk.Label(row2, text="Замінити:", bg=COLORS["bg_main"], fg=COLORS["text"],
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.files_repl_var, width=15).pack(side=tk.LEFT, padx=(8, 20))

        tb.Checkbutton(row2, text="Копіювати", variable=self.files_copy_var,
                       bootstyle="round-toggle").pack(side=tk.LEFT, padx=(0, 15))

        self._create_button(row2, "📂 Ціль", lambda: self._choose_target(self.files_state, self.files_tgt_var),
                           "outline").pack(side=tk.LEFT)
        tk.Label(row2, textvariable=self.files_tgt_var, bg=COLORS["bg_main"],
                 fg=COLORS["text_dim"], font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=8)

        # Treeview
        self.files_tree = self._create_treeview(self.files_frame, self.files_state, SUPPORTED, self._refresh_files)

        # Actions
        action_frame = tk.Frame(self.files_frame, bg=COLORS["bg_main"])
        action_frame.pack(fill=tk.X, padx=15, pady=10)

        self._create_button(action_frame, "🚀 ПЕРЕЙМЕНУВАТИ",
                           lambda: self._rename_selected(self.files_state, self.files_tree, self.files_copy_var, self._refresh_files),
                           "success").pack(side=tk.LEFT, padx=(0, 10))
        self._create_button(action_frame, "🔄 Оновити", self._refresh_files, "outline").pack(side=tk.LEFT)

    def _create_treeview(self, parent, state: AppState, allowed_ext: tuple, refresh_fn) -> ttk.Treeview:
        """Створення таблиці файлів."""
        tree_frame = tk.Frame(parent, bg=COLORS["bg_main"])
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        cols = ("✓", "№", "Тип", "Оригінал", "Нове ім'я", "Розмір", "Інфо")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="extended")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        widths = {"✓": 40, "№": 45, "Тип": 45, "Оригінал": 300, "Нове ім'я": 300, "Розмір": 80, "Інфо": 150}
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=widths.get(c, 100), anchor="w" if c not in ("✓", "№", "Тип") else "center")

        tree.bind("<Button-1>", lambda e: self._on_tree_click(e, tree, state))

        # Drag and drop support
        if self.dnd_enabled:
            try:
                tree.drop_target_register(DND_FILES)
                tree.dnd_bind("<<Drop>>", lambda e: self._on_drop(e, state, tree, allowed_ext, refresh_fn))
            except Exception:
                pass

        return tree

    def _setup_settings_page(self) -> None:
        """Сторінка налаштувань."""
        container = tk.Frame(self.settings_frame, bg=COLORS["bg_main"])
        container.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)

        tk.Label(container, text="⚙️ Налаштування", font=("Segoe UI", 18, "bold"),
                 bg=COLORS["bg_main"], fg=COLORS["cyan"]).pack(anchor="w", pady=(0, 20))

        # Groups
        self._settings_group(container, "Вибір файлів", [
            ("Автоматично вибирати всі файли при додаванні", self.auto_select_var),
            ("Використовувати оригінальну назву як запасний варіант", self.use_fallback_var),
        ])

        self._settings_group(container, "Підтвердження", [
            ("Запитувати підтвердження перед кожним перейменуванням", self.confirm_rename_var),
            ("Підтверджувати лише для великих пакетів", self.confirm_large_var),
        ])

        # Threshold
        thresh_frame = tk.LabelFrame(container, text=" Поріг великого пакету ",
                                      bg=COLORS["bg_main"], fg=COLORS["cyan"], font=("Segoe UI", 10, "bold"))
        thresh_frame.pack(fill=tk.X, pady=10)

        thresh_inner = tk.Frame(thresh_frame, bg=COLORS["bg_main"])
        thresh_inner.pack(fill=tk.X, padx=20, pady=15)

        self.threshold_label = tk.Label(thresh_inner, text=f"{self.large_threshold_var.get()} файлів",
                                         bg=COLORS["bg_main"], fg=COLORS["text"], font=("Segoe UI", 12, "bold"))
        self.threshold_label.pack(anchor="w")

        def update_thresh(val):
            v = int(float(val))
            self.large_threshold_var.set(v)
            self.threshold_label.config(text=f"{v} файлів")

        ttk.Scale(thresh_inner, from_=10, to=500, variable=self.large_threshold_var,
                  orient=tk.HORIZONTAL, length=350, command=update_thresh).pack(anchor="w", pady=(8, 0))

        self._settings_group(container, "Після перейменування", [
            ("Видаляти файли зі списку після успішного перейменування", self.auto_remove_var),
            ("Показувати сповіщення про завершення", self.show_notif_var),
        ])

        # Buttons
        btn_frame = tk.Frame(container, bg=COLORS["bg_main"])
        btn_frame.pack(fill=tk.X, pady=25)

        self._create_button(btn_frame, "💾 Зберегти", self._save_settings, "success").pack(side=tk.LEFT, padx=(0, 10))
        self._create_button(btn_frame, "↩️ Скинути", self._reset_settings, "danger").pack(side=tk.LEFT)

    def _settings_group(self, parent, title: str, options: list) -> None:
        """Група налаштувань."""
        group = tk.LabelFrame(parent, text=f" {title} ", bg=COLORS["bg_main"],
                               fg=COLORS["cyan"], font=("Segoe UI", 10, "bold"))
        group.pack(fill=tk.X, pady=10)

        inner = tk.Frame(group, bg=COLORS["bg_main"])
        inner.pack(fill=tk.X, padx=20, pady=12)

        for label, var in options:
            tb.Checkbutton(inner, text=label, variable=var, bootstyle="round-toggle").pack(anchor="w", pady=4)

    def _save_settings(self) -> None:
        """Зберегти налаштування."""
        self.settings.set("auto_select_all", self.auto_select_var.get())
        self.settings.set("confirm_rename", self.confirm_rename_var.get())
        self.settings.set("confirm_large_batch", self.confirm_large_var.get())
        self.settings.set("large_batch_threshold", self.large_threshold_var.get())
        self.settings.set("auto_remove_after_rename", self.auto_remove_var.get())
        self.settings.set("show_notifications", self.show_notif_var.get())
        self.settings.set("use_original_name_fallback", self.use_fallback_var.get())
        self.status_var.set("✅ Налаштування збережено")
        messagebox.showinfo("Успіх", "Налаштування збережено!")

    def _reset_settings(self) -> None:
        """Скинути налаштування."""
        if not messagebox.askyesno("Підтвердження", "Скинути налаштування?"): return
        self.settings.settings = Settings.DEFAULT_SETTINGS.copy()
        self.settings.save()
        self.auto_select_var.set(True)
        self.confirm_rename_var.set(False)
        self.confirm_large_var.set(True)
        self.large_threshold_var.set(100)
        self.auto_remove_var.set(True)
        self.show_notif_var.set(True)
        self.use_fallback_var.set(True)
        self.threshold_label.config(text="100 файлів")
        self.status_var.set("✅ Налаштування скинуто")

    # ========== File Operations ==========

    def _on_drop(self, event, state: AppState, tree: ttk.Treeview, allowed_ext: tuple, refresh_fn) -> None:
        """Обробка drag & drop."""
        try:
            # Parse dropped files - handle both formats
            data = event.data
            if data.startswith("{"):
                # Windows format with braces
                paths = []
                for item in data.split("} {"):
                    item = item.strip("{}")
                    if item:
                        paths.append(item)
            else:
                # Unix format or simple paths
                paths = self.root.tk.splitlist(data)

            if paths:
                self._process_paths(list(paths), state, tree, allowed_ext, refresh_fn)
        except Exception as e:
            self.status_var.set(f"❌ Помилка drag & drop: {e}")

    def _get_file_type(self, ext: str) -> str:
        if ext in AUDIO: return "🎵"
        if ext in IMG: return "🖼"
        if ext in DOC: return "📄"
        if ext in VID: return "🎬"
        if ext in ARC: return "📦"
        if ext in PRESENTATION: return "📊"
        if ext in CODE: return "💻"
        if ext in TEXT: return "📝"
        if ext in GAME: return "🎮"
        return "📁"

    def _add_files_to(self, state: AppState, tree: ttk.Treeview, allowed_ext: tuple, refresh_fn) -> None:
        """Додати файли."""
        paths = list(filedialog.askopenfilenames(
            title="Виберіть файли",
            filetypes=[("Підтримувані", " ".join(f"*{e}" for e in allowed_ext)), ("Всі", "*.*")]
        ))
        if paths:
            self._process_paths(paths, state, tree, allowed_ext, refresh_fn)

    def _add_folder_to(self, state: AppState, tree: ttk.Treeview, allowed_ext: tuple, refresh_fn) -> None:
        """Додати папку."""
        folder = filedialog.askdirectory(title="Виберіть папку")
        if folder:
            self._process_paths([folder], state, tree, allowed_ext, refresh_fn)

    def _process_paths(self, paths: List[str], state: AppState, tree: ttk.Treeview,
                       allowed_ext: tuple, refresh_fn) -> None:
        """Обробити шляхи."""
        added = 0
        auto_select = self.auto_select_var.get()

        for filepath in collect_files(paths):
            filepath = os.path.abspath(filepath)
            if filepath in state.path_set or not os.path.isfile(filepath): continue
            ext = os.path.splitext(filepath)[1].lower()
            if ext not in allowed_ext: continue

            filename = os.path.basename(filepath)
            directory = os.path.dirname(filepath)

            try:
                artist, title, info, size = extract_metadata(filepath, ext)
            except Exception:
                continue

            artist = sanitize(artist) if artist else ""
            title = sanitize(title) if title else ""
            if not title and self.use_fallback_var.get():
                title = sanitize(os.path.splitext(filename)[0])
            if not title: continue

            file_type = self._get_file_type(ext)
            entry = FileEntry(
                path=filepath, original=filename, directory=directory,
                new_name=filename, ext=ext, file_type=file_type,
                selected=tk.BooleanVar(value=auto_select), size=size, info=info,
            )

            if state.add_entry(entry):
                added += 1

        refresh_fn()
        self.status_var.set(f"✅ Додано {added} файлів")

    def _refresh_music(self) -> None:
        """Оновити музичну таблицю."""
        self._refresh_tree(self.music_state, self.music_tree, self.music_count_var,
                          self.music_tmpl_var, self.music_pre_var, self.music_suf_var,
                          self.music_find_var, self.music_repl_var, is_audio=True)

    def _refresh_files(self) -> None:
        """Оновити файлову таблицю."""
        self._refresh_tree(self.files_state, self.files_tree, self.files_count_var,
                          self.files_tmpl_var, self.files_pre_var, self.files_suf_var,
                          self.files_find_var, self.files_repl_var, is_audio=False)

    def _refresh_tree(self, state: AppState, tree: ttk.Treeview, count_var: tk.StringVar,
                      tmpl_var: tk.StringVar, pre_var: tk.StringVar, suf_var: tk.StringVar,
                      find_var: tk.StringVar, repl_var: tk.StringVar, is_audio: bool) -> None:
        """Оновити таблицю."""
        tree.delete(*tree.get_children())

        for i, entry in enumerate(state.entries):
            # Generate new name
            title = sanitize(os.path.splitext(entry.original)[0])
            artist = ""

            if is_audio and entry.ext in AUDIO:
                try:
                    artist, tag_title, _, _ = get_audio_tags(entry.path)
                    if tag_title: title = sanitize(tag_title)
                    artist = sanitize(artist) if artist else ""
                except Exception:
                    pass

                tmpl = tmpl_var.get()
                template_func = self.AUDIO_TEMPLATES.get(tmpl, self.AUDIO_TEMPLATES["Оригінал"])
                base = template_func(artist, title, i + 1, "")
            else:
                tmpl = tmpl_var.get()
                template_func = self.FILE_TEMPLATES.get(tmpl, self.FILE_TEMPLATES["Оригінал"])
                base = template_func(title, i + 1, "")

            if not base:
                base = title or "unnamed"

            base = pre_var.get() + base + suf_var.get()
            if find_var.get():
                base = base.replace(find_var.get(), repl_var.get())

            entry.new_name = sanitize(base) + entry.ext

            tree.insert("", "end", iid=i, values=(
                "✓" if entry.selected.get() else "",
                i + 1,
                entry.file_type,
                entry.original,
                entry.new_name,
                bytes_to_human_readable(entry.size),
                entry.info
            ))

        selected = state.count_selected()
        count_var.set(f"{selected} / {len(state.entries)}")

    def _on_tree_click(self, event: tk.Event, tree: ttk.Treeview, state: AppState) -> None:
        """Клік по таблиці."""
        region = tree.identify_region(event.x, event.y)
        if region != "cell": return
        col = tree.identify_column(event.x)
        item = tree.identify_row(event.y)
        if not item: return
        idx = int(item)
        if idx >= len(state.entries): return

        if col == "#1":
            entry = state.entries[idx]
            entry.selected.set(not entry.selected.get())
            tree.set(idx, "✓", "✓" if entry.selected.get() else "")

            if state == self.music_state:
                self.music_count_var.set(f"{state.count_selected()} / {len(state.entries)}")
            else:
                self.files_count_var.set(f"{state.count_selected()} / {len(state.entries)}")

    def _select_all_in(self, state: AppState, tree: ttk.Treeview) -> None:
        for i, e in enumerate(state.entries):
            e.selected.set(True)
            tree.set(i, "✓", "✓")
        if state == self.music_state:
            self.music_count_var.set(f"{len(state.entries)} / {len(state.entries)}")
        else:
            self.files_count_var.set(f"{len(state.entries)} / {len(state.entries)}")

    def _deselect_all_in(self, state: AppState, tree: ttk.Treeview) -> None:
        for i, e in enumerate(state.entries):
            e.selected.set(False)
            tree.set(i, "✓", "")
        if state == self.music_state:
            self.music_count_var.set(f"0 / {len(state.entries)}")
        else:
            self.files_count_var.set(f"0 / {len(state.entries)}")

    def _clear_all_in(self, state: AppState, tree: ttk.Treeview) -> None:
        tree.delete(*tree.get_children())
        state.clear()
        if state == self.music_state:
            self.music_count_var.set("0 / 0")
        else:
            self.files_count_var.set("0 / 0")
        self.status_var.set("🗑 Очищено")

    def _choose_target(self, state: AppState, tgt_var: tk.StringVar) -> None:
        directory = filedialog.askdirectory(title="Виберіть цільову папку")
        if directory:
            state.target_dir = directory
            tgt_var.set("..." + directory[-30:] if len(directory) > 30 else directory)
        else:
            state.target_dir = None
            tgt_var.set("")

    def _rename_selected(self, state: AppState, tree: ttk.Treeview, copy_var: tk.BooleanVar, refresh_fn) -> None:
        """Перейменувати вибрані."""
        selected = state.get_selected()
        if not selected:
            messagebox.showinfo("Інформація", "Немає вибраних файлів")
            return

        if self.confirm_rename_var.get():
            if not messagebox.askyesno("Підтвердження", f"Перейменувати {len(selected)} файлів?"): return
        elif self.confirm_large_var.get() and len(selected) > self.large_threshold_var.get():
            if not messagebox.askyesno("Підтвердження", f"Перейменувати {len(selected)} файлів?"): return

        if check_for_duplicate_destinations(state.entries, state.target_dir):
            messagebox.showerror("Помилка", "Однакові імена призначення!")
            return

        success_count = 0
        success_entries = []

        def on_success(entry: FileEntry) -> None:
            nonlocal success_count
            success_count += 1
            success_entries.append(entry)

        def on_error(entry: FileEntry, error: str) -> None:
            self.root.after(0, lambda: self.status_var.set(f"❌ {entry.original}: {error}"))

        def on_complete() -> None:
            self.root.after(0, lambda: self._on_rename_done(state, success_count, success_entries, refresh_fn))

        self.status_var.set(f"⏳ Перейменування {len(selected)} файлів...")

        self._operation_worker = FileOperationWorker(
            entries=selected, target_dir=state.target_dir,
            copy_mode=copy_var.get(), on_success=on_success,
            on_error=on_error, on_complete=on_complete,
        )
        self._operation_worker.start()

    def _on_rename_done(self, state: AppState, success: int, entries: list, refresh_fn) -> None:
        self.status_var.set(f"✅ Перейменовано {success} файлів")

        if self.auto_remove_var.get() and entries:
            for entry in entries:
                if entry in state.entries:
                    state.path_set.discard(entry.path)
                    state.entries.remove(entry)
            refresh_fn()

        if self.show_notif_var.get():
            messagebox.showinfo("Готово", f"Перейменовано: {success}")

    def run(self) -> None:
        """Запустити програму."""
        self.root.mainloop()


def main() -> None:
    app = RenamerApp()
    app.run()


if __name__ == "__main__":
    main()
