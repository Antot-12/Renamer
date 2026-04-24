"""Main application UI and logic."""

from __future__ import annotations

import ctypes
import json
import os
import platform
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, List, Optional
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
from PIL import ImageTk

from renamer.constants import (
    AUDIO, IMG, DOC, VID, ARC, PRESENTATION, CODE, TEXT, GAME, SUPPORTED,
)
from renamer.metadata import (
    sanitize, bytes_to_human_readable, extract_metadata,
    get_audio_tags_extended, get_file_dates, get_album_art,
)
from renamer.file_ops import (
    FileEntry, AppState, collect_files,
    check_for_duplicate_destinations, FileOperationWorker,
    find_destination_conflicts, resolve_conflicts_auto_number,
)
from renamer.history import OperationHistory, RenameOperation
from renamer.transformers import (
    apply_case, remove_pattern, trim_spaces, apply_regex_replace,
    CASE_LABELS, PATTERN_LABELS, DATE_FORMATS,
)
from renamer.duplicates import find_duplicates, get_duplicate_stats
from renamer.history_log import get_history_log
from renamer.musicbrainz import search_by_filename, search_recording
from renamer.profiles import get_profile_manager, RenameProfile

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
    "cyan": "#02DDFD",
    "cyan_dark": "#00b8d4",
    "cyan_dim": "#00838f",
    "cyan_selection": "#006064",
    "text": "#ffffff",
    "text_secondary": "#b0b0b0",
    "text_dim": "#707070",
    "success": "#4caf50",
    "error": "#f44336",
    "warning": "#ff9800",
}

# Font configuration
FONT_FAMILY = "Segoe UI"
FONT_MONO = "Consolas"
FONTS = {
    "title": (FONT_FAMILY, 16, "bold"),
    "heading": (FONT_FAMILY, 12, "bold"),
    "normal": (FONT_FAMILY, 10),
    "bold": (FONT_FAMILY, 10, "bold"),
    "small": (FONT_FAMILY, 9),
    "mono": (FONT_MONO, 10),
}

