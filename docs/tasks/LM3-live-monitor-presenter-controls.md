# LM.3 — Live Monitor: controles de presentador (Fase 3/3)

**Notion:** ninguna todavía. Fuente de verdad: [`docs/design/live-monitor-panel.md`](../design/live-monitor-panel.md).
**Fase:** Live Monitor · Fase 3 de 3 (Pulido para presentador) | **Scope:** DEMO | **Prioridad:** P2 Media | **Estimación:** S (½ día)

> Lee `CLAUDE.md` completo y `docs/tasks/README.md` antes de empezar. Lee `docs/design/live-monitor-panel.md` completo.

## Estado de dependencias

- **LM.1 (MVP funcional):** bloqueador directo — estos controles gobiernan el replay que LM.1 construye.
- **LM.2 (vista de detalle):** no es un bloqueador estricto, pero es lógico tenerla ya para probar los controles contra el flujo completo.

## 🎯 Objetivo

Dar a quien presenta el demo control manual sobre el ritmo del replay — no dejarlo correr a velocidad fija — y la posibilidad de elegir qué narrativa mostrar (proceso estable, drift, salto tras evento, alta varianza, outlier NOK), reutilizando los 5 escenarios que el generador de seed ya define.

## 📋 Contexto

Esta es la fase de "experiencia de pitch", no de funcionalidad core — el panel ya es completamente demostrable sin esto (LM.1+LM.2). El valor aquí es que el presentador no dependa de que el replay "llegue solo" al momento dramático (un NOK, un drift claro) durante una demo en vivo frente al cliente.

## ✅ Alcance

- Backend (`live_replay_service.py` de LM.1): soporte para pausar/reanudar una sesión de replay activa, cambiar su velocidad (1x/5x/20x) sin reiniciarla, y arrancar una sesión nueva filtrada por escenario (`stable_capable`, `slow_drift`, `shift_after_event`, `high_variance`, más el patrón NOK — mismos 5 de `seed/config/scenarios.yaml` y `seed/generators/measurements.py`). Añade el/los mensajes WS necesarios para estos comandos (ej. `{"type": "control", "action": "pause" | "resume" | "set_speed" | "set_scenario", ...}`) o, si es más simple, un endpoint REST corto (`POST /live-monitor/sessions/{id}/control`) que el backend traduce a comandos sobre la sesión de replay activa — decide cuál encaja mejor con lo que LM.1 realmente construyó y documenta la elección en el PR.
- Frontend (`LiveMonitorPage.tsx`): barra de controles con play/pause, selector de velocidad, selector de escenario. Solo visible/habilitada para roles con permiso de control (reusa el mismo `live_monitor.stream` de LM.1, o si se decide que controlar es una acción distinta de solo ver, un token `live_monitor.stream` `control` adicional — documenta la decisión).

## 🚫 Fuera de alcance

Cualquier cosa que no sea LM.1/LM.2 ya cubrieron; no se agregan escenarios nuevos más allá de los 5 ya definidos en el seed.

## 📁 Archivos esperados

- Cambios en `backend/app/services/live_replay_service.py` y `backend/app/api/v1/live_monitor.py` (de LM.1).
- Cambios en `frontend/src/features/live-monitor/LiveMonitorPage.tsx` (de LM.1/LM.2) + nuevo componente de controles si se justifica (ej. `LiveMonitorControls.tsx`).

## Referencias obligatorias

- `docs/design/live-monitor-panel.md`.
- `seed/config/scenarios.yaml` y `seed/generators/measurements.py` — los 5 escenarios reales a exponer, no inventar nuevos.
- El resultado de LM.1 (forma del replay service y del WS/API) y LM.2 (si ya existe, para no romper el panel de detalle al cambiar de escenario).

## ✔️ Criterios de aceptación

- [ ] Pausar/reanudar no pierde ni duplica puntos ya emitidos (test).
- [ ] Cambiar de escenario reinicia limpiamente la sesión de replay (sin mezclar puntos de dos escenarios distintos en el mismo grid).
- [ ] Los controles respetan RBAC — un rol sin permiso de control no puede pausar/cambiar velocidad/escenario ajeno (test, aunque sí pueda seguir viendo el stream si `read` alcanza para eso).

## 🧪 Testing

Backend: integración (pausa/reanuda/cambia velocidad sobre una sesión real, sin pérdida de datos). Frontend: RTL de los controles, incluida la visibilidad condicional por rol.

## Al terminar

Sigue el flujo estándar de `docs/tasks/README.md` (branch `feat/lm-3-live-monitor-controls`, apilada sobre LM.1/LM.2 según lo que esté mergeado). Commit, push, PR — **nunca mergear sin autorización explícita del usuario**. Con esto, las 3 fases de Live Monitor quedan completas.
