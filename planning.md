# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): ...
- `size` (str): ...
- `max_price` (float): ...

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->

**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->

---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): ...
- `wardrobe` (dict): ...

**What it returns:**
<!-- Describe the return value -->

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->

---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (...): ...

**What it returns:**
<!-- Describe the return value -->

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | |
| suggest_outfit | Wardrobe is empty | |
| create_fit_card | Outfit input is missing or incomplete | |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**

**Milestone 4 — Planning loop and state management:**

---

## A Complete Interaction (Step by Step)

FitFindr is a thrift-shopping assistant that helps users find secondhand clothing and style it with what they already own. When a user describes what they want, the agent calls `search_listings` to find matching items from the mock dataset; once a candidate item is chosen, it calls `suggest_outfit` to pair it with the user's wardrobe (or give general styling advice if the wardrobe is empty); finally it calls `create_fit_card` to generate a shareable caption. If any tool fails or returns nothing — no search results, an empty wardrobe, or a missing outfit string — the agent surfaces a friendly fallback message rather than crashing or going silent.

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
The agent parses the query and calls `search_listings(description="vintage graphic tee", max_price=30.0)`. The tool loads all listings, drops anything over $30, scores each remaining item for keyword overlap with "vintage graphic tee", and returns a sorted list. Top matches include *Graphic Tee — 2003 Tour Bootleg Style* ($24, depop) and *Y2K Baby Tee — Butterfly Print* ($18, depop). If nothing matched, the agent would tell the user no listings were found and suggest loosening the price or description.

**Step 2:**
The agent picks the top result (the bootleg-style graphic tee at $24) and calls `suggest_outfit(new_item=<that listing dict>, wardrobe=<user's wardrobe>)`. The user mentioned baggy jeans and chunky sneakers, so the wardrobe contains items like "Baggy straight-leg jeans, dark wash" and "Chunky white sneakers." The LLM returns two specific outfit combinations that name those pieces — e.g., "Wear the bootleg tee tucked into your baggy dark-wash jeans with your chunky white sneakers for an easy vintage streetwear look." If the wardrobe had been empty, the tool would instead return general styling advice about silhouette and color palette.

**Step 3:**
The agent calls `create_fit_card(outfit=<suggestion from Step 2>, new_item=<listing dict>)`. The LLM produces a 2–4 sentence Instagram/TikTok-style caption that naturally mentions the item name, $24 price, and depop platform. If the outfit string were empty or whitespace-only, the tool returns a fixed error string instead of calling the LLM.

**Final output to user:**
The user sees: (1) a list of matching thrift listings with title, price, condition, and platform; (2) two styled outfit ideas that call out specific pieces from their wardrobe; and (3) a ready-to-post fit-card caption they can copy straight to social media.
