# ============================================================
# MERCHX SHOPPING INTELLIGENCE AGENT
# ============================================================

import os
import re
from urllib.parse import quote_plus

from google import genai
from google.genai import types


MODEL_NAME = "gemini-3.8-flash"


def get_client():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key:
        return None

    return genai.Client(api_key=api_key)


def extract_urls(text):
    if not text:
        return []

    urls = re.findall(
        r"https?://[^\s)\]}>\"']+",
        text,
    )

    cleaned = []

    for url in urls:
        url = url.rstrip(".,;:)")

        if url not in cleaned:
            cleaned.append(url)

    return cleaned


def marketplace_search_links(product_name):
    """
    Creates legitimate marketplace SEARCH links.
    These are not fake product pages.
    """

    q = quote_plus(product_name)

    return {
        "Amazon India": f"https://www.amazon.in/s?k={q}",
        "Flipkart": f"https://www.flipkart.com/search?q={q}",
        "Meesho": f"https://www.meesho.com/search?q={q}",
        "Myntra": f"https://www.myntra.com/{q}",
    }


def shopping_agent(user_request):

    client = get_client()

    if client is None:
        return {
            "success": False,
            "error": "GEMINI_API_KEY is not configured.",
            "text": "",
            "sources": [],
            "products": [],
        }

    prompt = f"""
You are MERCHX Shopping Intelligence Agent.

USER REQUEST:
{user_request}

MERCHX is an AI-native commerce intelligence and
authorization protocol.

Your job is to research the LIVE web and help the user
make a better buying decision.

============================================================
IMPORTANT
============================================================

Use Google Search grounding.

Research REAL products from REAL websites.

NEVER invent:

- products
- prices
- ratings
- review counts
- sellers
- availability
- product URLs

If exact information cannot be verified, clearly say:

"Not verified"

============================================================
RESEARCH
============================================================

Understand:

- product category
- budget
- features
- use case
- quantity
- brand preference
- important constraints

Then research real products.

Prefer legitimate Indian retailers such as:

Amazon India
Flipkart
Croma
Reliance Digital
Vijay Sales
Myntra
Meesho
Official brand stores

Also use reputable review sources when useful.

============================================================
URL REQUIREMENT
============================================================

For EVERY important product:

1. Try to find the exact product page URL.
2. Only output URLs actually discovered from web research.
3. Never fabricate an exact product URL.
4. If exact product URL cannot be verified,
   write:

Exact product URL: NOT VERIFIED

5. Also provide a marketplace SEARCH LINK section
   using the product name.

These marketplace search links are navigation links,
NOT claims that the product exists on that marketplace.

============================================================
OUTPUT
============================================================

Return the following structure.

# 🛍️ MERCHX SHOPPING INTELLIGENCE

## 🎯 UNDERSTOOD REQUEST

Explain the user's intent.

## 🔎 LIVE RESEARCH

Explain what was researched.

## 🏆 TOP PICKS

### #1 PRODUCT NAME

Price: ₹...
Seller: ...
Availability: ...
Trust Score: .../100

Why recommended:
...

Pros:
- ...
- ...
- ...

Cons:
- ...
- ...
- ...

Exact Product URL:
https://...

If exact URL cannot be verified:

Exact Product URL: NOT VERIFIED

Marketplace Search Links:

Amazon India:
https://www.amazon.in/...

Flipkart:
https://www.flipkart.com/...

Myntra:
https://www.myntra.com/...

Meesho:
https://www.meesho.com/...

Repeat for #2 and #3 when appropriate.

## 💰 PRICE COMPARISON

| Product | Seller | Price | Trust |
|---|---|---:|---:|

## ⭐ REVIEW INTELLIGENCE

Summarize review patterns.

## 🛡️ TRUST & RISK

Explain seller/source quality.

## 🧠 MERCHX RECOMMENDATION

BEST OVERALL:
...

BEST VALUE:
...

BEST ALTERNATIVE:
...

## ⚠️ IMPORTANT

Mention anything the user should verify before purchase.

============================================================
MERCHX CONTROL BOUNDARY
============================================================

AI Buyer
↓
Live Research
↓
Product Intelligence
↓
MERCHX Policy
↓
Risk Engine
↓
Human Approval
↓
Payment

The shopping agent MUST NOT claim that payment occurred.

The shopping agent MUST NOT claim that an order was created.

============================================================
STRICT RULES
============================================================

- Use live Google Search grounding.
- Prefer current information.
- Never fabricate URLs.
- Never fabricate prices.
- Never fabricate products.
- Never fabricate reviews.
- Clearly mark unverified information.
- Recommend based on the user's goal, not simply price.
"""

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        google_search=types.GoogleSearch()
                    )
                ]
            ),
        )

        text = response.text or ""

        sources = extract_urls(text)

        return {
            "success": True,
            "error": "",
            "text": text,
            "sources": sources,
            "products": [],
        }

    except Exception as error:
        return {
            "success": False,
            "error": str(error),
            "text": "",
            "sources": [],
            "products": [],
        }


def shopping_agent_status():

    client = get_client()

    return {
        "agent": "MERCHX Shopping Intelligence Agent",
        "status": "ONLINE" if client else "OFFLINE",
        "capabilities": [
            "Intent Understanding",
            "Live Web Research",
            "Real Product Discovery",
            "Price Intelligence",
            "Review Intelligence",
            "Pros & Cons",
            "Seller Trust Analysis",
            "Product Ranking",
            "Recommendation",
            "Source Verification",
            "Marketplace Navigation",
        ],
    }