# Plan de trabajo — Demo Industrial Quality (dimensional + IIoT + IA)

> Documento vivo de trabajo. Fuente: "Prompt maestro Metro Intelligence × cliente de inyección" (26/oct/2026).
> Rama: `feat/industrial-quality-demo` (creada desde `origin/main` @ `0f8ec0a`). No merge ni deploy sin autorización del propietario.
> Este archivo está en español por ser documento operativo de proyecto (CLAUDE.md §10 pide docs técnicas en inglés; la guía final de demo podrá ir en inglés o bilingüe).

## Protocolo de sesión (leer primero en cada chat nuevo)

Se trabaja **una fase por sesión de chat**. Este archivo es la fuente de verdad del avance; el agente lo mantiene actualizado.

1. Leer `CLAUDE.md` (reglas vinculantes) y este archivo completo.
2. Leer `demo-private/client-brief.md` si existe (contexto confidencial: nombre del cliente, cifras del informe, mensaje comercial). **Gitignored: nunca commitear ni copiar su contenido a archivos versionados.**
3. `git switch feat/industrial-quality-demo && git pull` (si ya existe en remoto). Verificar `git status` limpio salvo los `.pptx` untracked.
4. Tomar la **primera fase ⬜ del tablero** (o la que indique el usuario), marcarla 🟨 y anotar en la bitácora.
5. Implementar solo esa fase. Si algo no cabe, moverlo explícitamente a otra fase o a §7 "Pendientes / ideas", nunca dejarlo implícito.
6. Al cerrar: pruebas de la fase pasando, marcar ✅ en tablero, tachar criterios del DoD que se cumplan, registrar en bitácora (qué se hizo, pruebas corridas, qué quedó pendiente, decisiones nuevas), commit Conventional (`feat: ... (IQ-F<n>)`) y push de la rama. **Sin merge ni deploy sin autorización.**
7. Terminar la sesión con un resumen corto para el usuario y cuál es la siguiente fase.

---

## Tablero de estado

| Fase | Nombre | Estado | Rama / PR | Notas |
|---|---|---|---|---|
| F0 | Reconocimiento y decisiones | ✅ Hecho | — | Ver §1 y §2 |
| F1 | Edición configurable, shell de demo, procedencia y recorrido | ✅ Hecho | `feat/industrial-quality-demo` | Pasos 2,3,5,6,7 son placeholders honestos hasta sus fases |
| F2 | Generador IIoT determinista + API de señales | ✅ Hecho | `feat/industrial-quality-demo` | Paso 4 muestra escenarios, inventario y eventos reales de la API |
| F3 | Explorador de señales estilo iba | ⬜ Pendiente | | Pieza central del demo |
| F4 | Correlación, regresión y caso sintético causal | ⬜ Pendiente | | Vista A / Vista B |
| F5 | Dashboard de calidad dimensional (nidos) | ⬜ Pendiente | | KPIs, Pareto, heatmap |
| F6 | Importación CSV con mapeo de columnas | ⬜ Pendiente | | Ancho/largo, muestra |
| F7 | Laboratorio ML/DL y oleadas NOK | ⬜ Pendiente | | Cifras precalculadas |
| F8 | Oportunidad de integración, pulido, guía y handoff | ⬜ Pendiente | | Docs, pruebas, PR |
| F9 | Despliegue de dos ediciones (metrology + industrial) | ⬜ Pendiente | | Requiere autorización para tocar VPS/deploy |

Leyenda: ⬜ pendiente · 🟨 en curso · ✅ hecho · ⛔ bloqueado

Orden de ejecución: F1 → F2 → F3 → F4 → F5 → F6 → F7 → F8 → F9. Si el tiempo se acorta, F1–F4 + F7 son el mínimo presentable (DoD puntos 1–6 + relato honesto de modelos).

---

## 1. Diagnóstico del repositorio (F0)

### 1.1 Estado de ramas y CI

