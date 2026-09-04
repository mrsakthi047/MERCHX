# MERCHX Agent Context Engine
# Adds MEMORY + ENTITY EXTRACTION + REFERENCE RESOLUTION
# so the agent understands short/one-word follow-up commands
# like "best", "cheapest", "it", "same one", "buy" without
# the user repeating full details.
#
# This file works TOGETHER with agent_engine.py (intent detection).
# agent_engine.py = "WHAT does the user want to do" (intent)
# agent_context.py = "WHAT/WHICH product/order are they talking about" (entity)

import re
from datetime import datetime, timedelta


# ----------------------------------------------------------------
# 1. CONVERSATION MEMORY (per-agent session state)
# ----------------------------------------------------------------

class AgentMemory:
    """
    Holds short-term memory for a single user/agent session.
    In production this should be stored in Streamlit session_state
    or a DB row keyed by agent_id -- NOT a global Python variable,
    otherwise multiple users will share memory.
    """

    def __init__(self):
        self.last_search_results = []      # list of product dicts from last SEARCH
        self.selected_product = None       # product currently "in focus"
        self.last_intent = None
        self.last_quote = None             # active quote dict (id, price, expiry)
        self.pending_action = None         # e.g. "AWAITING_PRODUCT", "AWAITING_CONFIRMATION"
        self.budget_hint = None            # e.g. 8000
        self.quantity_hint = 1
        self.history = []                  # rolling log of (user_input, intent, entity)

    def remember_search(self, results, budget=None, quantity=None):
        self.last_search_results = results
        if budget:
            self.budget_hint = budget
        if quantity:
            self.quantity_hint = quantity

    def remember_selection(self, product):
        self.selected_product = product

    def remember_quote(self, quote):
        self.last_quote = quote

    def log(self, user_input, intent, entity):
        self.history.append({
            "input": user_input,
            "intent": intent,
            "entity": entity,
            "time": datetime.utcnow().isoformat(),
        })
        # keep memory light -- last 20 turns only
        self.history = self.history[-20:]

    def clear_pending(self):
        self.pending_action = None


# ----------------------------------------------------------------
# 2. ENTITY EXTRACTION (budget, quantity, product keywords)
# ----------------------------------------------------------------

# Common product keywords MERCHX catalog understands.
# In production this should come from the actual product DB,
# not a hardcoded list.
KNOWN_PRODUCT_KEYWORDS = [
    "headphones", "headphone", "earbuds", "earphones",
    "laptop", "mouse", "keyboard", "monitor",
    "smartwatch", "watch", "charger", "speaker",
    "phone", "tablet", "webcam",
]

# Words that mean "pick the cheapest option"
CHEAPEST_WORDS = ["cheapest", "lowest price", "budget one", "cheap one"]

# Words that mean "pick the best/recommended option"
BEST_WORDS = ["best", "best one", "top pick", "recommended"]

# Reference words meaning "the thing we were just talking about"
REFERENCE_WORDS = ["it", "that", "this", "same one", "same", "the one above"]


def extract_budget(text):
    """
    Extracts a rupee budget from free text.
    Handles: "under 8k", "under ₹8000", "below 5000", "8k budget"
    """
    text = text.lower()

    # e.g. "8k", "7.5k"
    k_match = re.search(r'(\d+(?:\.\d+)?)\s*k\b', text)
    if k_match:
        return int(float(k_match.group(1)) * 1000)

    # e.g. "₹8000", "8000", "rs 8000"
    num_match = re.search(r'(?:under|below|within|budget)?\s*(?:₹|rs\.?)?\s*(\d{3,6})', text)
    if num_match and any(w in text for w in ["under", "below", "within", "budget", "₹", "rs"]):
        return int(num_match.group(1))

    return None


def extract_quantity(text):
    """
    Extracts quantity. Defaults to 1 if not mentioned.
    Handles: "2 headphones", "buy 3", "headphones x2"
    """
    text = text.lower()
    qty_match = re.search(r'\b(\d{1,3})\s*(?:x|pcs|pieces|units)?\s*(?:' +
                           "|".join(KNOWN_PRODUCT_KEYWORDS) + r')?', text)
    if qty_match:
        val = int(qty_match.group(1))
        if 0 < val < 1000:  # sanity guard, avoid matching budget numbers
            return val
    return None


def extract_product_keyword(text):
    """
    Finds a known product keyword inside free text.
    Returns None if nothing recognized (agent must then ask
    a clarifying question rather than guessing).
    """
    text = text.lower()
    for kw in KNOWN_PRODUCT_KEYWORDS:
        if kw in text:
            return kw
    return None


