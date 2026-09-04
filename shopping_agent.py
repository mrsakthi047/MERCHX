import os
import re
from urllib.parse import quote_plus

from google import genai
from google.genai import types

MODEL_NAME = "gemini-2.5-flash"


def get_api_key():
    # 1. Environment variable
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    # 2. Streamlit Cloud Secrets fallback
    if not api_key:
        try:
            import streamlit as st
            api_key = str(st.secrets.get("GEMINI_API_KEY", "")).strip()
        except Exception:
            pass

    return api_key


def get_client():
    api_key = get_api_key()

    if not api_key:
        return None

    try:
        return genai.Client(api_key=api_key)
    except Exception:
        return None


def extract_urls(text):
    if not text:
        return []

    urls = re.findall(
        r"https?://[^\s)\]}>\"']+",
        text
    )

    cleaned = []

    for url in urls:
        url = url.rstrip(".,;:)")

        if url not in cleaned:
            cleaned.append(url)

    return cleaned


def marketplace_search_links(product_name):
    q = quote_plus(product_name)

    return {
        "Amazon India": f"https://www.amazon.in/s?k={q}",
        "Flipkart": f"https://www.flipkart.com/search?q={q}",
        "Myntra": f"https://www.myntra.com/{q}",
        "Meesho": f"https://www.meesho.com/search?q={q}",
    }


def shopping_agent(user_request):
    client = get_client()

    if client is None:
        return {
            "success": False,
            "error": "GEMINI_API_KEY is missing or unavailable.",
            "text": "",
            "sources": [],
            "products": [],
        }

    prompt = f"""
You are MERCHX Shopping Intelligence Agent.

USER REQUEST:
{user_request}

Research REAL products from the live web.

Do NOT invent:
- products
- prices
- ratings
- sellers
- availability
- reviews
- URLs

If information cannot be verified, say:
"Not verified."

Analyze:
1. User intent
2. Real products
3. Current prices
4. Sellers
5. Reviews
6. Pros and cons
7. Trust
8. Risk
9. Product ranking
10. Final recommendation

For every important product, provide an exact product URL
ONLY if it was actually discovered during web research.

Structure:

# MERCHX SHOPPING INTELLIGENCE

## UNDERSTOOD REQUEST

## LIVE RESEARCH

## TOP PICKS

### #1 PRODUCT
- Price:
- Seller:
- Availability:
- Trust:
- Why recommended:
- Pros:
- Cons:
- Exact Product URL:

### #2 PRODUCT
- Price:
- Seller:
- Availability:
- Trust:
- Why recommended:
- Pros:
- Cons:
- Exact Product URL:

## PRICE COMPARISON

## REVIEW INTELLIGENCE

## TRUST & RISK

## MERCHX RECOMMENDATION

## IMPORTANT

MERCHX flow:

AI Buyer
→ Live Research
→ Product Intelligence
→ Policy Engine
→ Risk Engine
→ Authorization
→ Human Approval
→ Payment

Do not claim that a payment or order was completed.
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

        return {
            "success": True,
            "error": "",
            "text": text,
            "sources": extract_urls(text),
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
    return {
        "agent": "MERCHX Shopping Intelligence Agent",
        "status": "ONLINE" if get_client() else "OFFLINE",
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