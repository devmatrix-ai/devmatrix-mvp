# Hardcoded Domain-Specific Patterns

Este documento lista todos los patterns hardcodeados que violan el principio de **100% domain-agnostic**.

## Principio

DevMatrix es un **Cognitive Compiler**. NUNCA debe "conocer" dominios específicos como ecommerce, healthcare, etc. TODA la información debe derivarse del ApplicationIR en runtime.

---

## ✅ ARREGLADOS

| Archivo | Línea | Pattern | Fix |
|---------|-------|---------|-----|
| `runtime_flow_validator.py` | - | `check_stock_invariant()` | → `check_comparison_constraint()` |
| `golden_path_validator.py` | - | `register_ecommerce_paths()` | → `register_paths_from_ir()` |
| `smoke_repair_orchestrator.py` | 473 | `['stock', 'inventory', ...]` keywords | → Removed, use HTTP status codes |
| `validation_routing_matrix.py` | - | keyword matching | → IR-based detection |
| `causal_chain_builder.py` | 133 | `'stock', 'inventory', 'quantity'` | → IR-based + HTTP status |
| `ir_backpropagation_engine.py` | 166 | `'stock_constraint'` | → generic `'comparison'` |
| `runtime_smoke_validator.py` | 821 | `'quantity', 'stock', 'count'` | → Type-based only |
| `spec_to_application_ir.py` | 1165 | `'stock', 'inventory', 'quantity'` | → Flow type based |
| `invariant_inferencer.py` | 67 | `QUANTITY_FIELDS = {'stock', ...}` | → `NUMERIC_TYPES` |
| `flow_logic_synthesizer.py` | 259 | `'stock'` default | → Empty, parse from condition |
| `flow_logic_synthesizer.py` | 392 | `"Quantity exceeds available stock"` | → IR metadata message |
| `flow_logic_synthesizer.py` | 404 | `'quantity'` default field | → Empty, require from metadata |
| `production_code_generators.py` | 649 | `'stock' in constraint` | → `'comparison_constraint'` |
| `code_generation_service.py` | 5861 | `'quantity', 'stock'` → 100 | → Type-based default |
| `code_generation_service.py` | 4152 | `['checkout', 'pay', ...]` | → Path structure detection |
| `compliance_validator.py` | 2022 | `'stock' and 'decrement'` | → Generic ops detection |
| `seed_data_agent.py` | 324 | `'quantity', 'stock'` | → IR type-based |

---

## ❌ PENDIENTES DE ARREGLAR

### Alta Prioridad (afectan generación de código)

| Archivo | Línea | Pattern | Impacto | Solución Propuesta |
|---------|-------|---------|---------|-------------------|
| `business_logic_extractor.py` | 44 | `'stock', 'inventory', 'quantity', 'balance'` regex | Extracción de lógica | Usar IR constraint types |
| `validation_code_generator.py` | 181 | `'quantity', 1` hardcoded | Generación de validación | Leer de IR |
| `production_code_generators.py` | 533 | `PRICE_PATTERNS = ('price', ...)` | Snapshot detection | Usar IR attribute metadata |
| ~~`production_code_generators.py`~~ | ~~805~~ | ~~`'quantity'` default field~~ | ~~Guard generation~~ | ✅ ARREGLADO en flow_logic_synthesizer |
| `tests_ir_generator.py` | 316-318 | `'price', 'quantity', 'stock'` | Test data generation | Type-based from IR |
| `tests_ir_generator.py` | 622 | `['price', 'quantity', 'stock', ...]` | Numeric field detection | IR type annotation |
| `code_generation_service.py` | 4345-4347 | `'quantity', 'price'` | Line item detection | IR attribute metadata |

### Media Prioridad (afectan clasificación)

| Archivo | Línea | Pattern | Impacto | Solución Propuesta |
|---------|-------|---------|---------|-------------------|
| `smoke_repair_orchestrator.py` | 2136 | `return 'checkout'` | Default operation | Extraer de path/IR |
| `smoke_repair_orchestrator.py` | 2310 | `'checkout', 'process', 'complete'` | Operation detection | Path structure |
| `smoke_repair_orchestrator.py` | 2350 | `payment_data.get('amount')` | Payment validation | IR field detection |
| `compliance_validator.py` | 1949 | `['clear', 'cancel', 'checkout']` | Action detection | Path structure |

### Baja Prioridad (patterns lingüísticos genéricos)

| Archivo | Línea | Pattern | Justificación |
|---------|-------|---------|---------------|
| `anti_pattern_advisor.py` | 256 | `['checkout', 'activate', ...]` | Detecta TIPO de operación (state transition), no dominio |
| `pattern_bank.py` | 781-783 | `'checkout': 'state_transition'` | Mapeo semántico de verbo → pattern type |
| `multi_pass_planner.py` | 1454 | `['checkout', 'submit', 'process', ...]` | Verbos que indican transición de estado |
| `runtime_smoke_validator.py` | 862 | `'quantity': 1` | Test data generation (low risk) |

---

## Notas

1. **Patterns lingüísticos vs domain-specific**: "checkout" como verbo indica "state transition" en cualquier dominio. Esto es pattern recognition lingüístico, no conocimiento de ecommerce.

2. **Traducciones i18n**: `producto → product` en `spec_to_application_ir.py` es internacionalización, no domain logic.

3. **Ejemplos en docstrings**: OK para documentación, no afectan runtime.

4. **`src/models/entities.py`**: `ProductEntity` es un ejemplo/demo, no código usado en generación.

