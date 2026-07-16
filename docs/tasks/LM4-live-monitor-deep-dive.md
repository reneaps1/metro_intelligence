# LM.4 — Live Monitor: página de detalle completa (Fase 4/4)

**Notion:** ninguna todavía — este es un feature de demo nacido de brainstorming, no de un ticket ya priorizado. Fuente de verdad: [`docs/design/live-monitor-panel.md`](../design/live-monitor-panel.md).
**Fase:** Live Monitor · Fase 4 de 4 (deep dive) | **Scope:** DEMO | **Prioridad:** P2 Media | **Estimación:** M (1 día)

> Lee `CLAUDE.md` en la raíz del repo completo antes de empezar. Lee `docs/tasks/README.md` para el flujo de trabajo compartido que asume este archivo. **Lee también `docs/design/live-monitor-panel.md` completo — es el diseño del que sale esta tarea, no lo reinventes.**

## Estado de dependencias

- **LM.1 (MVP funcional):** bloqueador directo — esta página vive dentro del feature Live Monitor que LM.1 construye (grid, modelo de eventos WS, `catalog_characteristics`/`catalog_specifications` como fuente de verdad).
- **LM.2 (vista de detalle — panel):** dependencia lógica, no dura. El panel/modal de LM.2 es el punto de entrada natural (botón "Ver detalle completo"), pero esta página también debe poder abrirse por URL directa sin pasar por el panel.
- **F4.6 (Measurements read API):** ✅ Done — `GET /characteristics/{id}/series` ya soporta `from`/`to`/`max_points`; esta tarea lo reusa tal cual para la navegación temporal, no lo reimplementa.
- **F8.D (SPC engine):** ✅ Done — `app/engines/spc/{capability,control_limits}.py`; esta tarea reusa `cpk()`/`individuals_moving_range_limits()`, nunca reimplementa la matemática.

## 🎯 Objetivo

Una página propia (`/live-monitor/:characteristicId`, no un modal) para que el presentador se meta de lleno en una sola característica: la serie histórica completa (no acotada a lo que el replay en vivo ya reprodujo), límites de tolerancia **y de control** superpuestos, navegación por rango de fechas, y un histórico de Cpk por ventanas de tiempo — todo sobre datos reales.

## 📋 Contexto

`docs/tasks/LM2-live-monitor-detail-view.md` deja explícito que su panel es liviano (reusa `TrendChart` con la serie ya replayada, sin navegación temporal) y pospone "controles" a LM.3 — pero LM.3 solo gobierna el replay del **grid completo** (play/pause/velocidad/escenario), no la exploración histórica de una señal individual. Ninguna de las dos fases cubre "zoom-in a una sola característica con límites de control históricos y moverse en el tiempo" — de ahí esta fase nueva.

Dos hallazgos clave de la exploración que hicimos antes de escribir esta tarea:
1. `GET /characteristics/{id}/series` (F4.6) **ya** acepta `from`/`to` arbitrarios con downsampling — la navegación temporal básica no requiere tocar el backend existente, solo consumirlo desde una página nueva.
2. **No existe hoy ninguna persistencia ni cálculo bajo demanda de Cpk/límites de control por ventana histórica** — ni tabla, ni endpoint. El replay de LM.1 recalcula Cpk de forma acumulativa (ventana expansiva) para el WS en vivo, pero es efímero y no sirve para reconstruir "cómo evolucionó el Cpk" sobre un rango arbitrario. Este es el único trabajo de backend genuinamente nuevo en esta fase.

`frontend/src/features/measurements/CharacteristicTrendPage.tsx` (`/measurements/:characteristicId`) es el precedente más cercano de "página completa de una característica", pero corre sobre datos mock (`useDemoData()` — F5.7 todavía no conectó mediciones a la API real en frontend). Por eso esta página es nueva y propia dentro de `features/live-monitor/`, 100% datos reales, en vez de ampliar esa página mock o adelantar F5.7 fuera de alcance.

## ✅ Alcance

### Backend

- `backend/app/services/capability_history_service.py`: dado `characteristic_id` + rango `from`/`to` + tamaño de ventana (en puntos), reusa la misma consulta que `get_characteristic_series` (join `MeasurementResult`+`Specification`, ordenado por `measured_at`) para traer la serie en el rango, la parte en ventanas no solapadas, y llama a `cpk()`/`individuals_moving_range_limits()` (F8.D) por ventana. Si una ventana cruza un cambio de versión de especificación, se parte en el borde de la spec (mismo criterio que ya usa `/series` para no re-evaluar contra una versión que no estaba vigente — CLAUDE.md §6).
- `backend/app/api/v1/measurements.py`: nuevo endpoint `GET /characteristics/{id}/capability-history?from=&to=&window_size=`. RBAC: reusa el permiso ya existente `measurement.measurement_result.read` (mismo que `/series`) — no se crea un permiso nuevo. Respuesta: lista de ventanas con `window_start`, `window_end`, `point_count`, `cpk` (nullable — indefinido para spec unilateral con varianza cero, igual que LM.1), `center_line`, `ucl`, `lcl`, `engine_name`, `engine_version`.
- `backend/app/schemas/measurements.py`: nuevos schemas (`CapabilityWindow`, `CapabilityHistoryResponse` o similar).

### Frontend

