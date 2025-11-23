import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from parsing.spec_parser import SpecParser

def main():
    parser = SpecParser()
    spec_path = Path("DOCS/mvp/ecommerce-api-spec-human.md")
    
    if not spec_path.exists():
        print(f"Error: {spec_path} not found")
        return

    print(f"Parsing {spec_path}...")
    try:
        result = parser.parse(spec_path)
        print("Parsing successful!")
        print(f"Entities: {len(result.entities)}")
        print(f"Endpoints: {len(result.endpoints)}")
        print(f"Business Logic: {len(result.business_logic)}")
        print(f"Validations: {len(result.validations)}")
        
        print("\nEntities found:")
        for e in result.entities:
            print(f"- {e.name}")
            
        print("\nValidations found:")
        for v in result.validations:
            print(f"- {v.rule}")
            
    except Exception as e:
        print(f"Error parsing spec: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
