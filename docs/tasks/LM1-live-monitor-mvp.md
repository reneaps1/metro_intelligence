# LM.1 — Live Monitor: replay backend + WebSocket + grid frontend (Fase 1/3)

**Notion:** ninguna todavía — este es un feature de demo nacido de brainstorming, no de un ticket ya priorizado. Fuente de verdad: [`docs/design/live-monitor-panel.md`](../design/live-monitor-panel.md).
**Fase:** Live Monitor · Fase 1 de 3 (MVP funcional) | **Scope:** DEMO | **Prioridad:** P1 Alta | **Estimación:** M (1-2 días)

> Lee `CLAUDE.md` en la raíz del repo completo antes de empezar. Lee `docs/tasks/README.md` para el flujo de trabajo compartido que asume este archivo. **Lee también `docs/design/live-monitor-panel.md` completo — es el diseño del que sale esta tarea, no lo reinventes.**

## Estado de dependencias

- **F7.D (Compliance engine):** ✅ Done — `app/engines/compliance/evaluate.py`.
- **F8.D (SPC engine):** ✅ Done — `app/engines/spc/capability.py`, `control_limits.py`.
- **F4.2 (JWT auth):** ✅ Done — reutiliza `get_current_user`/`require_permission`.
- **F3.3 (seed measurement series):** ✅ Done — `measurement_results` ya tiene ~90 días de historia por característica; esta tarea consume esos datos, no genera nuevos.

## 🎯 Objetivo

Backend: un servicio que "reproduce" en el tiempo la historia ya sembrada de un conjunto de características (determinístico, mismo seed → misma secuencia), y un endpoint WebSocket autenticado que empuja cada punto reproducido a los clientes conectados. Frontend: una pantalla nueva `Live Monitor` con un grid de tarjetas, una por característica, que se actualizan en vivo conforme llegan los puntos.

## 📋 Contexto — principios no negociables (de `docs/design/live-monitor-panel.md`)

1. **Framing honesto, nunca "ML"**: el panel muestra la salida real de los motores Compliance/SPC (`engine_name`/`engine_version` incluidos). No existe un motor de ML en el sistema (CLAUDE.md §22) — no se simula que exista.
2. **Todo se ancla al modelo de datos existente** (ver tabla completa en el doc de diseño): número de parte → `catalog_part_numbers`; característica → `catalog_characteristics`; límites → `catalog_specifications` (spec **activa**, `valid_to IS NULL`); punto de medición → filas reales de `measurement_results` (el replay las reproduce, no inventa valores nuevos).
3. **El replay NUNCA escribe en `measurement_results`** (tabla real, insert-only, CLAUDE.md §6) — es una capa de presentación efímera sobre datos ya persistidos, no una nueva fuente de datos.
4. **RBAC en el WebSocket igual que en REST** (CLAUDE.md §5) — no es una excepción "porque es demo".

## ✅ Alcance

### Backend
- `backend/app/services/live_replay_service.py`: dado un conjunto de `characteristic_id` y una velocidad de reproducción, lee sus `measurement_results` ya sembrados (ordenados por `measured_at`) y los "reproduce" a un ritmo configurable (ej. 1 día real de datos = 1-3s de reloj real). Cada punto reproducido re-evalúa con el motor de Compliance real (`evaluate()`, usando la spec activa de la característica) — no reutiliza ciegamente el `is_ok`/`deviation` ya guardado, para que el pipeline completo (valor → evaluación → evento) quede demostrado en vivo. Cada N puntos, recalcula Cpk/límites de control con el motor SPC real y emite un evento de actualización.
- `backend/app/api/v1/live_monitor.py`: endpoint WebSocket `/ws/live-monitor`. Autenticación: el JWT de acceso se pasa como query param (`?token=...`) en el handshake (WS no soporta headers custom fácilmente desde el navegador) y se valida con la misma lógica que `get_current_user`. Autorización: nuevo permission token `live_monitor.stream` (acción `read`), otorgado a `metrologist`, `quality_engineer`, `admin`, `auditor` (mismo patrón que `context.process_event.read`) — **requiere una migración nueva** (`0006_live_monitor_permission.py`, cabeza única, coordina con lo que exista en `backend/alembic/versions/` al momento de implementar).
- Eventos emitidos (JSON): `{"type": "point", "characteristic_id": ..., "value": ..., "deviation": ..., "is_ok": ..., "measured_at": ...}` y `{"type": "control_limits_updated", "characteristic_id": ..., "cpk": ..., "ucl": ..., "lcl": ..., "engine_version": ...}`.
- Connection manager in-memory (un solo proceso) para el fan-out — documentar explícitamente esta limitación demo-grade en el docstring del módulo, mismo estilo que el revocation store de F4.2 (`app/core/security.py`).

