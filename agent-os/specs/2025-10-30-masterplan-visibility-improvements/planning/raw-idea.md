# Raw Idea: Mejorar visibilidad de generación de MasterPlan en el frontend

**Date**: 2025-10-30

## Title
Mejorar visibilidad de generación de MasterPlan en el frontend

## Description
Implementar mejoras de visibilidad durante la generación de MasterPlan en el frontend, mostrando:
- Progreso en tiempo real con indicadores visuales
- Fases del proceso (Discovery → Parsing → Validation → Saving)
- Estadísticas en tiempo real (tokens, costo, entidades, tareas)
- Manejo explícito de errores
- Resumen final con datos generados

## Context
Currently, the frontend shows only text messages about MasterPlan generation. The backend sends WebSocket events with detailed progress information (discovery_generation_start, masterplan_parsing_complete, masterplan_saving_start, etc.) but the UI doesn't fully utilize this data.

## Current Situation
- Backend WebSocket events are available with rich data
- Frontend only displays basic text messages
- No visual progress indicators
- Limited real-time feedback during generation
- No structured error handling or final summary

## Desired Outcome
Enhanced user experience during MasterPlan generation with:
- Clear visual progress tracking
- Real-time statistics and metrics
- Phase-by-phase visibility
- Comprehensive error handling
- Professional final summary with generated data

## Technical Scope
- Frontend WebSocket event handling improvements
- UI components for progress visualization
- State management for generation phases
- Error handling and display
- Statistics aggregation and display
