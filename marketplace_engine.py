# ============================================================
# MERCHX MARKETPLACE AGGREGATOR
# ============================================================
# Multi-platform product discovery layer.
#
# MVP:
# - Uses normalized demo marketplace data
# - Supports multiple marketplace sources
# - Provides cross-platform comparison
#
# Future:
# - Official marketplace APIs
# - Partner feeds
# - Vendor APIs
# ============================================================


MARKETPLACE_PRODUCTS = [

    # ========================================================
    # HEADPHONES
    # ========================================================

    {
        "platform": "Amazon",
        "product_id": "AMZ-H001",
        "canonical_id": "MERCHX-HEADPHONES-001",
        "name": "Wireless ANC Headphones",
        "brand": "SoundMax",
        "category": "Electronics",
        "price": 7499,
        "rating": 4.6,
        "reviews": 18420,
        "delivery_days": 2,
        "seller": "SoundMax Official",
        "seller_rating": 4.8,
        "stock": 35,
        "warranty_months": 12,
        "returnable": True,
        "cod": True,
    },

    {
        "platform": "Flipkart",
        "product_id": "FLP-H001",
        "canonical_id": "MERCHX-HEADPHONES-001",
        "name": "SoundMax Wireless ANC Headphones",
        "brand": "SoundMax",
        "category": "Electronics",
        "price": 7299,
        "rating": 4.5,
        "reviews": 12680,
        "delivery_days": 3,
        "seller": "RetailNet",
        "seller_rating": 4.6,
        "stock": 18,
        "warranty_months": 12,
        "returnable": True,
        "cod": True,
    },

    {
        "platform": "Meesho",
        "product_id": "MEE-H001",
        "canonical_id": "MERCHX-HEADPHONES-001",
        "name": "SoundMax ANC Wireless Headphone",
        "brand": "SoundMax",
        "category": "Electronics",
        "price": 6999,
        "rating": 4.2,
        "reviews": 3820,
        "delivery_days": 5,
        "seller": "AudioStore",
        "seller_rating": 4.1,
        "stock": 10,
        "warranty_months": 6,
        "returnable": True,
        "cod": True,
    },


    # ========================================================
    # LAPTOP
    # ========================================================

    {
        "platform": "Amazon",
        "product_id": "AMZ-L001",
        "canonical_id": "MERCHX-LAPTOP-001",
        "name": "Business Laptop 16GB 512GB",
        "brand": "TechBook",
        "category": "Computers",
        "price": 49999,
        "rating": 4.7,
        "reviews": 9340,
        "delivery_days": 2,
        "seller": "TechBook Official",
        "seller_rating": 4.9,
        "stock": 8,
        "warranty_months": 24,
        "returnable": True,
        "cod": False,
    },

    {
        "platform": "Flipkart",
        "product_id": "FLP-L001",
        "canonical_id": "MERCHX-LAPTOP-001",
        "name": "TechBook Business Notebook 16GB",
        "brand": "TechBook",
        "category": "Computers",
        "price": 48999,
        "rating": 4.6,
        "reviews": 7120,
        "delivery_days": 3,
        "seller": "SuperComNet",
        "seller_rating": 4.7,
        "stock": 6,
        "warranty_months": 24,
        "returnable": True,
        "cod": True,
    },


    # ========================================================
    # SMART WATCH
    # ========================================================

    {
        "platform": "Amazon",
        "product_id": "AMZ-W001",
        "canonical_id": "MERCHX-WATCH-001",
        "name": "Smart Fitness Watch AMOLED",
        "brand": "FitPro",
        "category": "Electronics",
        "price": 5999,
        "rating": 4.5,
        "reviews": 15200,
        "delivery_days": 2,
        "seller": "FitPro Official",
        "seller_rating": 4.8,
        "stock": 20,
        "warranty_months": 12,
        "returnable": True,
        "cod": True,
    },

    {
        "platform": "Myntra",
        "product_id": "MYN-W001",
        "canonical_id": "MERCHX-WATCH-001",
        "name": "FitPro AMOLED Smart Watch",
        "brand": "FitPro",
        "category": "Electronics",
        "price": 5799,
        "rating": 4.4,
        "reviews": 8420,
        "delivery_days": 4,
        "seller": "Myntra Partner",
        "seller_rating": 4.5,
        "stock": 11,
        "warranty_months": 12,
        "returnable": True,
        "cod": True,
    },


    # ========================================================
    # KEYBOARD
    # ========================================================

    {
        "platform": "Amazon",
        "product_id": "AMZ-K001",
        "canonical_id": "MERCHX-KEYBOARD-001",
        "name": "Mechanical RGB Keyboard",
        "brand": "KeyMaster",
        "category": "Electronics",
        "price": 4499,
        "rating": 4.5,
        "reviews": 6210,
        "delivery_days": 2,
        "seller": "KeyMaster Official",
        "seller_rating": 4.7,
        "stock": 18,
        "warranty_months": 12,
        "returnable": True,
        "cod": True,
    },

    {
        "platform": "Flipkart",
        "product_id": "FLP-K001",
        "canonical_id": "MERCHX-KEYBOARD-001",
        "name": "KeyMaster RGB Mechanical Gaming Keyboard",
        "brand": "KeyMaster",
        "category": "Electronics",
        "price": 4199,
        "rating": 4.3,
        "reviews": 4880,
        "delivery_days": 3,
        "seller": "GameGear",
        "seller_rating": 4.4,
        "stock": 14,
        "warranty_months": 12,
        "returnable": True,
        "cod": True,
    },
]


