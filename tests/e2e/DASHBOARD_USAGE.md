# 📈 Cómo Usar el Dashboard E2E

## 🚀 Guía Rápida

### Opción 1: Dashboard en Modo Mock (Demo)

```bash
# Ejecutar dashboard con datos simulados (perfecto para testing)
python3 tests/e2e/progress_dashboard.py --mock --duration 60
```

**Qué verás:**
- Progreso simulado de todas las fases del pipeline
- Checkpoints completándose en tiempo real
- Métricas actualizándose (patterns, CPU, memoria)
- Errores simulados y recuperaciones

**Duración:** Especificás con `--duration` (en segundos)

---

### Opción 2: Dashboard + Test E2E Real

**Terminal 1 - Ejecutar Dashboard:**
```bash
python3 tests/e2e/progress_dashboard.py --mock --duration 300
```

**Terminal 2 - Ejecutar Test E2E:**
```bash
python3 tests/e2e/simple_e2e_test.py
```

**Resultado:** Dashboard muestra progreso simulado mientras el test real corre en paralelo

---

### Opción 3: Ver Métricas de Tests Anteriores

```bash
# Ver todas las métricas guardadas
ls -lh tests/e2e/metrics/

# Ver métricas en formato JSON bonito
jq . tests/e2e/metrics/e2e_metrics_demo_*.json

# Ver resumen específico
python3 -c "
import json
with open('tests/e2e/metrics/e2e_metrics_demo_1763562824.json') as f:
    m = json.load(f)
    print(f\"Status: {m['overall_status']}\")
    print(f\"Duration: {m['total_duration_ms']/1000/60:.1f} min\")
    print(f\"Pattern Reuse: {m['pattern_reuse_rate']:.1%}\")
"
```

---

## 📊 Interpretando el Dashboard

### Vista del Dashboard
```
╔══════════════════════════════════════════════════════════════════╗
║           🚀 E2E PIPELINE EXECUTION DASHBOARD                     ║
╠══════════════════════════════════════════════════════════════════╣
║ Pipeline: pipeline_12345_1732023045           ← ID del pipeline   ║
║ Spec: simple_crud_api.md                      ← Spec en ejecución║
║ Elapsed: 4m 32s                               ← Tiempo transcurrido║
╠══════════════════════════════════════════════════════════════════╣
║ Phase Progress                                                    ║
║ ─────────────────────────────────────────────────────────────    ║
║ Spec Ingestion      ✅ ████████████████████ 100% (4/4) 2.3s     ║
║                     ↑   ↑                    ↑    ↑     ↑        ║
║                  Status Barra de progreso  % Checks Tiempo       ║
╠══════════════════════════════════════════════════════════════════╣
║ Real-time Metrics                                                 ║
║ ─────────────────────────────────────────────────────────────    ║
║ 📊 Pattern Bank        │ ⚡ Performance                           ║
║   Patterns: 25         │   Peak Memory: 823.4 MB                 ║
║   Reuse Rate: 42.3%    │   Peak CPU: 65.2%                       ║
╚══════════════════════════════════════════════════════════════════╝
```

### Símbolos de Estado
- ✅ **Completado** - Fase terminada exitosamente
- 🔄 **En Progreso** - Fase ejecutándose ahora
- ⏳ **Pendiente** - Fase aún no iniciada
- ❌ **Fallido** - Fase falló
- 🔁 **Reintentando** - Recuperándose de error

### Barra de Progreso
- `████████` Verde = >75% completado
- `████████` Amarillo = 50-75% completado
- `████████` Rojo = <50% completado
- `░░░░░░░░` Gris = No iniciado

---

## 🎯 Flujo Completo Recomendado

### Paso 1: Ver Dashboard Demo
```bash
cd /home/kwar/code/agentic-ai
python3 tests/e2e/progress_dashboard.py --mock --duration 90
```
**Observá:** Cómo progresan las 9 fases con sus 44 checkpoints

### Paso 2: Ejecutar Test E2E Real
```bash
python3 tests/e2e/simple_e2e_test.py
```
**Observá:**
- Progreso fase por fase en la consola
- Checkpoints completándose
- Ejecución de 12 atoms en 3 waves
- Métricas finales

### Paso 3: Analizar Métricas
```bash
# Ver archivo de métricas generado
cat tests/e2e/metrics/e2e_metrics_demo_*.json | jq .

# O mejor aún, ver el resumen que imprime el test al final
```

---

