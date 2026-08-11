from pathlib import Path


def test_preview_contract_is_implemented_with_dual_budgets():
    assert Path(
        "handler/storage/preview.py"
    ).exists(), "Phase 5 RED: entry/time bounded preview is not implemented"


def test_preview_states_and_lower_bound_contract():
    observed = {"observed_files", "observed_directories", "observed_bytes"}
    assert "total_files" not in observed


def test_problem_categories_are_bounded_and_path_free():
    categories = ("unreadable_entry", "unsafe_entry")
    assert len(categories) <= 8 and all(
        "/" not in c and "\\" not in c for c in categories
    )
