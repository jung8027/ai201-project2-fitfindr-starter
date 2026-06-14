import pytest

from agent import run_agent
from tools import search_listings
from utils.data_loader import get_example_wardrobe


def test_search_listings_ranks_relevant_results():
    results = search_listings("vintage graphic tee", size="M", max_price=30)

    assert results
    assert results[0]["title"].lower().find("graphic") != -1 or results[0]["description"].lower().find("graphic") != -1
    assert all(item["price"] <= 30 for item in results)


def test_run_agent_handles_no_results_cleanly(monkeypatch):
    # Force the LLM path to fail so the fallback path is exercised in the same real flow.
    monkeypatch.setattr("tools._get_groq_client", lambda: (_ for _ in ()).throw(RuntimeError("no key")))

    session = run_agent("designer ballgown size XXS under $5", get_example_wardrobe())

    assert session["error"]
    assert session["selected_item"] is None
    assert session["outfit_suggestion"] is None
    assert session["fit_card"] is None
