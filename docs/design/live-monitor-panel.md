# Live Monitor — panel de mediciones en tiempo real (brainstorm → diseño)

**Estado:** diseño propuesto, sin tareas creadas en Notion todavía. Este documento es el resultado de una sesión de brainstorming (2026-07-15) y sirve de base para partirlo en tareas F#.x cuando se decida priorizarlo.

## Objetivo

Un panel tipo SCADA que muestre mediciones "llegando" en tiempo real — señales graficándose conforme entran, límites de tolerancia visibles, y evaluación de tendencia — para que el demo se sienta como un sistema de planta viva, no una serie de pantallas CRUD sobre datos estáticos. Es probablemente la pieza de mayor impacto visual del demo completo.

## Por qué esto encaja con lo que ya existe

- El motor SPC (F8.D, `backend/app/engines/spc/`) ya calcula Cp/Cpk y límites de control I-MR — el panel consume esa lógica real, no necesita inventar nada nuevo.
- El motor de Compliance (F7.D) ya evalúa OK/NOK por punto.
- `frontend/src/components/charts/{Sparkline,TrendChart}.tsx` ya existen y son la base natural para las tarjetas del grid y la vista expandida.
- Los datos sembrados (`seed/generators/measurements.py`) ya tienen 90 días de historia por característica con 5 patrones (stable, drift, shift_after_event, high_variance, nok_outlier) — material perfecto para "reproducir" en vivo.

## ⚠️ Decisión de framing — importante, no negociable con CLAUDE.md

El usuario originalmente pidió mostrar "tendencias del modelo de ML". **El proyecto es explícitamente basado en reglas explicables, no ML** (CLAUDE.md §22: *"ML enters only when data foundation justifies it... rules-based engines are the baseline and the fallback"*; §16: *"No unexplainable black-box outputs presented as recommendations"*). Decisión tomada en esta sesión:

- El panel muestra la salida del **motor SPC/Compliance real**, con lenguaje honesto: *"Cpk 0.91 — por debajo del umbral de 1.33"*, no *"el modelo de IA predice..."*.
- El punto de venta correcto no es "tenemos ML corriendo" — es **"el sistema explica cada alerta con la regla exacta que la disparó, en tiempo real"**. Eso es un diferenciador más fuerte y defendible frente a un cliente técnico (BMW) que "tenemos un modelo" sin poder explicarlo.
- Si en el futuro se agrega un modelo predictivo real (fase 13 del roadmap, post-demo), este panel es exactamente donde iría — pero hoy no existe y no se simula que exista.

## Decisiones de diseño (de la sesión de brainstorm)

| Decisión | Elegido |
|---|---|
| Fuente de datos | **Replay acelerado del histórico ya sembrado** — determinístico, reproducible entre demos, cero infraestructura nueva. No es un generador aleatorio en vivo. |
| Framing de "IA" | **Honesto**: cada alerta cita la regla/umbral real (motor + versión), nunca lenguaje de ML. |
| Alcance visual | **Grid multi-señal** tipo SCADA — varias características a la vez en tarjetas con sparkline, click para expandir a vista completa (reusa `TrendChart`). |
| Ubicación en la app | **Módulo nuevo "Live Monitor"** en el sidebar — separado de `Measurements` (histórico) para no mezclar "en vivo" con "histórico". |
| Mecanismo de actualización | **WebSocket** — el backend empuja puntos conforme el replay avanza; sensación real de "vivo", sin polling. |

## Arquitectura propuesta

### Backend

```
backend/app/services/live_replay_service.py   # orquesta el replay determinístico
backend/app/api/v1/live_monitor.py             # endpoint WebSocket /ws/live-monitor
```

- **Replay service**: por sesión de demo, toma N características (configurable, ej. las mismas 8-12 que ya se muestran en el dashboard operativo mock hoy) y "reproduce" su historia de 90 días a una velocidad configurable (ej. 1 día de datos reales = 1-3 segundos de reloj real). Determinístico: mismo seed → misma secuencia, para que la demo sea repetible.
- Cada punto emitido pasa por **el motor de Compliance real** (`evaluate()`) para is_ok/deviation, y periódicamente (cada N puntos) por **el motor SPC real** (`cpk()`, `individuals_moving_range_limits()`) para refrescar la tendencia/límites de control mostrados.
- **WebSocket endpoint** (`/ws/live-monitor`): autenticado (el JWT ya emitido por F4.2 se pasa como query param o subprotocol en el handshake, ya que WS no soporta headers custom fácilmente desde el navegador) y con el mismo `require_permission` que el resto de la API (RBAC — mínimo `metrologist`+, igual que `context.process_event.read`). Emite eventos tipados: `{type: "point", characteristic_id, value, deviation, is_ok, measured_at}` y `{type: "control_limits_updated", characteristic_id, ...}`.
- Un connection manager simple (in-memory, un solo proceso — igual de "demo-grade" que el revocation store de F4.2) hace fan-out a los clientes conectados a la misma sesión de replay.

### Frontend

```
frontend/src/features/live-monitor/LiveMonitorPage.tsx     # grid de tarjetas
frontend/src/features/live-monitor/SignalCard.tsx           # una característica: sparkline + estado + último valor
frontend/src/features/live-monitor/SignalDetailPanel.tsx    # vista expandida (reusa TrendChart)
frontend/src/lib/live-monitor/useLiveSocket.ts               # hook WebSocket con reconexión
```

