# Spec Translator Architecture

## CRITICAL PRINCIPLE

**EL SPEC TRANSLATOR SOLO TRADUCE. NUNCA MODIFICA EL CONTENIDO.**

```
❌ PROHIBIDO: Cambiar estructura, agregar campos, modificar lógica
✅ PERMITIDO: Traducir texto descriptivo de cualquier idioma a inglés
```

---

## Problem Statement

El pipeline espera specs en inglés para:
1. YAML parsing consistente (sin problemas de caracteres especiales)
2. Code generation (templates en inglés)
3. LLM prompts (lenguaje consistente)

Specs en español/otros idiomas causan:
- Errores de parsing YAML (block scalars con unicode)
- Inconsistencias en generación de código
- Confusión en prompts de LLM

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRE-PIPELINE TRANSLATION                      │
│                                                                  │
│   Spec (cualquier idioma)                                        │
│          │                                                       │
│          ▼                                                       │
│   ┌──────────────────┐                                          │
│   │  SpecTranslator  │  ◀── SOLO TRADUCE                        │
│   │                  │      NO MODIFICA ESTRUCTURA              │
│   │  - detect_lang() │      NO AGREGA CAMPOS                    │
│   │  - translate()   │      NO CAMBIA LÓGICA                    │
│   └────────┬─────────┘                                          │
│            │                                                     │
│            ▼                                                     │
│   Spec (inglés, MISMA estructura)                               │
│            │                                                     │
│            ▼                                                     │
│   ┌──────────────────┐                                          │
│   │  Pipeline        │  ← Recibe spec traducida                 │
│   │  Ingestion       │                                          │
│   └──────────────────┘                                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Translation Rules

### SOLO SE TRADUCE

| Elemento | Traducir | Ejemplo |
|----------|----------|---------|
| Descripciones | ✅ SÍ | "Producto activo" → "Active product" |
| Comentarios | ✅ SÍ | "# Entidad principal" → "# Main entity" |
| Documentación | ✅ SÍ | "Una guía amigable" → "A friendly guide" |

### NUNCA SE TRADUCE/MODIFICA

| Elemento | Modificar | Razón |
|----------|-----------|-------|
| Nombres de campos | ❌ NO | `nombre` queda `nombre` (código depende de esto) |
| Paths de endpoints | ❌ NO | `/productos` queda `/productos` |
| Tipos de datos | ❌ NO | `string`, `integer` sin cambios |
| Estructuras | ❌ NO | Jerarquía YAML/JSON intacta |
| Ejemplos de código | ❌ NO | Código es código |
| Identificadores | ❌ NO | IDs, nombres técnicos intactos |

---

## Implementation

### Archivo: `src/services/spec_translator.py`

```python
class SpecTranslator:
    """
    Translates specs to English before pipeline ingestion.

    CRITICAL: This service ONLY translates descriptive text.
    It NEVER modifies:
    - Field names
    - Endpoint paths
    - Data types
    - Code examples
    - Technical identifiers
    - Document structure
    """
```

### Translation Prompt (CRÍTICO)

```python
TRANSLATION_PROMPT = """You are a technical translator specializing in API specifications.

Translate the following API specification to English. Preserve:
1. All technical terms (API, REST, CRUD, UUID, etc.)
2. The exact structure and formatting (markdown, YAML, etc.)
3. All code examples unchanged
4. All field names and identifiers unchanged

Only translate the descriptive text, comments, and documentation.

IMPORTANT:
- Keep the same file format (markdown stays markdown, YAML stays YAML)
- Preserve all code blocks exactly
- Keep all technical identifiers (field names, endpoint paths, etc.)
- Translate descriptions, comments, and explanations to clear, professional English
"""
```

---

## Usage Flow

### 1. Detection

```python
translator = SpecTranslator()
language, confidence = translator.detect_language(spec_content)
# ("spanish", 0.85)
```

### 2. Translation (si es necesario)

```python
translated, was_translated = translator.translate_if_needed_sync(
    content=spec_content,
    spec_path="specs/ecommerce.md"
)
# (english_content, True)
```

### 3. Pipeline Ingestion

```python
# La spec traducida se pasa al pipeline
# MISMA estructura, SOLO texto traducido
pipeline.ingest(translated)
```

---

## Integration Point

### E2E Pipeline (`tests/e2e/real_e2e_full_pipeline.py`)

```python
# ANTES de ingestion
from src.services.spec_translator import translate_spec_if_needed

async def run_pipeline(spec_path: str):
    # 1. Leer spec original
    with open(spec_path) as f:
        spec_content = f.read()

    # 2. TRADUCIR (solo si es necesario)
    translated_content, was_translated = translate_spec_if_needed(spec_content, spec_path)

    if was_translated:
        logger.info(f"📝 Spec translated from non-English to English")

    # 3. Ahora sí, ingestar en pipeline
    # La spec tiene MISMA estructura pero texto en inglés
    await pipeline.process(translated_content)
```

---

## Language Detection

### Idiomas Soportados

| Idioma | Patrones | Confianza |
|--------|----------|-----------|
| Español | `qué`, `cómo`, `entidades`, `obligatorio` | 0.85+ |
| Portugués | `especificação`, `obrigatório` | 0.80+ |
| Francés | `spécification`, `obligatoire` | 0.80+ |
| Alemán | `Spezifikation`, `erforderlich` | 0.80+ |

### Threshold de Traducción

```python
# Solo traduce si NO es inglés con confianza > 0.7
if language == "english" and confidence > 0.7:
    return (content, False)  # No traducir
else:
    return (translate(content), True)  # Traducir
```

---

## Caching

Las traducciones se cachean para evitar re-procesar:

```
.devmatrix/translations/
├── a1b2c3d4e5f6.txt  # Hash del contenido original
├── f7g8h9i0j1k2.txt  # Otra traducción cacheada
└── ...
```

- **Key**: SHA256 del contenido original (16 chars)
- **Value**: Contenido traducido
- **Beneficio**: Specs repetidas no requieren nueva llamada LLM

---

## Cost Considerations

| Modelo | Costo Aprox | Uso |
|--------|-------------|-----|
| claude-sonnet-4-20250514 | ~$0.003/1K input | Default (balance costo/calidad) |

- Típica spec: 2-5K tokens input, 2-5K output
- Costo por traducción: ~$0.03-0.05
- Con cache: Costo único por spec

---

## Validation Checklist

Antes de integrar SpecTranslator, verificar:

- [ ] ¿Solo traduce texto descriptivo? ✅
- [ ] ¿Preserva nombres de campos? ✅
- [ ] ¿Preserva paths de endpoints? ✅
- [ ] ¿Preserva estructura YAML/JSON? ✅
- [ ] ¿Preserva código de ejemplo? ✅
- [ ] ¿Cache funciona? ✅

---

## Error Handling

```python
try:
    translated = await translate(content)
except Exception as e:
    logger.error(f"Translation failed: {e}")
    # FALLBACK: Usar contenido original
    # Mejor continuar con spec no traducida que fallar
    return content
```

---

**Documento creado**: 2025-11-29
**Propósito**: Documentar arquitectura de traducción de specs pre-pipeline
**Principio clave**: SOLO TRADUCE, NUNCA MODIFICA
