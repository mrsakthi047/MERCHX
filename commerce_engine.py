# MERCHX Commerce Engine
# Product discovery and inventory foundation

PRODUCTS = [
    {
        "id": "MX-P001",
        "name": "MERCHX Wireless ANC Headphones",
        "category": "Electronics",
        "price": 7499,
        "stock": 35,
        "features": ["ANC", "Bluetooth", "Wireless", "40-hour battery"]
    },
    {
        "id": "MX-P002",
        "name": "MERCHX Premium Wireless Headphones",
        "category": "Electronics",
        "price": 8999,
        "stock": 12,
        "features": ["ANC", "Bluetooth", "Wireless", "30-hour battery"]
    },
    {
        "id": "MX-P003",
        "name": "MERCHX Smart Watch",
        "category": "Electronics",
        "price": 5999,
        "stock": 20,
        "features": ["AMOLED", "Fitness Tracking", "Bluetooth"]
    },
    {
        "id": "MX-P004",
        "name": "MERCHX Mechanical Keyboard",
        "category": "Electronics",
        "price": 4499,
        "stock": 18,
        "features": ["RGB", "Mechanical Switches", "USB-C"]
    },
    {
        "id": "MX-P005",
        "name": "MERCHX Business Laptop",
        "category": "Computers",
        "price": 64999,
        "stock": 8,
        "features": ["16GB RAM", "512GB SSD", "Intel Processor"]
    }
]


def search_products(query, max_price=None, category=None):
    """
    Search MERCHX product catalog using basic matching.
    """

    query = query.lower().strip()

    results = []

    for product in PRODUCTS:

        searchable_text = (
            product["name"] + " " +
            product["category"] + " " +
            " ".join(product["features"])
        ).lower()

        if query not in searchable_text:
            continue

        if max_price is not None and product["price"] > max_price:
            continue

        if category is not None:
            if product["category"].lower() != category.lower():
                continue

        results.append(product)

    return results


def check_inventory(product_id, quantity=1):
    """
    Check whether requested quantity is available.
    """

    for product in PRODUCTS:

        if product["id"] == product_id:

            if product["stock"] >= quantity:
                return {
                    "available": True,
                    "product_id": product_id,
                    "requested_quantity": quantity,
                    "available_stock": product["stock"]
                }

            return {
                "available": False,
                "product_id": product_id,
                "requested_quantity": quantity,
                "available_stock": product["stock"]
            }

    return {
        "available": False,
        "product_id": product_id,
        "requested_quantity": quantity,
        "available_stock": 0,
        "error": "Product not found"
    }


def get_product(product_id):
    """
    Retrieve a product by ID.
    """

    for product in PRODUCTS:

        if product["id"] == product_id:
            return product

    return None