## 📋 Comandos Útiles

### Ver Dashboard con Diferentes Duraciones
```bash
# Demo corta (30 segundos)
python3 tests/e2e/progress_dashboard.py --mock --duration 30

# Demo media (2 minutos)
python3 tests/e2e/progress_dashboard.py --mock --duration 120

# Demo larga (5 minutos)
python3 tests/e2e/progress_dashboard.py --mock --duration 300
```

### Ejecutar Test E2E con Variaciones
```bash
# Test simple y rápido
python3 tests/e2e/simple_e2e_test.py

# Test con más delays (para ver el progreso mejor)
# (editar los asyncio.sleep en el archivo para hacerlos más largos)
```

### Crear Directorios si No Existen
```bash
mkdir -p tests/e2e/metrics tests/e2e/logs tests/e2e/results
```

---

## 🔍 Métricas Clave a Observar

### Durante la Ejecución (en consola):
```
📍 Phase Started: wave_execution
  ✓ Checkpoint: CP-6.1: Wave 0 started (1/5)
  🌊 Executing Wave 0 (4 atoms)...
    ✓ Atom 1 completed
    ✓ Atom 2 completed
```

### En el Dashboard:
- **Progreso General**: Barra en la parte inferior
- **Pattern Reuse Rate**: Debe ser >40% para apps bien diseñadas
- **Test Coverage**: Debe ser >80% para calidad
- **Recovery Rate**: Debe ser >90% para confiabilidad

### En las Métricas JSON:
```json
{
  "overall_status": "success",      ← Debe ser "success"
  "total_duration_ms": 99257,       ← <360000 para app simple (6min)
  "pattern_reuse_rate": 0.667,      ← >0.40 es bueno
  "test_coverage": 0.87,            ← >0.80 es bueno
  "recovery_success_rate": 1.0      ← 1.0 es perfecto
}
```

---

## 🎬 Ejemplo Completo de Sesión

```bash
# Terminal 1: Iniciar dashboard
cd /home/kwar/code/agentic-ai
python3 tests/e2e/progress_dashboard.py --mock --duration 120

# Observás el dashboard arrancando y mostrando las fases...

# Terminal 2: (en otra terminal) Ejecutar test E2E
cd /home/kwar/code/agentic-ai
python3 tests/e2e/simple_e2e_test.py

# El test corre mostrando progreso:
# ✅ Phase Completed: spec_ingestion (1502ms)
# ✅ Phase Completed: requirements_analysis (8005ms)
# ...
# === Pipeline Execution Summary ===
# Status: SUCCESS
# Duration: 1.7 minutes

# Terminal 3: (opcional) Ver métricas en tiempo real
watch -n 1 'ls -lh tests/e2e/metrics/'

# Al final, analizar métricas
jq '.phases | keys[]' tests/e2e/metrics/e2e_metrics_demo_*.json
```

---

## ⚙️ Troubleshooting

### Dashboard no arranca
```bash
# Verificar que rich esté instalado
pip install rich

# Verificar que el script tiene permisos
chmod +x tests/e2e/progress_dashboard.py
```

### No se ven las métricas
```bash
# Crear directorio si no existe
mkdir -p tests/e2e/metrics

# Verificar que se generó el archivo
ls -lh tests/e2e/metrics/
```

### Dashboard se cierra inmediatamente
- Verificá el parámetro `--duration` (debe ser >10 segundos)
- Verificá que no haya errores de sintaxis con `python3 -m py_compile tests/e2e/progress_dashboard.py`

---

## 📚 Archivos Importantes

```
tests/e2e/
├── progress_dashboard.py          ← Dashboard visual en tiempo real
├── simple_e2e_test.py             ← Test E2E funcional
├── metrics_framework.py           ← Framework de métricas
├── DASHBOARD_USAGE.md             ← Este archivo
├── E2E_TEST_PLAN_SUMMARY.md       ← Plan completo
├── metrics/                        ← Métricas guardadas (JSON)
├── logs/                           ← Logs de ejecución
└── results/                        ← Reportes generados
```

---

## 🎯 Próximos Pasos

1. **Familiarizarte con el dashboard:** Correr en modo mock varias veces
2. **Ejecutar test E2E real:** Ver métricas reales del pipeline
3. **Analizar métricas:** Entender qué significa cada métrica
4. **Integrar con pipeline real:** Conectar a tu pipeline cognitivo existente

---

*Última actualización: 2025-11-19*
*Versión: 1.0*