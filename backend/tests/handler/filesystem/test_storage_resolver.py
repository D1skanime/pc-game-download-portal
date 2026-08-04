import unicodedata

import pytest
from hypothesis import given
from hypothesis import strategies as st

from exceptions.storage_exceptions import InvalidRelativePathError
from handler.filesystem.storage_resolver import normalize_relative_path


@pytest.mark.parametrize(
    ("raw", "case"),
    [
        ("", "empty mapping path"),
        ("/games", "POSIX absolute path"),
        ("games/", "trailing separator"),
        ("games//arcade", "repeated separator"),
        ("games/./arcade", "dot segment"),
        (".", "single dot segment"),
        ("..", "parent traversal"),
        ("games/../arcade", "nested parent traversal"),
        ("../../etc", "repeated parent traversal"),
        ("C:/Games", "Windows drive path with forward separators"),
        (r"C:\Games", "Windows drive path"),
        ("C:Games", "Windows drive-relative path"),
        (r"\\server\share", "UNC path"),
        (r"\\?\C:\Games", "Windows device path"),
        (r"games\arcade", "backslash separator"),
        ("games\x00arcade", "NUL control"),
        ("games\x1farcade", "C0 control"),
        ("games\x7farcade", "DEL control"),
    ],
)
def test_normalize_rejects_unsafe_lexical_forms(raw: str, case: str) -> None:
    with pytest.raises(InvalidRelativePathError):
        normalize_relative_path(raw)


def test_normalize_intenal_root_contract_allows_empty_path() -> None:
    assert normalize_relative_path("", allow_root=True) == ""


@pytest.mark.parametrize(
    "raw",
    [
        "Nintendo Switch",
        "Sony.PlayStation-2",
        "M\u00fcnchen/\u00dcber Spiele",
        "\u65e5\u672c\u8a9e/\u30b2\u30fc\u30e0",
        "nested/archive.with dots/game-set",
        "a" * 255,
    ],
)
def test_valid_names_are_preserved_exactly(raw: str) -> None:
    assert normalize_relative_path(raw) == raw


def test_valid_names_preserve_composed_and_decomposed_unicode() -> None:
    composed = "Caf\u00e9"
    decomposed = unicodedata.normalize("NFD", composed)

    assert composed != decomposed
    assert normalize_relative_path(composed) == composed
    assert normalize_relative_path(decomposed) == decomposed


@given(
    st.text(
        alphabet=st.characters(
            blacklist_categories=("Cc", "Cs"),
            blacklist_characters="/\\",
        ),
        min_size=1,
        max_size=80,
    ).filter(lambda value: value not in {".", ".."})
)
def test_valid_names_are_not_case_folded_or_unicode_normalized(name: str) -> None:
    assert normalize_relative_path(name) == name


def test_safe_error_omits_unrelated_absolute_roots() -> None:
    unrelated_root = "/mnt/private/archive"

    with pytest.raises(InvalidRelativePathError) as exc_info:
        normalize_relative_path("../escape")

    assert unrelated_root not in str(exc_info.value)
    assert len(str(exc_info.value)) <= 200
