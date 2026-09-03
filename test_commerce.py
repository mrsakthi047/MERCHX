from commerce_engine import search_products, check_inventory


print("=== MERCHX PRODUCT SEARCH TEST ===")

results = search_products(
    query="headphones",
    max_price=8000
)

for product in results:
    print(
        product["id"],
        "|",
        product["name"],
        "| ₹",
        product["price"],
        "| Stock:",
        product["stock"]
    )


print("\n=== MERCHX INVENTORY TEST ===")

if results:

    product = results[0]

    inventory = check_inventory(
        product_id=product["id"],
        quantity=1
    )

    print(inventory)