# PatternBasedValidator - User Guide

## Overview

El `PatternBasedValidator` es un componente de Fase 1 del sistema de validación que extrae automáticamente reglas de validación a partir de patrones predefinidos. Mejora la cobertura de validación en +30-40% (de 22 a 45-50 validaciones) mediante matching inteligente de patrones.

## Arquitectura

```
Specification (Entities + Endpoints)
         |
         v
PatternBasedValidator
         |
         +---> Type Patterns (UUID, String, Integer, DateTime, Boolean, Decimal)
         +---> Semantic Patterns (email, password, phone, status, quantity, price)
         +---> Constraint Patterns (unique, not_null, foreign_key)
         +---> Endpoint Patterns (POST, GET, PUT, DELETE)
         +---> Domain Patterns (e-commerce, inventory, user-management, workflow)
         +---> Implicit Patterns (created_at, updated_at, is_active, version)
         |
         v
ValidationRule[] (deduplicated)
```

## Uso Básico

### Ejemplo Simple

```python
from src.services.pattern_validator import PatternBasedValidator
from src.cognitive.ir.domain_model import Entity, Attribute, DataType
from src.cognitive.ir.api_model import Endpoint, HttpMethod

# Crear validador
validator = PatternBasedValidator()

# Definir entidades
user = Entity(
    name="User",
    attributes=[
        Attribute(name="id", data_type=DataType.UUID, is_primary_key=True, is_nullable=False),
        Attribute(name="email", data_type=DataType.STRING, is_unique=True, is_nullable=False),
        Attribute(name="password", data_type=DataType.STRING, is_nullable=False),
    ]
)

# Definir endpoints
endpoints = [
    Endpoint(path="/api/v1/users", method=HttpMethod.POST, operation_id="create_user")
]

# Extraer validaciones
rules = validator.extract_patterns([user], endpoints)

# Resultado: ~15 ValidationRule objects
for rule in rules:
    print(f"{rule.entity}.{rule.attribute}: {rule.type.value} - {rule.error_message}")
```

### Función de Conveniencia

```python
from src.services.pattern_validator import extract_validation_patterns

# Forma rápida sin instanciar clase
rules = extract_validation_patterns(entities, endpoints)
```

## Patrones Soportados

### 1. Type Patterns (Basado en Tipo de Dato)

Aplica validaciones según el tipo de campo:

- **UUID**: Formato RFC 4122, presencia
- **String**: No vacío, rango de longitud, presencia
- **Integer**: Rango numérico, presencia
- **Decimal**: Precisión decimal, presencia
- **DateTime**: Formato ISO 8601, presencia
- **Boolean**: Formato booleano, presencia

**Ejemplo**:
```python
Attribute(name="id", data_type=DataType.UUID, is_nullable=False)
→ ValidationRule(type=FORMAT, condition="uuid")
→ ValidationRule(type=PRESENCE)
```

### 2. Semantic Patterns (Basado en Nombre de Campo)

Detecta semántica por nombre usando regex:

- **email**: Formato email, unicidad, presencia
- **password**: Complejidad fuerte, longitud 8-128, presencia
- **phone**: Formato teléfono, presencia
- **url**: Formato URL válido
- **status**: Enum, presencia, transiciones
- **quantity**: No negativo, stock constraint
- **price**: Positivo, formato decimal
- **id**: Unicidad, presencia

**Ejemplo**:
```python
Attribute(name="email", data_type=DataType.STRING, is_unique=True)
→ ValidationRule(type=FORMAT, condition="email", message="email must be a valid email address")
→ ValidationRule(type=UNIQUENESS, message="email must be unique")
→ ValidationRule(type=PRESENCE, message="email is required")
```

### 3. Constraint Patterns (Basado en Restricciones)

Aplica validaciones según constraints del campo:

- **unique**: Unicidad
- **not_null**: Presencia obligatoria
- **foreign_key**: Referencia válida a entidad relacionada
- **check**: Violación de constraint

