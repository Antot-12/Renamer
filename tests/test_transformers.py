"""Tests for text transformation utilities."""

import pytest
from renamer.transformers import (
    apply_case,
    remove_pattern,
    trim_spaces,
    apply_regex_replace,
    clean_filename,
    add_prefix_suffix,
    replace_text,
    REMOVE_PATTERNS,
    CASE_LABELS,
)


class TestApplyCase:
    """Tests for case transformations."""

    def test_title_case(self):
        assert apply_case("hello world", "title") == "Hello World"
        assert apply_case("HELLO WORLD", "title") == "Hello World"

    def test_sentence_case(self):
        assert apply_case("hello world", "sentence") == "Hello world"
        assert apply_case("HELLO WORLD", "sentence") == "Hello world"

    def test_upper_case(self):
        assert apply_case("hello world", "upper") == "HELLO WORLD"

    def test_lower_case(self):
        assert apply_case("HELLO WORLD", "lower") == "hello world"

    def test_swap_case(self):
        assert apply_case("Hello World", "swap") == "hELLO wORLD"

    def test_camel_case(self):
        assert apply_case("hello world", "camel") == "helloWorld"
        assert apply_case("hello-world", "camel") == "helloWorld"
        assert apply_case("hello_world", "camel") == "helloWorld"

    def test_pascal_case(self):
        assert apply_case("hello world", "pascal") == "HelloWorld"
        assert apply_case("hello-world", "pascal") == "HelloWorld"

    def test_snake_case(self):
        assert apply_case("Hello World", "snake") == "hello_world"
        assert apply_case("helloWorld", "snake") == "hello_world"
        assert apply_case("HelloWorld", "snake") == "hello_world"

    def test_kebab_case(self):
        assert apply_case("Hello World", "kebab") == "hello-world"
        assert apply_case("hello_world", "kebab") == "hello-world"

    def test_empty_string(self):
        assert apply_case("", "title") == ""
        assert apply_case("", "upper") == ""

    def test_none_returns_unchanged(self):
        assert apply_case("hello", "none") == "hello"
        assert apply_case("hello", "invalid") == "hello"


class TestRemovePattern:
    """Tests for pattern removal."""

    def test_remove_brackets_all(self):
        result = remove_pattern("file (copy) [2024] {test}", "brackets")
        assert "(" not in result
        assert "[" not in result
        assert "{" not in result

    def test_remove_round_brackets(self):
        result = remove_pattern("file (copy) [keep]", "round_brackets")
        assert "(copy)" not in result
        assert "[keep]" in result

    def test_remove_square_brackets(self):
        result = remove_pattern("file (keep) [remove]", "square_brackets")
        assert "(keep)" in result
        assert "[remove]" not in result

    def test_remove_curly_brackets(self):
        result = remove_pattern("file {remove} (keep)", "curly_brackets")
        assert "{remove}" not in result
        assert "(keep)" in result

    def test_remove_numbers(self):
        result = remove_pattern("file123test456", "numbers")
        assert result == "filetest"

    def test_remove_leading_numbers(self):
        result = remove_pattern("01 - song name", "leading_numbers")
        assert result == "song name"

    def test_remove_trailing_numbers(self):
        result = remove_pattern("song name 01", "trailing_numbers")
        assert result == "song name"

    def test_remove_special_chars(self):
        result = remove_pattern("file@name#test!", "special_chars")
        assert "@" not in result
        assert "#" not in result
        assert "!" not in result

    def test_empty_string(self):
        assert remove_pattern("", "brackets") == ""

    def test_invalid_pattern(self):
        assert remove_pattern("test", "invalid_pattern") == "test"


class TestTrimSpaces:
    """Tests for space trimming."""

    def test_trim_leading(self):
        assert trim_spaces("   hello", "leading") == "hello"

    def test_trim_trailing(self):
        assert trim_spaces("hello   ", "trailing") == "hello"

    def test_trim_multiple(self):
        assert trim_spaces("hello   world", "multiple") == "hello world"

    def test_trim_all(self):
        result = trim_spaces("   hello   world   ", "all")
        assert result == "hello world"

    def test_empty_string(self):
        assert trim_spaces("", "all") == ""


class TestApplyRegexReplace:
    """Tests for regex replacement."""

    def test_simple_replace(self):
        result = apply_regex_replace("hello world", r"world", "there")
        assert result == "hello there"

    def test_regex_pattern(self):
        result = apply_regex_replace("file123.txt", r"\d+", "XXX")
        assert result == "fileXXX.txt"

    def test_capture_groups(self):
        result = apply_regex_replace("hello world", r"(\w+) (\w+)", r"\2 \1")
        assert result == "world hello"

    def test_invalid_regex_returns_none(self):
        result = apply_regex_replace("test", r"[invalid", "replace")
        assert result is None

    def test_empty_string(self):
        result = apply_regex_replace("", r"test", "replace")
        assert result == ""


class TestCleanFilename:
    """Tests for filename cleaning."""

    def test_removes_illegal_chars(self):
        result = clean_filename('file:name*test?"<>|')
        assert ":" not in result
        assert "*" not in result
        assert "?" not in result
        assert '"' not in result
        assert "<" not in result
        assert ">" not in result
        assert "|" not in result

    def test_normalizes_spaces(self):
        result = clean_filename("hello    world")
        assert result == "hello world"

    def test_normalizes_underscores(self):
        result = clean_filename("hello___world")
        assert result == "hello_world"

    def test_normalizes_dashes(self):
        result = clean_filename("hello---world")
        assert result == "hello-world"

    def test_strips_leading_trailing(self):
        result = clean_filename(" .-hello world-. ")
        assert result == "hello world"

    def test_empty_string(self):
        assert clean_filename("") == ""


class TestAddPrefixSuffix:
    """Tests for prefix/suffix addition."""

    def test_add_prefix(self):
        assert add_prefix_suffix("name", prefix="pre_") == "pre_name"

    def test_add_suffix(self):
        assert add_prefix_suffix("name", suffix="_suf") == "name_suf"

    def test_add_both(self):
        assert add_prefix_suffix("name", prefix="pre_", suffix="_suf") == "pre_name_suf"

    def test_no_modification(self):
        assert add_prefix_suffix("name") == "name"


class TestReplaceText:
    """Tests for text replacement."""

    def test_simple_replace(self):
        assert replace_text("hello world", "world", "there") == "hello there"

    def test_no_match(self):
        assert replace_text("hello world", "xyz", "abc") == "hello world"

    def test_regex_replace(self):
        result = replace_text("file123.txt", r"\d+", "XXX", use_regex=True)
        assert result == "fileXXX.txt"

    def test_invalid_regex_returns_original(self):
        result = replace_text("test", r"[invalid", "replace", use_regex=True)
        assert result == "test"

    def test_empty_find(self):
        assert replace_text("hello", "", "x") == "hello"

    def test_empty_text(self):
        assert replace_text("", "a", "b") == ""


class TestPatternLabels:
    """Tests for pattern and case label dictionaries."""

    def test_case_labels_exist(self):
        assert "none" in CASE_LABELS
        assert "title" in CASE_LABELS
        assert "upper" in CASE_LABELS
        assert "lower" in CASE_LABELS

    def test_remove_patterns_exist(self):
        assert "brackets" in REMOVE_PATTERNS
        assert "numbers" in REMOVE_PATTERNS
        assert "special_chars" in REMOVE_PATTERNS
