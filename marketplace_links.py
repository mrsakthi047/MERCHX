from urllib.parse import quote_plus


MARKETPLACE_CONFIG = {
    "Amazon": {
        "search_url": "https://www.amazon.in/s?k={query}",
    },
    "Flipkart": {
        "search_url": "https://www.flipkart.com/search?q={query}",
    },
    "Meesho": {
        "search_url": "https://www.meesho.com/search?q={query}",
    },
    "Myntra": {
        "search_url": "https://www.myntra.com/{query}",
    },
}


def create_marketplace_url(
    marketplace,
    product_name,
    exact_url=None,
):
    """
    Return an exact product URL when available.
    Otherwise generate a marketplace search URL.
    """

    if exact_url:
        return exact_url

    config = MARKETPLACE_CONFIG.get(marketplace)

    if not config:
        return None

    query = quote_plus(product_name)

    return config["search_url"].format(
        query=query
    )


def get_marketplace_links(
    product_name,
    exact_urls=None,
):
    """
    Generate clickable marketplace destinations.

    exact_urls can contain known product URLs.
    """

    if exact_urls is None:
        exact_urls = {}

    links = {}

    for marketplace in MARKETPLACE_CONFIG:

        exact_url = exact_urls.get(
            marketplace
        )

        links[marketplace] = create_marketplace_url(
            marketplace=marketplace,
            product_name=product_name,
            exact_url=exact_url,
        )

    return links