def wants_cheapest(text):
    text = text.lower()
    return any(w in text for w in CHEAPEST_WORDS)


def wants_best(text):
    text = text.lower()
    return any(w in text for w in BEST_WORDS)


def is_reference_only(text):
    """
    True when the user is pointing back at something already
    discussed ("it", "that", "same one") instead of naming a
    new product.
    """
    text = text.lower().strip()
    return text in REFERENCE_WORDS or any(w in text for w in REFERENCE_WORDS)


# ----------------------------------------------------------------
# 3. RESOLVER -- combines intent + entities + memory
# ----------------------------------------------------------------

def resolve_target_product(user_input, memory: AgentMemory):
    """
    Decides WHICH product the current command refers to.
    Returns one of:
      - a product dict (resolved)
      - None (agent must ask a clarifying question)
    Priority order:
      1. Explicit new product keyword in this message -> new search needed
      2. "cheapest" / "best" -> pick from last_search_results
      3. Reference word ("it", "same one") -> selected_product from memory
      4. Nothing found, but a selection already exists -> reuse it
    """
    new_keyword = extract_product_keyword(user_input)
    if new_keyword:
        # fresh product mentioned -> caller should re-run SEARCH
        return {"needs_search": True, "keyword": new_keyword}

    if wants_cheapest(user_input) and memory.last_search_results:
        cheapest = min(memory.last_search_results, key=lambda p: p["price"])
        memory.remember_selection(cheapest)
        return cheapest

    if wants_best(user_input) and memory.last_search_results:
        # "best" = cheapest that still satisfies budget_hint, else lowest price
        candidates = memory.last_search_results
        if memory.budget_hint:
            within_budget = [p for p in candidates if p["price"] <= memory.budget_hint]
            candidates = within_budget or candidates
        best = min(candidates, key=lambda p: p["price"])
        memory.remember_selection(best)
        return best

    if is_reference_only(user_input) and memory.selected_product:
        return memory.selected_product

    # fallback: if there is already something selected, reuse silently
    if memory.selected_product:
        return memory.selected_product

    return None


# ----------------------------------------------------------------
# 4. MULTI-STEP ACTION PLANNER
# ----------------------------------------------------------------

def plan_next_step(intent, user_input, memory: AgentMemory):
    """
    Turns (intent, resolved entity, memory state) into the SINGLE
    next safe action MERCHX should take. This keeps the agent from
    ever jumping straight to payment without required steps.

    Returns a dict describing the action:
      { "action": "ASK_PRODUCT" | "SEARCH" | "SELECT_AND_QUOTE" |
                   "CONFIRM_PURCHASE" | "RUN_POLICY_CHECK" | ... ,
        "payload": {...} }
    """
    budget = extract_budget(user_input) or memory.budget_hint
    quantity = extract_quantity(user_input) or memory.quantity_hint

    if intent in ("SEARCH", "COMPARE", "QUOTE", "INVENTORY"):
        target = resolve_target_product(user_input, memory)
        if target is None:
            return {"action": "ASK_PRODUCT", "payload": {"intent": intent}}
        if isinstance(target, dict) and target.get("needs_search"):
            return {
                "action": "SEARCH",
                "payload": {"keyword": target["keyword"], "budget": budget, "quantity": quantity},
            }
        # already resolved to a specific product from memory
        return {"action": intent, "payload": {"product": target, "quantity": quantity}}

    if intent == "BUY":
        target = resolve_target_product(user_input, memory)

        if target is None:
            memory.pending_action = "AWAITING_PRODUCT"
            return {"action": "ASK_PRODUCT", "payload": {"intent": "BUY"}}

        if isinstance(target, dict) and target.get("needs_search"):
            memory.pending_action = "AWAITING_PRODUCT"
            return {
                "action": "SEARCH_THEN_BUY",
                "payload": {"keyword": target["keyword"], "budget": budget, "quantity": quantity},
            }

        # We have a concrete product -> proceed through the SAFE pipeline.
        # NOTE: this never skips policy/risk/approval -- it just tells
        # MERCHX which product to run the pipeline against.
        return {
            "action": "RUN_PURCHASE_PIPELINE",
            "payload": {"product": target, "quantity": quantity},
        }

    if intent == "CANCEL":
        return {"action": "ASK_ORDER_ID", "payload": {}}

    if intent == "REFUND":
        return {"action": "ASK_ORDER_ID", "payload": {}}

    if intent == "ORDER_STATUS":
        return {"action": "ASK_ORDER_ID", "payload": {}}

    return {"action": "HELP", "payload": {}}
