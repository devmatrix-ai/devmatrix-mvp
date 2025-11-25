"""
Pass 1: Global Context Extraction Prompt

Extracts high-level domain information from full specifications without truncation.
Outputs small JSON (~2-3K tokens) despite large input to avoid truncation risk.
"""


def get_global_context_prompt(spec_content: str) -> str:
    """
    Generate the Pass 1 prompt for global context extraction.

    Args:
        spec_content: Full specification text (NO truncation)

    Returns:
        Formatted prompt for LLM
    """
    return f"""You are an expert API architect. Analyze this specification and extract GLOBAL CONTEXT ONLY.

# FULL Specification
{spec_content}

# Task: Extract Global Context (Pass 1)

Extract ONLY high-level information. Do NOT extract field details (that's Pass 2).

Extract into this JSON structure:

{{
    "domain": "Brief domain description (e.g., 'E-commerce platform for order management')",
    "entities": [
        {{
            "name": "EntityName",
            "description": "Brief entity description (1-2 sentences)",
            "relationships": ["RelatedEntity1", "RelatedEntity2"]
        }}
    ],
    "relationships": [
        {{
            "source": "SourceEntity",
            "target": "TargetEntity",
            "type": "one_to_many|many_to_many|one_to_one|many_to_one",
            "description": "Relationship description"
        }}
    ],
    "business_logic": [
        "Business rule 1 description",
        "Business rule 2 description"
    ],
    "endpoints": [
        {{
            "method": "POST",
            "path": "/resource",
            "entity": "RelatedEntity"
        }}
    ]
}}

CRITICAL INSTRUCTIONS:
1. Extract ALL entities mentioned in the spec (even if briefly described)
2. Include entity relationships in the "relationships" array of each entity
3. Do NOT extract field-level details (names, types, constraints) - that's Pass 2
4. Focus on entity names, descriptions, and how they relate
5. Accept relationship types: one_to_many, many_to_many, one_to_one, many_to_one
6. Return ONLY valid JSON, no markdown formatting

Output must be complete, valid JSON. Better to return fewer entities completely than incomplete JSON."""