# ============================================================
# SEARCH MARKETPLACES
# ============================================================

def search_marketplaces(
    query,
    max_price=None,
    category=None,
    min_rating=None,
    cod_only=False,
):

    query = query.lower().strip()

    results = []

    for product in MARKETPLACE_PRODUCTS:

        searchable = " ".join(
            [
                product["name"],
                product["brand"],
                product["category"],
            ]
        ).lower()

        if query and query not in searchable:
            words = query.split()

            if not any(
                word in searchable
                for word in words
                if len(word) >= 3
            ):
                continue

        if max_price is not None:
            if product["price"] > max_price:
                continue

        if category is not None:
            if product["category"].lower() != category.lower():
                continue

        if min_rating is not None:
            if product["rating"] < min_rating:
                continue

        if cod_only and not product["cod"]:
            continue

        results.append(product)

    return results


# ============================================================
# GROUP SAME PRODUCTS
# ============================================================

def group_products(products):

    groups = {}

    for product in products:

        key = product["canonical_id"]

        if key not in groups:
            groups[key] = []

        groups[key].append(product)

    return groups


# ============================================================
# CROSS-PLATFORM COMPARISON
# ============================================================

def compare_platforms(products):

    groups = group_products(products)

    comparison = []

    for canonical_id, offers in groups.items():

        cheapest = min(
            offers,
            key=lambda item: item["price"]
        )

        fastest = min(
            offers,
            key=lambda item: item["delivery_days"]
        )

        best_rated = max(
            offers,
            key=lambda item: item["rating"]
        )

        comparison.append(
            {
                "canonical_id": canonical_id,
                "offers": offers,
                "cheapest": cheapest,
                "fastest": fastest,
                "best_rated": best_rated,
            }
        )

    return comparison


# ============================================================
# BEST VALUE SCORE
# ============================================================

def calculate_value_score(product):

    price_score = max(
        0,
        100 - (product["price"] / 1000)
    )

    rating_score = product["rating"] * 15

    review_score = min(
        product["reviews"] / 1000,
        20
    )

    delivery_score = max(
        0,
        30 - (product["delivery_days"] * 5)
    )

    seller_score = product["seller_rating"] * 10

    warranty_score = min(
        product["warranty_months"] / 12 * 5,
        10
    )

    return round(
        (
            price_score * 0.30
            + rating_score * 0.20
            + review_score * 0.15
            + delivery_score * 0.15
            + seller_score * 0.10
            + warranty_score * 0.10
        ),
        2
    )


# ============================================================
# RANK OFFERS
# ============================================================

def rank_products(products):

    ranked = []

    for product in products:

        item = dict(product)

        item["value_score"] = calculate_value_score(
            product
        )

        ranked.append(item)

    ranked.sort(
        key=lambda item: item["value_score"],
        reverse=True
    )

    return ranked


# ============================================================
# SMART FILTER
# ============================================================

def smart_filter(
    products,
    brand=None,
    min_rating=None,
    max_price=None,
    cod_only=False,
    warranty_required=False,
):

    filtered = []

    for product in products:

        if brand is not None:

            if product["brand"].lower() != brand.lower():
                continue

        if min_rating is not None:

            if product["rating"] < min_rating:
                continue

        if max_price is not None:

            if product["price"] > max_price:
                continue

        if cod_only and not product["cod"]:
            continue

        if warranty_required:

            if product["warranty_months"] <= 0:
                continue

        filtered.append(product)

    return filtered


# ============================================================
# MARKETPLACE SUMMARY
# ============================================================

def marketplace_summary(products):

    if not products:
        return {
            "total_results": 0,
            "platforms": [],
            "lowest_price": None,
            "fastest_delivery": None,
        }

    platforms = sorted(
        list(
            set(
                product["platform"]
                for product in products
            )
        )
    )

    cheapest = min(
        products,
        key=lambda item: item["price"]
    )

    fastest = min(
        products,
        key=lambda item: item["delivery_days"]
    )

    return {
        "total_results": len(products),
        "platforms": platforms,
        "lowest_price": cheapest,
        "fastest_delivery": fastest,
    }