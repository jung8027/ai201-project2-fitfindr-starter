# FitFindr

A thrift-shopping assistant that finds secondhand clothing and styles it with what you already own. Describe what you're looking for, and FitFindr searches a mock listings dataset, generates outfit ideas from your wardrobe, and produces a shareable social-media caption — all in one planning loop.

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file with your Groq API key (free at [console.groq.com](https://console.groq.com)):

```
GROQ_API_KEY=your_key_here
```

Run the Gradio interface:

```bash
python app.py
```

Then open the URL shown in your terminal (usually `http://localhost:7860`).

---

## Tool Inventory

### `search_listings(description, size, max_price)`

**Purpose:** Find mock secondhand listings that match the user's query.

| Parameter | Type | Description |
|-----------|------|-------------|
| `description` | `str` | Keywords describing the item (e.g., `"vintage graphic tee"`). Used for keyword-overlap scoring against listing fields. |
| `size` | `str \| None` | Size filter (e.g., `"M"`, `"S/M"`). Case-insensitive substring match. Pass `None` to skip. |
| `max_price` | `float \| None` | Price ceiling in dollars, inclusive. Pass `None` to skip. |

**Output:** `list[dict]` — matching listing dicts sorted by relevance score descending (ties broken by price ascending). Each dict contains `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`. Returns `[]` if nothing matches — never raises an exception.

---

### `suggest_outfit(new_item, wardrobe)`

**Purpose:** Generate outfit suggestions pairing the thrifted item with the user's existing wardrobe (or give general styling advice when the wardrobe is empty).

| Parameter | Type | Description |
|-----------|------|-------------|
| `new_item` | `dict` | A listing dict as returned by `search_listings`. |
| `wardrobe` | `dict` | A wardrobe dict with an `"items"` key. May be empty (`{"items": []}`) or missing the key. |

**Output:** A non-empty `str`. When the wardrobe has items, returns two bullet-point outfit combinations naming specific wardrobe pieces. When the wardrobe is empty, returns general styling advice about silhouette, color palette, and basics. Falls back to a hardcoded blurb if the LLM call fails — always returns a usable string.

---

### `create_fit_card(outfit, new_item)`

**Purpose:** Generate a 2–4 sentence Instagram/TikTok-style caption for the outfit.

| Parameter | Type | Description |
|-----------|------|-------------|
| `outfit` | `str` | The outfit suggestion string from `suggest_outfit`. If empty or whitespace-only, the tool short-circuits without calling the LLM. |
| `new_item` | `dict` | The listing dict — used to supply item name, price, and platform to the LLM. |

**Output:** A `str` caption that naturally mentions the item name, price, and platform once each. Returns the fixed string `"Outfit details are missing, so I can't generate a fit card yet."` if `outfit` is empty. Falls back to a minimal caption from listing fields alone if the LLM fails.

---

## Planning Loop

The agent follows a fixed five-step sequence with one conditional early exit. It does not iterate — each tool is called at most once per session.

```
User query
    │
    ▼
_parse_query()          ← regex extracts description, size, max_price
    │
    ▼
search_listings()       ← filter by price/size, score by keyword overlap
    │
    ├── results == []   → set session["error"], return early
    │                     (suggest_outfit and create_fit_card are never called)
    │
    │  results exist
    │
    ▼
selected_item = results[0]   ← top relevance score, lowest price on ties
    │
    ▼
suggest_outfit(selected_item, wardrobe)
    │
    ▼
create_fit_card(outfit_suggestion, selected_item)
    │
    ▼
Return session
```

**Why a fixed sequence?** Each tool's output is a direct input to the next — there is no decision to make about which tool to call. The only branch is the early exit after `search_listings`: if no listings match, there is nothing to style or caption, so the loop stops immediately with a user-facing error message.

---

## State Management

All state lives in a single `session` dict created at the start of each `run_agent()` call. No tool receives the session dict — each is called with explicit arguments extracted from it, and results are stored back immediately.

| Key | Type | Written by | Read by |
|-----|------|-----------|---------|
| `query` | `str` | `_new_session` | `_parse_query` |
| `parsed` | `dict` | `_parse_query` | `search_listings` call |
| `search_results` | `list[dict]` | `search_listings` return | early-exit check, `selected_item` assignment |
| `selected_item` | `dict` | step 3 assignment | `suggest_outfit`, `create_fit_card` calls |
| `wardrobe` | `dict` | `_new_session` | `suggest_outfit` call |
| `outfit_suggestion` | `str` | `suggest_outfit` return | `create_fit_card` call |
| `fit_card` | `str` | `create_fit_card` return | returned to caller |
| `error` | `str \| None` | early-exit branch | returned to caller |

This design keeps tools stateless and independently testable. The session dict is the single source of truth — there are no global variables, no re-prompting the user, and no hardcoded values passed between steps.

---

## Error Handling

### `search_listings` — no results

**Failure mode:** The query is too specific (wrong size, price too low, or unusual item type) and no listings match.

**Agent response:** Sets `session["error"] = "No listings matched your search. Try a broader description or a higher price limit."` and returns the session immediately. `suggest_outfit` and `create_fit_card` are never called.

**Tested with:**
```bash
python -c "from tools import search_listings; print(search_listings('designer ballgown', size='XXS', max_price=5))"
# Output: []
```
Then via the full agent:
```bash
python -c "
from agent import run_agent
from utils.data_loader import get_example_wardrobe
s = run_agent('designer ballgown size XXS under \$5', get_example_wardrobe())
print(s['error'])       # No listings matched your search. Try a broader description or a higher price limit.
print(s['fit_card'])    # None
"
```

---

### `suggest_outfit` — empty wardrobe

**Failure mode:** The user has no wardrobe items, so there are no specific pieces to pair with.

**Agent response:** The tool detects `wardrobe["items"] == []` (or the key is missing) and switches from a specific-pairing prompt to a general-styling prompt. The LLM returns advice about silhouette, color palette, and basics instead of named combinations. If the LLM also fails, `_fallback_outfit_text(new_item)` returns a hardcoded blurb.

**Tested with:**
```bash
python -c "
from tools import search_listings, suggest_outfit
from utils.data_loader import get_empty_wardrobe
results = search_listings('vintage graphic tee', size=None, max_price=50)
print(suggest_outfit(results[0], get_empty_wardrobe()))
# Output: general styling advice (two looks with silhouette/color/vibe) — non-empty string, no exception
"
```

---

### `create_fit_card` — empty outfit string

**Failure mode:** The `outfit` argument is empty or whitespace-only (e.g., if a future code path somehow skips `suggest_outfit`).

**Agent response:** Returns the fixed string `"Outfit details are missing, so I can't generate a fit card yet."` without calling the LLM.

**Tested with:**
```bash
python -c "
from tools import search_listings, create_fit_card
results = search_listings('vintage graphic tee', size=None, max_price=50)
print(create_fit_card('', results[0]))
# Output: Outfit details are missing, so I can't generate a fit card yet.
"
```

---

## Spec Reflection

**What matched the spec:** The planning loop implementation matched `planning.md` closely. The fixed sequence with one conditional branch, the session dict structure, and the early-exit behavior all implemented exactly as specified. Running the two `__main__` test cases in `agent.py` confirmed the happy path and no-results path both behaved as described.

**What I learned from the process:** Writing the spec before coding made the early-exit branch obvious — by listing which keys are "written by" vs "read by" in the state table, it became clear that calling `suggest_outfit` with an empty `selected_item` would be a silent failure rather than an explicit one. The spec forced that decision upfront instead of discovering it at runtime.

**What I would change:** The `_parse_query` function uses regex, which misses queries like "I need something under thirty dollars" or "looking for a medium-sized jacket." A small LLM call to extract structured fields (description, size, max_price) would be more robust, though it adds latency and a potential failure point. The spec documents the regex approach as intentional — a real system would tradeoff cost vs. coverage here.

---

## AI Usage

### Instance 1 — Implementing `search_listings`

**Input given to Claude:** The full Tool 1 block from `planning.md` (input parameters with types and descriptions, the return shape, and the empty-list failure mode), plus the note that `load_listings()` from `utils/data_loader` returns raw listing dicts. I asked it to implement only `search_listings` — nothing else.

**What it produced:** A function that filters by `max_price` (using `<=`) and `size` (case-insensitive substring) before scoring, calls a `_normalize_text` helper to tokenize and lowercase fields, computes keyword overlap, drops zero-score items, and sorts descending by score with price as a tiebreaker.

**What I checked before using it:** (1) The price filter used `<=` not `<`. (2) Passing `size=None` skipped filtering rather than crashing. (3) An all-miss query returned `[]` not raised an exception. (4) All `pytest tests/test_tools.py -k search` tests passed.

---

### Instance 2 — Implementing `run_agent`

**Input given to Claude:** The Planning Loop section, the State Management section (including the full key/type/written-by/read-by table), and the Architecture diagram from `planning.md`, plus the `_new_session` and `_parse_query` function signatures already in `agent.py`. I asked it to implement only `run_agent()`, using the existing helpers rather than rewriting them.

**What it produced:** A function that calls `_new_session`, then `_parse_query`, then `search_listings` with the parsed values, checks `if not results` and returns early with the error message, sets `selected_item = results[0]`, calls `suggest_outfit` with the item and wardrobe, calls `create_fit_card` with the suggestion and item, and returns the session.

**What I checked before using it:** (1) Every session key in the state table was written before it was read. (2) No tool was called after the early-exit `return`. (3) I ran the two `__main__` test cases directly — the happy path printed a non-empty `fit_card` with `session["error"] == None`, and the no-results path printed the error message with `session["fit_card"] == None`.

---

## Project Structure

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # load_listings, get_example_wardrobe, get_empty_wardrobe
├── tests/
│   └── test_tools.py          # Unit tests for all three tools
├── tools.py                   # search_listings, suggest_outfit, create_fit_card
├── agent.py                   # run_agent() — planning loop
├── app.py                     # Gradio interface
├── planning.md                # Design spec (fill out before coding)
└── requirements.txt
```
