"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set. Add it to a .env file in the project root.")
    return Groq(api_key=api_key)


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _size_matches(listing_size: str | None, requested_size: str | None) -> bool:
    if not requested_size or not listing_size:
        return True
    requested = _normalize_text(requested_size)
    listing = _normalize_text(str(listing_size))
    if requested in listing:
        return True
    return any(token in listing for token in requested.split())


def _score_listing(description: str, listing: dict) -> int:
    query_tokens = set(_normalize_text(description).split())
    if not query_tokens:
        return 0

    haystacks = [
        listing.get("title", ""),
        listing.get("description", ""),
        " ".join(listing.get("style_tags", []) or []),
        listing.get("category", ""),
        " ".join(listing.get("colors", []) or []),
        listing.get("brand") or "",
    ]
    haystack_text = " ".join(haystacks).lower()
    score = 0
    for token in query_tokens:
        if token in haystack_text:
            score += 1
    return score


def _fallback_outfit_text(new_item: dict) -> str:
    title = new_item.get("title", "this thrifted piece")
    price = new_item.get("price", "")
    category = new_item.get("category", "item")
    return (
        f"Try pairing {title} with relaxed basics in a similar color story. "
        f"For a balanced look, style it with neutral layers and one statement accessory. "
        f"If you want an easy thrifted outfit, keep the vibe casual and confident."
    )


def _fallback_fit_card(new_item: dict) -> str:
    title = new_item.get("title", "this thrifted find")
    price = new_item.get("price", "")
    platform = new_item.get("platform", "thrift shop")
    return (
        f"Found {title} for ${price:.2f} on {platform}. "
        f"It has that easy, lived-in thrift vibe and is perfect for a casual outfit refresh."
    )


def _llm_text(prompt: str, temperature: float = 0.8) -> str:
    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return ""


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()
    filtered = [item for item in listings if max_price is None or item.get("price", float("inf")) <= max_price]
    filtered = [item for item in filtered if _size_matches(item.get("size"), size)]

    scored = [(item, _score_listing(description, item)) for item in filtered]
    scored = [(item, score) for item, score in scored if score > 0]
    scored.sort(key=lambda entry: (-entry[1], entry[0].get("price", 0)))
    return [item for item, _ in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    wardrobe_items = wardrobe.get("items", []) if isinstance(wardrobe, dict) else []
    if not wardrobe_items:
        prompt = (
            "You are a fashion stylist. Give 2 casual styling ideas for this thrifted item. "
            "Focus on silhouette, color palette, vibe, and what basics to pair with it.\n\n"
            f"Item: {new_item}"
        )
        result = _llm_text(prompt, temperature=0.7)
        return result or _fallback_outfit_text(new_item)

    prompt = (
        "You are a fashion stylist. Suggest 2 complete outfits using the thrifted item "
        "and the user's wardrobe. Mention specific wardrobe pieces by name.\n\n"
        f"Thrifted item: {new_item}\n\n"
        f"Wardrobe: {wardrobe_items}\n\n"
        "Return 2 short bullet points."
    )
    result = _llm_text(prompt, temperature=0.7)
    return result or _fallback_outfit_text(new_item)


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    if not outfit or not str(outfit).strip():
        return "Outfit details are missing, so I can’t generate a fit card yet."

    prompt = (
        "Write a short, shareable Instagram/TikTok caption for this thrifted outfit. "
        "Make it sound casual and authentic, mention the item name, price, and platform once each, "
        "and keep it to 2–4 sentences.\n\n"
        f"Item details: {new_item}\n\n"
        f"Outfit notes: {outfit}"
    )
    result = _llm_text(prompt, temperature=0.9)
    return result or _fallback_fit_card(new_item)