- Rama anterior `feat/experimental-drift-detection` ya mergeada en `main` (PR #38).
- `main` local estaba 9 commits detrás de `origin/main` (Thompson Sampling #39, fix #40, `demo_data.py`, Dockerfile). La rama nueva parte de `origin/main`.
- CI (`.github/workflows/ci.yml`): **verde** en los últimos pushes a `main`.
- Deploy (`.github/workflows/deploy.yml`): **falla** en los 3 últimos runs (13/oct/2026, ~11–14 s, falla temprano). No asumir que el sitio público funciona. Fuera de alcance arreglarlo salvo que se pida.
- Untracked en el worktree: `docs/tasks/Metro_Intelligence_Overview*.pptx` (no tocar, no commitear).

### 1.2 Qué es real, mock o experimental hoy

| Área | Archivo(s) | Fuente de datos |
|---|---|---|
| Login / RBAC | `features/auth`, `backend/app/api/v1/auth.py` | **Real** (JWT) |
| Catálogo | `features/catalog`, `api/v1/catalog.py` | **Real** |
| Importación | `features/imports/ImportPage.tsx`, `services/import_service.py` | **Real**, formato ancho fijo |
| Live Monitor + detalle | `features/live-monitor`, `services/live_replay_service.py` | **Real** (replay de mediciones guardadas por WebSocket) |
| CUSUM drift / Thompson Sampling | `engines/experimental_ml/drift_cusum.py`, `engines/adaptive_sampling.py` | **Experimental** |
| Recomendaciones | `features/recommendations` | **Real** (API) |
| Dashboards ejecutivo/operativo | `features/dashboards/*` | **Mock** (`useDemoData()` en `lib/mock/`) |
| Mediciones lista/tendencia | `features/measurements/*` | **Mock** |
| Riesgo | `features/risk/RiskPage.tsx` | **Mock** |

### 1.3 Importación actual (restricciones)

- `MAX_FILE_SIZE_BYTES = 20 MB`, todo se procesa dentro del request (`process_upload`, `list(connector.parse_rows(...))`).
- Formato esperado: ancho, `part_number`, `run_at`, `machine`, … y columnas `COL_<balloon>` según `output_mapping` del programa (`seed/generators/catalog.py`). Solo resuelve piezas/características ya existentes en catálogo; lo demás va a cuarentena.
- Duplicados por SHA-256; original en MinIO; auditoría por evento.
- **No existe** concepto de nido/cavidad en el modelo (`models/measurement.py` solo tiene `batch_lot`). Un CSV real del cliente casi seguro no es compatible tal cual.

### 1.4 Frontend

- React 18 + TS + Vite + Tailwind + Recharts 2.13 + lucide-react. Tokens en `theme/tokens.css`, modo claro/oscuro en `lib/theme/ThemeProvider.tsx`.
- Rutas en `App.tsx`; navegación en `components/ui/Sidebar.tsx` (`NAV_ITEMS`).
- Componentes de gráfica reutilizables: `TrendChart`, `Histogram`, `RiskHeatmap`, `CapabilityHistoryChart`, `Sparkline`, `StatTile`, `StatusChip`.
- Pruebas: Vitest + RTL + MSW (`test/server.ts`, `test/renderAuthed.tsx`).

### 1.5 Insumos que NO están disponibles localmente

- Los PDF informe de alertas/oleadas NOK (V2.0) e informe de Data Science/ML/IIoT del cliente: **no encontrados** en `D:\`, `Documents`, `Downloads`, `Desktop`.
- Las 4 imágenes de referencia visual (`OnKaizen Dimensional Quality Dashboard.png`, etc.): **no encontradas**.
- Consecuencia: se usa el resumen del prompt como única fuente de cifras; cada cifra se marca "pendiente de verificar contra informe" hasta que se entreguen los PDF. El estilo visual se interpreta desde las descripciones.

---

## 2. Decisiones a confirmar (bloquean partes concretas)

| ID | Decisión | Conflicto | Default propuesto (se aplica si no hay respuesta) |
|---|---|---|---|
| D1 | ¿Dónde viven el nombre del cliente y las cifras del informe? | CLAUDE.md §7/§16/§20 prohíben datos reales de clientes en el repo; el repo es público en GitHub. | Repo solo con **etiqueta genérica** ("Cliente demo") y **cifras placeholder ficticias** en un fixture versionado. Nombre real vía variable de entorno `DEMO_CLIENT_LABEL` (solo en el `.env` del despliegue; implementado en F1). Cifras reales del informe en `demo-private/` (**gitignored**), a cargar en F7. Guía final como `docs/demo-industrial-quality.md` (ningún nombre de cliente en nombres de archivo). |
| D2 | Persistencia de señales IIoT | Crear tablas de series exige migración y volumen. | **Sin tablas nuevas**: generador determinista puro que el backend evalúa bajo demanda (escenario + ventana + resolución). "Restaurar escenario" = reset de estado, nunca borra BD. |
| D3 | Nido/cavidad en mediciones | No existe en el modelo. | Migración Alembic pequeña y reversible `0009`: columna nullable `cavity_code` en `measurement_runs` (+ índice). Sin tablas duplicadas. |
| D4 | Permiso RBAC para endpoints nuevos | Añadir permisos requiere migración y actualizar `rbac.md`. | Reusar `live_monitor:read` (misma naturaleza: replay/simulación de solo lectura) para señales y analítica demo; `imports` existentes para el mapeo. Documentar en `rbac.md`. |

D1–D4: el usuario no objetó → se aplican los defaults propuestos. Reabrir solo si aparece un bloqueo.

**D5 — Dos versiones de Metro Intelligence: ✅ decidido (26/oct/2026).** Un solo código y una sola rama de integración (`main`), con interruptor de edición en vez de dos ramas de larga vida:

- `APP_EDITION=metrology`: la versión actual (monitoreo de mediciones). Menú, rutas y routers IIoT/IA/demo **ocultos y no registrados**.
- `APP_EDITION=industrial`: todo lo anterior + demo industrial, IIoT, analítica y laboratorio IA.
- Se despliegan dos instancias del mismo código con distinta configuración (F9). Default si la variable falta: `metrology` (fail-closed: no exponer módulos nuevos por accidente).
- Motivo: evitar mantener y re-sincronizar dos ramas divergentes; un fix llega a ambas ediciones.

Otras decisiones técnicas ya tomadas (cambiables con justificación):

- **Gráficas**: seguir con Recharts + downsampling en backend (LTTB / min-max por bucket, ≤ ~2 000 puntos por traza). Solo si el explorador no rinde, evaluar `uPlot` (nueva dependencia → anotar en PR).
- **Drag & drop**: HTML5 nativo + botón "Agregar" como fallback accesible. Sin librería nueva.
- **Ruta**: `/demo/industrial-quality/*` (genérica, sin nombre de cliente).
- **Procedencia**: tipo único `DataOrigin = "REAL" | "HISTORICAL" | "SIMULATED" | "PRECOMPUTED" | "EXPERIMENTAL"` y componente `OriginBadge` usado en cada panel.

---

## 3. Fases

Cada fase = commits limpios en la rama, con pruebas, y actualización del tablero de estado arriba. Commit + push al cerrar cada fase (CLAUDE.md §8).

### F1 — Edición configurable, shell de demo, procedencia y recorrido guiado

**Objetivo:** abrir la demo y recorrer 7 pasos sin subir archivos, aunque varias pantallas sean aún esqueleto con datos ficticios; y que la edición `metrology` siga viéndose exactamente como hoy.

Entregables — edición (D5):
- Backend: `app_edition: Literal["metrology", "industrial"] = "metrology"` en `core/config.py`; documentado en `.env.example` y `backend/.env.example`.
- Backend: routers nuevos (señales, analítica de calidad, demo) se registran en `api/v1/router.py` **solo** si `app_edition == "industrial"`; en `metrology` responden 404.
- Endpoint `GET /api/v1/meta` (o extensión de uno existente) que devuelve `{edition, client_label}`; el frontend lo lee en runtime → **una sola imagen Docker** sirve a ambas ediciones (sin `VITE_*` horneado en build).
- Frontend: `lib/edition/` con hook `useEdition()`; `Sidebar` y `App.tsx` filtran entradas/rutas por edición.
- Pruebas: con `metrology` no hay rutas ni menú industrial y los endpoints devuelven 404; con `industrial` sí aparecen.

Entregables — demo:
- Rutas `/demo/industrial-quality` (inicio) y subrutas: `context`, `quality`, `dimensional`, `iiot`, `correlation`, `ai`, `integration`.
- Entrada "Demo industrial" en `Sidebar.tsx`.
- `DemoShell` con stepper superior (pasos 1–7), botones **Iniciar demo**, **Anterior/Siguiente**, **Restaurar escenario demo** (resetea estado de cliente; no toca BD).
- Accesos rápidos: "Ver problema del nido crítico" (número de nido desde perfil de cliente), "Explorar deriva de temperatura", "Comparar presión vs. dimensión", "Mostrar limitaciones del modelo ML".
- `OriginBadge` + leyenda de procedencia; `lib/demo/clientProfile.ts` (nombre configurable, D1).
- Interfaz de proveedor de datos de demo en `lib/demo/` que declare origen por dataset (siguiendo la frontera `lib/data` que pide CLAUDE.md §0).
- Paso 1 "Contexto industrial": diagrama inyección → nido → inspección → OK/NOK + estado de fuentes (dimensional: histórico; proceso: simulado; ML: precalculado).

Archivos previstos: `frontend/src/features/demo/*`, `frontend/src/lib/demo/*`, `App.tsx`, `Sidebar.tsx`.
Pruebas: navegación del stepper, restaurar escenario, badge renderiza los 5 orígenes.
Hecho cuando: DoD #1 se cumple con contenido en cada paso (aunque sea placeholder etiquetado).

**Resultado F1 (26/oct/2026):**
- Backend: `app_edition` / `demo_client_label` en `core/config.py`; `core/edition.py` (`require_industrial_edition` → 404 en metrology); `GET /api/v1/meta` (`api/v1/meta.py`, `schemas/meta.py`). Variables documentadas en `.env.example` y `backend/.env.example`.
- Frontend: `lib/edition/` (`EditionProvider`, `useEdition`, `RequireEdition`; default fail-closed = metrology), entrada "Demo industrial" en `Sidebar` solo en industrial, rutas `/demo/industrial-quality` y `/:stepId` en `App.tsx`.
- Demo: `features/demo/DemoShell.tsx` (stepper de 7 pasos, Anterior/Siguiente, "Restaurar escenario demo"), `DemoHomePage.tsx` ("Iniciar demo", 4 accesos rápidos, leyenda de procedencia), `DemoStepPage.tsx`, `steps/ContextStep.tsx` (flujo inyección→OK/NOK + estado de fuentes), `steps/StepPlaceholder.tsx` (contenido previsto por fase, sin gráficas falsas).
- Procedencia: `lib/demo/origin.ts` + `components/ui/OriginBadge.tsx` (`OriginBadge`, `OriginLegend`).
- Estado de demo: `lib/demo/DemoSessionProvider.tsx` (escenario activo; reset solo de estado del cliente).
- Desviación: el nombre del cliente va por env var en lugar de JSON privado (más simple, mismo efecto D1).

### F2 — Generador IIoT determinista + API de señales

**Objetivo:** señales de proceso simuladas verosímiles, reproducibles y servidas por ventana/resolución.

Entregables:
- Módulo puro `seed/generators/process_signals.py` (o `backend/app/engines/process_simulation/` si se sirve desde el backend; preferir un solo lugar importable por ambos) con:
  - Árbol planta → área → línea → máquina → grupo → canal; cada canal con `signal_id`, unidad, frecuencia, tipo analógico/digital/discreto.
  - Señales del prompt: T cilindro, T molde, P inyección, P mantenimiento, velocidad inyección, posición tornillo, t enfriamiento, t ciclo, corriente/vibración, nido activo, digitales (auto, ciclo activo, alarma, OK/NOK proceso), contador de disparos/`cycle_id`.
  - Perfil cíclico por fases (espera → inyección → mantenimiento → enfriamiento → expulsión), no ruido blanco.
  - ≥ 4 escenarios en YAML versionado: `normal`, `thermal_drift`, `pressure_setpoint_change`, `intermittent_fault_cavity_change`, con eventos/anotaciones.
  - Señales de control no informativas (p. ej. humedad ambiente, voltaje auxiliar).
  - Dos resoluciones: resumen (horas/días, agregado por ciclo) y alta frecuencia (10–100 ms) solo en ventanas cortas.
  - Semilla fija → misma salida; `source_type='SIMULATED'`, `scenario_id`.
  - Sin fuga: ninguna señal se condiciona a etiquetas NOK reales.
- Endpoints (`backend/app/api/v1/industrial_signals.py`, permiso D4):
  - `GET /api/v1/industrial-signals/tree`
  - `GET /api/v1/industrial-signals/scenarios`
  - `GET /api/v1/industrial-signals/series?scenario&signals&start&end&max_points`
  - `GET /api/v1/industrial-signals/events?scenario&start&end`
- Downsampling (LTTB o min/max) como función pura en `engines/`.
- Adaptador reemplazable: interfaz `SignalSource` con implementación `SimulatedSignalSource` (futuro: OPC UA / iba / PLC).

Pruebas: determinismo (misma semilla → mismo hash), forma cíclica, cada escenario produce sus eventos, downsampling preserva extremos, API con auth/RBAC, límites de `max_points` y rango.
Riesgos: volumen → nunca materializar más que la ventana pedida.

**Resultado F2 (26/oct/2026):**
- Ubicación final: `backend/app/engines/process_simulation/` (no `seed/`: la imagen Docker del backend solo copia `backend/`). Escenarios como datos Python versionados (`scenarios.py`), no YAML. README del módulo incluido. `GENERATOR_VERSION = "process-sim-1.0.0"`.
- Modelo: línea de tiempo de ~980 ciclos (~29 s) en 8 h desde 2026-10-20T06:00Z, cacheada; fases cierre → llenado → mantenimiento → enfriamiento (con dosificación) → apertura. Ruido por hash del índice de muestra → el valor de un instante no cambia con el zoom.
- 18 canales × 2 máquinas (`INY-01` con desviaciones de escenario, `INY-02` nominal como comparativo); 12 nidos en mesa rotativa; señales de control `ambient_humidity` y `aux_voltage` (`informative=false`).
- Escenarios: `normal`, `thermal_drift` (+8 °C molde, alarma > 60 °C), `pressure_setpoint_change` (620 → 560 bar, más dispersión, 4 picos), `intermittent_fault_cavity_change` (5 fallos de accionamiento + paro de 20 min por cambio de inserto). `process_ok` sale solo de la ventana de proceso simulada (sin fuga).
- Resolución: canales rápidos (10 Hz) en crudo hasta 6 000 muestras (~10 min) + vértices de cada ciclo; en ventanas largas, envolvente por ciclo. Canales lentos (1 Hz) en malla uniforme ≤ 6 000 + bordes de alarmas/paros. Después, min/max (`engines/timeseries/downsample.py`). 8 h completas de las 18 señales ≈ 1,1 s.
- API `api/v1/industrial_signals.py`: `/tree`, `/scenarios`, `/series` (≤ 12 señales, `max_points` 50–5000, timestamps con zona horaria, puntos `[epoch_ms, valor]`), `/events`. Permiso `live_monitor.stream` (documentado en `docs/security/rbac.md`); 404 en metrology.
- Frontend: `lib/industrial-signals/` (tipos + cliente) y `features/demo/steps/IiotSourcesStep.tsx` (selector de escenario, inventario por máquina/grupo, eventos con `T+hh:mm`).
- Interfaz `SignalSource` reemplazable: **no** se creó como clase; el contrato reemplazable es la API REST (`source_type` en cada respuesta). Crear la abstracción cuando exista una segunda fuente real (CLAUDE.md §4: sin abstracciones especulativas).

### F3 — Explorador de señales estilo iba Analyzer

**Objetivo:** el módulo más llamativo del demo, totalmente interactivo.

Entregables (`frontend/src/features/industrial-analytics/`, `frontend/src/lib/industrial-signals/`):
- Árbol con búsqueda, expandir/colapsar, unidad, frecuencia, tipo, badge SIMULADO.
- Arrastrar señal al área de gráficas + botón "Agregar".
- Tracks múltiples y superposición; quitar, ocultar, reordenar, color, leyenda; un eje Y por unidad (nunca mezclar bar y °C en el mismo eje). Señales digitales como pista escalonada.
- Eje X temporal común; zoom por selección (brush), pan, ventanas predefinidas, reset.
- Cursores A/B: tiempo, valor por traza y Δt / Δvalor; tooltip sincronizado entre tracks.
- Tabla de señales visible/color/unidad/actual/mín/máx (como la referencia visual "Monitoring").
- Eventos como franjas/marcadores; "saltar a evento".
- Reproducción play/pause/velocidad + selector de escenario, rotulado "Replay de simulación".
- Al hacer zoom, se piden datos a mayor resolución al backend (no se envían series masivas).

Pruebas: lógica de cursores (Δt), asignación de ejes por unidad, reducer de estado del explorador (agregar/quitar/ocultar), hook de carga de series con MSW.
Hecho cuando: DoD #4, #5, #6.

### F4 — Correlación, regresión y caso sintético causal

**Objetivo:** cálculos reales, no decorativos.

Entregables:
- Engine puro `backend/app/engines/statistics/regression.py` (o TS si basta en cliente; preferir backend para reusar en pruebas): alineación temporal por ventana/ciclo, Pearson r, OLS (pendiente, intercepto, R²), n pares, barrido de lag (correlación cruzada) con lag óptimo.
- Panel: selector X/Y, scatter con recta, ecuación, R², r, n, lag; solo sobre el rango visible/seleccionado.
- Ejemplos preparados: variable informativa (T molde vs. dimensión en Vista B) vs. no informativa (señal de control → r≈0).
- **Vista A** (dimensional histórico + sensores simulados superpuestos por tiempo): banner "Unión ilustrativa por tiempo; relación no validada".
- **Vista B** (todo sintético, mecanismo causal impuesto): sensores → dimensión → NOK sintéticos; banner "Simulación: relación causal impuesta".

Pruebas: regresión contra vectores calculados a mano (y=2x+1 → R²=1), r de series independientes ≈ 0, alineación con desfase conocido recupera el lag, determinismo de Vista B.
Hecho cuando: DoD #7.

### F5 — Dashboard de calidad dimensional (nidos)

**Objetivo:** pasos 2 y 3 del recorrido con filtros que sí filtran.

Entregables:
- Dataset dimensional sintético "estilo cliente": piezas, 2+ máquinas, N nidos (uno anómalo), turnos, ~20 variables (`PinsLength`, `PinPosition`, …) generado en `seed/`, rotulado ficticio; con el nido crítico configurable para coincidir con la narrativa del perfil privado (D1).
- Migración `0009` `cavity_code` (D3) y soporte en generador.
- Endpoint de agregados `GET /api/v1/quality-analytics/summary|by-cavity|pareto|heatmap|distribution` (o extensión de `measurements.py`) reusando engines SPC/compliance; se distinguen límites de especificación vs. de control.
- UI: KPIs (piezas, mediciones, OK/NOK, tasa NOK, dimensiones críticas, nidos de mayor riesgo), tendencia NOK día/hora/turno, Pareto, tasa por nido, heatmap nido × variable, histograma, boxplot, serie dimensional, Cp/Cpk solo con tolerancias.
- Filtros coordinados (fecha, pieza, variable, nido, máquina, lote); los que no existan en el dataset se deshabilitan con explicación.
- Pantalla con KPIs del informe histórico como bloque separado HISTÓRICO/PRECALCULADO con denominador, período y definición de NOK.
- Opcional: exportar CSV agregado.

Pruebas: agregados con dataset pequeño conocido, filtros cambian resultados, Cpk ausente sin tolerancias.
Hecho cuando: DoD #2.

### F6 — Importación CSV con mapeo de columnas

**Objetivo:** subir un CSV con formato distinto y ver analíticas que cambian.

Entregables:
- Endpoint de **preview** (primeras N filas, detección de delimitador/encoding, tipos inferidos, sugerencia de mapeo).
- UI de mapeo en `ImportPage`: fecha/hora, ID pieza/ciclo, variable, valor, OK/NOK, nido, tolerancias; formato ancho o largo.
- Adaptador en `connectors/` que convierte al esquema canónico sin modificar el flujo actual (el CSV demo estándar sigue funcionando igual).
- Validación: tipos, unidades, tiempos, duplicados, nulos; resumen aceptadas/cuarentena.
- Archivos grandes: **muestra** (tope configurable de filas / MB) con aviso "muestra de X filas (~Y % del archivo)"; ruta offline por lotes documentada como siguiente paso (no en request web).
- OK/NOK reportado por fuente vs. recalculado por especificación, rotulados distinto. Sin tolerancias → sin Cp/Cpk.
- El demo precargado funciona aunque falle la importación.
- Fixture sintético estructuralmente compatible en `seed/sample_files/` (formato largo y ancho). **Nunca** CSV reales del cliente en el repo.

Pruebas: preview y detección de delimitador, mapeo ancho/largo → filas canónicas, cuarentena por tipos inválidos, límite de muestra, regresión del import actual (`test_imports_api.py`).
Hecho cuando: DoD #3.

### F7 — Laboratorio ML/DL y oleadas NOK

**Objetivo:** relato honesto y visualmente sólido.

Entregables (`frontend/src/features/predictive/`):
- Fixture `PRECOMPUTED` (placeholder en repo; real vía D1) con: modelos (GB, MLP balanceado, MLP NOK=30), ROC-AUC, PR-AUC, recall, precisión, matrices de confusión, n de prueba, partición temporal, fecha del estudio.
- Barras comparativas, matrices de confusión, "costo de falsas alarmas" (FP por NOK detectado), callout: **DL no superó a ML tabular; falsas alarmas impiden rechazo automático**.
- Sin curvas ROC/PR inventadas: solo si llegan scores reales; si no, métricas agregadas y nota explícita.
- Módulo **Oleadas NOK**: línea de tiempo de episodios (sintéticos, Vista B, o histórico si se entrega), alertas antes/después del inicio, tiempo de anticipación por episodio, distinción "detección de persistencia" vs. "predicción del inicio".
- CUSUM experimental reutilizando `engines/experimental_ml/drift_cusum.py` sobre una serie seleccionada.
- What-if (presión, temperatura, ciclo) sobre el modelo de la Vista B, rotulado "HIPOTÉTICO — mecanismo sintético".
- Umbral precisión/recall interactivo **solo** si hay resultados por umbral reales/precalculados; si no, se omite.
- Lenguaje: indicio, asociación, hipótesis, requiere validación en planta.

Pruebas: render del fixture, evaluación por episodio (alerta antes del inicio cuenta, durante no), CUSUM sobre vector conocido.
Hecho cuando: DoD #9, #10.

### F8 — Oportunidad de integración, pulido, guía y handoff

Entregables:
- Paso 7 "Qué permitiría una integración real": PLC/OPC UA/iba → trazabilidad ciclo/pieza → modelo validado prospectivamente → alertas para ingeniería (con humano en el lazo, CLAUDE.md §2/§24). Mensaje central del prompt §13.
- Revisión de etiquetas de procedencia en todas las pantallas (DoD #11), textos en español, modo oscuro industrial + claro.
- Rendimiento: medir puntos por traza, lazy loading de rutas de demo.
- `docs/demo-industrial-quality.md`: levantar demo, cargar CSV, restaurar escenarios, pantallas, guion de 7–10 min, límites de interpretación.
- README de módulo para cada carpeta nueva (CLAUDE.md §10).
- Verificación: `npm run build`, `npm test`, `pytest` (importación, series, SPC, Live Monitor, nuevos), ruff/eslint; regresión de login, catálogo, importación, Live Monitor (DoD #12, #13).
- Check de confidencialidad: `seed/validation/confidentiality.py` ampliado; `git diff` sin nombre real ni datos del cliente (DoD #14).
- PR a `main` con resumen: real / simulado / precalculado / experimental, rutas, pruebas, limitaciones, próximos pasos PLC/iba, riesgos de deploy. **Sin merge ni deploy.**

### F9 — Despliegue de dos ediciones (metrology + industrial)

**Objetivo:** dos URLs en el VPS: versión actual y versión industrial, desde el mismo código. **Cada cambio en VPS, secretos, DNS o workflow de deploy requiere autorización explícita del usuario en esa sesión.**

Situación actual (`.github/workflows/deploy.yml` en `origin/main`): se dispara solo con push a `main`, hace `git reset --hard origin/main` en `/home/rene/projects/metro_intelligence`, usa `docker-compose.vps.yml` y borra contenedores con nombres fijos `metro-intelligence-backend-1/frontend-1`. **Los 3 últimos runs fallaron (~11–14 s)** → primero diagnosticar y arreglar.

Entregables:
- Diagnóstico y fix del deploy actual (leer logs del run con `gh run view --log-failed`).
- `docker-compose.vps.yml` parametrizado: nombre de proyecto (`-p`), puertos, volúmenes y `APP_EDITION` por instancia; sin nombres de contenedor fijos.
- Base de datos y bucket MinIO **separados** por edición (la industrial no toca datos de la actual).
- Archivos de entorno por instancia en el VPS (`.env.metrology`, `.env.industrial`), nunca en el repo; placeholders en `.env.example`.
- Workflow: un job (matrix) que despliega ambas instancias tras push a `main`, o disparo manual (`workflow_dispatch`) para la industrial durante las demos.
- Proxy/Nginx: dos subdominios (p. ej. `metro.<dominio>` y `industrial.<dominio>`), TLS en ambos.
- Seed: la instancia industrial carga escenarios demo de forma idempotente al arrancar (patrón de `backend/app/demo_data.py` con advisory lock), sin crear/borrar usuarios.
- Runbook en `docs/deployment-onpremise.md` (o `docs/deployment-editions.md`): cómo levantar, actualizar y revertir cada edición.

Pruebas: `docker compose config` válido para ambas instancias; smoke test post-deploy (`/health`, `/api/v1/meta` devuelve la edición correcta en cada URL); la edición metrology no expone rutas industriales.
Riesgos: recursos del VPS (RAM para 2× Postgres/MinIO/backend) → verificar capacidad antes; alternativa: un Postgres con dos bases.

---

## 4. Definition of Done (checklist de aceptación)

- [ ] 1. La demo abre y se recorre sin cargar archivos ni tocar código. (F1)
- [ ] 2. Dashboard con KPIs y varias gráficas coherentes, dataset rotulado. (F5)
- [ ] 3. Se carga un CSV representativo, se ve el mapeo y ≥ 2 analíticas cambian. (F6)
- [ ] 4. Árbol IIoT con señales analógicas/digitales, unidades y estado ficticio. (F2/F3)
- [ ] 5. Arrastrar/agregar 3 señales, tiempo común, zoom, quitar/ocultar; ejes por unidad. (F3)
- [ ] 6. Cursores A/B con tiempo, valor y Δt. (F3)
- [ ] 7. Scatter + regresión real con R²/coeficientes sobre datos alineados. (F4)
- [x] 8. Escenarios normal/deriva/anomalía reproducibles y restaurables sin borrar datos. (F2)
- [ ] 9. Lab ML/DL con cifras del informe, falsas alarmas y DL ≤ ML explícitos. (F7)
- [ ] 10. Oleadas NOK no confunde rachas detectadas con episodios prevenidos. (F7)
- [ ] 11. Cada pantalla distingue histórico / precalculado / simulado / experimental. (F8)
- [ ] 12. Sin regresiones en login, catálogo, importación, Live Monitor, navegación. (F8)
- [ ] 13. Pruebas de lógica nuevas pasan y el frontend compila. (todas)
- [ ] 14. Sin CSV sensibles, credenciales ni datos del cliente en el repo. (todas)

---

## 5. Riesgos

| Riesgo | Mitigación |
|---|---|
| Datos/nombre del cliente filtrados a repo público | D1; check de confidencialidad en F8; revisar `git diff --staged` en cada commit. |
| Recharts lento con muchas trazas/puntos | Downsampling backend, ≤ 2 000 pts/traza; plan B `uPlot`. |
| DnD frágil en algunos navegadores / presentador con touch | Botón "Agregar" siempre disponible. |
| CSV real incompatible o enorme | Preview + mapeo + muestra; fallback demo precargado. |
| Migración `0009` choca con otra rama | Verificar head único antes de crearla (CLAUDE.md §15). |
| Cifras del informe sin verificar (PDF no disponibles) | Marcar "pendiente de verificar"; pedir PDFs. |
| Deploy actualmente roto | No es objetivo; validar local + CI; reportar en PR. |
| Sobreprometer causalidad/predicción | Banners Vista A/B, lenguaje de hipótesis, sin métricas nuevas inventadas. |

---

## 6. Bitácora

| Fecha | Fase | Nota |
|---|---|---|
| 2026-10-26 | F0 | Reconocimiento hecho; rama `feat/industrial-quality-demo` creada desde `origin/main` `0f8ec0a`. PDFs e imágenes de referencia no encontrados localmente. Decisiones D1–D4 propuestas. |
| 2026-10-26 | F0 | D5 decidido: un código + `APP_EDITION` (metrology/industrial) en lugar de dos ramas; añadida F9 (despliegue de dos ediciones). Protocolo de sesión añadido: una fase por chat. Contexto confidencial del prompt en `demo-private/client-brief.md` (gitignored). |
| 2026-10-26 | F1+F2 | El usuario pidió avanzar el 25 % en una sola sesión → F1 y F2 hechas juntas. Pruebas: backend 1036 passed / 4 skipped (suite completa, Postgres local en :5433); frontend 120 passed (vitest), `tsc -b` limpio, `npm run build` OK. Arreglo de infraestructura de pruebas: `tests/conftest.py` reinicia el rate limiter de slowapi por prueba — en `origin/main` 40 pruebas fallaban por agotar el límite de 30 logins/min en la suite completa. DoD #8 ✅; DoD #4 parcial (árbol en API, explorador visual en F3). Siguiente: **F3**. |

---

## 7. Pendientes / ideas fuera de fase

- Recibir del usuario los PDF de los informes y las 4 imágenes de referencia → guardarlos en `demo-private/` (gitignored) y verificar cifras de `client-brief.md`.
- Vista por ciclo de inyección / comparativo de ciclos OK vs. NOK (opcional del prompt; solo si F3 queda estable).
- Importación offline por lotes para archivos de decenas de millones de filas (F6 solo hace muestra).
- Deuda previa (no introducida aquí): `ruff check app` reporta ~25 errores en archivos existentes (`demo_data.py`, `main.py`, `core/security.py`, `services/audit_service.py`…) y `ruff format` reformatearía ~15 archivos previos. Los archivos nuevos de IQ pasan ruff. El CI actual solo corre pruebas de `seed/`; los jobs backend/frontend siguen como comentario en `ci.yml`.
- Aviso de Vite: bundle > 500 kB (previo). En F8 considerar `lazy()` para las rutas de la demo.
- `.pyc` antiguos muestran rutas `C:\Users\renea\Proyectos\...` en tracebacks; es cosmético (borrar `__pycache__` si molesta).