### Frontend
- `frontend/src/lib/live-monitor/useLiveSocket.ts`: hook que abre el WebSocket (con el access token en memoria de `lib/api.ts`), reconecta con backoff si se cae, expone los eventos tipados.
- `frontend/src/features/live-monitor/LiveMonitorPage.tsx`: grid de `SignalCard`, una por característica activa en el replay.
- `frontend/src/features/live-monitor/SignalCard.tsx`: nombre de característica + número de parte, sparkline (reusa `components/charts/Sparkline.tsx`), último valor + unidad, `StatusChip` OK/NOK.
- Nueva entrada "Live Monitor" en `components/ui/Sidebar.tsx` y ruta `/live-monitor` en `App.tsx`, detrás de `RequireAuth` (mismo patrón que las demás rutas autenticadas).

## 🚫 Fuera de alcance

Vista de detalle expandida (Fase 2, `LM2`); controles de presentador play/pause/velocidad/escenario (Fase 3, `LM3`); ingesta real desde CMM/PLC (F12, fuera del demo); cualquier predicción real de tendencia futura (eso sería ML de verdad, F13 post-demo, no existe).

## 📁 Archivos esperados

- `backend/app/services/live_replay_service.py`, `backend/app/api/v1/live_monitor.py` + registro en `backend/app/api/v1/router.py`.
- `backend/alembic/versions/0006_live_monitor_permission.py` (nuevo permission token).
- `frontend/src/lib/live-monitor/useLiveSocket.ts`, `frontend/src/features/live-monitor/{LiveMonitorPage,SignalCard}.tsx`.
- Tests backend (replay determinístico, RBAC del WS) y frontend (RTL: grid renderiza, estado OK/NOK correcto).

## Referencias obligatorias

- `docs/design/live-monitor-panel.md` — diseño completo, tabla de anclaje al modelo de datos, decisión de framing.
- `backend/app/engines/compliance/evaluate.py`, `backend/app/engines/spc/{capability,control_limits}.py` — motores reales a invocar, no reimplementar.
- `backend/app/core/security.py` (`get_current_user`, revocation store) — patrón de auth y de documentar limitaciones demo-grade.
- `backend/alembic/versions/0001_org_security.py` (`ROLE_PERMISSIONS`, `_seed_rbac`) — patrón para agregar el nuevo permission token.
- `frontend/src/lib/api.ts` — de dónde sacar el access token en memoria para el WS.

## ✔️ Criterios de aceptación

- [ ] El replay es determinístico: mismo `characteristic_id` + mismo punto de partida → misma secuencia de eventos emitidos (test).
- [ ] El WS rechaza conexiones sin token válido o sin el permiso `live_monitor.stream` (401/cierre de conexión con código apropiado — test).
- [ ] Ningún punto reproducido se inserta en `measurement_results` (test que verifica el conteo de filas antes/después de un replay).
- [ ] El grid del frontend muestra al menos 4-6 características simultáneas actualizándose sin recargar la página.
- [ ] Cada característica mostrada resuelve a un `catalog_part_numbers`/`catalog_characteristics`/`catalog_specifications` real — nada hardcodeado.

## 🧪 Testing

Backend: integración contra Postgres real (replay determinístico, RBAC del WS, no-persistencia). Frontend: RTL para `SignalCard`/`LiveMonitorPage` con un WS mockeado (MSW no soporta WS directamente — usar un mock manual del hook o de `WebSocket` global, documentando el enfoque elegido).

## Al terminar

Sigue el flujo estándar de `docs/tasks/README.md` (branch `feat/lm-1-live-monitor-mvp`, commit, push, PR — **nunca mergear sin autorización explícita del usuario**). Como no hay página de Notion, deja la nota de entrega como comentario en el PR y, si el usuario lo pide, créala en ese momento. Desbloquea `LM2` (vista de detalle).
