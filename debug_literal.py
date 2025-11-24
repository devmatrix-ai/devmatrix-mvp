import re

def test_literal_replacement():
    # Case: Existing Literal needs update
    # Input: payment_status: Literal["pending", "failed"] = "pending"
    # Goal: Update to Literal["pending", "simulated_ok", "failed"]
    
    field_name = "payment_status"
    new_values = ['pending', 'simulated_ok', 'failed']
    values_quoted = ', '.join([f'"{v}"' for v in new_values])
    literal_type = f'Literal[{values_quoted}]'
    
    source_code = """
class OrderSchema(BaseModel):
    id: str
    payment_status: Literal["pending", "failed"] = "pending"
    other_field: int
"""
    print(f"Original Code:\n{source_code}")
    
    # Current logic (fails)
    field_type_pattern = rf'(\s+{field_name}):\s*(?:Optional\[)?str(?:\])?\s*='
    if re.search(field_type_pattern, source_code, re.MULTILINE):
        print("Matched str pattern (Unexpected)")
    else:
        print("Did not match str pattern (Expected failure of current logic)")

    # New logic
    # Match existing Literal: payment_status: Literal[...] =
    literal_pattern = rf'(\s+{field_name}):\s*(?:typing\.)?Literal\[.*?\]\s*='
    
    def replace_with_literal(match):
        indent_and_name = match.group(1)
        return f'{indent_and_name}: {literal_type} ='

    if re.search(literal_pattern, source_code, re.MULTILINE | re.DOTALL):
        new_code = re.sub(literal_pattern, replace_with_literal, source_code, flags=re.MULTILINE | re.DOTALL)
        print(f"\nNew Code:\n{new_code}")
    else:
        print("\nFailed to match Literal pattern")

if __name__ == "__main__":
    test_literal_replacement()
