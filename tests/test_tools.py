import pytest

from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# ── search_listings ────────────────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []  # empty list, no exception


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


def test_search_returns_list_of_dicts():
    results = search_listings("denim jacket", size=None, max_price=None)
    for item in results:
        assert "title" in item
        assert "price" in item
        assert "platform" in item


def test_search_size_filter():
    results = search_listings("top", size="XXL", max_price=None)
    # Every result must have a size that matches "xxl" (case-insensitive substring)
    for item in results:
        assert "xxl" in str(item.get("size", "")).lower()


def test_search_no_size_filter_returns_more_than_with_size():
    all_results = search_listings("vintage", size=None, max_price=None)
    sized_results = search_listings("vintage", size="XXS", max_price=None)
    assert len(all_results) >= len(sized_results)


def test_search_best_match_first():
    results = search_listings("graphic tee", size=None, max_price=None)
    assert len(results) > 1
    # First result should have "graphic" or "tee" in title or description
    top = results[0]
    combined = (top.get("title", "") + top.get("description", "") +
                " ".join(top.get("style_tags", []))).lower()
    assert "graphic" in combined or "tee" in combined


# ── suggest_outfit ─────────────────────────────────────────────────────────────

SAMPLE_ITEM = {
    "id": "lst_002",
    "title": "Y2K Baby Tee — Butterfly Print",
    "category": "tops",
    "style_tags": ["y2k", "vintage", "graphic tee"],
    "size": "S/M",
    "condition": "excellent",
    "price": 18.0,
    "colors": ["white", "pink", "purple"],
    "brand": None,
    "platform": "depop",
}


def test_suggest_outfit_empty_wardrobe_returns_string(monkeypatch):
    # Failure mode: wardrobe is empty — tool must not crash and must return non-empty string
    monkeypatch.setattr("tools._llm_text", lambda prompt, temperature=0.8: "General styling advice here.")
    result = suggest_outfit(SAMPLE_ITEM, get_empty_wardrobe())
    assert isinstance(result, str)
    assert len(result.strip()) > 0


def test_suggest_outfit_empty_wardrobe_no_exception():
    # Even without a working LLM key, the fallback keeps it from crashing
    result = suggest_outfit(SAMPLE_ITEM, {"items": []})
    assert isinstance(result, str)
    assert len(result.strip()) > 0


def test_suggest_outfit_with_wardrobe_returns_string(monkeypatch):
    monkeypatch.setattr(
        "tools._llm_text",
        lambda prompt, temperature=0.8: "• Outfit 1: pair with jeans\n• Outfit 2: layer with jacket",
    )
    result = suggest_outfit(SAMPLE_ITEM, get_example_wardrobe())
    assert isinstance(result, str)
    assert len(result.strip()) > 0


def test_suggest_outfit_missing_items_key_no_crash():
    # wardrobe dict without 'items' key must not raise KeyError
    result = suggest_outfit(SAMPLE_ITEM, {})
    assert isinstance(result, str)


# ── create_fit_card ────────────────────────────────────────────────────────────

def test_create_fit_card_empty_outfit_returns_error_string():
    # Failure mode: empty outfit string — must return fixed error message, not crash
    result = create_fit_card("", SAMPLE_ITEM)
    assert "missing" in result.lower() and "fit card" in result.lower()


def test_create_fit_card_whitespace_outfit_returns_error_string():
    result = create_fit_card("   ", SAMPLE_ITEM)
    assert "missing" in result.lower() and "fit card" in result.lower()


def test_create_fit_card_returns_string(monkeypatch):
    monkeypatch.setattr(
        "tools._llm_text",
        lambda prompt, temperature=0.8: "Found this Y2K tee on depop for $18. Obsessed.",
    )
    result = create_fit_card("Pair with baggy jeans and chunky sneakers.", SAMPLE_ITEM)
    assert isinstance(result, str)
    assert len(result.strip()) > 0


def test_create_fit_card_no_exception_on_llm_failure(monkeypatch):
    # If LLM returns empty string, fallback must produce a non-empty string
    monkeypatch.setattr("tools._llm_text", lambda prompt, temperature=0.8: "")
    result = create_fit_card("Some outfit suggestion.", SAMPLE_ITEM)
    assert isinstance(result, str)
    assert len(result.strip()) > 0
