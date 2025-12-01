
import sys
import os
import logging

# Add project root to path
sys.path.append(os.getcwd())

# Setup logging
logging.basicConfig(level=logging.INFO)

from src.services.production_code_generators import generate_entities

def test_entity_generation():
    print("--- Testing Entity Generation with Relationships ---")
    
    # Mock entities
    entities = [
        {
            "name": "Cart",
            "plural": "Carts",
            "fields": [
                {"name": "status", "type": "string", "required": True, "default": "OPEN", "constraints": []}
            ]
        },
        {
            "name": "CartItem",
            "plural": "CartItems",
            "fields": [
                {"name": "quantity", "type": "int", "required": True, "default": 1, "constraints": []},
                {"name": "cart_id", "type": "UUID", "required": True, "default": None, "constraints": []},
                {"name": "product_id", "type": "UUID", "required": True, "default": None, "constraints": []}
            ]
        },
        {
            "name": "Product",
            "plural": "Products",
            "fields": [
                {"name": "name", "type": "string", "required": True, "default": None, "constraints": []}
            ]
        }
    ]
    
    # Generate entities code
    code = generate_entities(entities)
    
    print("\n--- Generated Code Snippet (Cart) ---")
    lines = code.split('\n')
    in_cart = False
    cart_relationships = []
    
    for line in lines:
        if "class CartEntity" in line:
            in_cart = True
        elif "class" in line and "CartEntity" not in line:
            in_cart = False
        
        if in_cart:
            if "relationship" in line:
                print(f"Cart: {line.strip()}")
                cart_relationships.append(line.strip())

    print("\n--- Generated Code Snippet (CartItem) ---")
    in_item = False
    item_relationships = []
    item_fks = []
    
    for line in lines:
        if "class CartItemEntity" in line:
            in_item = True
        elif "class" in line and "CartItemEntity" not in line:
            in_item = False
        
        if in_item:
            if "relationship" in line:
                print(f"CartItem: {line.strip()}")
                item_relationships.append(line.strip())
            if "ForeignKey" in line:
                print(f"CartItem FK: {line.strip()}")
                item_fks.append(line.strip())

    # Verification
    print("\n--- Verification Results ---")
    
    # Check Cart relationships (should have items)
    has_items_rel = any('items = relationship("CartItemEntity"' in r for r in cart_relationships)
    if has_items_rel:
        print("✅ Cart has 'items' relationship")
    else:
        print("❌ Cart MISSING 'items' relationship")

    # Check CartItem relationships (should have cart and product)
    has_cart_rel = any('cart = relationship("CartEntity"' in r for r in item_relationships)
    if has_cart_rel:
        print("✅ CartItem has 'cart' relationship")
    else:
        print("❌ CartItem MISSING 'cart' relationship")

    # Check ForeignKey
    has_cart_fk = any('ForeignKey("carts.id")' in f for f in item_fks)
    if has_cart_fk:
        print("✅ CartItem has ForeignKey to carts")
    else:
        print("❌ CartItem MISSING ForeignKey to carts")

if __name__ == "__main__":
    test_entity_generation()
