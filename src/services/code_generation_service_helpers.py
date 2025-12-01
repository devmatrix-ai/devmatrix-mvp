    def _extract_entity_name_from_task(self, task: MasterPlanTask) -> Optional[str]:
        """
        Extract entity name from task description/name.
        
        LEARNING_GAPS Phase 1.1 helper.
        
        Examples:
            "Generate Product entity" -> "Product"
            "Create Order model" -> "Order"
            "entities.py for Cart" -> "Cart"
        
        Returns:
            Entity name or None if not detected
        """
        import re
        
        # Try to extract from task name/description
        text = task.name + " " + task.description
        
        # Pattern 1: "Generate/Create/Implement {Entity} entity/model"
        match = re.search(r'(?:generate|create|implement|add)\s+(\w+)\s+(?:entity|model)', text, re.IGNORECASE)
        if match:
            return match.group(1).capitalize()
        
        # Pattern 2: "entities.py for {Entity}"
        match = re.search(r'entities\.py\s+for\s+(\w+)', text, re.IGNORECASE)
        if match:
            return match.group(1).capitalize()
        
        # Pattern 3: "{Entity}Entity class"
        match = re.search(r'(\w+)Entity\s+class', text, re.IGNORECASE)
        if match:
            return match.group(1).capitalize()
        
        return None
    
    def _extract_endpoint_pattern_from_task(self, task: MasterPlanTask) -> Optional[str]:
        """
        Extract endpoint pattern from task description/name.
        
        LEARNING_GAPS Phase 1.1 helper.
        
        Examples:
            "Generate POST /products endpoint" -> "/products"
            "Create GET /orders/{id} route" -> "/orders/{id}"
        
        Returns:
            Endpoint pattern or None if not detected
        """
        import re
        
        text = task.name + " " + task.description
        
        # Pattern 1: "POST /products"
        match = re.search(r'(?:GET|POST|PUT|DELETE|PATCH)\s+(/[\w/{}-]+)', text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Pattern 2: "endpoint for /products"
        match = re.search(r'endpoint\s+for\s+(/[\w/{}-]+)', text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Pattern 3: "route /products"
        match = re.search(r'route\s+(/[\w/{}-]+)', text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        return None
    
    def _extract_schema_name_from_task(self, task: MasterPlanTask) -> Optional[str]:
        """
        Extract schema name from task description/name.
        
        LEARNING_GAPS Phase 1.1 helper.
        
        Examples:
            "Generate ProductCreate schema" -> "ProductCreate"
            "Create OrderResponse Pydantic model" -> "OrderResponse"
        
        Returns:
            Schema name or None if not detected
        """
        import re
        
        text = task.name + " " + task.description
        
        # Pattern 1: "{Schema}Create/Update/Response schema"
        match = re.search(r'(\w+(?:Create|Update|Response|List|Base))\s+schema', text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Pattern 2: "Pydantic {Schema} model"
        match = re.search(r'Pydantic\s+(\w+)\s+model', text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Pattern 3: "schemas.py for {Entity}" -> "{Entity}Create"
        match = re.search(r'schemas\.py\s+for\s+(\w+)', text, re.IGNORECASE)
        if match:
            return f"{match.group(1).capitalize()}Create"
        
        return None

