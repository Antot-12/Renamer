"""Constants and configuration for the Renamer application."""

from typing import Tuple

# Supported file type extensions

# Audio files
AUDIO: Tuple[str, ...] = (
    ".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".wma", ".aiff", ".alac",
    ".opus", ".mid", ".midi", ".amr", ".ape", ".mka"
)

# Image files
IMG: Tuple[str, ...] = (
    ".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".gif", ".svg", ".ico",
    ".heic", ".heif", ".raw", ".cr2", ".nef", ".arw", ".dng", ".psd", ".ai",
    ".eps", ".tga", ".exr", ".hdr"
)

# Document files
DOC: Tuple[str, ...] = (
    ".pdf", ".docx", ".txt", ".doc", ".rtf", ".odt", ".xls", ".xlsx", ".csv",
    ".ods", ".epub", ".mobi", ".djvu", ".xps", ".oxps"
)

# Video files
VID: Tuple[str, ...] = (
    ".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm", ".m4v", ".mpeg",
    ".mpg", ".3gp", ".3g2", ".vob", ".ogv", ".mts", ".m2ts", ".ts", ".divx"
)

# Archive files
ARC: Tuple[str, ...] = (
    ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso", ".dmg",
    ".cab", ".lzh", ".lzma", ".z", ".tgz", ".tbz2", ".txz"
)

# Presentation files
PRESENTATION: Tuple[str, ...] = (
    ".ppt", ".pptx", ".odp", ".key", ".pps", ".ppsx", ".pot", ".potx"
)

# Programming/code files
CODE: Tuple[str, ...] = (
    # Web
    ".html", ".htm", ".css", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte",
    # Python
    ".py", ".pyw", ".pyx", ".pxd", ".pyi",
    # Java/JVM
    ".java", ".kt", ".kts", ".scala", ".groovy", ".clj",
    # C/C++
    ".c", ".h", ".cpp", ".hpp", ".cc", ".cxx", ".hxx",
    # C#/F#
    ".cs", ".fs", ".fsx",
    # Go/Rust
    ".go", ".rs",
    # Ruby/PHP/Perl
    ".rb", ".php", ".pl", ".pm",
    # Shell
    ".sh", ".bash", ".zsh", ".fish", ".ps1", ".psm1", ".bat", ".cmd",
    # Data/Config
    ".json", ".yaml", ".yml", ".xml", ".toml", ".ini", ".cfg", ".conf",
    # Database
    ".sql", ".sqlite", ".db",
    # Other languages
    ".swift", ".m", ".mm", ".r", ".R", ".lua", ".dart", ".ex", ".exs",
    ".hs", ".erl", ".elm", ".v", ".vhdl", ".asm", ".s",
    # Markup
    ".md", ".markdown", ".rst", ".tex", ".latex",
)

# Text files (plain text, logs, etc.)
TEXT: Tuple[str, ...] = (
    ".txt", ".log", ".nfo", ".diz", ".srt", ".sub", ".ass", ".ssa", ".vtt",
    ".lrc", ".readme", ".changelog", ".license", ".authors", ".todo",
    ".gitignore", ".dockerignore", ".editorconfig", ".env"
)

# Game files
GAME: Tuple[str, ...] = (
    # Save files
    ".sav", ".save", ".savegame",
    # Game packages
    ".pak", ".vpk", ".wad", ".bsp", ".gcf", ".ncf",
    # Unity
    ".unity", ".unitypackage", ".asset", ".prefab",
    # Unreal
    ".uasset", ".umap", ".upk",
    # Game archives
    ".nds", ".3ds", ".cia", ".nsp", ".xci", ".nes", ".snes", ".gba", ".gbc",
    ".n64", ".z64", ".iso", ".cso", ".pbp", ".pkg",
    # Mods
    ".esp", ".esm", ".esl", ".bsa", ".ba2",
    # Other
    ".rom", ".bin", ".cue", ".mdf", ".mds"
)

# All supported extensions
SUPPORTED: Tuple[str, ...] = AUDIO + IMG + DOC + VID + ARC + PRESENTATION + CODE + TEXT + GAME

# Regex for illegal filename characters (Windows forbidden)
ILLEGAL_CHARS_PATTERN: str = r'[\\/:*?"<>|]'

# UI styling - Dark theme with neon cyan
ACCENT_COLOR: str = "#00ffff"  # Neon cyan
ACCENT_COLOR_DARK: str = "#00cccc"  # Darker cyan for hover
ACCENT_COLOR_LIGHT: str = "#66ffff"  # Lighter cyan for highlights
FONT_FAMILY: str = "Consolas"
FONT_SIZE: int = 10
BACKGROUND_COLOR: str = "#0d0d0d"  # Very dark background
BACKGROUND_SECONDARY: str = "#1a1a1a"  # Secondary dark background
TREEVIEW_BG: str = "#141414"  # Treeview background
TREEVIEW_SELECTED: str = "#003333"  # Selected row background
BORDER_COLOR: str = "#00ffff33"  # Cyan with transparency
TEXT_COLOR: str = "#e0e0e0"  # Light gray text
TEXT_MUTED: str = "#666666"  # Muted text

# Resource limits
MAX_FILES: int = 10000
MAX_PREVIEW_SIZE: int = 4096  # Max image dimension in pixels
MAX_PREVIEW_MEMORY: int = 50 * 1024 * 1024  # 50 MB max file size for preview
MAX_LOG_LINES: int = 1000

# File type emoji indicators
TYPE_EMOJI = {
    "audio": "🎵",
    "image": "🖼",
    "document": "📄",
    "video": "🎬",
    "archive": "📦",
    "presentation": "📊",
    "code": "💻",
    "text": "📝",
    "game": "🎮",
}
