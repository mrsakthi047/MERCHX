# ============================================================
# MERCHX SHOPPING INTELLIGENCE AGENT
# ============================================================
#
# Responsibilities:
# - Understand shopping goals
# - Research live web
# - Find real products
# - Compare prices
# - Analyse reviews
# - Identify pros / cons
# - Rank products
# - Return source URLs
#
# This is an AGENT, not a static product database.
# ============================================================

import os
import re

from google import genai
from google.genai import types


# ============================================================
# GEMINI CLIENT
# ============================================================

def get_client():

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return None

    return genai.Client(
        api_key=api_key
    )


# ============================================================
# URL EXTRACTION
# ============================================================

def extract_urls(text):

    if not text:
        return []

    urls = re.findall(
        r"https?://[^\s)\]}>\"']+",
        text
    )

    cleaned = []

    for url in urls:

        url = url.rstrip(
            ".,;:)"
        )

        if url not in cleaned:
            cleaned.append(url)

    return cleaned


# ============================================================
# SHOPPING AGENT
# ============================================================

def shopping_agent(user_request):

    client = get_client()

    if client is None:

        return {
            "success": False,
            "error": (
                "GEMINI_API_KEY is not configured."
            ),
            "products": [],
            "sources": []
        }

    prompt = f"""
You are MERCHX Shopping Intelligence Agent.

Your goal is to help the user make the best purchasing
decision using live web research.

USER REQUEST:
{user_request}

============================================================
RESEARCH OBJECTIVE
============================================================

Understand the user's intent first.

Extract:

- Product
- Category
- Budget
- Quantity
- Important features
- Use case
- Brand preference
- Other constraints

If the user says things like:

"best"
"cheapest"
"under ₹50000"
"for gaming"
"good camera"
"best value"

interpret those requirements intelligently.

============================================================
LIVE PRODUCT RESEARCH
============================================================

Search the live web.

Prefer real product pages from:

- Amazon India
- Flipkart
- Myntra
- Meesho
- Croma
- Reliance Digital
- Official brand stores
- Other trustworthy retailers

IMPORTANT:

NEVER invent:

- product names
- prices
- ratings
- review counts
- product URLs
- retailer names

Only return information that can be verified from
web research.

============================================================
PRICE INTELLIGENCE
============================================================

For the SAME or equivalent product:

find multiple retailers where possible.

Compare:

Retailer
Price
Availability
Product URL

Identify:

BEST PRICE
BEST VALUE
PREMIUM OPTION

Do not assume the lowest price is automatically
the best product.

============================================================
REVIEW INTELLIGENCE
============================================================

Research available reviews.

Look for recurring:

Positive points
Negative points
Reliability issues
Battery issues
Build quality
Performance
Value for money
Common complaints

Create a short AI summary.

Do NOT pretend to have analysed reviews that were
not available.

============================================================
PRODUCT QUALITY
============================================================

For every product calculate an approximate:

MERCHX SCORE / 100

Use these factors:

- Value
- Reviews
- Brand trust
- Specifications
- Price
- Availability
- User sentiment

Explain the score briefly.

============================================================
TOP 1% STYLE FILTER
============================================================

Reject obviously poor choices when evidence supports it.

Prefer:

high-value
well-reviewed
trusted
reliable
good specification
reasonable price

Do NOT claim literal "top 1%" market coverage unless
the research actually supports such a claim.

Call this:

MERCHX TOP PICKS

============================================================
OUTPUT FORMAT
============================================================

Return clean Markdown.

# 🛍️ MERCHX SHOPPING RESULTS

## 🎯 Understanding Your Request

Product:
Budget:
Use Case:
Important Requirements:

---

## 🏆 MERCHX TOP PICKS

For each recommended product:

### PRODUCT NAME

**Brand:** ...
**Retailer:** ...
**Price:** ...
**Rating:** ...
**Reviews:** ...
**Availability:** ...

**MERCHX SCORE:** XX/100

### ✅ Pros

- ...
- ...
- ...

### ❌ Cons

- ...
- ...
- ...

### ⭐ Review Intelligence

...

### 🔗 Product Page

REAL URL ONLY

---

## 💰 PRICE COMPARISON

Create a table:

| Retailer | Price | Availability | Product Link |
|---|---:|---|---|

Use REAL URLs only.

---

## 🥇 BEST PRICE

Product:
Retailer:
Price:
URL:

---

## 🧠 BEST VALUE

Product:
Reason:

---

## ⭐ REVIEW VERDICT

Short summary.

---

## 🛡️ MERCHX TRUST CHECK

Mention:

- Product legitimacy
- Retailer trust
- Review consistency
- Price anomaly
- Important warnings

---

## 🤖 MERCHX DECISION

Give one recommendation:

BUY
CONSIDER
WAIT
AVOID

Explain why.

============================================================
FINAL RULE
============================================================

MERCHX is an intelligence layer.

It does NOT automatically purchase anything.

Before payment:

USER
↓
MERCHX POLICY
↓
RISK ENGINE
↓
HUMAN APPROVAL if required
↓
PAYMENT

Never claim a purchase occurred.
"""

    try:

        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        google_search=types.GoogleSearch()
                    )
                ]
            )
        )

        text = response.text

        return {
            "success": True,
            "text": text,
            "sources": extract_urls(text),
            "products": []
        }

    except Exception as error:

        return {
            "success": False,
            "error": str(error),
            "products": [],
            "sources": []
        }


# ============================================================
# AGENT STATUS
# ============================================================

def shopping_agent_status():

    client = get_client()

    return {
        "agent": "MERCHX Shopping Intelligence Agent",
        "status": "ONLINE" if client else "OFFLINE",
        "capabilities": [
            "Intent Understanding",
            "Live Web Research",
            "Product Discovery",
            "Price Comparison",
            "Review Intelligence",
            "Pros & Cons",
            "Trust Analysis",
            "Product Ranking",
            "Recommendation"
        ]
    }