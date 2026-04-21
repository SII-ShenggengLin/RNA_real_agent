"""Unit tests for task_type normalization (no HTTP)."""

from __future__ import annotations

import pytest

from agent_core.workflow_dispatch import (
    IMPLEMENTED_TASK_TYPES,
    KNOWN_TASK_TYPES,
    PLACEHOLDER_TASK_TYPES,
    classify_task_type,
    normalize_task_type,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("", "mrna"),
        ("mrna", "mrna"),
        ("MRNA", "mrna"),
        ("5'UTR", "utr5"),
        ("5utr", "utr5"),
        ("3-UTR", "utr3"),
        ("circ", "circrna"),
        ("circRNA", "circrna"),
        ("IRES", "ires"),
        ("intron", "intron"),
    ],
)
def test_normalize_task_type_aliases(raw: str, expected: str):
    assert normalize_task_type(raw) == expected


def test_classify_known_vocab():
    assert classify_task_type("mrna") == "implemented"
    assert classify_task_type("utr5") == "placeholder"
    assert classify_task_type("unknown_xyz") == "unknown"


def test_known_sets_cover_placeholders():
    assert PLACEHOLDER_TASK_TYPES.isdisjoint(IMPLEMENTED_TASK_TYPES)
    assert KNOWN_TASK_TYPES == IMPLEMENTED_TASK_TYPES | PLACEHOLDER_TASK_TYPES