# UI sizes
SIZES = {
    "entry_width": 15,
    "combo_width": 25,
    "padding": 15,
    "row_height": 28,
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
        # Window geometry
        "window_width": 1400,
        "window_height": 900,
        "window_x": None,
        "window_y": None,
        "window_maximized": False,
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
        "Альбом - Назва": lambda a, t, i, ext, album="": f"{album} - {t}{ext}" if album and t else (t + ext if t else ""),
        "[Рік] Виконавець - Назва": lambda a, t, i, ext, year="": f"[{year}] {a} - {t}{ext}" if year and a and t else (f"{a} - {t}{ext}" if a and t else ""),
    }

    # File templates (no artist)
    FILE_TEMPLATES = {
        "Оригінал": lambda t, i, ext: t + ext if t else "",
        "## - Назва": lambda t, i, ext: f"{i:02d} - {t}{ext}" if t else "",
        "### - Назва": lambda t, i, ext: f"{i:03d} - {t}{ext}" if t else "",
        "ВЕЛИКІ ЛІТЕРИ": lambda t, i, ext: (t.upper() + ext) if t else "",
        "малі літери": lambda t, i, ext: (t.lower() + ext) if t else "",
        "Назва_без_пробілів": lambda t, i, ext: (t.replace(" ", "_") + ext) if t else "",
        "Title Case": lambda t, i, ext: (t.title() + ext) if t else "",
        "Sentence case": lambda t, i, ext: (t.capitalize() + ext) if t else "",
        "snake_case": lambda t, i, ext: (re.sub(r'[\s\-]+', '_', t).lower() + ext) if t else "",
        "kebab-case": lambda t, i, ext: (re.sub(r'[\s_]+', '-', t).lower() + ext) if t else "",
    }

    def __init__(self) -> None:
        self.settings = Settings()
        self.music_state = AppState()
        self.files_state = AppState()
        self._preview_references: List[ImageTk.PhotoImage] = []
        self._log_line_count = 0
        self._operation_worker: Optional[FileOperationWorker] = None

        # New: undo/redo history
        self.music_history = OperationHistory(filepath=Path.home() / ".renamer_music_history.json")
        self.files_history = OperationHistory(filepath=Path.home() / ".renamer_files_history.json")

        # New: profile manager
        self.profile_manager = get_profile_manager()

        # New: history log
        self.history_log = get_history_log()

        # Debounce timers for live preview
        self._music_preview_timer = None
        self._files_preview_timer = None
        self._drag_data = {"item": None, "start_y": 0}

        # Search filter text
        self._music_search_var = None
        self._files_search_var = None

        self._setup_root()
        self._setup_variables()
        self._configure_styles()
        self._setup_notebook()
        self._setup_music_page()
        self._setup_files_page()
        self._setup_settings_page()

        # Setup live preview bindings
        self._setup_live_preview()

        # Load profiles
        self._update_profile_combos()

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

        # Get screen dimensions for responsive sizing
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Calculate default size based on screen (80% of screen, min 1400x900)
        default_width = max(1400, int(screen_width * 0.8))
        default_height = max(900, int(screen_height * 0.8))

        # Restore window geometry from settings or use calculated defaults
        width = self.settings.get("window_width") or default_width
        height = self.settings.get("window_height") or default_height
        x = self.settings.get("window_x")
        y = self.settings.get("window_y")

        # Ensure window fits on screen
        width = min(width, screen_width - 50)
        height = min(height, screen_height - 100)

        if x is not None and y is not None:
            # Ensure position is on screen
            x = max(0, min(x, screen_width - width))
            y = max(0, min(y, screen_height - height))
            self.root.geometry(f"{width}x{height}+{x}+{y}")
        else:
            # Center on screen
            x = (screen_width - width) // 2
            y = (screen_height - height) // 2
            self.root.geometry(f"{width}x{height}+{x}+{y}")

        if self.settings.get("window_maximized", False):
            self.root.state('zoomed') if platform.system() == 'Windows' else self.root.attributes('-zoomed', True)

        self.root.minsize(1100, 750)
        self.root.configure(bg=COLORS["bg_main"])

        # Save geometry on close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Initialize ttkbootstrap
        self.style = tb.Style("darkly")

    def _on_close(self) -> None:
        """Save window geometry and close."""
        try:
            # Check if maximized
            is_maximized = self.root.state() == 'zoomed' if platform.system() == 'Windows' else bool(self.root.attributes('-zoomed'))
            self.settings.set("window_maximized", is_maximized)

            if not is_maximized:
                # Save geometry only if not maximized
                geo = self.root.geometry()
                # Parse geometry string: WxH+X+Y
                import re
                match = re.match(r'(\d+)x(\d+)\+(-?\d+)\+(-?\d+)', geo)
                if match:
                    self.settings.settings["window_width"] = int(match.group(1))
                    self.settings.settings["window_height"] = int(match.group(2))
                    self.settings.settings["window_x"] = int(match.group(3))
                    self.settings.settings["window_y"] = int(match.group(4))
                    self.settings.save()
        except Exception:
            pass

        self.root.destroy()

    def _configure_styles(self) -> None:
        """Налаштування стилів."""
        s = self.style

        # Custom cyan button style
        s.configure("Cyan.TButton",
                    background=COLORS["cyan"],
                    foreground="#000000",
                    font=("Segoe UI", 10))
        s.map("Cyan.TButton",
              background=[("active", COLORS["cyan_dark"]), ("pressed", COLORS["cyan_dim"])],
              foreground=[("active", "#000000"), ("pressed", "#000000")])

        # Cyan outline button
        s.configure("CyanOutline.TButton",
                    background=COLORS["bg_main"],
                    foreground=COLORS["cyan"],
                    bordercolor=COLORS["cyan"],
                    relief="solid",
                    borderwidth=1,
                    font=("Segoe UI", 10))
        s.map("CyanOutline.TButton",
              background=[("active", COLORS["cyan_dim"]), ("pressed", COLORS["cyan_dark"])],
              foreground=[("active", "#ffffff"), ("pressed", "#ffffff")])

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
              background=[("selected", COLORS["cyan_dark"])],
              foreground=[("selected", "#000000")])

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
        self.music_regex_var = tk.BooleanVar(value=False)
        self.music_case_var = tk.StringVar(value="none")
        self.music_remove_var = tk.StringVar(value="none")
        self.music_trim_var = tk.BooleanVar(value=True)
        self.music_backup_var = tk.BooleanVar(value=False)
        self.music_backup_dir_var = tk.StringVar()
        self.music_profile_var = tk.StringVar()
        self.music_filter_var = tk.StringVar(value="Всі")
        self.music_recursive_var = tk.BooleanVar(value=False)
        # Numbering options
        self.music_num_start_var = tk.IntVar(value=1)
        self.music_num_step_var = tk.IntVar(value=1)
        self.music_num_padding_var = tk.IntVar(value=2)
        # Date options
        self.music_date_mode_var = tk.StringVar(value="none")
        self.music_date_format_var = tk.StringVar(value="YYYY-MM-DD")

        # Files tab
        self.files_tmpl_var = tk.StringVar(value="Оригінал")
        self.files_pre_var = tk.StringVar()
        self.files_suf_var = tk.StringVar()
        self.files_find_var = tk.StringVar()
        self.files_repl_var = tk.StringVar()
        self.files_copy_var = tk.BooleanVar(value=False)
        self.files_tgt_var = tk.StringVar()
        self.files_count_var = tk.StringVar(value="0 / 0")
        self.files_regex_var = tk.BooleanVar(value=False)
        self.files_case_var = tk.StringVar(value="none")
        self.files_remove_var = tk.StringVar(value="none")
        self.files_trim_var = tk.BooleanVar(value=True)
        self.files_backup_var = tk.BooleanVar(value=False)
        self.files_backup_dir_var = tk.StringVar()
        self.files_profile_var = tk.StringVar()
        self.files_filter_var = tk.StringVar(value="Всі")
        self.files_recursive_var = tk.BooleanVar(value=False)
        # Numbering options
        self.files_num_start_var = tk.IntVar(value=1)
        self.files_num_step_var = tk.IntVar(value=1)
        self.files_num_padding_var = tk.IntVar(value=2)
        # Date options
        self.files_date_mode_var = tk.StringVar(value="none")
        self.files_date_format_var = tk.StringVar(value="YYYY-MM-DD")

        # Settings
        self.auto_select_var = tk.BooleanVar(value=self.settings.get("auto_select_all"))
        self.confirm_rename_var = tk.BooleanVar(value=self.settings.get("confirm_rename"))
        self.confirm_large_var = tk.BooleanVar(value=self.settings.get("confirm_large_batch"))
        self.large_threshold_var = tk.IntVar(value=self.settings.get("large_batch_threshold"))
        self.auto_remove_var = tk.BooleanVar(value=self.settings.get("auto_remove_after_rename"))
        self.show_notif_var = tk.BooleanVar(value=self.settings.get("show_notifications"))
        self.use_fallback_var = tk.BooleanVar(value=self.settings.get("use_original_name_fallback"))

        self.status_var = tk.StringVar(value="Готово")

        # Sorting state
        self._music_sort_key = "name"
        self._music_sort_reverse = False
        self._files_sort_key = "name"
        self._files_sort_reverse = False

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
        """Створити кнопку з cyan/teal кольором."""
        if style == "danger":
            return tb.Button(parent, text=text, command=command, bootstyle="danger")
        elif style == "outline" or style == "secondary":
            return tb.Button(parent, text=text, command=command, style="CyanOutline.TButton")
        elif style == "success":
            return tb.Button(parent, text=text, command=command, style="Cyan.TButton")
        else:
            # Primary buttons - use cyan filled
            return tb.Button(parent, text=text, command=command, style="Cyan.TButton")

    def _setup_music_page(self) -> None:
        """Сторінка для музичних файлів - user-friendly layout."""
        # Enable drag & drop on whole frame
        if self.dnd_enabled:
            try:
                self.music_frame.drop_target_register(DND_FILES)
                self.music_frame.dnd_bind("<<Drop>>", lambda e: self._on_drop(e, self.music_state, self.music_tree, AUDIO, self._refresh_music))
            except Exception:
                pass

        # ===== TOP SECTION: Drop Zone + Quick Actions =====
        top_section = tk.Frame(self.music_frame, bg=COLORS["bg_main"])
        top_section.pack(fill=tk.X, padx=15, pady=(15, 10))

        # Left: Drop zone area
        drop_frame = tk.Frame(top_section, bg=COLORS["bg_secondary"], relief="groove", bd=2)
        drop_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))

        drop_inner = tk.Frame(drop_frame, bg=COLORS["bg_secondary"])
        drop_inner.pack(expand=True, pady=20)

        tk.Label(drop_inner, text="🎵", font=("Segoe UI", 32),
                 bg=COLORS["bg_secondary"], fg=COLORS["cyan"]).pack()
        tk.Label(drop_inner, text="Перетягніть музичні файли сюди",
                 font=("Segoe UI", 11), bg=COLORS["bg_secondary"], fg=COLORS["cyan"]).pack(pady=(5, 0))
        tk.Label(drop_inner, text="або використовуйте кнопки нижче",
                 font=("Segoe UI", 9), bg=COLORS["bg_secondary"], fg=COLORS["text_dim"]).pack()

        # Quick add buttons inside drop zone
        btn_row = tk.Frame(drop_frame, bg=COLORS["bg_secondary"])
        btn_row.pack(pady=(0, 15))

        self._create_button(btn_row, "➕ Додати файли",
                           lambda: self._add_files_to(self.music_state, self.music_tree, AUDIO, self._refresh_music),
                           "primary").pack(side=tk.LEFT, padx=5)
        self._create_button(btn_row, "📁 Додати папку",
                           lambda: self._add_folder_to(self.music_state, self.music_tree, AUDIO, self._refresh_music),
                           "primary").pack(side=tk.LEFT, padx=5)

        # Right: Stats & Quick Actions
        right_panel = tk.Frame(top_section, bg=COLORS["bg_main"])
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))

        # File counter - big and prominent
        tk.Label(right_panel, text="Файлів:", font=("Segoe UI", 10),
                 bg=COLORS["bg_main"], fg=COLORS["cyan"]).pack(anchor="e")
        tk.Label(right_panel, textvariable=self.music_count_var, font=("Segoe UI", 24, "bold"),
                 bg=COLORS["bg_main"], fg=COLORS["cyan"]).pack(anchor="e", pady=(0, 10))

        # Quick action buttons - 2x2 grid
        btn_grid = tk.Frame(right_panel, bg=COLORS["bg_main"])
        btn_grid.pack()

        tb.Button(btn_grid, text="Все", width=7,
                  command=lambda: self._select_all_in(self.music_state, self.music_tree),
                  style="CyanOutline.TButton").grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        tb.Button(btn_grid, text="Ні", width=7,
                  command=lambda: self._deselect_all_in(self.music_state, self.music_tree),
                  style="CyanOutline.TButton").grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        tb.Button(btn_grid, text="Дубл", width=7,
                  command=lambda: self._find_duplicates(self.music_state, self.music_tree),
                  style="CyanOutline.TButton").grid(row=1, column=0, padx=2, pady=2, sticky="ew")
        tb.Button(btn_grid, text="Очист", width=7,
                  command=lambda: self._clear_all_in(self.music_state, self.music_tree),
                  style="CyanOutline.TButton").grid(row=1, column=1, padx=2, pady=2, sticky="ew")

        # ===== MAIN TEMPLATE SECTION =====
        tmpl_frame = tk.LabelFrame(self.music_frame, text=" 📝 Налаштування перейменування ",
                                    bg=COLORS["bg_main"], fg=COLORS["cyan"], font=("Segoe UI", 10, "bold"))
        tmpl_frame.pack(fill=tk.X, padx=15, pady=(0, 10))

        inner = tk.Frame(tmpl_frame, bg=COLORS["bg_main"])
        inner.pack(fill=tk.X, padx=15, pady=12)

        # Row 1: Template (most important) + Profile
        row1 = tk.Frame(inner, bg=COLORS["bg_main"])
        row1.pack(fill=tk.X, pady=(0, 10))

        tk.Label(row1, text="🎯 Шаблон:", bg=COLORS["bg_main"], fg=COLORS["cyan"],
                 font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        music_combo = ttk.Combobox(row1, textvariable=self.music_tmpl_var,
                                    values=list(self.AUDIO_TEMPLATES.keys()), width=24, state="readonly")
        music_combo.pack(side=tk.LEFT, padx=(8, 20))
        music_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_music())

        tk.Label(row1, text="Профіль:", bg=COLORS["bg_main"], fg=COLORS["cyan"],
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)
        self.music_profile_combo = ttk.Combobox(row1, textvariable=self.music_profile_var,
                                                 values=[], width=14, state="readonly")
        self.music_profile_combo.pack(side=tk.LEFT, padx=(8, 5))
        self.music_profile_combo.bind("<<ComboboxSelected>>", lambda e: self._load_profile_music())

        self._create_button(row1, "▪", lambda: self._save_profile_music(), "outline").pack(side=tk.LEFT, padx=2)
        self._create_button(row1, "▫", lambda: self._delete_profile_music(), "outline").pack(side=tk.LEFT, padx=2)
        self._create_button(row1, "▲", lambda: self._export_profile("audio"), "outline").pack(side=tk.LEFT, padx=2)
        self._create_button(row1, "▼", lambda: self._import_profile("audio"), "outline").pack(side=tk.LEFT, padx=2)

        # Separator
        ttk.Separator(inner, orient="horizontal").pack(fill=tk.X, pady=8)

        # Row 2: Basic options in a cleaner grid
        row2 = tk.Frame(inner, bg=COLORS["bg_main"])
        row2.pack(fill=tk.X, pady=(0, 8))

        # Left column: Prefix/Suffix
        col1 = tk.Frame(row2, bg=COLORS["bg_main"])
        col1.pack(side=tk.LEFT, padx=(0, 30))

        tk.Label(col1, text="Префікс:", bg=COLORS["bg_main"], fg=COLORS["cyan"],
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="e", padx=(0, 5))
        ttk.Entry(col1, textvariable=self.music_pre_var, width=14).grid(row=0, column=1)

        tk.Label(col1, text="Суфікс:", bg=COLORS["bg_main"], fg=COLORS["cyan"],
                 font=("Segoe UI", 9)).grid(row=1, column=0, sticky="e", padx=(0, 5), pady=(5, 0))
        ttk.Entry(col1, textvariable=self.music_suf_var, width=14).grid(row=1, column=1, pady=(5, 0))

        # Middle column: Find/Replace
        col2 = tk.Frame(row2, bg=COLORS["bg_main"])
        col2.pack(side=tk.LEFT, padx=(0, 30))

        tk.Label(col2, text="Знайти:", bg=COLORS["bg_main"], fg=COLORS["cyan"],
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="e", padx=(0, 5))
        ttk.Entry(col2, textvariable=self.music_find_var, width=14).grid(row=0, column=1)

        tk.Label(col2, text="Замінити:", bg=COLORS["bg_main"], fg=COLORS["cyan"],
                 font=("Segoe UI", 9)).grid(row=1, column=0, sticky="e", padx=(0, 5), pady=(5, 0))
        ttk.Entry(col2, textvariable=self.music_repl_var, width=14).grid(row=1, column=1, pady=(5, 0))

        # Right column: Toggles
        col3 = tk.Frame(row2, bg=COLORS["bg_main"])
        col3.pack(side=tk.LEFT)

        tb.Checkbutton(col3, text="Regex", variable=self.music_regex_var,
                       bootstyle="success").pack(anchor="w")
        tb.Checkbutton(col3, text="Trim пробіли", variable=self.music_trim_var,
                       bootstyle="success").pack(anchor="w", pady=(5, 0))

        # ===== ADVANCED OPTIONS (Collapsible) =====
        self.music_adv_visible = tk.BooleanVar(value=False)

        adv_toggle = tk.Frame(inner, bg=COLORS["bg_main"])
        adv_toggle.pack(fill=tk.X, pady=(5, 0))

        def toggle_advanced():
            self.music_adv_visible.set(not self.music_adv_visible.get())
            if self.music_adv_visible.get():
                music_adv_frame.pack(fill=tk.X, pady=(8, 0))
                adv_btn.config(text="▼ Приховати розширені опції")
            else:
                music_adv_frame.pack_forget()
                adv_btn.config(text="▶ Розширені опції")

        adv_btn = tb.Button(adv_toggle, text="▶ Розширені опції", command=toggle_advanced,
                            bootstyle="link")
        adv_btn.pack(side=tk.LEFT)

        # Advanced options frame (initially hidden)
        music_adv_frame = tk.Frame(inner, bg=COLORS["bg_secondary"])

        adv_inner = tk.Frame(music_adv_frame, bg=COLORS["bg_secondary"])
        adv_inner.pack(fill=tk.X, padx=10, pady=10)

        # Row: Numbering, Date, Remove, Case
        adv_row = tk.Frame(adv_inner, bg=COLORS["bg_secondary"])
        adv_row.pack(fill=tk.X)

        # Numbering
        num_frame = tk.LabelFrame(adv_row, text="Нумерація", bg=COLORS["bg_secondary"],
                                   fg=COLORS["cyan"], font=("Segoe UI", 9))
        num_frame.pack(side=tk.LEFT, padx=(0, 15))
        num_inner = tk.Frame(num_frame, bg=COLORS["bg_secondary"])
        num_inner.pack(padx=8, pady=5)

        tk.Label(num_inner, text="Старт:", bg=COLORS["bg_secondary"], fg=COLORS["cyan"],
                 font=("Segoe UI", 8)).grid(row=0, column=0)
        ttk.Spinbox(num_inner, textvariable=self.music_num_start_var, from_=0, to=9999,
                    width=4).grid(row=0, column=1, padx=2)
        tk.Label(num_inner, text="Крок:", bg=COLORS["bg_secondary"], fg=COLORS["cyan"],
                 font=("Segoe UI", 8)).grid(row=0, column=2, padx=(5, 0))
        ttk.Spinbox(num_inner, textvariable=self.music_num_step_var, from_=1, to=100,
                    width=3).grid(row=0, column=3, padx=2)
        tk.Label(num_inner, text="Цифри:", bg=COLORS["bg_secondary"], fg=COLORS["cyan"],
                 font=("Segoe UI", 8)).grid(row=0, column=4, padx=(5, 0))
        ttk.Spinbox(num_inner, textvariable=self.music_num_padding_var, from_=1, to=5,
                    width=3).grid(row=0, column=5, padx=2)

        # Date
        date_frame = tk.LabelFrame(adv_row, text="Додати дату", bg=COLORS["bg_secondary"],
                                    fg=COLORS["cyan"], font=("Segoe UI", 9))
        date_frame.pack(side=tk.LEFT, padx=(0, 15))
        date_inner = tk.Frame(date_frame, bg=COLORS["bg_secondary"])
        date_inner.pack(padx=8, pady=5)

        ttk.Combobox(date_inner, textvariable=self.music_date_mode_var,
                     values=["none", "modified", "created"], width=9, state="readonly").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Combobox(date_inner, textvariable=self.music_date_format_var,
                     values=list(DATE_FORMATS.keys()), width=13, state="readonly").pack(side=tk.LEFT)

        # Remove pattern
        remove_frame = tk.LabelFrame(adv_row, text="Видалити", bg=COLORS["bg_secondary"],
                                      fg=COLORS["cyan"], font=("Segoe UI", 9))
        remove_frame.pack(side=tk.LEFT, padx=(0, 15))
        ttk.Combobox(remove_frame, textvariable=self.music_remove_var,
                     values=list(PATTERN_LABELS.keys()), width=13, state="readonly").pack(padx=8, pady=5)

        # Case
        case_frame = tk.LabelFrame(adv_row, text="Регістр", bg=COLORS["bg_secondary"],
                                    fg=COLORS["cyan"], font=("Segoe UI", 9))
        case_frame.pack(side=tk.LEFT)
        ttk.Combobox(case_frame, textvariable=self.music_case_var,
                     values=list(CASE_LABELS.keys()), width=11, state="readonly").pack(padx=8, pady=5)

        # Row 2: Output options
        adv_row2 = tk.Frame(adv_inner, bg=COLORS["bg_secondary"])
        adv_row2.pack(fill=tk.X, pady=(10, 0))

        tb.Checkbutton(adv_row2, text="📋 Копіювати (не переміщувати)", variable=self.music_copy_var,
                       bootstyle="success").pack(side=tk.LEFT, padx=(0, 20))

        tb.Checkbutton(adv_row2, text="💾 Backup оригіналів", variable=self.music_backup_var,
                       bootstyle="success").pack(side=tk.LEFT, padx=(0, 5))
        self._create_button(adv_row2, "📂", lambda: self._choose_backup_dir(self.music_backup_dir_var),
                           "outline").pack(side=tk.LEFT, padx=(0, 20))

        self._create_button(adv_row2, "📂 Цільова папка", lambda: self._choose_target(self.music_state, self.music_tgt_var),
                           "outline").pack(side=tk.LEFT)
        tk.Label(adv_row2, textvariable=self.music_tgt_var, bg=COLORS["bg_secondary"],
                 fg=COLORS["text_dim"], font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=8)

        # Filter row
        adv_row3 = tk.Frame(adv_inner, bg=COLORS["bg_secondary"])
        adv_row3.pack(fill=tk.X, pady=(10, 0))

        tk.Label(adv_row3, text="Фільтр:", bg=COLORS["bg_secondary"], fg=COLORS["cyan"],
                 font=("Segoe UI", 9)).pack(side=tk.LEFT)
        ttk.Combobox(adv_row3, textvariable=self.music_filter_var,
                     values=["Всі", ".mp3", ".flac", ".wav", ".ogg", ".m4a"],
                     width=8, state="readonly").pack(side=tk.LEFT, padx=(5, 15))

        tb.Checkbutton(adv_row3, text="Включати підпапки", variable=self.music_recursive_var,
                       bootstyle="success").pack(side=tk.LEFT)

        # ===== ACTION BAR (Bottom) - pack BEFORE treeview =====
        action_frame = tk.Frame(self.music_frame, bg=COLORS["bg_secondary"])
        action_frame.pack(fill=tk.X, side=tk.BOTTOM)

        action_inner = tk.Frame(action_frame, bg=COLORS["bg_secondary"])
        action_inner.pack(pady=10)

        # Main action button - larger and more prominent with cyan fill
        rename_btn = tb.Button(action_inner, text="  ПЕРЕЙМЕНУВАТИ  ",
                               command=lambda: self._rename_selected(self.music_state, self.music_tree, self.music_copy_var,
                                                         self._refresh_music, self.music_history,
                                                         self.music_backup_var, self.music_backup_dir_var),
                               style="Cyan.TButton", width=18)
        rename_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Secondary actions - outline buttons with icons
        self._create_button(action_inner, "◉ Перегляд",
                           lambda: self._show_preview(self.music_state), "outline").pack(side=tk.LEFT, padx=2)
        self._create_button(action_inner, "⎗",
                           lambda: self._undo(self.music_history, self._refresh_music), "outline").pack(side=tk.LEFT, padx=2)
        self._create_button(action_inner, "⎘",
                           lambda: self._redo(self.music_history, self._refresh_music), "outline").pack(side=tk.LEFT, padx=2)
        self._create_button(action_inner, "⟳",
                           self._refresh_music, "outline").pack(side=tk.LEFT, padx=2)

        # Status on the right
        tk.Label(action_frame, textvariable=self.status_var, bg=COLORS["bg_secondary"],
                 fg=COLORS["cyan"], font=("Segoe UI", 9)).pack(side=tk.RIGHT, padx=15)

        # ===== SEARCH BAR =====
        search_frame = tk.Frame(self.music_frame, bg=COLORS["bg_main"])
        search_frame.pack(fill=tk.X, padx=15, pady=(5, 0))

        tk.Label(search_frame, text="🔍", bg=COLORS["bg_main"], fg=COLORS["cyan"],
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)
        self._music_search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self._music_search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)
        search_entry.bind("<KeyRelease>", lambda e: self._filter_music_list())
        tb.Button(search_frame, text="✗", width=3, bootstyle="secondary-outline",
                  command=lambda: (self._music_search_var.set(""), self._filter_music_list())).pack(side=tk.LEFT)

        # ===== FILE LIST =====
        self.music_tree = self._create_treeview(self.music_frame, self.music_state, AUDIO, self._refresh_music, is_music=True)

    def _setup_files_page(self) -> None:
        """Сторінка для загальних файлів - user-friendly layout."""
        # Enable drag & drop on whole frame
        if self.dnd_enabled:
            try:
                self.files_frame.drop_target_register(DND_FILES)
                self.files_frame.dnd_bind("<<Drop>>", lambda e: self._on_drop(e, self.files_state, self.files_tree, SUPPORTED, self._refresh_files))
            except Exception:
                pass

        # ===== TOP SECTION: Drop Zone + Quick Actions =====
        top_section = tk.Frame(self.files_frame, bg=COLORS["bg_main"])
        top_section.pack(fill=tk.X, padx=15, pady=(15, 10))

        # Left: Drop zone area
        drop_frame = tk.Frame(top_section, bg=COLORS["bg_secondary"], relief="groove", bd=2)
        drop_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))

        drop_inner = tk.Frame(drop_frame, bg=COLORS["bg_secondary"])
        drop_inner.pack(expand=True, pady=20)

        tk.Label(drop_inner, text="📁", font=("Segoe UI", 32),
                 bg=COLORS["bg_secondary"], fg=COLORS["cyan"]).pack()
        tk.Label(drop_inner, text="Перетягніть файли сюди",
                 font=("Segoe UI", 11), bg=COLORS["bg_secondary"], fg=COLORS["cyan"]).pack(pady=(5, 0))
        tk.Label(drop_inner, text="або використовуйте кнопки нижче",
                 font=("Segoe UI", 9), bg=COLORS["bg_secondary"], fg=COLORS["text_dim"]).pack()

        # Quick add buttons inside drop zone
        btn_row = tk.Frame(drop_frame, bg=COLORS["bg_secondary"])
        btn_row.pack(pady=(0, 15))

        self._create_button(btn_row, "➕ Додати файли",
                           lambda: self._add_files_to(self.files_state, self.files_tree, SUPPORTED, self._refresh_files),
                           "primary").pack(side=tk.LEFT, padx=5)
        self._create_button(btn_row, "📁 Додати папку",
                           lambda: self._add_folder_to(self.files_state, self.files_tree, SUPPORTED, self._refresh_files),
                           "primary").pack(side=tk.LEFT, padx=5)

        # Right: Stats & Quick Actions
        right_panel = tk.Frame(top_section, bg=COLORS["bg_main"])
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))

        # File counter - big and prominent
        tk.Label(right_panel, text="Файлів:", font=("Segoe UI", 10),
                 bg=COLORS["bg_main"], fg=COLORS["cyan"]).pack(anchor="e")
        tk.Label(right_panel, textvariable=self.files_count_var, font=("Segoe UI", 24, "bold"),
                 bg=COLORS["bg_main"], fg=COLORS["cyan"]).pack(anchor="e", pady=(0, 10))

        # Quick action buttons - 2x2 grid
        btn_grid = tk.Frame(right_panel, bg=COLORS["bg_main"])
        btn_grid.pack()

        tb.Button(btn_grid, text="Все", width=7,
                  command=lambda: self._select_all_in(self.files_state, self.files_tree),
                  style="CyanOutline.TButton").grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        tb.Button(btn_grid, text="Ні", width=7,
                  command=lambda: self._deselect_all_in(self.files_state, self.files_tree),
                  style="CyanOutline.TButton").grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        tb.Button(btn_grid, text="Дубл", width=7,
                  command=lambda: self._find_duplicates(self.files_state, self.files_tree),
                  style="CyanOutline.TButton").grid(row=1, column=0, padx=2, pady=2, sticky="ew")
        tb.Button(btn_grid, text="Очист", width=7,
                  command=lambda: self._clear_all_in(self.files_state, self.files_tree),
                  style="CyanOutline.TButton").grid(row=1, column=1, padx=2, pady=2, sticky="ew")

        # ===== MAIN TEMPLATE SECTION =====
        tmpl_frame = tk.LabelFrame(self.files_frame, text=" 📝 Налаштування перейменування ",
                                    bg=COLORS["bg_main"], fg=COLORS["cyan"], font=("Segoe UI", 10, "bold"))
        tmpl_frame.pack(fill=tk.X, padx=15, pady=(0, 10))

        inner = tk.Frame(tmpl_frame, bg=COLORS["bg_main"])
        inner.pack(fill=tk.X, padx=15, pady=12)

        # Row 1: Template (most important) + Profile
        row1 = tk.Frame(inner, bg=COLORS["bg_main"])
        row1.pack(fill=tk.X, pady=(0, 10))

        tk.Label(row1, text="🎯 Шаблон:", bg=COLORS["bg_main"], fg=COLORS["cyan"],
                 font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        files_combo = ttk.Combobox(row1, textvariable=self.files_tmpl_var,
                                    values=list(self.FILE_TEMPLATES.keys()), width=24, state="readonly")
        files_combo.pack(side=tk.LEFT, padx=(8, 20))
        files_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_files())

        tk.Label(row1, text="Профіль:", bg=COLORS["bg_main"], fg=COLORS["cyan"],
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)
        self.files_profile_combo = ttk.Combobox(row1, textvariable=self.files_profile_var,
                                                 values=[], width=14, state="readonly")
        self.files_profile_combo.pack(side=tk.LEFT, padx=(8, 5))
        self.files_profile_combo.bind("<<ComboboxSelected>>", lambda e: self._load_profile_files())

        self._create_button(row1, "▪", lambda: self._save_profile_files(), "outline").pack(side=tk.LEFT, padx=2)
        self._create_button(row1, "▫", lambda: self._delete_profile_files(), "outline").pack(side=tk.LEFT, padx=2)
        self._create_button(row1, "▲", lambda: self._export_profile("general"), "outline").pack(side=tk.LEFT, padx=2)
        self._create_button(row1, "▼", lambda: self._import_profile("general"), "outline").pack(side=tk.LEFT, padx=2)

        # Separator
        ttk.Separator(inner, orient="horizontal").pack(fill=tk.X, pady=8)

        # Row 2: Basic options in a cleaner grid
        row2 = tk.Frame(inner, bg=COLORS["bg_main"])
        row2.pack(fill=tk.X, pady=(0, 8))

        # Left column: Prefix/Suffix
        col1 = tk.Frame(row2, bg=COLORS["bg_main"])
        col1.pack(side=tk.LEFT, padx=(0, 30))

        tk.Label(col1, text="Префікс:", bg=COLORS["bg_main"], fg=COLORS["cyan"],
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="e", padx=(0, 5))
        ttk.Entry(col1, textvariable=self.files_pre_var, width=14).grid(row=0, column=1)

        tk.Label(col1, text="Суфікс:", bg=COLORS["bg_main"], fg=COLORS["cyan"],
                 font=("Segoe UI", 9)).grid(row=1, column=0, sticky="e", padx=(0, 5), pady=(5, 0))
        ttk.Entry(col1, textvariable=self.files_suf_var, width=14).grid(row=1, column=1, pady=(5, 0))

        # Middle column: Find/Replace
        col2 = tk.Frame(row2, bg=COLORS["bg_main"])
        col2.pack(side=tk.LEFT, padx=(0, 30))

        tk.Label(col2, text="Знайти:", bg=COLORS["bg_main"], fg=COLORS["cyan"],
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="e", padx=(0, 5))
        ttk.Entry(col2, textvariable=self.files_find_var, width=14).grid(row=0, column=1)

        tk.Label(col2, text="Замінити:", bg=COLORS["bg_main"], fg=COLORS["cyan"],
                 font=("Segoe UI", 9)).grid(row=1, column=0, sticky="e", padx=(0, 5), pady=(5, 0))
        ttk.Entry(col2, textvariable=self.files_repl_var, width=14).grid(row=1, column=1, pady=(5, 0))

        # Right column: Toggles
        col3 = tk.Frame(row2, bg=COLORS["bg_main"])
        col3.pack(side=tk.LEFT)

        tb.Checkbutton(col3, text="Regex", variable=self.files_regex_var,
                       bootstyle="success").pack(anchor="w")
        tb.Checkbutton(col3, text="Trim пробіли", variable=self.files_trim_var,
                       bootstyle="success").pack(anchor="w", pady=(5, 0))

        # ===== ADVANCED OPTIONS (Collapsible) =====
        self.files_adv_visible = tk.BooleanVar(value=False)

        adv_toggle = tk.Frame(inner, bg=COLORS["bg_main"])
        adv_toggle.pack(fill=tk.X, pady=(5, 0))

        def toggle_advanced():
            self.files_adv_visible.set(not self.files_adv_visible.get())
            if self.files_adv_visible.get():
                files_adv_frame.pack(fill=tk.X, pady=(8, 0))
                adv_btn.config(text="▼ Приховати розширені опції")
            else:
                files_adv_frame.pack_forget()
                adv_btn.config(text="▶ Розширені опції")

        adv_btn = tb.Button(adv_toggle, text="▶ Розширені опції", command=toggle_advanced,
                            bootstyle="link")
        adv_btn.pack(side=tk.LEFT)

        # Advanced options frame (initially hidden)
        files_adv_frame = tk.Frame(inner, bg=COLORS["bg_secondary"])

        adv_inner = tk.Frame(files_adv_frame, bg=COLORS["bg_secondary"])
        adv_inner.pack(fill=tk.X, padx=10, pady=10)

        # Row: Numbering, Date, Remove, Case
        adv_row = tk.Frame(adv_inner, bg=COLORS["bg_secondary"])
        adv_row.pack(fill=tk.X)

        # Numbering
        num_frame = tk.LabelFrame(adv_row, text="Нумерація", bg=COLORS["bg_secondary"],
                                   fg=COLORS["cyan"], font=("Segoe UI", 9))
        num_frame.pack(side=tk.LEFT, padx=(0, 15))
        num_inner = tk.Frame(num_frame, bg=COLORS["bg_secondary"])
        num_inner.pack(padx=8, pady=5)

        tk.Label(num_inner, text="Старт:", bg=COLORS["bg_secondary"], fg=COLORS["cyan"],
                 font=("Segoe UI", 8)).grid(row=0, column=0)
        ttk.Spinbox(num_inner, textvariable=self.files_num_start_var, from_=0, to=9999,
                    width=4).grid(row=0, column=1, padx=2)
        tk.Label(num_inner, text="Крок:", bg=COLORS["bg_secondary"], fg=COLORS["cyan"],
                 font=("Segoe UI", 8)).grid(row=0, column=2, padx=(5, 0))
        ttk.Spinbox(num_inner, textvariable=self.files_num_step_var, from_=1, to=100,
                    width=3).grid(row=0, column=3, padx=2)
        tk.Label(num_inner, text="Цифри:", bg=COLORS["bg_secondary"], fg=COLORS["cyan"],
                 font=("Segoe UI", 8)).grid(row=0, column=4, padx=(5, 0))
        ttk.Spinbox(num_inner, textvariable=self.files_num_padding_var, from_=1, to=5,
                    width=3).grid(row=0, column=5, padx=2)

        # Date
        date_frame = tk.LabelFrame(adv_row, text="Додати дату", bg=COLORS["bg_secondary"],
                                    fg=COLORS["cyan"], font=("Segoe UI", 9))
        date_frame.pack(side=tk.LEFT, padx=(0, 15))
        date_inner = tk.Frame(date_frame, bg=COLORS["bg_secondary"])
        date_inner.pack(padx=8, pady=5)

        ttk.Combobox(date_inner, textvariable=self.files_date_mode_var,
                     values=["none", "modified", "created"], width=9, state="readonly").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Combobox(date_inner, textvariable=self.files_date_format_var,
                     values=list(DATE_FORMATS.keys()), width=13, state="readonly").pack(side=tk.LEFT)

        # Remove pattern
        remove_frame = tk.LabelFrame(adv_row, text="Видалити", bg=COLORS["bg_secondary"],
                                      fg=COLORS["cyan"], font=("Segoe UI", 9))
        remove_frame.pack(side=tk.LEFT, padx=(0, 15))
        ttk.Combobox(remove_frame, textvariable=self.files_remove_var,
                     values=list(PATTERN_LABELS.keys()), width=13, state="readonly").pack(padx=8, pady=5)

        # Case
        case_frame = tk.LabelFrame(adv_row, text="Регістр", bg=COLORS["bg_secondary"],
                                    fg=COLORS["cyan"], font=("Segoe UI", 9))
        case_frame.pack(side=tk.LEFT)
        ttk.Combobox(case_frame, textvariable=self.files_case_var,
                     values=list(CASE_LABELS.keys()), width=11, state="readonly").pack(padx=8, pady=5)

        # Row 2: Output options
        adv_row2 = tk.Frame(adv_inner, bg=COLORS["bg_secondary"])
        adv_row2.pack(fill=tk.X, pady=(10, 0))

        tb.Checkbutton(adv_row2, text="📋 Копіювати (не переміщувати)", variable=self.files_copy_var,
                       bootstyle="success").pack(side=tk.LEFT, padx=(0, 20))

        tb.Checkbutton(adv_row2, text="💾 Backup оригіналів", variable=self.files_backup_var,
                       bootstyle="success").pack(side=tk.LEFT, padx=(0, 5))
        self._create_button(adv_row2, "📂", lambda: self._choose_backup_dir(self.files_backup_dir_var),
                           "outline").pack(side=tk.LEFT, padx=(0, 20))

        self._create_button(adv_row2, "📂 Цільова папка", lambda: self._choose_target(self.files_state, self.files_tgt_var),
                           "outline").pack(side=tk.LEFT)
        tk.Label(adv_row2, textvariable=self.files_tgt_var, bg=COLORS["bg_secondary"],
                 fg=COLORS["text_dim"], font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=8)

        # Filter row
        adv_row3 = tk.Frame(adv_inner, bg=COLORS["bg_secondary"])
        adv_row3.pack(fill=tk.X, pady=(10, 0))

        tk.Label(adv_row3, text="Фільтр:", bg=COLORS["bg_secondary"], fg=COLORS["cyan"],
                 font=("Segoe UI", 9)).pack(side=tk.LEFT)
        filter_combo = ttk.Combobox(adv_row3, textvariable=self.files_filter_var,
                     values=["Всі", "🎵 Аудіо", "🖼 Зображення", "📄 Документи", "🎬 Відео"],
                     width=12, state="readonly")
        filter_combo.pack(side=tk.LEFT, padx=(5, 15))
        filter_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filter_files())

        tb.Checkbutton(adv_row3, text="Включати підпапки", variable=self.files_recursive_var,
                       bootstyle="success").pack(side=tk.LEFT)

        # ===== ACTION BAR (Bottom) - pack BEFORE treeview =====
        action_frame = tk.Frame(self.files_frame, bg=COLORS["bg_secondary"])
        action_frame.pack(fill=tk.X, side=tk.BOTTOM)

        action_inner = tk.Frame(action_frame, bg=COLORS["bg_secondary"])
        action_inner.pack(pady=10)

        # Main action button - larger and more prominent with cyan fill
        rename_btn = tb.Button(action_inner, text="  ПЕРЕЙМЕНУВАТИ  ",
                               command=lambda: self._rename_selected(self.files_state, self.files_tree, self.files_copy_var,
                                                         self._refresh_files, self.files_history,
                                                         self.files_backup_var, self.files_backup_dir_var),
                               style="Cyan.TButton", width=18)
        rename_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Secondary actions - outline buttons with icons
        self._create_button(action_inner, "◉ Перегляд",
                           lambda: self._show_preview(self.files_state), "outline").pack(side=tk.LEFT, padx=2)
        self._create_button(action_inner, "⎗",
                           lambda: self._undo(self.files_history, self._refresh_files), "outline").pack(side=tk.LEFT, padx=2)
        self._create_button(action_inner, "⎘",
                           lambda: self._redo(self.files_history, self._refresh_files), "outline").pack(side=tk.LEFT, padx=2)
        self._create_button(action_inner, "⟳",
                           self._refresh_files, "outline").pack(side=tk.LEFT, padx=2)

        # Status on the right
        tk.Label(action_frame, textvariable=self.status_var, bg=COLORS["bg_secondary"],
                 fg=COLORS["cyan"], font=("Segoe UI", 9)).pack(side=tk.RIGHT, padx=15)

        # ===== SEARCH BAR =====
        search_frame = tk.Frame(self.files_frame, bg=COLORS["bg_main"])
        search_frame.pack(fill=tk.X, padx=15, pady=(5, 0))

        tk.Label(search_frame, text="🔍", bg=COLORS["bg_main"], fg=COLORS["cyan"],
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)
        self._files_search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self._files_search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)
        search_entry.bind("<KeyRelease>", lambda e: self._filter_files_list())
        tb.Button(search_frame, text="✗", width=3, bootstyle="secondary-outline",
                  command=lambda: (self._files_search_var.set(""), self._filter_files_list())).pack(side=tk.LEFT)

        # ===== FILE LIST =====
        self.files_tree = self._create_treeview(self.files_frame, self.files_state, SUPPORTED, self._refresh_files, is_music=False)

    def _create_treeview(self, parent, state: AppState, allowed_ext: tuple, refresh_fn, is_music: bool = False) -> ttk.Treeview:
        """Створення таблиці файлів з сортуванням."""
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

        widths = {"✓": 40, "№": 45, "Тип": 45, "Оригінал": 280, "Нове ім'я": 280, "Розмір": 75, "Інфо": 130}

        # Add sorting on column click
        for c in cols:
            tree.heading(c, text=c, command=lambda col=c: self._sort_column(tree, state, col, is_music, refresh_fn))
            tree.column(c, width=widths.get(c, 100), anchor="w" if c not in ("✓", "№", "Тип") else "center")

        tree.bind("<Button-1>", lambda e: self._on_tree_click(e, tree, state))
        tree.bind("<Double-1>", lambda e: self._on_tree_double_click(e, tree, state, refresh_fn))
        tree.bind("<Button-3>", lambda e: self._on_tree_right_click(e, tree, state, refresh_fn))  # Right-click menu

        # Drag and drop support
        if self.dnd_enabled:
            try:
                tree.drop_target_register(DND_FILES)
                tree.dnd_bind("<<Drop>>", lambda e: self._on_drop(e, state, tree, allowed_ext, refresh_fn))
            except Exception:
                pass

        # Drag to reorder within tree
        tree.bind("<ButtonPress-1>", lambda e: self._on_drag_start(e, tree, state))
        tree.bind("<B1-Motion>", lambda e: self._on_drag_motion(e, tree, state))
        tree.bind("<ButtonRelease-1>", lambda e: self._on_drag_end(e, tree, state, refresh_fn))
        self._drag_data = {"item": None, "start_y": 0}

        return tree

    def _sort_column(self, tree: ttk.Treeview, state: AppState, col: str, is_music: bool, refresh_fn) -> None:
        """Сортувати за колонкою."""
        sort_keys = {
            "Оригінал": "name",
            "Розмір": "size",
            "Тип": "type",
            "Інфо": "modified",
        }

        if col not in sort_keys:
            return

        key = sort_keys[col]

        # Toggle sort direction
        if is_music:
            if self._music_sort_key == key:
                self._music_sort_reverse = not self._music_sort_reverse
            else:
                self._music_sort_key = key
                self._music_sort_reverse = False
            state.sort_entries(key, self._music_sort_reverse)
        else:
            if self._files_sort_key == key:
                self._files_sort_reverse = not self._files_sort_reverse
            else:
                self._files_sort_key = key
                self._files_sort_reverse = False
            state.sort_entries(key, self._files_sort_reverse)

        refresh_fn()

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
            tb.Checkbutton(inner, text=label, variable=var, bootstyle="success").pack(anchor="w", pady=4)

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

    # ========== Live Preview ==========

    def _setup_live_preview(self) -> None:
        """Setup live preview - update table as user types."""
        # Music page variables to watch
        music_vars = [
            self.music_tmpl_var, self.music_pre_var, self.music_suf_var,
            self.music_find_var, self.music_repl_var, self.music_case_var,
            self.music_remove_var, self.music_date_mode_var, self.music_date_format_var,
        ]
        for var in music_vars:
            var.trace_add("write", lambda *args: self._debounce_music_preview())

        # Files page variables to watch
        files_vars = [
            self.files_tmpl_var, self.files_pre_var, self.files_suf_var,
            self.files_find_var, self.files_repl_var, self.files_case_var,
            self.files_remove_var, self.files_date_mode_var, self.files_date_format_var,
        ]
        for var in files_vars:
            var.trace_add("write", lambda *args: self._debounce_files_preview())

    def _debounce_music_preview(self) -> None:
        """Debounced update for music preview."""
        if self._music_preview_timer:
            self.root.after_cancel(self._music_preview_timer)
        self._music_preview_timer = self.root.after(300, self._refresh_music)

    def _debounce_files_preview(self) -> None:
        """Debounced update for files preview."""
        if self._files_preview_timer:
            self.root.after_cancel(self._files_preview_timer)
        self._files_preview_timer = self.root.after(300, self._refresh_files)

    def _filter_music_list(self) -> None:
        """Filter music list by search term."""
        search = self._music_search_var.get().lower() if self._music_search_var else ""
        self._refresh_music(filter_text=search)

    def _filter_files_list(self) -> None:
        """Filter files list by search term."""
        search = self._files_search_var.get().lower() if self._files_search_var else ""
        self._refresh_files(filter_text=search)

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

    def _refresh_music(self, filter_text: str = "") -> None:
        """Оновити музичну таблицю."""
        self._refresh_tree(
            self.music_state, self.music_tree, self.music_count_var,
            self.music_tmpl_var, self.music_pre_var, self.music_suf_var,
            self.music_find_var, self.music_repl_var,
            self.music_regex_var, self.music_case_var, self.music_remove_var,
            self.music_trim_var, self.music_date_mode_var, self.music_date_format_var,
            self.music_num_start_var, self.music_num_step_var, self.music_num_padding_var,
            is_audio=True, filter_text=filter_text
        )

    def _refresh_files(self, filter_text: str = "") -> None:
        """Оновити файлову таблицю."""
        self._refresh_tree(
            self.files_state, self.files_tree, self.files_count_var,
            self.files_tmpl_var, self.files_pre_var, self.files_suf_var,
            self.files_find_var, self.files_repl_var,
            self.files_regex_var, self.files_case_var, self.files_remove_var,
            self.files_trim_var, self.files_date_mode_var, self.files_date_format_var,
            self.files_num_start_var, self.files_num_step_var, self.files_num_padding_var,
            is_audio=False, filter_text=filter_text
        )

    def _refresh_tree(self, state: AppState, tree: ttk.Treeview, count_var: tk.StringVar,
                      tmpl_var: tk.StringVar, pre_var: tk.StringVar, suf_var: tk.StringVar,
                      find_var: tk.StringVar, repl_var: tk.StringVar,
                      regex_var: tk.BooleanVar, case_var: tk.StringVar, remove_var: tk.StringVar,
                      trim_var: tk.BooleanVar, date_mode_var: tk.StringVar, date_format_var: tk.StringVar,
                      num_start_var: tk.IntVar, num_step_var: tk.IntVar, num_padding_var: tk.IntVar,
                      is_audio: bool, filter_text: str = "") -> None:
        """Оновити таблицю з усіма трансформаціями."""
        tree.delete(*tree.get_children())

        num_start = num_start_var.get()
        num_step = num_step_var.get()

        visible_count = 0
        for i, entry in enumerate(state.entries):
            # Apply search filter
            if filter_text:
                if filter_text not in entry.original.lower() and filter_text not in entry.new_name.lower():
                    continue
            # Calculate current number
            current_num = num_start + (i * num_step)

            # Get base name
            title = sanitize(os.path.splitext(entry.original)[0])
            artist = ""
            album = ""
            year = ""

            if is_audio and entry.ext in AUDIO:
                try:
                    tags = get_audio_tags_extended(entry.path)
                    if tags.get("title"):
                        title = sanitize(tags["title"])
                    artist = sanitize(tags.get("artist") or "")
                    album = sanitize(tags.get("album") or "")
                    year = str(tags.get("year") or "")
                except Exception:
                    pass

                tmpl = tmpl_var.get()
                template_func = self.AUDIO_TEMPLATES.get(tmpl, self.AUDIO_TEMPLATES["Оригінал"])

                # Handle templates with extra params
                if tmpl == "Альбом - Назва":
                    base = template_func(artist, title, current_num, "", album)
                elif tmpl == "[Рік] Виконавець - Назва":
                    base = template_func(artist, title, current_num, "", year)
                else:
                    base = template_func(artist, title, current_num, "")
            else:
                tmpl = tmpl_var.get()
                template_func = self.FILE_TEMPLATES.get(tmpl, self.FILE_TEMPLATES["Оригінал"])
                base = template_func(title, current_num, "")

            if not base:
                base = title or "unnamed"

            # Apply prefix/suffix
            base = pre_var.get() + base + suf_var.get()

            # Apply find/replace (with optional regex)
            if find_var.get():
                if regex_var.get():
                    result = apply_regex_replace(base, find_var.get(), repl_var.get())
                    if result is not None:
                        base = result
                else:
                    base = base.replace(find_var.get(), repl_var.get())

            # Apply remove pattern
            if remove_var.get() and remove_var.get() != "none":
                base = remove_pattern(base, remove_var.get())

            # Apply case transformation
            if case_var.get() and case_var.get() != "none":
                base = apply_case(base, case_var.get())

            # Apply trim spaces
            if trim_var.get():
                base = trim_spaces(base, "all")

            # Apply date prefix
            if date_mode_var.get() and date_mode_var.get() != "none":
                try:
                    created, modified = get_file_dates(entry.path)
                    date_to_use = modified if date_mode_var.get() == "modified" else created
                    if date_to_use:
                        fmt = DATE_FORMATS.get(date_format_var.get(), "%Y-%m-%d")
                        date_str = date_to_use.strftime(fmt)
                        base = f"{date_str} - {base}"
                except Exception:
                    pass

            # Format number in base if template uses ##
            if "##" in tmpl_var.get() or "###" in tmpl_var.get():
                # Number formatting already done in template
                pass

            entry.new_name = sanitize(base) + entry.ext

            visible_count += 1
            tree.insert("", "end", iid=i, values=(
                "✓" if entry.selected.get() else "",
                visible_count,
                entry.file_type,
                entry.original,
                entry.new_name,
                bytes_to_human_readable(entry.size),
                entry.info
            ))

        selected = state.count_selected()
        if filter_text:
            count_var.set(f"{selected} / {len(state.entries)} (показано: {visible_count})")
        else:
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

    def _on_tree_double_click(self, event: tk.Event, tree: ttk.Treeview, state: AppState, refresh_fn) -> None:
        """Подвійний клік для редагування нового імені."""
        region = tree.identify_region(event.x, event.y)
        if region != "cell": return
        col = tree.identify_column(event.x)
        item = tree.identify_row(event.y)
        if not item: return
        idx = int(item)
        if idx >= len(state.entries): return

        # Only allow editing the "New Name" column (#5)
        if col != "#5": return

        entry = state.entries[idx]

        # Get cell position
        x, y, w, h = tree.bbox(item, "Нове ім'я")
        if not x: return

        # Create entry widget for editing
        edit_var = tk.StringVar(value=os.path.splitext(entry.new_name)[0])
        edit_entry = ttk.Entry(tree, textvariable=edit_var, font=("Segoe UI", 10))
        edit_entry.place(x=x, y=y, width=w, height=h)
        edit_entry.focus_set()
        edit_entry.select_range(0, tk.END)

        def save_edit(event=None):
            new_base = edit_var.get().strip()
            if new_base:
                entry.new_name = sanitize(new_base) + entry.ext
                tree.set(idx, "Нове ім'я", entry.new_name)
            edit_entry.destroy()

        def cancel_edit(event=None):
            edit_entry.destroy()

        edit_entry.bind("<Return>", save_edit)
        edit_entry.bind("<Escape>", cancel_edit)
        edit_entry.bind("<FocusOut>", save_edit)

    def _on_tree_right_click(self, event: tk.Event, tree: ttk.Treeview, state: AppState, refresh_fn) -> None:
        """Right-click context menu."""
        item = tree.identify_row(event.y)
        if not item:
            return

        idx = int(item)
        if idx >= len(state.entries):
            return

        # Select the item if not already selected
        tree.selection_set(item)
        entry = state.entries[idx]

        # Create context menu
        menu = tk.Menu(self.root, tearoff=0, bg=COLORS["bg_secondary"], fg=COLORS["text"],
                      activebackground=COLORS["cyan"], activeforeground="#000000")

        menu.add_command(label="✓ Вибрати", command=lambda: self._ctx_select(entry, tree, idx, state))
        menu.add_command(label="✗ Зняти вибір", command=lambda: self._ctx_deselect(entry, tree, idx, state))
        menu.add_separator()
        menu.add_command(label="✏️ Редагувати ім'я", command=lambda: self._ctx_edit_name(tree, state, idx, refresh_fn))
        menu.add_command(label="🔄 Скинути ім'я", command=lambda: self._ctx_reset_name(entry, tree, idx))
        menu.add_separator()

        # Add preview option for images and audio with album art
        if entry.ext.lower() in IMG or entry.ext.lower() in AUDIO:
            menu.add_command(label="🖼️ Перегляд", command=lambda: self._ctx_preview_media(entry))

        # Add MusicBrainz search for audio files
        if entry.ext.lower() in AUDIO:
            menu.add_command(label="🌐 Шукати в MusicBrainz",
                           command=lambda: self._ctx_search_musicbrainz(entry, tree, idx, refresh_fn))

        if entry.ext.lower() in IMG or entry.ext.lower() in AUDIO:
            menu.add_separator()

        menu.add_command(label="📂 Відкрити папку", command=lambda: self._ctx_open_folder(entry))
        menu.add_command(label="📄 Відкрити файл", command=lambda: self._ctx_open_file(entry))
        menu.add_separator()
        menu.add_command(label="🗑 Видалити зі списку", command=lambda: self._ctx_remove(state, tree, idx, refresh_fn))

        menu.tk_popup(event.x_root, event.y_root)

    def _ctx_select(self, entry: FileEntry, tree: ttk.Treeview, idx: int, state: AppState) -> None:
        entry.selected.set(True)
        tree.set(idx, "✓", "✓")
        self._update_count(state)

    def _ctx_deselect(self, entry: FileEntry, tree: ttk.Treeview, idx: int, state: AppState) -> None:
        entry.selected.set(False)
        tree.set(idx, "✓", "")
        self._update_count(state)

    def _ctx_edit_name(self, tree: ttk.Treeview, state: AppState, idx: int, refresh_fn) -> None:
        # Simulate double-click on the name column
        item = str(idx)
        bbox = tree.bbox(item, "Нове ім'я")
        if bbox:
            class FakeEvent:
                def __init__(self, x, y):
                    self.x = x
                    self.y = y
            event = FakeEvent(bbox[0] + 5, bbox[1] + 5)
            self._on_tree_double_click(event, tree, state, refresh_fn)

    def _ctx_reset_name(self, entry: FileEntry, tree: ttk.Treeview, idx: int) -> None:
        entry.new_name = entry.original
        tree.set(idx, "Нове ім'я", entry.new_name)

    def _ctx_open_folder(self, entry: FileEntry) -> None:
        import subprocess
        folder = entry.directory
        if platform.system() == "Windows":
            subprocess.run(["explorer", folder])
        elif platform.system() == "Darwin":
            subprocess.run(["open", folder])
        else:
            subprocess.run(["xdg-open", folder])

    def _ctx_open_file(self, entry: FileEntry) -> None:
        import subprocess
        if platform.system() == "Windows":
            os.startfile(entry.path)
        elif platform.system() == "Darwin":
            subprocess.run(["open", entry.path])
        else:
            subprocess.run(["xdg-open", entry.path])

    def _ctx_remove(self, state: AppState, tree: ttk.Treeview, idx: int, refresh_fn) -> None:
        if idx < len(state.entries):
            entry = state.entries[idx]
            state.path_set.discard(entry.path)
            state.entries.remove(entry)
            refresh_fn()

    def _ctx_preview_media(self, entry: FileEntry) -> None:
        """Preview image or album art from audio file."""
        import io

        preview_win = tk.Toplevel(self.root)
        preview_win.title(f"Перегляд: {entry.original_name}")
        preview_win.configure(bg=COLORS["bg_main"])
        preview_win.geometry("400x400")
        preview_win.transient(self.root)

        frame = tk.Frame(preview_win, bg=COLORS["bg_main"], padx=10, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        img_data = None
        img = None

        if entry.ext.lower() in IMG:
            try:
                img = Image.open(entry.path)
            except Exception:
                pass
        elif entry.ext.lower() in AUDIO:
            img_data = get_album_art(entry.path)
            if img_data:
                try:
                    img = Image.open(io.BytesIO(img_data))
                except Exception:
                    pass

        if img:
            max_size = 380
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self._preview_references.append(photo)

            label = tk.Label(frame, image=photo, bg=COLORS["bg_main"])
            label.pack(expand=True)

            info_text = f"{img.size[0]}×{img.size[1]}"
            tk.Label(frame, text=info_text, bg=COLORS["bg_main"], fg=COLORS["cyan"],
                    font=("Segoe UI", 10)).pack(pady=(5, 0))
        else:
            tk.Label(frame, text="Зображення недоступне",
                    bg=COLORS["bg_main"], fg=COLORS["text"],
                    font=("Segoe UI", 12)).pack(expand=True)

        ttk.Button(frame, text="Закрити", command=preview_win.destroy,
                  bootstyle="outline").pack(pady=(10, 0))

    def _ctx_search_musicbrainz(self, entry: FileEntry, tree: ttk.Treeview,
                                 idx: int, refresh_fn) -> None:
        """Search MusicBrainz for track metadata."""
        import threading

        dialog = tk.Toplevel(self.root)
        dialog.title("MusicBrainz пошук")
        dialog.geometry("550x400")
        dialog.configure(bg=COLORS["bg_main"])
        dialog.transient(self.root)
        dialog.grab_set()

        # Header
        tk.Label(dialog, text="🌐 Пошук метаданих в MusicBrainz",
                 font=("Segoe UI", 12, "bold"), bg=COLORS["bg_main"],
                 fg=COLORS["cyan"]).pack(pady=(10, 5))

        tk.Label(dialog, text=f"Файл: {entry.original}",
                 font=("Segoe UI", 9), bg=COLORS["bg_main"],
                 fg=COLORS["text_dim"]).pack(pady=(0, 10))

        # Search fields
        search_frame = tk.Frame(dialog, bg=COLORS["bg_main"])
        search_frame.pack(fill=tk.X, padx=15)

        artist_var = tk.StringVar(value=entry.metadata.get("artist", ""))
        title_var = tk.StringVar(value=entry.metadata.get("title", "") or os.path.splitext(entry.original)[0])

        tk.Label(search_frame, text="Виконавець:", bg=COLORS["bg_main"],
                 fg=COLORS["text"]).grid(row=0, column=0, sticky="e", padx=5)
        ttk.Entry(search_frame, textvariable=artist_var, width=40).grid(row=0, column=1, pady=2)

        tk.Label(search_frame, text="Назва:", bg=COLORS["bg_main"],
                 fg=COLORS["text"]).grid(row=1, column=0, sticky="e", padx=5)
        ttk.Entry(search_frame, textvariable=title_var, width=40).grid(row=1, column=1, pady=2)

        # Results treeview
        results_frame = tk.Frame(dialog, bg=COLORS["bg_main"])
        results_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        cols = ("Виконавець", "Назва", "Альбом", "Рік")
        results_tree = ttk.Treeview(results_frame, columns=cols, show="headings", height=8)

        vsb = ttk.Scrollbar(results_frame, orient="vertical", command=results_tree.yview)
        results_tree.configure(yscrollcommand=vsb.set)
        results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        for col in cols:
            results_tree.heading(col, text=col)
            results_tree.column(col, width=120)

        status_var = tk.StringVar(value="Введіть дані та натисніть 'Шукати'")
        tk.Label(dialog, textvariable=status_var, bg=COLORS["bg_main"],
                 fg=COLORS["text_dim"], font=("Segoe UI", 9)).pack()

        results_data = []

        def do_search():
            artist = artist_var.get().strip()
            title = title_var.get().strip()

            if not artist and not title:
                status_var.set("Введіть виконавця або назву")
                return

            status_var.set("🔄 Пошук...")
            results_tree.delete(*results_tree.get_children())
            results_data.clear()

            def search_thread():
                try:
                    results = search_recording(artist=artist or None, title=title or None, limit=10)
                    dialog.after(0, lambda: show_results(results))
                except Exception as e:
                    dialog.after(0, lambda: status_var.set(f"❌ Помилка: {e}"))

            threading.Thread(target=search_thread, daemon=True).start()

        def show_results(results):
            results_data.clear()
            results_data.extend(results)

            if not results:
                status_var.set("Нічого не знайдено")
                return

            for i, r in enumerate(results):
                results_tree.insert("", "end", iid=str(i), values=(
                    r.get("artist", "—"),
                    r.get("title", "—"),
                    r.get("album", "—"),
                    r.get("year", "—")
                ))

            status_var.set(f"Знайдено {len(results)} результатів")

        def apply_selected():
            selection = results_tree.selection()
            if not selection:
                return

            idx_sel = int(selection[0])
            if idx_sel >= len(results_data):
                return

            result = results_data[idx_sel]

            # Update entry metadata and new_name
            if result.get("artist"):
                entry.metadata["artist"] = result["artist"]
            if result.get("title"):
                entry.metadata["title"] = result["title"]
            if result.get("album"):
                entry.metadata["album"] = result["album"]
            if result.get("year"):
                entry.metadata["year"] = result["year"]

            # Update new_name based on template
            artist = result.get("artist", "")
            title = result.get("title", "")
            if artist and title:
                entry.new_name = sanitize(f"{artist} - {title}") + entry.ext
            elif title:
                entry.new_name = sanitize(title) + entry.ext

            refresh_fn()
            dialog.destroy()
            self.status_var.set(f"✅ Застосовано: {entry.new_name}")

        # Buttons
        btn_frame = tk.Frame(dialog, bg=COLORS["bg_main"])
        btn_frame.pack(fill=tk.X, padx=15, pady=(0, 15))

        ttk.Button(btn_frame, text="🔍 Шукати", command=do_search,
                  bootstyle="info", width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="✓ Застосувати", command=apply_selected,
                  bootstyle="success", width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Закрити", command=dialog.destroy,
                  bootstyle="outline", width=12).pack(side=tk.LEFT, padx=5)

    def _update_count(self, state: AppState) -> None:
        count = state.count_selected()
        total = len(state.entries)
        if state == self.music_state:
            self.music_count_var.set(f"{count} / {total}")
        else:
            self.files_count_var.set(f"{count} / {total}")

    # ========== Drag to reorder ==========

    def _on_drag_start(self, event: tk.Event, tree: ttk.Treeview, state: AppState) -> None:
        """Start drag operation."""
        item = tree.identify_row(event.y)
        if item:
            self._drag_data["item"] = item
            self._drag_data["start_y"] = event.y

    def _on_drag_motion(self, event: tk.Event, tree: ttk.Treeview, state: AppState) -> None:
        """Handle drag motion - visual feedback."""
        if not self._drag_data["item"]:
            return
        # Could add visual feedback here (highlight drop target)

    def _on_drag_end(self, event: tk.Event, tree: ttk.Treeview, state: AppState, refresh_fn) -> None:
        """End drag - reorder if moved to different position."""
        if not self._drag_data["item"]:
            return

        source_item = self._drag_data["item"]
        target_item = tree.identify_row(event.y)

        if target_item and source_item != target_item:
            try:
                source_idx = int(source_item)
                target_idx = int(target_item)

                if 0 <= source_idx < len(state.entries) and 0 <= target_idx < len(state.entries):
                    # Reorder entries
                    entry = state.entries.pop(source_idx)
                    state.entries.insert(target_idx, entry)
                    refresh_fn()
                    self.status_var.set(f"📋 Переміщено на позицію {target_idx + 1}")
            except (ValueError, IndexError):
                pass

        self._drag_data["item"] = None
        self._drag_data["start_y"] = 0

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

    def _rename_selected(self, state: AppState, tree: ttk.Treeview, copy_var: tk.BooleanVar,
                         refresh_fn, history: OperationHistory,
                         backup_var: tk.BooleanVar, backup_dir_var: tk.StringVar) -> None:
        """Перейменувати вибрані з підтримкою undo та backup."""
        selected = state.get_selected()
        if not selected:
            messagebox.showinfo("Інформація", "Немає вибраних файлів")
            return

        if self.confirm_rename_var.get():
            if not messagebox.askyesno("Підтвердження", f"Перейменувати {len(selected)} файлів?"): return
        elif self.confirm_large_var.get() and len(selected) > self.large_threshold_var.get():
            if not messagebox.askyesno("Підтвердження", f"Перейменувати {len(selected)} файлів?"): return

        if check_for_duplicate_destinations(state.entries, state.target_dir):
            conflicts = find_destination_conflicts(state.entries, state.target_dir)
            if not self._show_conflict_dialog(conflicts, state, refresh_fn):
                return

        # Prepare backup directory
        backup_dir = None
        if backup_var.get():
            backup_dir = backup_dir_var.get()
            if not backup_dir:
                backup_dir = filedialog.askdirectory(title="Виберіть папку для backup")
                if backup_dir:
                    backup_dir_var.set(backup_dir)
                else:
                    return

        # Start history session for logging
        session_id = self.history_log.start_session()

        success_count = 0
        success_entries = []
        operations = []

        def on_success(entry: FileEntry) -> None:
            nonlocal success_count
            success_count += 1
            success_entries.append(entry)

        def on_error(entry: FileEntry, error: str) -> None:
            self.root.after(0, lambda: self.status_var.set(f"❌ {entry.original}: {error}"))
            self.history_log.log_operation(
                session_id, "rename", entry.path, "",
                success=False, error=error, size=entry.size
            )

        def on_complete() -> None:
            # Record operations for undo
            for entry in success_entries:
                dest = state.target_dir or entry.directory
                new_path = os.path.join(dest, entry.new_name)
                op = RenameOperation(
                    original_path=entry.path,
                    new_path=new_path,
                    was_copy=copy_var.get(),
                )
                operations.append(op)
                self.history_log.log_operation(
                    session_id, "copy" if copy_var.get() else "rename",
                    entry.path, new_path, success=True, size=entry.size
                )

            if operations:
                history.record_batch(operations)

            self.history_log.end_session(session_id)
            self.root.after(0, lambda: self._on_rename_done(state, success_count, success_entries, refresh_fn))

        self.status_var.set(f"⏳ Перейменування {len(selected)} файлів...")

        self._operation_worker = FileOperationWorker(
            entries=selected, target_dir=state.target_dir,
            copy_mode=copy_var.get(), on_success=on_success,
            on_error=on_error, on_complete=on_complete,
            backup_dir=backup_dir,
        )
        self._operation_worker.start()

    def _on_rename_done(self, state: AppState, success: int, entries: list, refresh_fn) -> None:
        self.status_var.set(f"✅ Перейменовано {success} файлів (↩️ для скасування)")

        if self.auto_remove_var.get() and entries:
            for entry in entries:
                if entry in state.entries:
                    state.path_set.discard(entry.path)
                    state.entries.remove(entry)
            refresh_fn()

        if self.show_notif_var.get():
            messagebox.showinfo("Готово", f"Перейменовано: {success}\n\nНатисніть ↩️ для скасування")

    # ========== Undo/Redo ==========

    def _undo(self, history: OperationHistory, refresh_fn) -> None:
        """Скасувати останню операцію."""
        if not history.can_undo():
            self.status_var.set("⚠️ Немає операцій для скасування")
            messagebox.showinfo("Undo", f"Історія порожня. Спочатку перейменуйте файли.")
            return

        desc = history.undo_description()
        self.status_var.set(f"⏳ {desc}...")

        def on_progress(msg: str):
            self.root.after(0, lambda: self.status_var.set(msg))

        try:
            if history.undo(on_progress):
                self.status_var.set("↩️ Операцію скасовано")
                refresh_fn()
            else:
                self.status_var.set("❌ Помилка скасування")
                messagebox.showerror("Помилка", "Не вдалося скасувати операцію. Можливо файли були переміщені або видалені.")
        except Exception as e:
            self.status_var.set(f"❌ Помилка: {e}")
            messagebox.showerror("Помилка", f"Помилка скасування: {e}")

    def _redo(self, history: OperationHistory, refresh_fn) -> None:
        """Повторити скасовану операцію."""
        if not history.can_redo():
            self.status_var.set("⚠️ Немає операцій для повторення")
            return

        def on_progress(msg: str):
            self.root.after(0, lambda: self.status_var.set(msg))

        if history.redo(on_progress):
            self.status_var.set("↪️ Операцію повторено")
            refresh_fn()
        else:
            self.status_var.set("❌ Помилка повторення")

    # ========== Conflict Resolution ==========

    def _show_conflict_dialog(self, conflicts: Dict[str, List[FileEntry]],
                               state: AppState, refresh_fn) -> bool:
        """
        Show conflict resolution dialog.

        Args:
            conflicts: Dict mapping destination path to conflicting entries
            state: App state
            refresh_fn: Function to refresh the tree view

        Returns:
            True if conflicts resolved and should proceed, False to cancel
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("Конфлікт імен файлів")
        dialog.geometry("600x400")
        dialog.configure(bg=COLORS["bg_main"])
        dialog.transient(self.root)
        dialog.grab_set()

        result = {"proceed": False}

        # Header
        tk.Label(dialog, text="⚠️ Знайдено конфлікти імен",
                 font=("Segoe UI", 14, "bold"), bg=COLORS["bg_main"],
                 fg=COLORS["warning"]).pack(pady=(15, 5))

        conflict_count = sum(len(entries) for entries in conflicts.values())
        tk.Label(dialog, text=f"{len(conflicts)} конфліктів ({conflict_count} файлів мають однакові імена)",
                 font=("Segoe UI", 10), bg=COLORS["bg_main"],
                 fg=COLORS["text"]).pack(pady=(0, 10))

        # Conflict list
        list_frame = tk.Frame(dialog, bg=COLORS["bg_main"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        cols = ("Нове ім'я", "Оригінал", "Папка")
        tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=8)

        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        tree.heading("Нове ім'я", text="Нове ім'я")
        tree.heading("Оригінал", text="Оригінал")
        tree.heading("Папка", text="Папка")

        tree.column("Нове ім'я", width=200)
        tree.column("Оригінал", width=200)
        tree.column("Папка", width=150)

        for dest_path, entries in conflicts.items():
            for entry in entries:
                tree.insert("", "end", values=(entry.new_name, entry.original, os.path.basename(entry.directory)))

        # Options
        options_frame = tk.Frame(dialog, bg=COLORS["bg_main"])
        options_frame.pack(fill=tk.X, padx=15, pady=10)

        tk.Label(options_frame, text="Оберіть дію:",
                 font=("Segoe UI", 10, "bold"), bg=COLORS["bg_main"],
                 fg=COLORS["cyan"]).pack(anchor="w")

        def auto_number():
            resolve_conflicts_auto_number(conflicts)
            refresh_fn()
            result["proceed"] = True
            dialog.destroy()

        def skip_conflicts():
            for entries in conflicts.values():
                for entry in entries[1:]:
                    entry.selected.set(False)
            refresh_fn()
            result["proceed"] = True
            dialog.destroy()

        def cancel():
            dialog.destroy()

        btn_frame = tk.Frame(dialog, bg=COLORS["bg_main"])
        btn_frame.pack(fill=tk.X, padx=15, pady=(0, 15))

        ttk.Button(btn_frame, text="🔢 Додати номери",
                  command=auto_number, bootstyle="success",
                  width=18).pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="⏭ Пропустити дублікати",
                  command=skip_conflicts, bootstyle="warning",
                  width=18).pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="❌ Скасувати",
                  command=cancel, bootstyle="danger",
                  width=18).pack(side=tk.LEFT, padx=5)

        # Descriptions
        desc_frame = tk.Frame(dialog, bg=COLORS["bg_main"])
        desc_frame.pack(fill=tk.X, padx=15, pady=(0, 10))

        tk.Label(desc_frame, text="• Додати номери: файли отримають суфікс (02), (03) і т.д.",
                 font=("Segoe UI", 9), bg=COLORS["bg_main"], fg=COLORS["text_dim"]).pack(anchor="w")
        tk.Label(desc_frame, text="• Пропустити: перейменується лише перший файл з кожної групи",
                 font=("Segoe UI", 9), bg=COLORS["bg_main"], fg=COLORS["text_dim"]).pack(anchor="w")

        dialog.wait_window()
        return result["proceed"]

    # ========== Preview ==========

    def _show_preview(self, state: AppState) -> None:
        """Показати попередній перегляд змін."""
        selected = state.get_selected()
        if not selected:
            messagebox.showinfo("Інформація", "Немає вибраних файлів")
            return

        # Create preview dialog
        preview = tk.Toplevel(self.root)
        preview.title("Перегляд змін")
        preview.geometry("800x500")
        preview.configure(bg=COLORS["bg_main"])

        tk.Label(preview, text="Попередній перегляд перейменування",
                 font=("Segoe UI", 14, "bold"), bg=COLORS["bg_main"],
                 fg=COLORS["cyan"]).pack(pady=10)

        # Treeview for preview
        tree_frame = tk.Frame(preview, bg=COLORS["bg_main"])
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        cols = ("№", "Оригінал", "→", "Нове ім'я")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        tree.heading("№", text="№")
        tree.heading("Оригінал", text="Оригінал")
        tree.heading("→", text="→")
        tree.heading("Нове ім'я", text="Нове ім'я")

        tree.column("№", width=40, anchor="center")
        tree.column("Оригінал", width=300)
        tree.column("→", width=30, anchor="center")
        tree.column("Нове ім'я", width=300)

        for i, entry in enumerate(selected[:200]):  # Limit to 200 for performance
            changed = entry.original != entry.new_name
            tree.insert("", "end", values=(i + 1, entry.original, "→" if changed else "=", entry.new_name))

        if len(selected) > 200:
            tk.Label(preview, text=f"... та ще {len(selected) - 200} файлів",
                     bg=COLORS["bg_main"], fg=COLORS["text_dim"]).pack()

        btn_frame = tk.Frame(preview, bg=COLORS["bg_main"])
        btn_frame.pack(pady=10)
        self._create_button(btn_frame, "Закрити", preview.destroy, "outline").pack()

    # ========== Duplicates ==========

    def _find_duplicates(self, state: AppState, tree: ttk.Treeview) -> None:
        """Знайти дублікати файлів."""
        if not state.entries:
            messagebox.showinfo("Інформація", "Немає файлів")
            return

        self.status_var.set("🔍 Пошук дублікатів...")
        self.root.update()

        def on_progress(current: int, total: int):
            self.root.after(0, lambda: self.status_var.set(f"🔍 Хешування: {current}/{total}"))

        duplicates = find_duplicates(state.entries, on_progress)
        stats = get_duplicate_stats(state.entries)

        if not duplicates:
            self.status_var.set("✅ Дублікатів не знайдено")
            messagebox.showinfo("Результат", "Дублікатів не знайдено")
            return

        # Show duplicates dialog
        dup_dialog = tk.Toplevel(self.root)
        dup_dialog.title("Знайдено дублікати")
        dup_dialog.geometry("700x450")
        dup_dialog.configure(bg=COLORS["bg_main"])

        tk.Label(dup_dialog, text="🔍 Знайдені дублікати",
                 font=("Segoe UI", 14, "bold"), bg=COLORS["bg_main"],
                 fg=COLORS["cyan"]).pack(pady=10)

        stats_text = f"Груп: {stats['duplicate_groups']} | Файлів-дублікатів: {stats['duplicate_files']} | Займають: {bytes_to_human_readable(stats['wasted_space'])}"
        tk.Label(dup_dialog, text=stats_text, bg=COLORS["bg_main"],
                 fg=COLORS["text_secondary"]).pack()

        # List duplicates
        tree_frame = tk.Frame(dup_dialog, bg=COLORS["bg_main"])
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        text = tk.Text(tree_frame, bg=COLORS["bg_input"], fg=COLORS["text"],
                       font=("Consolas", 9), wrap=tk.NONE)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=vsb.set)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        for hash_val, group in duplicates.items():
            text.insert(tk.END, f"\n═══ Група ({len(group)} файлів, {bytes_to_human_readable(group[0].size)} кожен) ═══\n")
            for entry in group:
                text.insert(tk.END, f"  {entry.path}\n")

        text.configure(state=tk.DISABLED)

        btn_frame = tk.Frame(dup_dialog, bg=COLORS["bg_main"])
        btn_frame.pack(pady=10)
        self._create_button(btn_frame, "Закрити", dup_dialog.destroy, "outline").pack()

        self.status_var.set(f"🔍 Знайдено {stats['duplicate_groups']} груп дублікатів")

    # ========== Profiles ==========

    def _update_profile_combos(self) -> None:
        """Оновити списки профілів."""
        audio_profiles = self.profile_manager.get_profile_names("audio")
        general_profiles = self.profile_manager.get_profile_names("general")

        self.music_profile_combo['values'] = audio_profiles
        self.files_profile_combo['values'] = general_profiles

    def _save_profile_music(self) -> None:
        """Зберегти профіль для музики."""
        name = tk.simpledialog.askstring("Зберегти профіль", "Назва профілю:")
        if not name:
            return

        profile = RenameProfile(
            name=name,
            template=self.music_tmpl_var.get(),
            prefix=self.music_pre_var.get(),
            suffix=self.music_suf_var.get(),
            find_text=self.music_find_var.get(),
            replace_text=self.music_repl_var.get(),
            use_regex=self.music_regex_var.get(),
            case_mode=self.music_case_var.get(),
            remove_pattern=self.music_remove_var.get(),
            trim_spaces=self.music_trim_var.get(),
            num_start=self.music_num_start_var.get(),
            num_step=self.music_num_step_var.get(),
            num_padding=self.music_num_padding_var.get(),
            date_mode=self.music_date_mode_var.get(),
            date_format=self.music_date_format_var.get(),
            copy_mode=self.music_copy_var.get(),
            backup_enabled=self.music_backup_var.get(),
            profile_type="audio",
        )
        self.profile_manager.save_profile(profile)
        self._update_profile_combos()
        self.music_profile_var.set(name)
        self.status_var.set(f"💾 Профіль '{name}' збережено")

    def _save_profile_files(self) -> None:
        """Зберегти профіль для файлів."""
        name = tk.simpledialog.askstring("Зберегти профіль", "Назва профілю:")
        if not name:
            return

        profile = RenameProfile(
            name=name,
            template=self.files_tmpl_var.get(),
            prefix=self.files_pre_var.get(),
            suffix=self.files_suf_var.get(),
            find_text=self.files_find_var.get(),
            replace_text=self.files_repl_var.get(),
            use_regex=self.files_regex_var.get(),
            case_mode=self.files_case_var.get(),
            remove_pattern=self.files_remove_var.get(),
            trim_spaces=self.files_trim_var.get(),
            num_start=self.files_num_start_var.get(),
            num_step=self.files_num_step_var.get(),
            num_padding=self.files_num_padding_var.get(),
            date_mode=self.files_date_mode_var.get(),
            date_format=self.files_date_format_var.get(),
            copy_mode=self.files_copy_var.get(),
            backup_enabled=self.files_backup_var.get(),
            profile_type="general",
        )
        self.profile_manager.save_profile(profile)
        self._update_profile_combos()
        self.files_profile_var.set(name)
        self.status_var.set(f"💾 Профіль '{name}' збережено")

    def _load_profile_music(self) -> None:
        """Завантажити профіль для музики."""
        name = self.music_profile_var.get()
        if not name:
            return

        profile = self.profile_manager.get_profile(name)
        if not profile:
            return

        self.music_tmpl_var.set(profile.template)
        self.music_pre_var.set(profile.prefix)
        self.music_suf_var.set(profile.suffix)
        self.music_find_var.set(profile.find_text)
        self.music_repl_var.set(profile.replace_text)
        self.music_regex_var.set(profile.use_regex)
        self.music_case_var.set(profile.case_mode)
        self.music_remove_var.set(profile.remove_pattern)
        self.music_trim_var.set(profile.trim_spaces)
        self.music_num_start_var.set(profile.num_start)
        self.music_num_step_var.set(profile.num_step)
        self.music_num_padding_var.set(profile.num_padding)
        self.music_date_mode_var.set(profile.date_mode)
        self.music_date_format_var.set(profile.date_format)
        self.music_copy_var.set(profile.copy_mode)
        self.music_backup_var.set(profile.backup_enabled)

        self._refresh_music()
        self.status_var.set(f"📂 Профіль '{name}' завантажено")

    def _load_profile_files(self) -> None:
        """Завантажити профіль для файлів."""
        name = self.files_profile_var.get()
        if not name:
            return

        profile = self.profile_manager.get_profile(name)
        if not profile:
            return

        self.files_tmpl_var.set(profile.template)
        self.files_pre_var.set(profile.prefix)
        self.files_suf_var.set(profile.suffix)
        self.files_find_var.set(profile.find_text)
        self.files_repl_var.set(profile.replace_text)
        self.files_regex_var.set(profile.use_regex)
        self.files_case_var.set(profile.case_mode)
        self.files_remove_var.set(profile.remove_pattern)
        self.files_trim_var.set(profile.trim_spaces)
        self.files_num_start_var.set(profile.num_start)
        self.files_num_step_var.set(profile.num_step)
        self.files_num_padding_var.set(profile.num_padding)
        self.files_date_mode_var.set(profile.date_mode)
        self.files_date_format_var.set(profile.date_format)
        self.files_copy_var.set(profile.copy_mode)
        self.files_backup_var.set(profile.backup_enabled)

        self._refresh_files()
        self.status_var.set(f"📂 Профіль '{name}' завантажено")

    def _delete_profile_music(self) -> None:
        """Видалити профіль музики."""
        name = self.music_profile_var.get()
        if not name:
            return
        if messagebox.askyesno("Підтвердження", f"Видалити профіль '{name}'?"):
            self.profile_manager.delete_profile(name)
            self._update_profile_combos()
            self.music_profile_var.set("")
            self.status_var.set(f"🗑 Профіль '{name}' видалено")

    def _delete_profile_files(self) -> None:
        """Видалити профіль файлів."""
        name = self.files_profile_var.get()
        if not name:
            return
        if messagebox.askyesno("Підтвердження", f"Видалити профіль '{name}'?"):
            self.profile_manager.delete_profile(name)
            self._update_profile_combos()
            self.files_profile_var.set("")
            self.status_var.set(f"🗑 Профіль '{name}' видалено")

    def _export_profile(self, profile_type: str) -> None:
        """Export profile to file."""
        from tkinter import filedialog

        if profile_type == "audio":
            name = self.music_profile_var.get()
        else:
            name = self.files_profile_var.get()

        if not name:
            messagebox.showwarning("Попередження", "Виберіть профіль для експорту")
            return

        filepath = filedialog.asksaveasfilename(
            title="Експорт профілю",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"{name}.json"
        )

        if filepath:
            if self.profile_manager.export_profile(name, filepath):
                self.status_var.set(f"📤 Профіль '{name}' експортовано")
            else:
                messagebox.showerror("Помилка", "Не вдалося експортувати профіль")

    def _import_profile(self, profile_type: str) -> None:
        """Import profile from file."""
        from tkinter import filedialog

        filepath = filedialog.askopenfilename(
            title="Імпорт профілю",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if filepath:
            success, message = self.profile_manager.import_profile(filepath)
            if success:
                self._update_profile_combos()
                self.status_var.set(f"📥 {message}")
            else:
                messagebox.showerror("Помилка", message)

    # ========== Filters ==========

    def _apply_filter_music(self) -> None:
        """Застосувати фільтр для музики."""
        filter_val = self.music_filter_var.get()
        if filter_val == "Всі":
            # Show all
            for entry in self.music_state.entries:
                entry.selected.set(True)
        else:
            # Filter by extension
            ext = filter_val.lower()
            for entry in self.music_state.entries:
                entry.selected.set(entry.ext.lower() == ext)
        self._refresh_music()

    def _apply_filter_files(self) -> None:
        """Застосувати фільтр для файлів."""
        filter_val = self.files_filter_var.get()
        type_map = {
            "🎵 Аудіо": AUDIO,
            "🖼 Зображення": IMG,
            "📄 Документи": DOC,
            "🎬 Відео": VID,
        }

        if filter_val == "Всі":
            for entry in self.files_state.entries:
                entry.selected.set(True)
        elif filter_val in type_map:
            allowed = type_map[filter_val]
            for entry in self.files_state.entries:
                entry.selected.set(entry.ext.lower() in allowed)
        self._refresh_files()

    # ========== Backup ==========

    def _choose_backup_dir(self, backup_dir_var: tk.StringVar) -> None:
        """Вибрати папку для backup."""
        directory = filedialog.askdirectory(title="Виберіть папку для backup")
        if directory:
            backup_dir_var.set(directory)

    def run(self) -> None:
        """Запустити програму."""
        self.root.mainloop()


def main() -> None:
    app = RenamerApp()
    app.run()


if __name__ == "__main__":
    main()
