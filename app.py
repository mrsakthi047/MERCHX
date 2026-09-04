import os
import re
import uuid
from urllib.parse import quote_plus

import streamlit as st

from agent_engine import detect_intent
from commerce_engine import PRODUCTS, check_inventory, search_products
from policy_engine import evaluate_policy


try:
    from risk_engine import calculate_risk, format_risk_report
except Exception:
    calculate_risk = None
    format_risk_report = None


try:
    from explainability_engine import (
        explain_decision,
        format_explanation,
    )
except Exception:
    explain_decision = None
    format_explanation = None


try:
    from audit_engine import AuditEngine
except Exception:
    AuditEngine = None


try:
    from shopping_agent import shopping_agent
except Exception:
    shopping_agent = None


st.set_page_config(
    page_title="MERCHX — AI-Native Commerce",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# STYLE
# ============================================================

st.markdown(
    """
<style>

.stApp {
    background: #07090d;
    color: #f5f7fa;
}

.block-container {
    max-width: 1200px;
    padding-top: 2rem;
    padding-bottom: 4rem;
}

.hero {
    text-align: center;
    padding: 30px 10px 20px;
}

.hero h1 {
    font-size: 52px;
    margin: 0;
    font-weight: 850;
    letter-spacing: -2px;
}

.hero p {
    color: #9aa4b2;
    font-size: 17px;
    margin-top: 10px;
}

.search-wrap {
    border: 1px solid #303846;
    background: #10141b;
    border-radius: 24px;
    padding: 14px;
    box-shadow: 0 15px 50px rgba(0, 0, 0, 0.28);
    margin: 10px auto 28px;
    max-width: 900px;
}

.search-hint {
    text-align: center;
    color: #7f8a99;
    font-size: 13px;
    margin-top: 10px;
}

.card {
    background: #10141b;
    border: 1px solid #252d38;
    border-radius: 18px;
    padding: 20px;
    margin-bottom: 14px;
}

.link-card {
    background: #0d1118;
    border: 1px solid #252d38;
    border-radius: 14px;
    padding: 14px;
    margin-bottom: 10px;
}

.muted {
    color: #8d98a7;
}

.small {
    font-size: 13px;
    color: #8d98a7;
}

.pill {
    display: inline-block;
    border: 1px solid #303846;
    border-radius: 999px;
    padding: 5px 10px;
    margin: 2px;
    font-size: 12px;
    color: #b8c1ce;
}

div[data-testid="stForm"] {
    border: 0;
    padding: 0;
}

div[data-testid="stForm"] input {
    font-size: 18px !important;
    min-height: 52px !important;
}

button[kind="primaryFormSubmit"] {
    border-radius: 14px !important;
    min-height: 50px !important;
    font-weight: 750 !important;
}

.stButton > button {
    border-radius: 14px;
    min-height: 46px;
    font-weight: 700;
}

section[data-testid="stSidebar"] {
    background: #0b0e13;
}

a {
    color: #8fb8ff !important;
}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# HELPERS
# ============================================================

def get_api_key():
    return os.getenv("GEMINI_API_KEY", "").strip()


def money(value):
    try:
        return f"₹{value:,.0f}"
    except Exception:
        return "Price not verified"


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


def marketplace_links(product_name):

    q = quote_plus(product_name)

    return {
        "Amazon India": f"https://www.amazon.in/s?k={q}",
        "Flipkart": f"https://www.flipkart.com/search?q={q}",
        "Meesho": f"https://www.meesho.com/search?q={q}",
        "Myntra": f"https://www.myntra.com/{q}",
    }


def render_marketplace_links(product_name):

    st.markdown(
        "#### 🛍️ Marketplace Search"
    )

    st.caption(
        "These are marketplace search links. "
        "They do not claim that the exact product "
        "is available on every marketplace."
    )

    links = marketplace_links(product_name)

    cols = st.columns(4)

    for col, (name, url) in zip(
        cols,
        links.items(),
    ):
        with col:
            st.link_button(
                f"{name} ↗",
                url,
                use_container_width=True,
            )


def render_verified_sources(text):

    urls = extract_urls(text)

    if not urls:
        st.info(
            "No exact product URLs were returned "
            "by the live research response."
        )
        return

    st.markdown(
        "### 🔗 Verified Research Links"
    )

    for index, url in enumerate(urls, 1):

        st.markdown(
            f"""
<div class="link-card">
<b>Source {index}</b>
<br>
<span class="small">{url}</span>
</div>
""",
            unsafe_allow_html=True,
        )

        st.link_button(
            f"Open Source {index} ↗",
            url,
            use_container_width=True,
        )


def render_local_product(product):

    st.markdown(
        '<div class="card">',
        unsafe_allow_html=True,
    )

    st.subheader(
        product["name"]
    )

    st.write(
        f'**{money(product["price"])}** · '
        f'Category: {product["category"]} · '
        f'Stock: {product["stock"]}'
    )

    features = " ".join(
        f'<span class="pill">{feature}</span>'
        for feature in product.get(
            "features",
            [],
        )
    )

    st.markdown(
        features,
        unsafe_allow_html=True,
    )

    render_marketplace_links(
        product["name"]
    )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )


# ============================================================
# AUDIT
# ============================================================

def audit_event(action, payload):

    if "audit_engine" not in st.session_state:

        if AuditEngine:

            try:
                st.session_state.audit_engine = AuditEngine()
            except Exception:
                st.session_state.audit_engine = None

        else:
            st.session_state.audit_engine = None

    engine = st.session_state.audit_engine

    if engine is None:
        return

    try:

        if hasattr(engine, "record"):
            engine.record(
                action,
                payload,
            )

        elif hasattr(engine, "log"):
            engine.log(
                action,
                payload,
            )

    except Exception:
        pass


# ============================================================
# PURCHASE PIPELINE
# ============================================================

def run_purchase_pipeline(
    product,
    quantity,
    budget=None,
):

    transaction_id = (
        "MX-"
        + uuid.uuid4().hex[:10].upper()
    )

    total = (
        product["price"]
        * quantity
    )

    inventory = check_inventory(
        product["id"],
        quantity,
    )

    policy = evaluate_policy(
        product,
        quantity,
        budget=budget,
        spent_today=st.session_state.get(
            "spent_today",
            0,
        ),
    )

    risk = None

    if calculate_risk:

        try:

            risk = calculate_risk(
                product=product,
                quantity=quantity,
                total=total,
                inventory=inventory,
                policy=policy,
            )

        except TypeError:

            try:

                risk = calculate_risk(
                    product,
                    quantity,
                    total,
                )

            except Exception:
                risk = None

        except Exception:
            risk = None

    approved = (
        bool(inventory.get("available"))
        and bool(policy.get("approved"))
    )

    risk_level = "LOW"

    if isinstance(risk, dict):

        risk_level = str(
            risk.get(
                "risk_level",
                risk.get(
                    "level",
                    "LOW",
                ),
            )
        ).upper()

        if risk_level in {
            "HIGH",
            "CRITICAL",
        }:
            approved = False

    explanation = None

    if explain_decision:

        try:

            explanation = explain_decision(
                product=product,
                quantity=quantity,
                inventory=inventory,
                policy=policy,
                risk=risk,
                approved=approved,
            )

        except Exception:
            explanation = None

    audit_event(
        "PURCHASE_DECISION",
        {
            "transaction_id": transaction_id,
            "product_id": product["id"],
            "quantity": quantity,
            "total": total,
            "approved": approved,
            "risk_level": risk_level,
        },
    )

    return {
        "transaction_id": transaction_id,
        "total": total,
        "inventory": inventory,
        "policy": policy,
        "risk": risk,
        "risk_level": risk_level,
        "explanation": explanation,
        "approved": approved,
    }


# ============================================================
# SEARCH
# ============================================================

def handle_search(query):

    query = query.strip()

    if not query:
        return

    st.session_state.last_query = query

    st.session_state.messages.append(
        {
            "role": "user",
            "content": query,
        }
    )

    intent = detect_intent(query)

    audit_event(
        "AGENT_INTENT",
        {
            "intent": intent,
            "query": query,
        },
    )

    # --------------------------------------------------------
    # LIVE GEMINI RESEARCH
    # --------------------------------------------------------

    if shopping_agent and get_api_key():

        with st.spinner(
            "🧠 MERCHX is researching live products, "
            "prices, reviews and sources..."
        ):

            result = shopping_agent(query)

        if result.get("success"):

            text = result.get(
                "text",
                "",
            )

            sources = result.get(
                "sources",
                [],
            )

            if not sources:
                sources = extract_urls(text)

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": text,
                    "sources": sources,
                }
            )

            return

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": (
                    "⚠️ MERCHX Live Shopping Agent "
                    "could not complete the research.\n\n"
                    "Local catalog fallback is available.\n\n"
                    f"Error: {result.get('error', 'Unknown error')}"
                ),
            }
        )

    else:

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": (
                    "🔎 MERCHX Live Shopping Agent is "
                    "offline because GEMINI_API_KEY "
                    "is not configured.\n\n"
                    "Local MERCHX catalog search is available."
                ),
            }
        )

    results = search_products(query)

    st.session_state.local_results = results


# ============================================================
# SESSION STATE
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "local_results" not in st.session_state:
    st.session_state.local_results = []

if "last_query" not in st.session_state:
    st.session_state.last_query = ""

if "spent_today" not in st.session_state:
    st.session_state.spent_today = 0


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown("## 🛒 MERCHX")

    st.caption(
        "AI-Native Commerce Protocol"
    )

    st.divider()

    api_status = (
        "ONLINE"
        if get_api_key()
        else "OFFLINE"
    )

    st.metric(
        "Shopping Agent",
        api_status,
    )

    st.metric(
        "Catalog Products",
        len(PRODUCTS),
    )

    st.metric(
        "Daily Spend",
        money(
            st.session_state.spent_today
        ),
    )

    st.divider()

    st.markdown(
        "### 🛡️ Control Boundary"
    )

    st.write(
        "AI Buyer → MERCHX → "
        "Policy → Risk → Payment"
    )

    st.caption(
        "AI can recommend and research. "
        "MERCHX controls authorization."
    )


# ============================================================
# HERO
# ============================================================

st.markdown(
    """
<div class="hero">

<h1>🛒 MERCHX</h1>

<p>
AI-native shopping intelligence
with policy-controlled commerce.
</p>

</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# SEARCH BAR
# ============================================================

st.markdown(
    '<div class="search-wrap">',
    unsafe_allow_html=True,
)

with st.form(
    "merchx_main_search",
    clear_on_submit=True,
):

    search_query = st.text_input(
        "Search",
        placeholder=(
            "Find the best laptop for AI/ML under ₹70,000..."
        ),
        label_visibility="collapsed",
    )

    submitted = st.form_submit_button(
        "🔎 Search with MERCHX",
        use_container_width=True,
        type="primary",
    )

st.markdown(
    """
<div class="search-hint">

💡 Try:
"Best laptop for AI/ML under ₹70,000"
&nbsp; · &nbsp;
"Compare ANC headphones under ₹5,000"
&nbsp; · &nbsp;
"Find running shoes under ₹3,000"

</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    "</div>",
    unsafe_allow_html=True,
)


if submitted and search_query.strip():

    handle_search(
        search_query
    )

    st.rerun()


# ============================================================
# AI RESULTS
# ============================================================

if st.session_state.messages:

    st.markdown(
        "## 🧠 MERCHX Intelligence"
    )

    for message in st.session_state.messages:

        if message["role"] == "user":

            st.markdown("**You**")

            st.info(
                message["content"]
            )

        else:

            st.markdown("**MERCHX**")

            st.markdown(
                message["content"]
            )

            # Exact URLs discovered by Gemini
            render_verified_sources(
                message.get(
                    "content",
                    "",
                )
            )

            # Marketplace navigation
            # Uses last user query as search term
            user_query = st.session_state.get(
                "last_query",
                "",
            )

            if user_query:

                st.markdown(
                    "### 🛍️ Shop & Compare"
                )

                st.caption(
                    "Open a marketplace search for "
                    "the requested product."
                )

                links = marketplace_links(
                    user_query
                )

                cols = st.columns(4)

                for col, (name, url) in zip(
                    cols,
                    links.items(),
                ):

                    with col:

                        st.link_button(
                            f"{name} ↗",
                            url,
                            use_container_width=True,
                        )


# ============================================================
# LOCAL CATALOG
# ============================================================

if st.session_state.local_results:

    st.markdown(
        "## 🛍️ MERCHX Catalog Results"
    )

    for product in (
        st.session_state.local_results
    ):

        render_local_product(
            product
        )


# ============================================================
# AUTHORIZATION CENTER
# ============================================================

st.markdown(
    "## 🧾 Authorization Center"
)

st.caption(
    "AI recommendation ≠ payment authority. "
    "MERCHX makes the authorization decision."
)


catalog_names = [
    product["name"]
    for product in PRODUCTS
]

selected_name = st.selectbox(
    "Select a MERCHX catalog product",
    catalog_names,
)

selected_product = next(
    product
    for product in PRODUCTS
    if product["name"] == selected_name
)


col1, col2 = st.columns(2)


with col1:

    quantity = st.number_input(
        "Quantity",
        min_value=1,
        max_value=10,
        value=1,
        step=1,
    )


with col2:

    budget_input = st.number_input(
        "Optional budget (₹)",
        min_value=0,
        value=0,
        step=500,
    )


budget = (
    budget_input
    if budget_input > 0
    else None
)


st.markdown(
    f"""
<div class="card">

<b>Selected:</b>
{selected_product["name"]}

<br><br>

<b>Unit price:</b>
{money(selected_product["price"])}

<br>

<b>Estimated total:</b>
{money(selected_product["price"] * quantity)}

</div>
""",
    unsafe_allow_html=True,
)


authorize = st.button(
    "🛡️ Run MERCHX Authorization",
    use_container_width=True,
    type="primary",
)


if authorize:

    result = run_purchase_pipeline(
        selected_product,
        int(quantity),
        budget=budget,
    )

    st.session_state.last_decision = result


# ============================================================
# DECISION
# ============================================================

if "last_decision" in st.session_state:

    result = st.session_state.last_decision

    st.markdown(
        "### 🔐 MERCHX Decision"
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Transaction",
            result["transaction_id"],
        )

    with c2:
        st.metric(
            "Total",
            money(result["total"]),
        )

    with c3:
        st.metric(
            "Risk",
            result["risk_level"],
        )


    if result["approved"]:

        st.success(
            "✅ MERCHX APPROVED — "
            "inventory, policy and risk gates passed."
        )

    else:

        st.error(
            "🛑 MERCHX BLOCKED — "
            "payment must not proceed."
        )


    with st.expander(
        "📦 Inventory Check",
        expanded=True,
    ):

        st.json(
            result["inventory"]
        )


    with st.expander(
        "🛡️ Policy Decision",
        expanded=True,
    ):

        st.json(
            result["policy"]
        )


    with st.expander(
        "⚠️ Risk Decision"
    ):

        if (
            format_risk_report
            and result["risk"] is not None
        ):

            try:

                st.markdown(
                    format_risk_report(
                        result["risk"]
                    )
                )

            except Exception:

                st.json(
                    result["risk"]
                )

        else:

            st.json(
                result["risk"]
                or {
                    "risk_level":
                    result["risk_level"]
                }
            )


    with st.expander(
        "💡 Explainability"
    ):

        if result["explanation"] is not None:

            if format_explanation:

                try:

                    st.markdown(
                        format_explanation(
                            result["explanation"]
                        )
                    )

               