**Ejemplo**:
```python
Attribute(name="user_id", data_type=DataType.UUID, is_nullable=False)
→ ValidationRule(type=RELATIONSHIP, message="Invalid User reference")
→ ValidationRule(type=PRESENCE, message="user_id is required")
```

### 4. Endpoint Patterns (Basado en HTTP Method)

Valida endpoints por método HTTP:

- **POST**: Body obligatorio, JSON válido
- **GET**: ID parameter presencia, formato UUID
- **PUT**: ID parameter, body obligatorio
- **DELETE**: ID parameter presencia, formato UUID

**Ejemplo**:
```python
Endpoint(path="/api/v1/users/{id}", method=HttpMethod.GET)
→ ValidationRule(attribute="id", type=PRESENCE, message="ID parameter is required")
→ ValidationRule(attribute="id", type=FORMAT, condition="uuid")
```

### 5. Domain Patterns (Basado en Dominio de Negocio)

Detecta dominio por entidades presentes y aplica reglas específicas:

- **e-commerce**: SKU único, price positivo, quantity stock, status transitions
- **inventory**: Stock no negativo, reorder point, movement type
- **user-management**: Email único/formato, password fuerte, status transitions
- **workflow**: Estado válido, assignee relationship, due_date presencia

**Ejemplo**:
```python
# Dominio detectado: e-commerce (Product, Order, OrderItem presentes)
Attribute(name="sku", entity="Product")
→ ValidationRule(type=UNIQUENESS, message="Product SKU must be unique")

Attribute(name="quantity", entity="OrderItem")
→ ValidationRule(type=STOCK_CONSTRAINT, message="Quantity cannot exceed available stock")
```

### 6. Implicit Patterns (Convenciones Comunes)

Infiere validaciones de nombres convencionales:

- **created_at**: ISO 8601 datetime
- **updated_at**: ISO 8601 datetime
- **deleted_at**: ISO 8601 datetime o null
- **version**: Integer no negativo
- **is_active**: Boolean
- **is_deleted**: Boolean

**Ejemplo**:
```python
Attribute(name="created_at", data_type=DataType.DATETIME)
→ ValidationRule(type=FORMAT, condition="iso8601_datetime")
```

## Deduplicación

El validador elimina reglas duplicadas basándose en la clave `(entity, attribute, type)`:

```python
# Dos patterns diferentes generan la misma validación:
Type Pattern: User.email → FORMAT (confidence=0.85)
Semantic Pattern: User.email → FORMAT (confidence=0.95)

# Resultado: Se mantiene la de mayor confianza
→ ValidationRule(entity="User", attribute="email", type=FORMAT) # confidence=0.95
```

## Scoring de Confianza

Cada regla tiene un score de confianza:

- **0.95**: Alta confianza (UUID format, email uniqueness, primary keys)
- **0.90**: Confianza media-alta (password complexity, datetime format)
- **0.85**: Confianza media (status transitions, domain patterns)
- **0.80**: Confianza base

La deduplicación usa este score para resolver conflictos.

## Performance

- **Velocidad**: <1 segundo para procesar 60+ campos
- **Escalabilidad**: Lineal con número de campos
- **Memoria**: Mínima, solo patrones YAML cargados una vez

## Integración con Pipeline

```python
from src.cognitive.ir.ir_builder import IRBuilder
from src.services.pattern_validator import PatternBasedValidator

# 1. Construir ApplicationIR
ir_builder = IRBuilder()
app_ir = ir_builder.build_from_prd(prd_text)

# 2. Extraer patrones de validación
validator = PatternBasedValidator()
pattern_rules = validator.extract_patterns(
    entities=app_ir.domain_model.entities,
    endpoints=app_ir.api_model.endpoints
)

# 3. Agregar a ValidationModelIR
app_ir.validation_model.rules.extend(pattern_rules)

# 4. Generar código
# ... code generation con rules completos
```

