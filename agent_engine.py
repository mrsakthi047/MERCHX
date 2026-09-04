# MERCHX AI Agent Engine
# Understands short commands and maps them
# to safe commerce actions.

SUPPORTED_INTENTS = {
    "SEARCH": "Search for products",
    "COMPARE": "Compare products",
    "BUY": "Purchase a product",
    "QUOTE": "Create a purchase quote",
    "INVENTORY": "Check product availability",
    "ORDER_STATUS": "Check order status",
    "CANCEL": "Cancel an order",
    "REFUND": "Request a refund",
    "HELP": "Show available commands",
}


def normalize_input(user_input):
    return user_input.strip().lower()


def detect_intent(user_input):
    """
    Detect the user's commerce intent
    using short commands and keywords.
    """

    text = normalize_input(user_input)

    # Exact one-word commands
    exact_commands = {
        "search": "SEARCH",
        "find": "SEARCH",
        "browse": "SEARCH",

        "compare": "COMPARE",

        "buy": "BUY",
        "purchase": "BUY",
        "order": "BUY",

        "quote": "QUOTE",
        "price": "QUOTE",

        "stock": "INVENTORY",
        "inventory": "INVENTORY",
        "available": "INVENTORY",

        "status": "ORDER_STATUS",
        "track": "ORDER_STATUS",

        "cancel": "CANCEL",

        "refund": "REFUND",

        "help": "HELP",
    }

    if text in exact_commands:
        return exact_commands[text]

    # Natural language commands

    if any(
        word in text
        for word in [
            "compare",
            "comparison",
            "which is better",
        ]
    ):
        return "COMPARE"

    if any(
        word in text
        for word in [
            "buy",
            "purchase",
            "order",
            "get me",
        ]
    ):
        return "BUY"

    if any(
        word in text
        for word in [
            "quote",
            "quotation",
            "how much",
            "price",
        ]
    ):
        return "QUOTE"

    if any(
        word in text
        for word in [
            "stock",
            "available",
            "availability",
        ]
    ):
        return "INVENTORY"

    if any(
        word in text
        for word in [
            "track",
            "order status",
            "where is my order",
        ]
    ):
        return "ORDER_STATUS"

    if any(
        word in text
        for word in [
            "cancel",
            "stop order",
        ]
    ):
        return "CANCEL"

    if any(
        word in text
        for word in [
            "refund",
            "money back",
        ]
    ):
        return "REFUND"

    # Default:
    # If user enters a product name,
    # treat it as product discovery.
    return "SEARCH"


def requires_product(intent):
    """
    Determines whether the intent needs
    a specific product.
    """

    return intent in [
        "SEARCH",
        "COMPARE",
        "BUY",
        "QUOTE",
        "INVENTORY",
    ]


def requires_confirmation(intent):
    """
    Dangerous commerce actions require
    explicit confirmation.
    """

    return intent in [
        "BUY",
        "CANCEL",
        "REFUND",
    ]


def get_agent_response(intent):
    """
    Returns the safe next action for the agent.
    """

    responses = {
        "SEARCH":
            "I can search the MERCHX catalog.",

        "COMPARE":
            "I can compare matching products.",

        "BUY":
            "I can prepare a purchase, but payment requires MERCHX authorization.",

        "QUOTE":
            "I can create a verified purchase quote.",

        "INVENTORY":
            "I can check real-time catalog inventory.",

        "ORDER_STATUS":
            "I can check the status of an order.",

        "CANCEL":
            "I can prepare an order cancellation request.",

        "REFUND":
            "I can prepare a refund request.",

        "HELP":
            "Available commands: search, compare, buy, quote, stock, status, cancel, refund.",
    }

    return responses.get(
        intent,
        "I can help with commerce tasks."
    )
