# LM.2 — Live Monitor: vista de detalle explicable (Fase 2/3)

**Notion:** ninguna todavía. Fuente de verdad: [`docs/design/live-monitor-panel.md`](../design/live-monitor-panel.md).
**Fase:** Live Monitor · Fase 2 de 3 (Profundidad explicable) | **Scope:** DEMO | **Prioridad:** P2 Media | **Estimación:** S (½ día)

> Lee `CLAUDE.md` completo y `docs/tasks/README.md` antes de empezar. Lee `docs/design/live-monitor-panel.md` completo.

## Estado de dependencias

- **LM.1 (MVP funcional):** bloqueador directo — este es un panel de detalle sobre el grid y el WebSocket que LM.1 construye. Verifica que su PR esté mergeado (o rama sobre la que apilar si no) antes de empezar.

## 🎯 Objetivo

Al hacer click en una `SignalCard` del grid de Live Monitor (LM.1), abrir un panel de detalle con la serie temporal completa (no solo el sparkline), límites de tolerancia y de control superpuestos, y el **rationale explicable** de por qué el motor marca esa característica como OK/NOK o en riesgo — el mismo patrón de evidencia trazable que ya existe en `RecommendationDetailPanel` (F5.9).

## 📋 Contexto

Este panel es el argumento de venta central del feature: no basta con ver que una señal "está en rojo", el presentador debe poder mostrar *la regla exacta* que la marcó así (CLAUDE.md §16 — nunca una salida de caja negra). Reutiliza `frontend/src/components/charts/TrendChart.tsx` (ya existe, usado en `CharacteristicTrendPage`) en vez de construir un gráfico nuevo.

## ✅ Alcance

- `frontend/src/features/live-monitor/SignalDetailPanel.tsx`: se abre (modal o panel lateral, decide el patrón según lo que ya exista en `components/ui/` a esa fecha) al hacer click en una `SignalCard`. Contenido:
  - `TrendChart` con la serie completa reproducida hasta el momento (no solo los últimos N puntos del sparkline), con nominal/límites de tolerancia como líneas de referencia (mismas convenciones que `CharacteristicTrendPage`, F5.7).
  - Límites de control (UCL/LCL del motor SPC, del evento `control_limits_updated` de LM.1) superpuestos.
  - Texto de rationale: `"Cpk 0.91 (motor spc_engine v1) — por debajo del umbral de 1.33"` / `"Dentro de tolerancia (deviation +0.012mm)"` — generado a partir de los campos reales del evento WS, nunca un texto genérico ni "score=X".
  - Botón/link "Ver detalle completo" que navega a la página propia de deep-dive de LM.4 (`/live-monitor/:characteristicId` — límites de control históricos + navegación temporal), **no** a `/measurements/:characteristicId` (esa página sigue en datos mock hasta F5.7; no mezclar). Si LM.4 todavía no está implementada cuando se construya este panel, dejar el botón enlazando a `/measurements/:characteristicId` como fallback temporal y anotarlo explícitamente en el PR — no bloquear LM.2 esperando a LM.4.
- Actualiza `LiveMonitorPage.tsx` (de LM.1) para manejar el estado de "tarjeta expandida" y montar `SignalDetailPanel`.

## 🚫 Fuera de alcance

Controles de presentador (play/pause/velocidad/escenario — Fase 3, `LM3`); la página de deep-dive con histórico de Cpk y navegación temporal (Fase 4, `LM4` — este panel solo enlaza hacia allá, no la reimplementa); cualquier edición o registro manual de datos desde este panel (es de solo lectura).

## 📁 Archivos esperados

- `frontend/src/features/live-monitor/SignalDetailPanel.tsx` + test RTL.
- Cambios en `frontend/src/features/live-monitor/LiveMonitorPage.tsx` (de LM.1) para el estado de expansión.

## Referencias obligatorias

- `docs/design/live-monitor-panel.md`.
- `frontend/src/features/recommendations/RecommendationDetailPanel.tsx` (F5.9) — patrón ya establecido de "evidencia explicable" a seguir, mismo tono de rationale.
- `frontend/src/components/charts/TrendChart.tsx` y `frontend/src/features/measurements/CharacteristicTrendPage.tsx` (F5.7) — convenciones de nominal/límites como líneas de referencia.
- El resultado de LM.1: forma exacta de los eventos `point`/`control_limits_updated` del WebSocket.
- `docs/tasks/LM4-live-monitor-deep-dive.md` — la página de destino del botón "Ver detalle completo".

## ✔️ Criterios de aceptación

- [ ] El rationale mostrado siempre incluye el nombre y versión del motor (`engine_name`/`engine_version`) — nunca un texto sin esa trazabilidad.
- [ ] Los límites mostrados (tolerancia y control) son los reales del evento WS, no recalculados ni aproximados en el frontend.
- [ ] El botón "Ver detalle completo" navega a la característica correcta (a LM.4 si ya existe, o al fallback documentado si no).
- [ ] Ambos temas (light/dark) verificados.

## 🧪 Testing

RTL: abrir el panel desde una `SignalCard` mockeada, verificar que el rationale y los límites mostrados coinciden con los datos del evento simulado.

## Al terminar

Sigue el flujo estándar de `docs/tasks/README.md` (branch `feat/lm-2-live-monitor-detail`, apilada sobre la rama de LM.1 si aún no está mergeada — igual que el patrón ya usado en este repo para F4.2→F4.3 o F5.4→F5.5→F5.6). Commit, push, PR — **nunca mergear sin autorización explícita del usuario**. Desbloquea `LM3` (controles de presentador).
