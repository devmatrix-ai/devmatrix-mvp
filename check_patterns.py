
import sys
import os
import logging

# Add project root to path
sys.path.append(os.getcwd())

# Configure logging
logging.basicConfig(level=logging.INFO)

try:
    from src.learning.negative_pattern_store import get_negative_pattern_store
    
    store = get_negative_pattern_store()
    print(f"Store connected: {store._neo4j_available}")
    
    if store._neo4j_available:
        print("\n--- Checking Patterns for 'Cart' ---")
        patterns = store.get_patterns_for_entity("Cart", min_occurrences=1)
        print(f"Found {len(patterns)} patterns for Cart (min_occurrences=1)")
        for p in patterns:
            print(f"  - {p.pattern_id}: {p.exception_class} on {p.field_pattern} (count={p.occurrence_count})")
            
        print("\n--- Checking Patterns for 'Cart' (default min=2) ---")
        patterns_default = store.get_patterns_for_entity("Cart")
        print(f"Found {len(patterns_default)} patterns for Cart (min_occurrences=2)")
        
        print("\n--- Checking Patterns for 'Product' ---")
        patterns_prod = store.get_patterns_for_entity("Product", min_occurrences=1)
        print(f"Found {len(patterns_prod)} patterns for Product")
        for p in patterns_prod:
            print(f"  - {p.pattern_id}: {p.exception_class} on {p.field_pattern} (count={p.occurrence_count})")

except Exception as e:
    print(f"Error: {e}")