## Extensión de Patrones

Los patrones se definen en `src/services/validation_patterns.yaml`. Para agregar nuevos patrones:

### Agregar Semantic Pattern

```yaml
semantic_patterns:
  zip_code:
    pattern: "(?:zip|postal_code|zipcode)"
    description: "Zip/postal code field"
    validations:
      - type: "FORMAT"
        condition: "zip_code"
        error_message: "{attribute} must be a valid zip code"
        confidence: 0.90
```

### Agregar Domain Pattern

```yaml
domain_patterns:
  healthcare:
    entities:
      - Patient
      - Appointment
      - MedicalRecord
    patterns:
      - field: "patient_id"
        type: "RELATIONSHIP"
        error_message: "Invalid patient reference"
        confidence: 0.95
```

## Testing

### Test Simple

```python
def test_email_validation():
    validator = PatternBasedValidator()
    entity = Entity(
        name="User",
        attributes=[
            Attribute(name="email", data_type=DataType.STRING, is_unique=True, is_nullable=False)
        ]
    )

    rules = validator.extract_patterns([entity], [])

    # Debe detectar FORMAT, UNIQUENESS, PRESENCE
    assert len(rules) >= 3
    types = {r.type for r in rules if r.attribute == "email"}
    assert ValidationType.FORMAT in types
    assert ValidationType.UNIQUENESS in types
    assert ValidationType.PRESENCE in types
```

### Ejecutar Tests

```bash
# Tests unitarios
pytest tests/services/test_pattern_validator.py -v

# Test de integración
python scripts/test_pattern_validator.py
```

## Troubleshooting

### Problema: No se detectan patrones semánticos

**Solución**: Verificar que el nombre del campo coincida con el regex del patrón:

```python
# No funciona: "user_mail" (no coincide con "email|mail|e_mail")
Attribute(name="user_mail")

# Funciona: "email" o "mail" o "e_mail"
Attribute(name="email")
```

### Problema: Demasiadas validaciones duplicadas

**Solución**: La deduplicación automática maneja esto. Si persiste, revisar logs:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
validator = PatternBasedValidator()
# Verás mensajes de deduplicación en logs
```

### Problema: Patrones de dominio no detectados

**Solución**: Asegurar que al menos 50% de las entidades del dominio estén presentes:

```python
# E-commerce requiere: Product, Order, OrderItem
# Si solo tienes Product, no se detectará el dominio
# Solución: Agregar Order o ajustar threshold en _detect_domains()
```

## Métricas de Cobertura

### Baseline (Sin Pattern Validator)

- Validaciones extraídas: ~22
- Fuente: Reglas de negocio explícitas en PRD

### Con Pattern Validator (Fase 1)

- Validaciones extraídas: ~45-85 (según complejidad de spec)
- Mejora: +30-40% a +286% sobre baseline
- Breakdown típico:
  - Type patterns: ~35-40%
  - Semantic patterns: ~30-35%
  - Constraint patterns: ~15-20%
  - Endpoint patterns: ~5-10%
  - Domain patterns: ~5%
  - Implicit patterns: ~5%

## Roadmap

### Fase 2: LLM-Based Extraction (Futuro)

- Business logic inferencing
- Cross-entity validations
- Complex workflow rules
- Natural language rule parsing

### Fase 3: Hybrid Approach (Futuro)

- Pattern matching (Phase 1) como baseline
- LLM enrichment (Phase 2) para casos complejos
- Confidence scoring combinado
- Máxima cobertura con eficiencia óptima

## Referencias

- Código: `src/services/pattern_validator.py`
- Patrones: `src/services/validation_patterns.yaml`
- Tests: `tests/services/test_pattern_validator.py`
- Script demo: `scripts/test_pattern_validator.py`
- Modelo IR: `src/cognitive/ir/validation_model.py`
