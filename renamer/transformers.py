"""Text transformation utilities for filename manipulation."""

from __future__ import annotations

import re
from typing import Optional

# Patterns for removing content
REMOVE_PATTERNS = {
    "brackets": r'\([^)]*\)|\[[^\]]*\]|\{[^}]*\}',  # (content), [content], {content}
    "round_brackets": r'\([^)]*\)',  # (content)
    "square_brackets": r'\[[^\]]*\]',  # [content]
    "curly_brackets": r'\{[^}]*\}',  # {content}
    "numbers": r'\d+',  # All numbers
    "leading_numbers": r'^\d+[\s\-_.]*',  # Numbers at start
    "trailing_numbers": r'[\s\-_.]*\d+$',  # Numbers at end
    "special_chars": r'[^\w\s\-.]',  # Non-word chars except dash and dot
    "underscores": r'_+',  # Multiple underscores
    "dashes": r'-+',  # Multiple dashes
    "dots": r'\.+',  # Multiple dots (except extension)
}

# Ukrainian pattern labels
PATTERN_LABELS = {
    "none": "Нічого",
    "brackets": "Всі дужки ()",
    "round_brackets": "Круглі ()",
    "square_brackets": "Квадратні []",
    "curly_brackets": "Фігурні {}",
    "numbers": "Всі числа",
    "leading_numbers": "Числа на початку",
    "trailing_numbers": "Числа в кінці",
    "special_chars": "Спецсимволи",
    "underscores": "Підкреслення _",
    "dashes": "Дефіси -",
}


def apply_case(text: str, mode: str) -> str:
    """
    Apply case transformation to text.

    Modes:
    - title: Title Case (кожне слово з великої)
    - sentence: Sentence case (тільки перше слово)
    - upper: ВЕРХНІЙ РЕГІСТР
    - lower: нижній регістр
    - swap: sWAP cASE
    - camel: camelCase
    - pascal: PascalCase
    - snake: snake_case
    - kebab: kebab-case
    """
    if not text:
        return text

    mode = mode.lower()

    if mode == "title":
        return text.title()

    elif mode == "sentence":
        return text.capitalize()

    elif mode == "upper":
        return text.upper()

    elif mode == "lower":
        return text.lower()

    elif mode == "swap":
        return text.swapcase()

    elif mode == "camel":
        words = re.split(r'[\s_\-]+', text)
        if not words:
            return text
        return words[0].lower() + ''.join(w.capitalize() for w in words[1:])

    elif mode == "pascal":
        words = re.split(r'[\s_\-]+', text)
        return ''.join(w.capitalize() for w in words)

    elif mode == "snake":
        # Convert to snake_case
        s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', text)
        s = re.sub(r'([a-z\d])([A-Z])', r'\1_\2', s)
        s = re.sub(r'[\s\-]+', '_', s)
        return s.lower()

    elif mode == "kebab":
        # Convert to kebab-case
        s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1-\2', text)
        s = re.sub(r'([a-z\d])([A-Z])', r'\1-\2', s)
        s = re.sub(r'[\s_]+', '-', s)
        return s.lower()

    return text


# Ukrainian case labels
CASE_LABELS = {
    "none": "Без змін",
    "title": "Title Case",
    "sentence": "Sentence case",
    "upper": "ВЕЛИКІ",
    "lower": "малі",
    "swap": "sWAP cASE",
    "camel": "camelCase",
    "pascal": "PascalCase",
    "snake": "snake_case",
    "kebab": "kebab-case",
}


def remove_pattern(text: str, pattern_name: str) -> str:
    """Remove specified pattern from text."""
    if not text or pattern_name not in REMOVE_PATTERNS:
        return text

    pattern = REMOVE_PATTERNS[pattern_name]
    result = re.sub(pattern, '', text)

    # Clean up extra spaces
    result = re.sub(r'\s+', ' ', result).strip()

    return result


def trim_spaces(text: str, mode: str = "all") -> str:
    """
    Trim spaces based on mode.

    Modes:
    - leading: Remove leading spaces
    - trailing: Remove trailing spaces
    - multiple: Replace multiple spaces with single
    - all: All of the above
    """
    if not text:
        return text

    mode = mode.lower()

    if mode == "leading":
        return text.lstrip()

    elif mode == "trailing":
        return text.rstrip()

    elif mode == "multiple":
        return re.sub(r'\s+', ' ', text)

    elif mode == "all":
        return re.sub(r'\s+', ' ', text).strip()

    return text


def apply_regex_replace(text: str, pattern: str, replacement: str) -> Optional[str]:
    """
    Apply regex find/replace.
    Returns None if regex is invalid.
    """
    try:
        return re.sub(pattern, replacement, text)
    except re.error:
        return None


def clean_filename(text: str) -> str:
    """
    Clean filename by removing illegal characters and normalizing.
    More thorough than sanitize().
    """
    if not text:
        return text

    # Remove illegal Windows filename chars
    text = re.sub(r'[\\/:*?"<>|]', '', text)

    # Replace multiple spaces/underscores/dashes with single
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'_+', '_', text)
    text = re.sub(r'-+', '-', text)

    # Remove leading/trailing spaces, dots, dashes
    text = text.strip(' .-_')

    return text


def add_prefix_suffix(text: str, prefix: str = "", suffix: str = "") -> str:
    """Add prefix and/or suffix to text."""
    return f"{prefix}{text}{suffix}"


def replace_text(text: str, find: str, replace: str, use_regex: bool = False) -> str:
    """Replace text, optionally using regex."""
    if not text or not find:
        return text

    if use_regex:
        result = apply_regex_replace(text, find, replace)
        return result if result is not None else text
    else:
        return text.replace(find, replace)


def generate_numbered_name(
    base: str,
    index: int,
    ext: str,
    start: int = 1,
    step: int = 1,
    padding: int = 2
) -> str:
    """Generate numbered filename."""
    number = start + (index * step)
    num_str = str(number).zfill(padding)
    return f"{num_str} - {base}{ext}"


def format_date_for_filename(dt, format_str: str = "%Y-%m-%d") -> str:
    """Format datetime for use in filename."""
    try:
        return dt.strftime(format_str)
    except (ValueError, AttributeError):
        return ""


# Date format options
DATE_FORMATS = {
    "YYYY-MM-DD": "%Y-%m-%d",
    "DD.MM.YYYY": "%d.%m.%Y",
    "YYYYMMDD": "%Y%m%d",
    "DD-MM-YYYY": "%d-%m-%Y",
    "YYYY.MM.DD": "%Y.%m.%d",
    "YYYY-MM-DD_HH-MM": "%Y-%m-%d_%H-%M",
    "YYYYMMDD_HHMM": "%Y%m%d_%H%M",
}

DATE_FORMAT_LABELS = {
    "none": "Без дати",
    "YYYY-MM-DD": "2024-01-15",
    "DD.MM.YYYY": "15.01.2024",
    "YYYYMMDD": "20240115",
    "DD-MM-YYYY": "15-01-2024",
    "YYYY.MM.DD": "2024.01.15",
    "YYYY-MM-DD_HH-MM": "2024-01-15_14-30",
    "YYYYMMDD_HHMM": "20240115_1430",
}