- `SignalCard`: nombre de característica, sparkline (reusa `components/charts/Sparkline.tsx`), último valor + unidad, `StatusChip` OK/NOK, mini-badge de nivel de riesgo si aplica.
- Click en una tarjeta → `SignalDetailPanel` con `TrendChart` completo, límites de tolerancia y de control superpuestos, y el texto de rationale del motor (mismo patrón que ya usamos en `RecommendationDetailPanel` para mostrar evidencia explicable).
- Controles del presentador: play/pause del replay, velocidad (1x/5x/20x), selector de escenario (stable/drift/shift/high_variance/nok — mismos 5 patrones del seed).

## Fuera de alcance (primera iteración)

- Ingesta real desde una CMM/PLC — sigue siendo F12 (integraciones reales), fuera del demo.
- Predicción real de tendencia futura (eso sería ML de verdad — F13, post-demo).
- Persistir los puntos del replay como `measurement_results` reales — el replay es una capa de presentación efímera, no debe escribir en la tabla de mediciones real (evitaría contaminar el histórico "real" del demo con datos de replay repetidos).

## Fases de despliegue

Tres fases, cada una independientemente demostrable y construyendo sobre la anterior — no bloquean al equipo de seguir con otras prioridades del roadmap entre una fase y la siguiente.

| Fase | Tareas (futuras F#.x en Notion) | Resultado demostrable |
|---|---|---|
| **Fase 1 — MVP funcional** | 1. Backend — replay service + WebSocket endpoint (nuevo, `BACKEND`+`ENGINES`, P1, ~M): orquesta el replay, conecta Compliance+SPC, expone `/ws/live-monitor` con RBAC.<br>2. Frontend — Live Monitor grid + signal cards (`FRONTEND`, P1, ~M): `LiveMonitorPage`, `SignalCard`, hook de WebSocket con reconexión. | Se puede prender el panel y ver señales "llegando" en vivo con estado OK/NOK — ya es demostrable end-to-end, aunque sin detalle ni controles. |
| **Fase 2 — Profundidad explicable** | 3. Frontend — vista de detalle expandida (`FRONTEND`, P2, ~S): `SignalDetailPanel` reusando `TrendChart`, límites de tolerancia/control superpuestos, rationale del motor. | El presentador puede entrar al detalle de una señal y mostrar *por qué* el sistema la marca en riesgo — el diferenciador de "explicable, no caja negra". |
| **Fase 3 — Pulido para presentador** | 4. Controles de presentador (`FRONTEND`, P2, ~S): play/pause, velocidad (1x/5x/20x), selector de escenario (stable/drift/shift/high_variance/nok). | El presentador controla el ritmo de la demo en vivo en lugar de dejar correr el replay a velocidad fija — mejora la experiencia de pitch, no añade funcionalidad core. |

## Todo se ancla al modelo de datos existente

Principio no negociable: el panel **no inventa una estructura de datos paralela**. Cada señal, límite y salida de motor que se muestre se traza a entidades reales ya definidas en `backend/app/models/` — números de parte, límites de tolerancia, SPC, y cualquier motor "inteligente" incluidos.

| Elemento mostrado en el panel | Entidad/tabla real (ya existente) |
|---|---|
| Número de parte | `catalog_part_numbers` (`app/models/catalog.py`) |
| Característica / señal | `catalog_characteristics`, vía `part_number_id` |
| Límites de tolerancia | `catalog_specifications` — versionada (`valid_from`/`valid_to`), se usa la spec **activa** (`valid_to IS NULL`), nunca un límite inventado o hardcodeado |
| Punto de medición | `measurement_results` (`value`, `deviation`, `is_ok`, `characteristic_id`, `specification_id`) — el replay reproduce filas reales ya sembradas, no genera valores sintéticos nuevos |
| Evaluación OK/NOK | Motor Compliance real (`app/engines/compliance/evaluate.py`, F7.D) — mismo `engine_name`/`engine_version` que ya se persiste hoy |
| Tendencia / capacidad de proceso | Motor SPC real (`app/engines/spc/capability.py` + `control_limits.py`, F8.D) — Cpk y límites I-MR calculados de verdad, no simulados |
| "IA" / "ML" | **No existe un motor de ML en el sistema** (CLAUDE.md §22). Lo que sí existe y se muestra es el motor de Riesgo real (`app/engines/risk/score.py`, F9.D), explicable — nunca se etiqueta como "modelo de ML" ni se fabrica un motor o entidad que no exista. |

Este mapeo es la única fuente de verdad sobre qué tabla/motor alimenta cada elemento visual del panel — cualquier implementación futura de las fases de arriba debe referenciar esta tabla en lugar de reinventar los campos.

## Riesgos y consideraciones de seguridad

- El endpoint WS debe respetar RBAC igual que cualquier endpoint REST (CLAUDE.md §5) — no es una excepción "porque es solo para demo".
- El connection manager in-memory es demo-grade (un solo proceso) — igual que el revocation store de F4.2; documentar la limitación igual que se hizo ahí, no ocultarla.
- Nunca escribir el replay a `measurement_results` (tabla real, insert-only, CLAUDE.md §6) — mantiene la separación entre "demo en vivo" y "histórico real" sembrado.