- `frontend/src/features/live-monitor/LiveMonitorDetailPage.tsx`: página nueva, ruta `/live-monitor/:characteristicId` en `App.tsx` (mismo patrón `/recurso/:id` que `/catalog/:partId` y `/measurements/:characteristicId`).
- `frontend/src/components/charts/TrendChart.tsx`: agregar prop opcional `controlLimits?: { centerLine, ucl, lcl }` (más `ReferenceLine`s) — cambio compatible hacia atrás; `CharacteristicTrendPage` sigue funcionando igual al no pasarla.
- Cliente mínimo para `/characteristics/{id}/series` y `/characteristics/{id}/capability-history` (no existe hoy un `lib/measurements/api.ts` real porque F5.7 no está hecho en frontend — esta página es su primer consumidor real; alcance acotado a lo que esta página necesita, no una migración completa de F5.7).
- Controles de rango de fechas (presets 7/30/90 días / todo, o selector de fechas) que vuelven a pedir `/series` y `/capability-history` al cambiar — cubre "moverse en el tiempo" reusando el backend existente, sin construir zoom/brush interactivo desde cero.
- Chart/lista secundaria con el histórico de Cpk por ventana.
- Enlace de vuelta al grid de Live Monitor. El panel de LM.2 gana un botón "Ver detalle completo" que navega aquí (ver ajuste ya anotado en `docs/tasks/LM2-live-monitor-detail-view.md`).

## 🎨 Calidad visual (no negociable para esta página)

Esta página es, por diseño, "el argumento de venta central" del feature completo (así la describe el propio `docs/tasks/LM2-live-monitor-detail-view.md`) — el momento en que el presentador se mete de lleno frente al cliente. No basta con que funcione: tiene que **verse pulida**.

- Usar los tokens del sistema de diseño ya establecido (`docs/design/design-system.md`, `frontend/src/theme/tokens.css`) — nunca colores/espaciados improvisados.
- Al construir los charts nuevos (límites de control superpuestos, histórico de Cpk), invocar el skill `dataviz` antes de escribir el código de la gráfica — cubre paleta por serie, cómo marcar OK/NOK visualmente, leyendas, tooltips, y consistencia light/dark.
- Para el layout general (jerarquía visual, cómo se presenta el Cpk/límites como "hero" de la página, controles de rango de fechas), apoyarse en el skill `ui-ux-pro-max` en vez de improvisar un layout genérico.
- Transiciones suaves al cambiar de rango de fechas (loading state legible, no un salto brusco del chart).

## 🚫 Fuera de alcance

Zoom/pan interactivo tipo "arrastrar para acercar" dentro del chart (queda como posible mejora futura, no requerida para esta fase); tocar `CharacteristicTrendPage`/F5.7; cualquier control de play/pause/velocidad/escenario (eso es LM.3, y es sobre el grid completo, no esta página).

## 📁 Archivos esperados

- `backend/app/services/capability_history_service.py`, cambios en `backend/app/api/v1/measurements.py` y `backend/app/schemas/measurements.py`.
- `frontend/src/features/live-monitor/LiveMonitorDetailPage.tsx`, cambios en `frontend/src/components/charts/TrendChart.tsx` y `frontend/src/App.tsx`.
- Tests backend (ventaneo determinístico, ventana que cruza cambio de spec, RBAC) y frontend (RTL: la página renderiza trend + límites de control + histórico de Cpk; cambiar el rango vuelve a pedir datos).

## Referencias obligatorias

- `docs/design/live-monitor-panel.md` — diseño completo, tabla de fases.
- `docs/tasks/LM2-live-monitor-detail-view.md` — patrón de "evidencia explicable" y punto de entrada desde el panel.
- `backend/app/api/v1/measurements.py` (`get_characteristic_series`) — consulta y convención de spec-vigente-al-momento-de-medición a reusar, no reinventar.
- `backend/app/engines/spc/{capability,control_limits}.py` — motores reales a invocar.
- `frontend/src/components/charts/TrendChart.tsx` y `frontend/src/features/measurements/CharacteristicTrendPage.tsx` — precedente de página de característica a imitar en estructura, no en fuente de datos (esa sigue siendo mock ahí).

## ✔️ Criterios de aceptación

- [ ] Los límites de control y el Cpk mostrados son siempre los reales devueltos por el motor SPC (`engine_name`/`engine_version` incluidos) — nunca recalculados ni aproximados en el frontend.
- [ ] Cambiar el rango de fechas trae datos reales distintos de la API (test).
- [ ] Una ventana que cruza un cambio de versión de especificación se parte correctamente en el borde (test).
- [ ] RBAC igual que `/series` (`measurement.measurement_result.read`) — mismos roles permitidos/denegados (test).
- [ ] Ambos temas (light/dark) verificados antes de cerrar la tarea.

## 🧪 Testing

Backend: unitarios sobre la función de ventaneo (determinismo, borde de spec, ventana con <2 puntos) + integración del endpoint (RBAC, rango real contra Postgres). Frontend: RTL para `LiveMonitorDetailPage` con la API real mockeada (MSW, mismo patrón que el resto de F5.x — a diferencia de LM.1, aquí no hay WebSocket que mockear a mano, todo es REST).

## Al terminar

Sigue el flujo estándar de `docs/tasks/README.md` (branch `feat/lm-4-live-monitor-deep-dive`, apilada sobre LM.1/LM.2 según lo que esté mergeado en ese momento). Commit, push, PR — **nunca mergear sin autorización explícita del usuario**. Con esto, las 4 fases de Live Monitor quedan completas.
