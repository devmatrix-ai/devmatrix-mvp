import re

def test_regex():
    # Case 1: Duplicate default=None
    # Original: is_active: Optional[bool] = Field(default=None)
    # Goal: Add default=True -> is_active: Optional[bool] = Field(default=True)
    
    case1_input = "is_active: Optional[bool] = Field(default=None)"
    constraint_type = "default"
    constraint_value = True
    
    print(f"--- Case 1: Replace default=None with default=True ---")
    print(f"Input: {case1_input}")
    
    field_pattern = r'(\s+is_active:\s*[\w\[\]]+)\s*=\s*Field\((.*?)\)'
    match = re.search(field_pattern, "    " + case1_input)
    
    if match:
        existing_args = match.group(2)
        print(f"Existing args: '{existing_args}'")
        
        # The regex from code_repair_agent.py
        if constraint_type in ('default', 'default_factory'):
             # Remove any existing default= or default_factory= (including quotes)
             existing_args = re.sub(r',?\s*default(_factory)?\s*=\s*(?:r?[\"\'](?:[^\"\'\\]|\.)*[\"\']|\d+(?:\.\d+)?|None|True|False|[a-zA-Z_][a-zA-Z0-9_]*)\s*,?', '', existing_args)
             # Clean up any double commas or leading/trailing commas
             existing_args = re.sub(r',\s*,', ',', existing_args).strip(', ')
        
        print(f"Args after removal: '{existing_args}'")
        
        if existing_args.strip() and existing_args.strip() != '...':
            existing_args += f', {constraint_type}={repr(constraint_value)}'
        elif existing_args.strip() == '...':
            existing_args = f'..., {constraint_type}={repr(constraint_value)}'
        else:
            existing_args = f'{constraint_type}={repr(constraint_value)}'
            
        print(f"Final args: '{existing_args}'")
        print(f"Result: Field({existing_args})")
        
    else:
        print("No match found")

    # Case 2: Malformed .utcnow
    # Input: registration_date: Optional[datetime] = Field(default_factory=datetime.utcnow)
    # Goal: Add default_factory='datetime.utcnow' (or similar)
    # The error was: Field(.utcnow, default_factory='datetime.utcnow')
    
    print(f"\n--- Case 2: Replace default_factory=datetime.utcnow ---")
    case2_input = "registration_date: Optional[datetime] = Field(default_factory=datetime.utcnow)"
    constraint_type = "default_factory"
    constraint_value = "datetime.utcnow"
    
    print(f"Input: {case2_input}")
    
    field_pattern = r'(\s+registration_date:\s*[\w\[\]]+)\s*=\s*Field\((.*?)\)'
    match = re.search(field_pattern, "    " + case2_input)
    
    if match:
        existing_args = match.group(2)
        print(f"Existing args: '{existing_args}'")
        
        if constraint_type in ('default', 'default_factory'):
             # Remove any existing default= or default_factory=
             # The regex needs to handle unquoted datetime.utcnow
             existing_args = re.sub(r',?\s*default(_factory)?\s*=\s*(?:r?[\"\'](?:[^\"\'\\]|\.)*[\"\']|\d+(?:\.\d+)?|None|True|False|[a-zA-Z_][a-zA-Z0-9_.]*)\s*,?', '', existing_args)
             existing_args = re.sub(r',\s*,', ',', existing_args).strip(', ')
        
        print(f"Args after removal: '{existing_args}'")
        
        if existing_args.strip():
             existing_args += f', {constraint_type}={constraint_value}' # No repr for factory if we want it raw? Or string?
             # In the agent code:
             # if constraint_type == 'default_factory':
             #    existing_args += f', {constraint_type}={constraint_value}'
        else:
             existing_args = f'{constraint_type}={constraint_value}'

        print(f"Final args: '{existing_args}'")
        print(f"Result: Field({existing_args})")

if __name__ == "__main__":
    test_regex()
