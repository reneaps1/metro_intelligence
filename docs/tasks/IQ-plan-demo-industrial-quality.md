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
| F3 | Explorador de señales estilo iba | ✅ Hecho | `feat/industrial-quality-demo` | Verificado en navegador (Edge headless, Playwright) |
| F4 | Correlación, regresión y caso sintético causal | ✅ Hecho | `feat/industrial-quality-demo` | Vista B completa; Vista A depende de F5/F6 |
| F5 | Dashboard de calidad dimensional (nidos) | ✅ Hecho | `feat/industrial-quality-demo` | Dataset sintético + informe privado; verificado en navegador |
| F6 | Importación CSV con mapeo de columnas | ✅ Hecho | `feat/industrial-quality-demo` | Ancho/largo, muestra, cuarentena; análisis en memoria (D6); verificado en navegador |
| F7 | Laboratorio ML/DL, oleadas NOK y predicción de alarmas | ✅ Hecho | `feat/industrial-quality-demo` | Cifras del brief (pendientes de PDF) + F7.b; verificado en navegador |
| F8 | Oportunidad de integración, pulido, guía y handoff | ✅ Hecho | PR #43 a `main` (sin merge) | Paso 7, guía, carga diferida, lint privado; regresión 20/20 |
| F9 | Despliegue de dos ediciones (metrology + industrial) | 🟨 Preparado en el repo | `feat/industrial-quality-demo` | Falta ejecución en VPS/secretos/DNS (autorización del usuario) |
| F10 | Convertidor offline y dataset REAL (backend) | ✅ Hecho | `feat/industrial-quality-demo` | Solo local (D8); verificado contra el export real en `demo-private/` |
| F11 | Pasos 2–3 sobre datos reales (frontend) | ✅ Hecho | `feat/industrial-quality-demo` | Verificado en navegador contra el dataset REAL local |
| F12 | Laboratorio IA sobre datos reales | ✅ Hecho | `feat/industrial-quality-demo` | Verificado en navegador contra el dataset REAL local |
| F13 | Proceso sintético en calendario real + Vista A | ✅ Hecho | `feat/industrial-quality-demo` | Verificado en navegador contra el dataset REAL local |
| F14 | Panel de calidad en línea: motor R1–R4 + API de repetición (backend) | ✅ Hecho | `feat/industrial-quality-demo` | Fuera del orden: pedido por el usuario el 28/oct (D11) |
| F15 | Panel de calidad en línea: vistas Andon, Mapa de proceso y Respuesta guiada (frontend) | ✅ Hecho | `feat/industrial-quality-demo` | Pantalla completa, botones Normal/Atención/Paro sobre momentos reales |
| F16 | Interfaz unificada: el lenguaje del panel en todo el banco de trabajo | ✅ Hecho | `feat/industrial-quality-demo` | Pedido por el usuario el 28/oct (D12); modo oscuro grafito |
| F17 | Normalización del número de nido (desfase del PLC) conservando el crudo | ✅ Hecho | `claude/gifted-cannon-5rrp1j` → PR a `feat/industrial-quality-demo` | Pedido por el usuario el 29/oct tras la presentación (D13) |
| F18 | Matriz nido × cavidad de molde + filtro por hora | ✅ Hecho | `claude/gifted-cannon-5rrp1j` | Pedido por el usuario el 29/oct |
| F19 | Dispersión X/Y de posición de pines contra tolerancia | ✅ Hecho | `claude/gifted-cannon-5rrp1j` | Pedido por el usuario el 29/oct; especificación privada (D13) |

Leyenda: ⬜ pendiente · 🟨 en curso · ✅ hecho · ⛔ bloqueado

Orden de ejecución: F1 → F2 → F3 → F4 → F5 → F6 → F7 → F8 → F9; después F10 → F11 → F12 → F13 (datos reales en local). Si el tiempo se acorta, F1–F4 + F7 son el mínimo presentable (DoD puntos 1–6 + relato honesto de modelos).

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
| D3 | Nido/cavidad en mediciones | No existe en el modelo. | Migración Alembic pequeña y reversible `0009`: columna nullable `cavity_code` en `measurement_runs` (+ índice). Sin tablas duplicadas. **Actualización F5:** no hizo falta para el dataset sintético (stateless). Se decide en F6 según cómo se persistan los CSV importados. **Actualización F6:** tampoco hizo falta: los CSV importados no se persisten (D6). Se reabre solo si se implementa la ruta offline por lotes hacia el historial. |
| D4 | Permiso RBAC para endpoints nuevos | Añadir permisos requiere migración y actualizar `rbac.md`. | Reusar `live_monitor:read` (misma naturaleza: replay/simulación de solo lectura) para señales y analítica demo; `imports` existentes para el mapeo. Documentar en `rbac.md`. |

D1–D4: el usuario no objetó → se aplican los defaults propuestos. Reabrir solo si aparece un bloqueo.

**D6 — Persistencia de CSV importados con mapeo (F6): en memoria, sin escribir.** Un CSV dimensional con mapeo es un *análisis exploratorio*, no una ingesta al historial inmutable de mediciones (eso sigue siendo `/imports`, formato del catálogo). El dataset resultante vive solo en la memoria del proceso, visible solo para quien lo importó, con TTL (`DIMENSIONAL_IMPORT_TTL_MINUTES`, default 240) y tope (3 por usuario, 12 en total). Nada va a PostgreSQL ni a MinIO, así que un archivo de cliente nunca queda guardado en un servidor de demo; solo se audita el evento (usuario, hash SHA-256 de lo analizado, conteos). Limitación: por proceso (un solo worker de uvicorn).

**D7 — Proceso sintético sobre el calendario real (F13): decidido por el usuario (28/oct/2026).** El escenario `real_calendar` se construye en ejecución desde el dataset REAL (inicio, fin, paros = huecos ≥ 20 min, número de nidos); no hay fechas de cliente en el código. La deriva simulada de `mold_temp` sigue la tasa horaria suavizada de rechazo real: relaja la regla de F2 (ninguna señal condicionada en etiquetas reales) **solo para este escenario**, marcado con `Scenario.quality_driven` → `causal_imposed`, y la Vista A dice «relación impuesta por construcción». Nunca se presenta como medición de planta.

**D8 — El dataset REAL es solo local (F10).** Se carga desde `DEMO_REAL_DATASET_PATH` (manifest en una carpeta privada, p. ej. `demo-private/real-dataset/`); el servicio lo ignora con `APP_ENV=production`; `docker-compose.vps.yml`, el script y el workflow de deploy nunca lo pasan (test en `tests/deploy`). El convertidor no escribe identificadores de pieza ni rutas de origen y se niega a escribir dentro del repo salvo en `demo-private/`. Subirlo a un servidor requiere autorización expresa del cliente.

**D9 — Hora local de planta (F10).** El dataset REAL lleva `utc_offset_minutes` (offset `GMT±HHMM` explícito de la fuente). Los buckets de día/hora y el Cpk diario de ese dataset usan hora de planta; los demás datasets siguen en UTC.

**D10 — Base de NOK explícita (F10).** `nok_basis="spec"` (cotas fuera de tolerancia) para sintético e importados, sin cambios; `nok_basis="reported"` para REAL, cuya fuente no trae LSL/USL ni unidades: veredicto total de la máquina, y cada pieza NOK se atribuye a la **primera estación que falla en el orden del proceso** (así una pieza rechazada en una estación temprana no cuenta también como fallo de las posteriores que no llegó a pasar).

**D12 — Interfaz unificada (F16): decidido por el usuario (28/oct/2026).** Tras revisar una maqueta Hoy/Propuesta (fuera del repo) el usuario pidió llevar el lenguaje visual del panel de calidad en línea a todo el banco de trabajo: tarjetas con banda de encabezado en mayúsculas, KPIs con cifra monoespaciada grande, gráficas neutras con referencias rotuladas, avisos neutros, chips y controles segmentados con el estado seleccionado del panel. Modo oscuro **grafito** (fondo `#1B1E22`), más cercano al negro sin llegar a negro puro. Color: «no saturar; un leve acento donde hay que resaltar» → un único acento NOK atenuado (`--wb-nok`) para piezas NOK, el peor grupo y outliers; rojo y ámbar solo para alarmas. Alcance: solo `.wb-root` (la edición de metrología no cambia).

**D13 — Reglas y especificaciones del dataset REAL fuera del código (F17–F19): decidido por el usuario (29/oct/2026).** Tras la presentación con el dataset REAL apareció un «nido 13» que no existe: el registro del número de nido trae a veces un desfase fijo (nido real + 12; p. ej. 13 en lugar de 1). La corrección es una regla `remap` en el mapping privado, no código específico del cliente: se valida (origen fuera del rango válido, destino dentro), se cuenta en el reporte, marca la pieza con la bandera 8 y **conserva el valor crudo** (`nest_raw`, formato `pieces-v2`). Igualmente, los nominales y tolerancias de posición de pines (F19) viven en un archivo privado (`DEMO_REAL_SPEC_PATH`), nunca en el repo. Cambiar la regla exige volver a convertir; el panel «Calidad del dato» muestra cuántas piezas se remapearon.

**D11 — Panel de calidad en línea (F14–F15): decidido por el usuario (28/oct/2026).** Tras un prototipo con tres propuestas (fuera del repo) el usuario pidió las tres como vistas de un mismo panel, con datos de **repetición real** (el backend repite el dataset activo y un motor de reglas decide las alarmas) y en una **pantalla aparte** a pantalla completa. Los botones Normal/Atención/Paro saltan a momentos reales del dataset; no se inyectan paros simulados sobre datos medidos. Reconocimientos y acciones son estado de la sesión, no se guardan.

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

**Resultado F3 (26/oct/2026):**
- `frontend/src/features/industrial-analytics/`: `SignalExplorer.tsx` (orquesta), `SignalTree.tsx` (búsqueda, expandir/colapsar, DnD con MIME `application/x-mi-signal` + botón «+» accesible; grupos de la máquina principal abiertos por defecto), `TrackChart.tsx` (Recharts, eje X común, un eje Y por unidad, brush-zoom, clic = cursor, eventos como franjas/líneas con marcadores `E<n>`, `syncId` para tooltip sincronizado), `SignalTable.tsx` (ver/color/unidad/A/B/Δ/mín./máx./muestras, subir/bajar/quitar). README del módulo.
- Lógica pura en `lib/industrial-signals/explorer.ts` (reducer ≤ 8 trazas, agrupación por unidad, `valueAt` lineal o escalón, zoom/pan con límites, formatos) + `useSeries.ts` (debounce 120 ms, descarta respuestas viejas, re-pide resolución al hacer zoom).
- Distribución «Pistas por unidad» (default) o «Superpuesto» (ejes múltiples, aviso si > 3 unidades); presets Todo/1 h/10 min/1 min; replay ×10/×60/×300 rotulado «Replay de simulación»; «Ir» a evento (ventana ±5 min + cursor A); «Vista sugerida para este escenario» para no abrir vacío.
- Honestidad: en series en modo envolvente, los valores de cursor se muestran como `≈` con aviso de hacer zoom.
- Paso 4 de la demo = `steps/IiotLabStep.tsx` (+ `steps/ScenarioPicker.tsx` compartido). Se eliminó `IiotSourcesStep.tsx` (lo reemplaza el explorador).
- **Verificación en navegador** (Edge headless vía `playwright-core` en scratchpad, backend `APP_EDITION=industrial` contra BD desechable `metro_iq_e2e`, borrada al terminar): 17/17 comprobaciones — login, recorrido 1→7, vista sugerida, zoom por barra y por arrastre, cursores A/B con Δt, DnD desde el árbol, ir a evento, superpuesto con 3 ejes, replay, presets de correlación, desfase óptimo, dispersión, reset; 0 errores de consola, 0 excepciones, 0 HTTP ≥ 400. Modo oscuro revisado por captura. Hallazgos corregidos en la misma sesión: valores `≈` en envolvente, etiquetas de eventos encimadas → marcadores `E<n>`, celdas que se partían.

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

**Resultado F4 (26/oct/2026):**
- Motor puro `backend/app/engines/statistics/regression.py` (`linear_fit`: OLS + Pearson con `fsum`; `None` si n < 3 o varianza cero).
- `process_simulation/alignment.py`: modo `cycle` (un par por disparo = trazabilidad simulada; perfil → pico del ciclo, continuas → media en el ciclo) y modo `time` (x(t) vs y(t+lag), malla de 1 200 puntos); barrido de desfase (−600…900 s cada 30 s, o −10…10 ciclos); dispersión adelgazada a ≤ 1 500 pares.
- **Vista B** (generador 1.1.0): canales `dim_pins_length` / `dim_nok` (grupo «Calidad sintética · causalidad impuesta», `causal_imposed=true`): `12.000 + 0.006·ΔT_molde − 0.0006·(P_mant − 620) + offset de nido + ruido`, tolerancia ±0.050 mm, publicados 300 s después del ciclo; nido 7 con inserto desgastado (+0.04 mm) hasta el cambio de inserto. RNG separado → las señales de proceso no cambian (sin fuga).
- Resultados reproducibles: P_mant→longitud (cambio de setpoint) r = −0.91, R² = 0.83, pendiente −0.00059 mm/bar; T_molde→longitud (deriva) r = 0.90, pendiente 0.0061 mm/°C; humedad (control) r = 0.05; unión por tiempo sin desfase r ≈ −0.01 → con el desfase óptimo 300 s r = −0.31.
- API `GET /api/v1/industrial-signals/correlation` (`mode`, `lag`, `scan`, ventana; 422 si `cycle` mezcla máquinas o lag fuera de rango).
- UI `CorrelationPanel.tsx` + paso 5 `steps/CorrelationStep.tsx`: 4 presets, selectores X/Y, modo por ciclo/por tiempo, desfase, tarjetas n / r / R² / ecuación / desfase, frase en lenguaje de «asociación», dispersión + recta, barrido con «Usar desfase óptimo», banner «Simulación: relación causal impuesta» cuando aplica, tarjeta de **Vista A pendiente** (requiere datos dimensionales de F5/F6).
- Pendiente para F5/F6: Vista A (mediciones históricas + sensores simulados, unión ilustrativa por tiempo).

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

**Resultado F5 (26/oct/2026):**
- Motor puro `backend/app/engines/quality_analytics/` (README): `DimensionalDataset` columnar e independiente de la fuente (F6 solo debe producir uno), `synthetic.py` (SIMULADO, semilla fija, 7 días × 2 máquinas × 12 nidos × 10 cotas = 60 480 piezas; mecanismos documentados: nido crítico `DEMO_CRITICAL_NEST` (default 4), 4 oleadas NOK, desgaste de herramienta + cambio en día 3.5, dispersión en turno C, contracción en lote MAT-C, coplanaridad INY-02) y `analytics.py` (KPIs con denominadores, IC de Wilson, riesgo relativo, tendencia día/hora/turno, Pareto con ↑/↓, heatmap, histograma, boxplots, Cp/Cpk e I-MR con los motores SPC existentes, Cpk diario). Resultado por defecto: tasa NOK 1.59 %, nido 4 9.2 % (RR ≈ 10×).
- Sin migración: el dataset demo es stateless (D3 se pospone a F6).
- Resumen del informe (PRECALCULADO) vía `DEMO_REPORT_SUMMARY_PATH` (`services/report_summary_service.py`): JSON privado validado (≤ 256 KB); si falta o es inválido, ejemplo ficticio marcado «Ejemplo ilustrativo». Cifras reales en `demo-private/report-summary.json` (gitignored).
- API `api/v1/quality_analytics.py`: `/datasets`, `/overview`, `/variable`, `/report-summary` (permiso `measurement.measurement_result.read`, 404 en metrology). Variables nuevas en `.env.example`.
- Frontend `features/quality-analytics/` (README): pasos 2 y 3 con filtros coordinados persistentes en la sesión de demo (se limpian con «Restaurar escenario»), filtros no soportados deshabilitados con explicación, CSV agregado por nido, «Verdad conocida del dataset sintético». Procedencia de pasos 2/3 corregida a SIMULADO (+ PRECALCULADO en el informe) y tabla de fuentes del paso 1 actualizada.
- Verificación en navegador: 9/9 (KPIs, filtro por nido cambia datos, tendencia horaria, informe privado cargado, Cpk, boxplot por turno, Cp unilateral explicado, filtros persisten y se reinician) + regresión F1–F4 17/17, 0 errores de consola. Hallazgos corregidos: heatmap cortaba el nido 12, etiquetas del Pareto cortadas, Cpk «1» → «1.00», plural de eventos, distribución de tarjetas.
- **Coherencia narrativa:** con el informe privado cargado, hay que desplegar con `DEMO_CRITICAL_NEST` igual al nido crítico del informe (valor en `demo-private/client-brief.md`); si no, el sintético y el informe señalan nidos distintos. Incluido en F9.

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

**Resultado F6 (26/oct/2026):**
- Adaptador puro `backend/app/connectors/dimensional_csv.py` (README en `app/connectors/`): `sniff()` detecta codificación (UTF-8/Windows-1252), delimitador (`, ; tab |`), decimal, tipos por mayoría, orden de fecha y sugiere el mapeo (alias ES/EN/DE); `build_dataset()` aplica el mapeo en formato largo (pivotea a piezas) o ancho y produce un `DimensionalDataset` con `source_type="IMPORTED"`. Cada fila rechazada va a cuarentena con su motivo (columnas, fecha, variable vacía, nulo, no numérico, unidad distinta, duplicado). Mismo blindaje que `manual_upload` (firmas binarias, inyección de fórmulas).
- API (`api/v1/quality_imports.py`, edición industrial, permiso `measurement.imported_file:create`, rate limit, auditoría): `POST /quality-analytics/imports/preview`, `POST /quality-analytics/datasets`, `DELETE /quality-analytics/datasets/{id}`. Los endpoints de F5 aceptan el id del dataset importado (solo su dueño). Persistencia: **D6** (memoria, TTL, nunca BD/MinIO). Archivos grandes: el navegador manda solo el inicio y el informe dice «muestra de X filas (~Y % del archivo)»; config `DIMENSIONAL_IMPORT_MAX_ROWS/_MAX_MB/_TTL_MINUTES`.
- Motor F5: OK/NOK de la fuente (`reported_nok`) separado del recalculado por especificación (`summary.source_reported`: ambos NOK / solo fuente / solo recalculado / ambos OK); variables sin tolerancia → sin NOK por spec ni Cp/Cpk y sin «nido de mayor riesgo»; `Variable.from_limits()` (sin nominal en la fuente no se muestra uno).
- UI: `DimensionalImport.tsx` (soltar archivo, delimitador/decimal/fechas, largo/ancho, mapeo por rol con tipo inferido, vista previa con rol por columna, tolerancias tecleadas en formato ancho, informe de aceptadas/cuarentena/muestra) en la página de importación (solo edición industrial) y dentro de los pasos 2/3 («Importar CSV propio», selector de dataset, «Descartar archivo»). Tarjeta «OK/NOK reportado por la fuente vs. recalculado», el informe privado se oculta para archivos importados y las insignias de procedencia del paso pasan a «Histórico».
- Fixtures ficticios deterministas `seed/sample_files/mi_demo_dimensional_{long,wide}.csv` (generador `seed/scripts/generate_dimensional_samples.py`, README con resultados esperados). Largo: 5 filas en cuarentena, NOK 2.19 %, nido 11 con RR 37.5×, fuente 5.0 % NOK (27 piezas solo NOK para la fuente). Ancho con tolerancias tecleadas: 3 en cuarentena, NOK 11.2 % (lote LOT-M2).
- Sin migración (D3 sigue sin hacer falta). Ruta offline por lotes para archivos completos: documentada en `app/connectors/README.md`, no implementada.

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

**F7.b — Predicción experimental de alarmas/fallas de máquina** (añadido 26/oct/2026 a petición del usuario; ~½ fase extra):
- Historial simulado largo (semanas, varias semillas) en el simulador de proceso: fallas aleatorias (proceso de Poisson con tasa que cambia por desgaste/mantenimiento) con **precursores** físicos (p. ej. vibración y corriente que suben horas antes), más mantenimientos que resetean el riesgo. Fallas sin precursor también existen (no todo es predecible).
- Features por ventana: frecuencia de fallas/alarmas recientes (1 h, 8 h, 24 h), tiempo desde la última falla/mantenimiento, tendencia de vibración/corriente.
- Modelo simple y explicable (regresión logística, pura en Python) con partición temporal train/test, comparado contra **líneas base**: «si hubo falla en la última hora → alertar» y tasa constante.
- Evaluación honesta: por episodio de falla, tiempo de anticipación, falsas alarmas por turno, matriz de confusión, curva precisión/recall por umbral (calculada sobre scores reales del modelo simulado). Coeficientes visibles (qué feature pesa).
- UI en paso 6: timeline de fallas reales-simuladas vs. alertas del modelo, umbral interactivo, tarjeta de limitaciones. Rotulado **EXPERIMENTAL · datos simulados**; nota de qué haría falta en planta: historial de alarmas del PLC, registro de paros y mantenimiento, etiquetado de causas.
- Sin fuga: el label (falla en las próximas N horas) nunca entra como feature; validación sobre semillas/periodos no vistos.

Pruebas: render del fixture, evaluación por episodio (alerta antes del inicio cuenta, durante no), CUSUM sobre vector conocido; F7.b: regresión logística contra vector conocido, ventana de features sin información futura, la línea base y el modelo se evalúan sobre el mismo test.
Hecho cuando: DoD #9, #10 (+ F7.b con métricas por episodio y comparación contra línea base).

**Resultado F7 (26/oct/2026):**
- Laboratorio ML/DL (`services/model_lab_service.py`, `GET /predictive/model-lab`): cifras PRECALCULADAS desde un JSON privado (`DEMO_MODEL_LAB_PATH`, D1) o un placeholder ficticio rotulado. El servicio deriva de cada matriz de confusión las falsas alarmas por NOK detectado y la tasa de alerta, y marca `consistent=false` si recall/precisión no cuadran con la matriz; exige el mismo conjunto de prueba en todos los modelos. La conclusión DL vs. ML se calcula (PR-AUC), no se escribe. Sin curvas ROC/PR ni umbral: el estudio solo trae métricas agregadas. `demo-private/model-lab.json` (gitignored) creado con las cifras del brief; las matrices de los MLP se reconstruyeron desde recall/precisión/~FP y se rotulan «aproximadas». Con las cifras privadas cargadas, el mejor DL no supera al ML tabular (cifras solo en `demo-private/`).
- Oleadas NOK (`engines/experimental_ml/nok_waves.py`, `services/predictive_service.py`, `GET /predictive/nok-waves`): regla de persistencia («≥ k NOK en los últimos w grupos», solo pasado) evaluada por episodio independiente contra las 4 oleadas inyectadas en el dataset sintético de F5 (verdad conocida): anticipada / detectada ya iniciada / no detectada, retraso, fracción de la oleada aún por delante, falsas alarmas debounced. Con w=5, k=4: 0 de 4 anticipadas, 4 de 4 detectadas en 4–20 min con ~96 % de la oleada aún por delante, ~0.6 falsas alarmas/día por máquina.
- CUSUM (`GET /predictive/cusum`): `drift_cusum` (sin cambios) sobre series horarias del dataset sintético; presets con su verdad conocida, incluido Coplanaridad INY-02, donde alarma sin mecanismo inyectado → se muestra como falso positivo del método.
- What-if (`engines/process_simulation/what_if.py`, `GET /predictive/what-if`): evalúa la fórmula exacta de la Vista B (presión, ΔT molde, nido, inserto desgastado); P(NOK) = cola normal. Rotulado HIPOTÉTICO. El tiempo de ciclo no está en el mecanismo y se dice en vez de ofrecerlo como palanca. `generator.py`: `nest_offsets()` extraído sin cambiar la secuencia aleatoria.
- **F7.b** (`process_simulation/failure_history.py`, `experimental_ml/failure_prediction.py`, `GET /predictive/failure-study`): 9 semanas × 4 máquinas simuladas, fallas por desgaste (~70 % con precursor de vibración/corriente), regresión logística IRLS en Python puro, partición temporal (6 semanas train / 3 test), líneas base «falla en la última hora» y «tasa constante» sobre las mismas filas. Umbral 0.5: 15 de 21 fallas anticipadas (14/14 con precursor, 1/7 sin precursor), anticipación media 2.8 h, 0.07 falsas alarmas por turno; PR-AUC 0.399 vs. 0.063 de ambas líneas base.
- UI paso 6 (`features/predictive/`, `steps/AiStep.tsx`): cinco pestañas con insignias de procedencia por panel, umbral interactivo solo en F7.b (scores reales simulados), tarjeta de limitaciones y «qué haría falta en planta».

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

**Resultado F8 (26/oct/2026):**
- Paso 7 `steps/IntegrationStep.tsx`: cadena máquina → conector en planta → trazabilidad ciclo ↔ pieza → modelo validado → alertas → decisión humana; tabla «hoy en la demo vs. con integración» con la procedencia de lo actual; qué haría falta de planta; camino de validación en 4 etapas; mensaje central. `StepPlaceholder` eliminado (ya no quedan pasos pendientes).
- Procedencia (DoD #11): cada paso declara sus insignias y cada panel las suyas; el paso 1 incluye ahora los CSV importados y la predicción de fallas. Revisado en claro y oscuro.
- Rendimiento: pasos 2–6 con `lazy()` (chunks de 10–33 kB) y Recharts en su propio chunk; el código de la app bajó de 735 kB a 208 kB (el chunk de Recharts, 548 kB, es la librería). Límite del aviso de Vite en 600 kB, comentado.
- Guía `docs/demo-industrial-quality.md` (en español por su público): levantar, usuarios, configuración privada, guion de 7–10 min con mensajes clave, CSV, procedencia por pantalla, límites, problemas frecuentes. READMEs nuevos: `features/demo`, `engines/experimental_ml`, `engines/statistics`.
- Confidencialidad (DoD #14): `seed/validation/confidentiality.py` añade un escaneo de todos los archivos versionados contra una lista privada (`demo-private/forbidden-terms.txt` o `CONFIDENTIAL_TERMS_FILE`, nunca en el repo; en CI se omite). Más prueba de la prueba y lint de los identificadores de los CSV dimensionales.
- Verificación (DoD #12/#13): backend 1177 passed / 4 skipped; frontend 172 passed, `tsc -b` limpio y build OK sobre el árbol exacto del commit (exportado aparte); lint de confidencialidad 14 passed (con la lista privada, sin coincidencias); navegador 20/20 (login, catálogo, importación, Live Monitor, los 7 pasos en claro y oscuro, edición metrology con rutas industriales en 404), 0 errores de consola. ESLint: el repo no tiene configuración (`eslint.config.*`); queda en §7.

### F9 — Despliegue de dos ediciones (metrology + industrial)

**Objetivo:** dos URLs en el VPS: versión actual y versión industrial, desde el mismo código. **Cada cambio en VPS, secretos, DNS o workflow de deploy requiere autorización explícita del usuario en esa sesión.**

Situación actual (`.github/workflows/deploy.yml` en `origin/main`): se dispara solo con push a `main`, hace `git reset --hard origin/main` en `/home/rene/projects/metro_intelligence`, usa `docker-compose.vps.yml` y borra contenedores con nombres fijos `metro-intelligence-backend-1/frontend-1`. **Los 3 últimos runs fallaron (~11–14 s)** → primero diagnosticar y arreglar.

Entregables:
- Diagnóstico y fix del deploy actual (leer logs del run con `gh run view --log-failed`).
- `docker-compose.vps.yml` parametrizado: nombre de proyecto (`-p`), puertos, volúmenes y `APP_EDITION` por instancia; sin nombres de contenedor fijos.
- Base de datos y bucket MinIO **separados** por edición (la industrial no toca datos de la actual).
- Archivos de entorno por instancia en el VPS (`.env.metrology`, `.env.industrial`), nunca en el repo; placeholders en `.env.example`.
- Instancia industrial del cliente: `DEMO_CLIENT_LABEL`, `DEMO_CRITICAL_NEST` (coherente con el informe), `DEMO_REPORT_SUMMARY_PATH` y `DEMO_MODEL_LAB_PATH` (IQ-F7) apuntando a copias privadas de los JSON en el VPS (fuera del repo y de la imagen). Valores en `demo-private/client-brief.md`.
- Workflow: un job (matrix) que despliega ambas instancias tras push a `main`, o disparo manual (`workflow_dispatch`) para la industrial durante las demos.
- Proxy/Nginx: dos subdominios (p. ej. `metro.<dominio>` y `industrial.<dominio>`), TLS en ambos.
- Seed: la instancia industrial carga escenarios demo de forma idempotente al arrancar (patrón de `backend/app/demo_data.py` con advisory lock), sin crear/borrar usuarios.
- Runbook en `docs/deployment-onpremise.md` (o `docs/deployment-editions.md`): cómo levantar, actualizar y revertir cada edición.

Pruebas: `docker compose config` válido para ambas instancias; smoke test post-deploy (`/health`, `/api/v1/meta` devuelve la edición correcta en cada URL); la edición metrology no expone rutas industriales.
Riesgos: recursos del VPS (RAM para 2× Postgres/MinIO/backend) → verificar capacidad antes; alternativa: un Postgres con dos bases.

**Resultado F9 — preparación en el repo (26/oct/2026).** Por decisión del usuario, sin tocar VPS, secretos ni DNS:
- Diagnóstico (solo lectura, `gh api …/jobs/<id>/logs`): los runs de deploy del 13/oct fallan en 0.2 s con `dial tcp: lookup *** … no such host` → el secreto `VPS_HOST` no resuelve. No es un fallo del código. Arreglo: corregir el secreto (acción del usuario). El workflow ahora lo verifica antes de conectarse y falla con un mensaje claro sin imprimir el valor.
- `docker-compose.vps.yml` parametrizado por `INSTANCE`, `PUBLIC_HOST`, `APP_ENV_FILE`, `APP_NETWORK`, `DEMO_PRIVATE_DIR`; sin `container_name`; volúmenes y red de datos interna por edición; solo `metro_net_app` (Traefik) compartida y declarada `external`. Con los valores por defecto produce exactamente los nombres actuales de la edición metrology (sus datos no cambian).
- `scripts/deploy_edition.sh metrology|industrial`: valida que el env declare la edición, `config --quiet`, build, up y smoke test dentro del contenedor (`/health` + edición en ejecución). Omite la industrial mientras no exista `.env.industrial`.
- Workflow `deploy.yml`: verificación de `VPS_HOST`, ambas ediciones vía el script, `workflow_dispatch` para elegir edición, `concurrency` para no solapar deploys. Solo se activa tras merge a `main`.
- Usuarios: la instancia industrial no requiere sembrar; con `SEED_DEMO_USER_PASSWORD` y `APP_ENV` ≠ production el backend crea al arrancar el admin ficticio (patrón existente de `main.py`). Los pasos de la demo no necesitan datos en BD.
- `.env.example` documenta las variables del VPS y el bloque mínimo de `.env.industrial`; `.env.*` sigue en `.gitignore`.
- Runbook `docs/deployment-editions.md` (capacidad, preparación única, DNS/TLS, actualización, smoke test, reversión); enlazado desde `docs/deployment-onpremise.md`.
- Pruebas: `tests/deploy/test_vps_compose.py` (6) interpreta el compose para ambas ediciones sin Docker (nombres actuales intactos, nada compartido salvo el proxy, sin `container_name` ni puertos publicados, secreto faltante = error, workflow y script con sus guardas); añadido al CI. `docker compose config` real queda en el VPS (primer paso del script).
- **Pendiente (requiere autorización):** corregir `VPS_HOST`; comprobar capacidad; crear `.env.industrial` y `~/metro-private` en el VPS; registro DNS del subdominio industrial; merge del PR (dispara el deploy).

---

### F10 — Convertidor offline y dataset REAL en el backend ✅

**Objetivo:** que el sistema calcule sobre el período real completo del cliente (no la muestra del importador web), solo en local.

Entregables (hechos):
- `backend/app/connectors/long_signal_batch.py` (solo stdlib + pydantic): `inventory` y `convert` para exports largos `id,address,timestamp,value`. Mapping privado (dirección → rol: nido, cavidad de molde, veredicto total, estaciones en orden de proceso, variables, ciclo vacío, presets). Dos pasadas con particiones por hash en disco (memoria acotada), último valor por pieza y dirección, sentinels → faltante, agrupaciones fuera de rango → faltante, ciclos vacíos excluidos, bandera de firma repetida (dato congelado). Salida `pieces.csv.gz` determinista + `manifest.json` con reporte solo de conteos.
- `backend/app/connectors/pieces_file.py`: valida manifest y SHA-256 y construye un `DimensionalDataset` REAL (`nok_basis="reported"`, hora de planta, sin grupos).
- `backend/app/services/real_dataset_service.py`: carga por `DEMO_REAL_DATASET_PATH` con caché (ruta, mtime, tamaño), topes de MB/piezas, guarda de producción, precarga en hilo al arrancar y LRU del overview.
- Motor: `DimensionalDataset` con `mold_cavities`, `stations`/`station_nok`, `primary_fail`, `flags`, `utc_offset_s`, `nok_basis`, `has_groups`, `presets`, `data_quality` (todos opcionales); `analytics.overview` con Pareto por estación, tasas por cavidad de molde, mapa nido × estación, filtros `mold_cavities`/`stations`/`exclude_flags`; `variable_detail` agrupa por cavidad de molde.
- API: `/datasets` lista REAL primero; `/overview` y `/variable` aceptan los filtros nuevos; esquemas ampliados sin romper los existentes.

Pruebas: `tests/test_long_signal_batch.py` (8), `tests/test_real_dataset_service.py` (6), ajustes en los tests de analítica; `tests/deploy` con la guarda D8. Todo con datos ficticios.

### F11 — Pasos 2–3 sobre datos reales (frontend) ✅

Tipos y filtros nuevos (`moldCavities`, `stations`, `excludeSuspect`), selector con prefijo «Real ·», banner REAL, procedencia `REAL`+`PRECOMPUTED` para `real-*`, chips de cavidad de molde y de estaciones, Pareto por estación, gráfica de 32 cavidades, mapa nido × estación, tarjeta «Calidad del dato», presets, hora de planta, agrupar por cavidad de molde en el paso 3, arreglo de «Limpiar filtros» (no debe volver al dataset sintético), MSW con fixture REAL ficticio.

Hecho además: la tendencia por hora corta la línea en los huecos sin producción (no se dibuja un puente sobre un paro); prefijos «Real · / Demo · / Importado ·» en el selector; el dataset REAL se preselecciona hasta que el presentador elige otro (`datasetChosen`).

### F12 — Laboratorio IA sobre datos reales ✅

`/nok-waves` y `/cusum` con `dataset`/`target` (máquina validada contra el dataset, episodios retrospectivos para REAL), `/predictive/group-alarms` (regla ≥k rechazos en n piezas por cavidad/nido), `/predictive/piece-risk` (logística en Python puro con variables solo del pasado, último día como prueba, comparada con líneas base), model-lab multiestudio, paneles nuevos y textos sin «7 días»/INY sobre REAL. Reescribir los JSON privados con las cifras verificadas.

Hecho además: las insignias del paso 6 y el inspector reflejan el dataset que analiza el laboratorio (REAL + PRECALCULADO + SIMULADO + EXPERIMENTAL con datos reales); la selección de datos vive en la URL (`?datos=sintetico`).

### F13 — Proceso sintético en el calendario real y Vista A ✅

`Scenario` con calendario absoluto, `real_calendar` derivado del dataset REAL (D7), generador/alineación/API reciben el objeto escenario (semillas y tests de hash intactos), envolvente rápida para ~60 h, `/quality-analytics/process-join` y `QualityJoinPanel` con insignias REAL+SIMULATED+EXPERIMENTAL y banner de unión ilustrativa.

Hecho (contrato y notas de implementación en `docs/design/process-quality-join.md`): campos de calendario opcionales en `Scenario` (`start`, `duration_s`, `nest_count`, `quality_driven`) con salida idéntica byte a byte para los cuatro escenarios existentes; `build_calendar_scenario` puro (paros = huecos ≥ 20 min, deriva de `mold_temp` según la tasa horaria suavizada de rechazo) y servicio con caché sobre el dataset REAL; motor puro `quality_analytics/process_join.py` y `GET /quality-analytics/process-join` (intervalos de 15/30/60 min, desfase −180…180 min, barrido y desfase óptimo, notas); generador `process-sim-1.2.0`. En el escenario `quality_driven` la temperatura de molde ya no mueve la presión pico, para que las demás señales sirvan de control. Frontend: `QualityJoinPanel` sustituye la tarjeta «Vista A pendiente» del paso 5 (señal simulada, objetivo NOK, intervalo, desfase, tarjetas n/r/R²/pendiente, dispersión con recta y dos series en el tiempo cortadas en los paros) y el paso 5 suma REAL a su procedencia con el dataset REAL activo. La envolvente para ~60 h no hizo falta: `real_calendar` solo se usa en Vista A (ver §7).


### F14 — Panel de calidad en línea: motor y API (backend) ✅

Diseño y contrato: `docs/design/line-quality-panel.md`. Motor puro `app/engines/line_alarms/` (`line_alarm_engine`, `v1-experimental`): R1 racha NOK ≥ 5 (prioridad 1, parar línea), R2 nido ≥ 3× el resto en sus últimas 100 con al menos 25 NOK (prioridad 2), R3 tasa de las últimas 200 ≥ 2.5× la referencia de la línea (prioridad 2), R4 cavidad de molde ≥ 3× la referencia en sus últimas 150 (aviso). Umbrales relativos a la tasa de referencia del dataset para que funcionen igual en el sintético y en el REAL, con banda muerta (ISA-18.2) en R2–R4 para que una alarma no parpadee alrededor del umbral. Servicio que evalúa toda la secuencia una vez (caché) y endpoints `/line-panel/moments` (momentos reales de paro, atención y normalidad) y `/line-panel/replay` (ventana con piezas, estado de cada regla por pieza, eventos y conteos del turno).

### F15 — Panel de calidad en línea: tres vistas (frontend) ✅

Ruta `/demo/industrial-quality/panel-linea` a pantalla completa fuera del banco de trabajo (`features/line-panel/`, `lib/line-panel/`), accesos en el árbol, menú Ver e inicio de la demo. Vistas A Andon, B Mapa de proceso y C Respuesta guiada sobre una misma repetición; comandos R/A/F; barra del presentador con vistas 1/2/3, Normal/Atención/Paro (saltan a momentos reales), pausa, velocidad y tema. Spec visual: design-system.md §4.2.

### F16 — Interfaz unificada: el lenguaje del panel en todo el banco de trabajo ✅

Decisión D12. Tokens en `tokens.css` (`.wb-root`): modo oscuro grafito, marcas de datos generales (`--wb-bar`, `--wb-mark`, `--wb-mark-soft`, `--wb-ramp`, con `--lp-*` como alias para que el panel no cambie) y el acento NOK atenuado (`--wb-nok`, `--wb-nok-soft`). Hoja `features/demo/workbench/workbench.css` con estilos acotados a `.wb-root`: `Card`, `CardHeader` y `Button` solo llevan clases marcadoras (`ui-card`, `ui-card-h`, `ui-btn`), así que la edición de metrología conserva su aspecto. Piezas nuevas: `components/workbench/` (`Kpi`, `Notice`, `Key`) y `lib/demo/chartTheme.ts` (marcas neutras, referencia y límite rotulados, rampa neutra). Barrido de los pasos 1–7, árbol, inspector y barra de herramientas. Las plumas de señales del paso 4 conservan la paleta categórica (cada pluma es una señal distinta). Spec: design-system.md §4.3.
---

### F17 — Normalización del número de nido conservando el crudo ✅

**Objetivo:** que un desfase conocido del número de nido en el registro del PLC no aparezca como un nido fantasma, sin ocultar el dato de origen.

Entregables (hechos):
- `long_signal_batch.py`: `_Grouping.remap` (`[{from: [a, b], offset}]`, validado: origen fuera de `valid`, destino dentro, sin traslapes ni reglas nulas); se aplica antes del chequeo de rango; bandera `FLAG_GROUPING_REMAPPED = 8`; reporte `grouping_remapped` (`{"nest": {"13→1": n}}`, solo conteos) y reglas en `manifest.grouping_remaps`. Formato `pieces-v2` con columnas `nest_raw` / `mold_cavity_raw` (el crudo también se conserva cuando queda fuera de rango).
- `pieces_file.py`: lee `pieces-v1` y `pieces-v2`; `DimensionalDataset.nests_raw` / `mold_cavities_raw` opcionales; `data_quality.grouping_remapped`.
- Frontend: fila «Nido remapeado (crudo → normalizado)» en «Calidad del dato» y chip «Excluir piezas con nido remapeado» (máscara de banderas combinada con la de valores repetidos).
- Paso manual local (no versionado): añadir la regla al `mapping.json` privado y volver a convertir.

Pruebas: `tests/test_long_signal_batch.py` (+3 casos, 5 variantes de reglas inseguras, compatibilidad v1), `filters.test.ts` y `RealDataset.test.tsx`. Todo con datos ficticios (desfase +4 en un rango 1–4).

### F18 — Matriz nido × cavidad de molde y filtro por hora ✅

**Objetivo:** mostrar que el riesgo depende de la combinación nido × cavidad de molde y no de cada eje por separado. Cada cavidad pasa solo por algunos nidos a la vez (los ciclos de inyección y de nidos comparten un factor), y el reparto cambia después de los paros.

Entregables (hechos):
- Motor: `analytics._nest_mold_matrix` → `overview()["nest_mold"]` con celdas `{nest, mold_cavity, pieces, nok, rate}`, **solo combinaciones observadas**. Respeta todos los filtros y la base de NOK. Esquema `NestMoldCell` / `OverviewResponse.nest_mold`.
- Frontend:
  - `NestMoldMatrix` en `QualityCharts.tsx`: filas = nidos, columnas = cavidades. Las celdas que no coincidieron se dibujan aparte («·», borde punteado), distintas de un 0 % medido. La peor celda con ≥ 30 piezas se recuadra con el acento NOK. La leyenda dice «asociación, no causa».
  - Tarjeta «NOK por nido × cavidad de molde» con CSV agregado (`nestMoldCsv`).
- Filtro: horas de planta opcionales junto a «Desde/Hasta» (`startHour` 0–23, `endHour` 1–24 exclusiva). Sin cambios en el backend. Sirve para comparar antes y después de un paro.

Pruebas:
- `tests/test_quality_analytics.py`: matriz calculada a mano, incluidas las combinaciones ausentes y el efecto de un filtro.
- `filters.test.ts`: límites horarios.
- `RealDataset.test.tsx`: matriz y horas.
- Se corrigió una carrera en una prueba previa: retenía el bloque KPI antes de que el dataset REAL reemplazara al sintético.

### F19 — Dispersión X/Y de posición de pines contra tolerancia ✅

**Objetivo:** ver hacia dónde se desvía la posición de cada pin, dentro de la tolerancia del plano y de la de fin de línea, y qué nidos o cavidades empujan esa desviación.

Entregables (hechos):
- Motor:
  - `PinPair` / `ToleranceCircle` en `dataset.py` (validados con `check_pin_pairs`).
  - `position.xy_detail`: desviación respecto al nominal con factor de escala; TP = 2·√(dx² + dy²); % fuera de cada círculo y del cuadro ±tol; TP mediana/p95/máx.; desplazamiento promedio general, de las NOK y por nido o cavidad; muestra determinista de ≤ 4 000 puntos, con las NOK muestreadas aparte.
- Datos:
  - Sintético: par ficticio `PinPositionX/Y` (Ø0.080, ±0.040), donde se ve el desvío del nido crítico.
  - REAL: especificación privada `DEMO_REAL_SPEC_PATH` (`connectors/pin_spec.py`, formato `pin-spec-v1`, D13). Una especificación inválida solo oculta la vista.
- API:
  - `GET /quality-analytics/xy?pair=…&group_by=nok|nest|mold_cavity` con los mismos filtros y la misma base de NOK que el overview.
  - `DatasetOut.pin_pairs`.
- Frontend (paso 3): tarjeta «Posición de pines X/Y vs. tolerancia» en el lenguaje del banco de trabajo (D12).
  - Gráfica SVG con ejes iguales; piezas en marca neutra; NOK como triángulos con el acento atenuado.
  - Primera zona discontinua y las demás punteadas, rotuladas en mayúsculas; flecha nominal → promedio.
  - Al marcar por nido o cavidad, panel ampliado de promedios por grupo, con el peor (≥ 30 piezas) resaltado.
  - KPIs y tabla alternativa accesible.

Pruebas:
- `tests/test_position_xy.py`: valores calculados a mano, borde de zona, agrupación, muestreo que no oculta NOK, validaciones, mecanismo sintético y especificación privada.
- `test_real_dataset_service.py`: especificación REAL, especificación inválida y API.
- `QualityAnalytics.test.tsx`.
- Verificación en navegador (Chromium headless, claro y oscuro, sin errores de consola) contra un export largo **ficticio** generado fuera del repo con los patrones del caso: desfase +12, rotación de cavidades y X/Y en centésimas.

## 4. Definition of Done (checklist de aceptación)

- [x] 1. La demo abre y se recorre sin cargar archivos ni tocar código. (F1)
- [x] 2. Dashboard con KPIs y varias gráficas coherentes, dataset rotulado. (F5)
- [x] 3. Se carga un CSV representativo, se ve el mapeo y ≥ 2 analíticas cambian. (F6)
- [x] 4. Árbol IIoT con señales analógicas/digitales, unidades y estado ficticio. (F2/F3)
- [x] 5. Arrastrar/agregar 3 señales, tiempo común, zoom, quitar/ocultar; ejes por unidad. (F3)
- [x] 6. Cursores A/B con tiempo, valor y Δt. (F3)
- [x] 7. Scatter + regresión real con R²/coeficientes sobre datos alineados. (F4)
- [x] 8. Escenarios normal/deriva/anomalía reproducibles y restaurables sin borrar datos. (F2)
- [x] 9. Lab ML/DL con cifras del informe, falsas alarmas y DL ≤ ML explícitos. (F7) — cifras del brief; verificar contra el PDF cuando llegue.
- [x] 10. Oleadas NOK no confunde rachas detectadas con episodios prevenidos. (F7)
- [x] 11. Cada pantalla distingue histórico / precalculado / simulado / experimental. (F8)
- [x] 12. Sin regresiones en login, catálogo, importación, Live Monitor, navegación. (F8)
- [x] 13. Pruebas de lógica nuevas pasan y el frontend compila. (todas)
- [x] 14. Sin CSV sensibles, credenciales ni datos del cliente en el repo. (todas) — archivos versionados limpios (lint privado); queda el nombre del cliente en el historial del commit `5476a23` (decisión pendiente antes del merge).

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
| 2026-10-26 | F3+F4 | El usuario pidió llegar al 50 % → F3 y F4 en esta sesión, y verificar con navegador real («Playwright»): no hay skill con ese nombre, se usó la skill `run` con `playwright-core` + Edge instalado. Pruebas: backend 1064 passed / 4 skipped; frontend 141 passed, `tsc -b` limpio, build OK; navegador 17/17, sin errores de consola. DoD #4, #5, #6, #7 ✅. Pendiente de decisión del usuario: commit `5476a23` contiene el nombre del cliente en el historial de la rama (ya eliminado del archivo). Siguiente: **F5**. |
| 2026-10-26 | F7 (plan) | A petición del usuario se añadió **F7.b**: predicción experimental de alarmas/fallas por frecuencia de fallas y precursores, sobre historial simulado, con línea base y evaluación por episodio. |
| 2026-10-26 | F5 | Hecho en esta sesión. Pruebas: backend 1095 passed / 4 skipped; frontend 152 passed, `tsc -b` limpio; navegador F5 9/9 + regresión F1–F4 17/17, sin errores de consola. DoD #2 ✅. Siguiente: **F6** (importación CSV con mapeo; Vista A de F4 depende de ella). |
| 2026-10-26 | F6 | Hecho. La implementación venía de la sesión anterior sin commit; en esta se revisó contra los entregables y se cerraron huecos: README de `connectors/` (ruta offline por lotes) y de `seed/sample_files/` (tolerancias para el formato ancho y resultados esperados, verificados con el adaptador), endpoints en `rbac.md`, D6 registrado, tipado mypy de la respuesta de preview, nombre del dataset sin «Importado ·» duplicado, plural de «variable», insignias de procedencia de los pasos 2/3 según el dataset. Pruebas: backend 1132 passed / 4 skipped (incluye `test_imports_api.py`); frontend 166 passed, `tsc -b` limpio, build OK; lint de confidencialidad de `seed/sample_files` 17 passed; generador determinista (regeneración idéntica byte a byte); navegador F6 16/16 (preview `;` + decimal coma, mapeo sugerido, cuarentena 5/3, tasa NOK y nido de mayor riesgo cambian, tarjeta fuente vs. recalculado, paso 3 con cotas importadas, tolerancias tecleadas, descartar → demo intacta), 0 errores de consola. DoD #3 ✅. Vista A de F4 pasa a §7. Siguiente: **F7**. |
| 2026-10-26 | F7 + F7.b | Hecho en la misma sesión que F6 a petición del usuario. El motor de F7.b se delegó a un subagente con contrato fijo (archivos nuevos) y se revisó antes de integrarlo (features solo del pasado, etiqueta (t, t+6], filas de train que cruzarían a test descartadas, evaluación por episodio). Los PDF siguen sin llegar: el laboratorio usa las cifras del brief en `demo-private/model-lab.json`, rotuladas «pendientes de verificar contra el PDF». Pruebas: backend 1177 passed / 4 skipped; frontend 171 passed, `tsc -b` limpio, build OK; navegador F7 15/15 con el archivo privado cargado (5 pestañas, umbral, what-if, regresión del paso 2), 0 errores de consola. DoD #9, #10 ✅. Para F9: desplegar `DEMO_MODEL_LAB_PATH` igual que `DEMO_REPORT_SUMMARY_PATH`. Siguiente: **F8**. |
| 2026-10-26 | F8 | Hecho. Paso 7, procedencia revisada, carga diferida, guía, READMEs, lint de confidencialidad con lista privada. Vista A de F4 sigue en §7 (no estaba en los entregables). Pruebas: backend 1177/4 skipped; frontend 172 sobre el árbol del commit; navegador 20/20. Durante la sesión apareció trabajo sin commit de otra sesión en el mismo checkout (layout «workbench» de la demo: `DemoShell`, `workbench/`, `WorkbenchLayout`, tema, `docs/design/*`); **no se incluyó** en los commits de F8/F9 y la regresión en navegador se vio con ese layout encima. PR a `main` abierto sin merge. El usuario decidió que F9 se prepare solo en el repo (sin tocar VPS, secretos ni DNS). Siguiente: **F9 (preparación)**. |
| 2026-10-26 | F9 (preparación) | Hecho en el repo sin tocar VPS/secretos/DNS (decisión del usuario). Causa del deploy roto: secreto `VPS_HOST` que no resuelve. Compose parametrizado por edición, script de deploy con smoke test, workflow con verificación del host y disparo manual, runbook, 6 pruebas en `tests/deploy` (en CI). Docker no está disponible en la máquina local: la validación real de `docker compose config` ocurre en el VPS. |
| 2026-10-26 | UI (fuera de fase) | A petición del usuario se evaluaron 5 propuestas de interfaz (prototipo navegable fuera del repo) y se aplicó la **propuesta 3 «Ingeniería Ribbon»** al módulo de la demo, en modo claro y oscuro: `DemoShell` pasa a banco de trabajo a pantalla completa (cinta, navegador de proyecto, propiedades, salida, barra de estado) en `features/demo/workbench/`; la ruta de la demo sale de `AppShell` a `layouts/WorkbenchLayout.tsx`; tokens `--wb-*`; spec en `design-system.md` §4.1 y nota en `docs/design/decisions.md`. Metrología sin cambios. Pruebas: frontend 174 passed, `tsc -b` limpio, build OK; capturas en Edge (claro/oscuro) con API interceptada, 0 errores de consola. Sin commit todavía. |
| 2026-10-28 | UI (fuera de fase) | Tras revisar 12 propuestas (lienzo de diseño fuera del repo, skills `apple-design` e `hmi-design-full` ISA-101) el usuario eligió **E2 «Estación de ingeniería refinada»**: barra de menús + barra de herramientas (ruta, escenario en dos pasos con Deshacer, alarmas simuladas con reconocer, `‹ n / 7 ›`, Re Pág/Av Pág) + árbol de 2 niveles + inspector técnico + barra de estado. Se quitaron la cinta, propiedades, salida y las redundancias (escenario en 4 sitios, paso en 3, selector de escenario dentro de los pasos 4/5). Grises ISA-101 con alcance `.wb-root`; `OriginBadge` neutro. Se commitea junto con el workbench del 26-oct (que ya no existe por separado). Pruebas: frontend 180 passed, `tsc -b` limpio. Pendiente: líneas de tolerancia de las gráficas aún en color NOK; detalles técnicos por panel en el inspector. |

| 2026-10-28 | F10 | Hecho. Convertidor offline (`long_signal_batch`), lector `pieces_file`, servicio REAL solo local (D8), motor con base reportada por estación (D10), cavidad de molde y hora de planta (D9). Verificado en local contra el export real del cliente: los conteos del manifest y las tasas del overview coinciden con el análisis previo (cifras solo en `demo-private/`, no versionadas). Rendimiento en local: carga de unos segundos y decenas de MB; overview ~2 s sin caché, por eso se añadió un LRU. Pruebas: backend 1191 passed / 4 skipped; `tests/deploy` 7 passed; lint de confidencialidad con la lista privada ampliada con tokens de direcciones del export. Decisiones D7–D10 registradas. Siguiente: **F11**. |
| 2026-10-28 | F11 | Hecho. Pasos 2–3 sobre el dataset REAL: selector con prefijo de procedencia y preselección de REAL, banner con hora local de planta, insignias REAL (+ PRECALCULADO en el paso 2), KPIs con base reportada y «Cavidad de molde de mayor riesgo», Pareto por estación (primera que falla), tasa por cavidad de molde con IC 95 % y CSV, mapa nido × estación, tarjeta «Calidad del dato», vistas rápidas (presets privados), filtros de cavidad de molde, estaciones y exclusión de piezas con valores repetidos, hora de planta en filtros de día, carta I-MR y Cpk diario, agrupación por cavidad de molde en el paso 3 con boxplot desplazable, corte de la tendencia en huecos sin producción. Arreglado: «Limpiar filtros» ya no regresa al dataset sintético. Pruebas: frontend 187 passed (7 nuevos con un fixture REAL ficticio), `tsc -b` limpio, build OK; navegador 11/11 contra el dataset REAL local (Edge headless, `playwright-core` fuera del repo, capturas solo en el scratchpad), 0 errores de consola. Nota: con la suite completa en paralelo algunos tests de UI (`LiveMonitorDetailPage`, `DimensionalImport`) fallan a veces por timeout y pasan aislados; deuda previa de rendimiento del runner, no regresión. Siguiente: **F12**. |
| 2026-10-28 | F12 | Hecho. Backend: `nok_waves.retrospective_episodes` (episodios de datos reales etiquetados a posteriori, con búsqueda binaria en la evaluación para series de 10^5 piezas), motores nuevos `group_alarms` (alarma por cavidad/nido) y `piece_risk` (riesgo por pieza con variables solo del pasado, logística en Python puro con submuestreo determinista de negativos, ROC-AUC por rangos, dos líneas base), servicio `real_predictive_service` con caché, `/nok-waves` y `/cusum` con `dataset`/`target` (los límites F7 se conservan para el sintético), endpoints `/predictive/group-alarms` y `/predictive/piece-risk`, model-lab con varios estudios (`additional_studies`, familia `baseline`). Frontend: selector «Datos del laboratorio» (real por omisión, `?datos=sintetico`), pestañas «Alarma por cavidad» y «Riesgo por pieza» solo con datos reales, oleadas y CUSUM con NOK por estación y hora de planta, selector de estudio en Modelos ML/DL, insignias e inspector con REAL. JSON privados reescritos con las cifras verificadas (solo en `demo-private/`). Resultado honesto que muestra el panel: el modelo de riesgo por pieza apenas supera a la tasa reciente de la cavidad. Pruebas: backend 1200 passed / 4 skipped (9 nuevos); frontend 193 passed con `--maxWorkers=4` (6 nuevos), `tsc -b` limpio, build OK; navegador 13/13 contra el dataset REAL local, 0 errores de consola. Siguiente: **F13**. |

---
| 2026-10-28 | F14 | Hecho. Motor `line_alarm_engine` (`app/engines/line_alarms/`, `v1-experimental`) con R1–R4 relativas a la tasa de referencia de la línea, estado de cada regla por pieza y eventos con evidencia, pico y retorno a normal; servicio con caché que evalúa la secuencia completa una vez; `/line-panel/moments` (paro, atención, normal) y `/line-panel/replay` (ventana con piezas previas, turnos de 8 h desde las 06:00, conteos del turno). Ajuste tras medir en local contra el dataset REAL: los umbrales del primer borrador producían una avalancha de alarmas de prioridad 2; se agregó banda muerta (`clear_fraction` 0.75) y se subieron R2 (3× sobre 100 piezas, mínimo 25 NOK) y R3 (2.5×) para quedar cerca de una alarma de prioridad 2 por hora; R1 sin cambio. Pruebas: backend 1222 passed / 4 skipped (22 nuevas del panel); ruff limpio; lint de confidencialidad sin coincidencias. Rendimiento local: primera llamada sobre REAL ~1.4 s, luego ~5 ms; ventana de 60 min ~120 KB. Umbrales pendientes de confirmar con el cliente. |
| 2026-10-28 | F15 | Hecho. Ruta `/demo/industrial-quality/panel-linea` a pantalla completa (lienzo 1920×1080 escalado) con las vistas A Andon, B Mapa de proceso y C Respuesta guiada sobre una misma repetición; comandos R/A/F, diálogo de acción 1–4 y botones de un toque en C; barra del presentador con vistas 1/2/3, Normal/Atención/Paro (saltan a momentos reales, 15 s antes del evento), pausa, velocidad ×1/×5/×20 y tema; alarmas previas al punto de arranque cuentan como reconocidas; R1 enclavada hasta que el operador la cierra; «Línea detenida» pausa la repetición. Tokens `--lp-*` en `.wb-root`, spec en design-system §4.2 y nota en decisions.md; accesos en el árbol, menú Ver e inicio de la demo. Pruebas: frontend 28/28 archivos (13 nuevas), `tsc -b` limpio; navegador (Edge headless contra el backend local con el dataset REAL): A/B/C en claro y oscuro, paro → reconocer → línea detenida, atención y normal, 0 errores de consola. Nota: SignalExplorer falló una vez con la suite completa en paralelo y pasó aislado y en la corrida siguiente (inestabilidad previa del runner). |
| 2026-10-28 | F13 | Hecho. Backend: calendario opcional en `Scenario` (salida idéntica byte a byte de los escenarios existentes, verificada con hashes antes y después), `build_calendar_scenario` y servicio `process_join_service` con cachés por señal, intervalo y objetivo, motor `process_join` y endpoint `/quality-analytics/process-join` (404 sin REAL, 422 por señal/objetivo/intervalo/desfase). Frontend: `QualityJoinPanel` (Vista A) en el paso 5 con insignias REAL + Simulado + Experimental y notas de unión ilustrativa y de relación impuesta por construcción; procedencia del paso 5 con REAL. Pruebas: backend 1254 passed / 4 skipped (32 nuevas); frontend 29/29 archivos (3 nuevas), `tsc -b` limpio; ruff limpio; lint de confidencialidad sin coincidencias. Navegador (Edge headless, backend local con el dataset REAL): temperatura de molde con asociación fuerte por construcción y presiones de control con asociación débil, como se espera; series cortadas en los paros; claro y oscuro; 0 errores de consola. Primera llamada local < 1 s, luego milisegundos. Con esto el tablero queda completo salvo la ejecución de F9 en el VPS. |
| 2026-10-28 | F16 | Hecho. Maqueta Hoy/Propuesta revisada por el usuario fuera del repo; aprobó el lenguaje del panel para todo el banco de trabajo, cifras grandes, oscuro grafito y «un leve color donde hay que resaltar» (D12). Tokens grafito y de marcas de datos con alias `--lp-*` (el panel solo cambia de tono), acento NOK atenuado `--wb-nok`, `workbench.css` acotado a `.wb-root` con clases marcadoras en `Card`/`CardHeader`/`Button` (metrología sin cambios, verificado en el dashboard), `components/workbench/` (`Kpi` con valor completo para lectores de pantalla y unidad pequeña, `Notice`, `Key`) y `lib/demo/chartTheme.ts`. Barrido de pasos 1–7, árbol, inspector y barra de herramientas (teclas Re Pág/Av Pág visibles en pantallas anchas). El acento se limita a piezas NOK, tasa NOK, peor grupo, outliers y lo que una alarma no detectó; las plumas de señales IIoT conservan su paleta. Pruebas: frontend 208 passed con `--maxWorkers=4`, `tsc -b` limpio, build OK; lint de confidencialidad y deploy 21 passed / 16 skipped; navegador en claro y oscuro de inicio, pasos 1–7, panel y dashboard de metrología contra el dataset REAL local, sin errores de consola salvo 404 previos al reinicio del backend. |
| 2026-10-29 | F17 | Hecho. En la presentación con el dataset REAL apareció un «nido 13»; el análisis fuera del repo mostró que es el nido 1 con un desfase de +12 en el registro (misma posición en la rotación, mismas cavidades y misma tasa NOK; también 19–24 = 7–12 en una vuelta). Regla `remap` en el mapping privado con valor crudo conservado (D13). Pruebas: backend 52 passed en los módulos de convertidor, dataset REAL y analítica; frontend 38 passed en quality-analytics; `tsc -b` y ruff limpios. Pendiente local: actualizar el mapping privado y re-convertir. |
| 2026-10-29 | F18 | Hecho. En el análisis del export real (fuera del repo), en un periodo dado cada cavidad de molde pasó solo por 3 de los 12 nidos, y ese trío cambió después de los paros. El salto de rechazo tras el paro del primer día coincide con el cambio de cavidades que recibe el nido crítico. La matriz nido × cavidad y el filtro por hora permiten mostrarlo en la demo. Pruebas: backend 53 passed (convertidor, dataset REAL, analítica y API); frontend 36 passed en quality-analytics; `tsc -b` limpio. |
| 2026-10-29 | F19 | Hecho. Gráfica X/Y de posición de pines pedida por el cliente tras la presentación, para ver hacia dónde se desvía la posición dentro del rango de tolerancia. Nominales y tolerancias del plano y de fin de línea solo en la especificación privada (D13). Durante el trabajo el usuario pidió respetar el diseño industrial: marcas neutras, un solo acento NOK y límites rotulados (D12). Pruebas: backend 1271 passed / 4 skipped (suite completa); frontend 213 passed (29 archivos), `tsc -b` y build limpios; confidencialidad y deploy 21 passed / 16 skipped. Pendiente local: crear `pin-spec.json` en `demo-private/` con los nominales del plano y re-convertir con la regla de F17. |

## 7. Pendientes / ideas fuera de fase

- **`real_calendar` en el explorador del paso 4 y en el selector de escenario** (IQ-F13): hoy el escenario de calendario real solo alimenta la Vista A. Mostrarlo en el explorador exige una envolvente de señales para ventanas de ~60 h y revisar los controles de tiempo pensados para 8 h.
- **Umbrales del panel de calidad en línea** (IQ-F14): R2/R3 y la banda muerta se ajustaron contra el dataset REAL local para evitar avalanchas de alarmas; confirmar con el cliente antes de usarlos fuera de la demo.

- Recibir del usuario los PDF de los informes y las 4 imágenes de referencia → el usuario los deja en la carpeta local de documentos del proyecto (fuera del repo; ruta en `demo-private/client-brief.md`): `Informes/`, `Referencias visuales/`; CSV reales en `Datos cliente/`. Revisarlos al inicio de la sesión correspondiente y verificar las cifras de `client-brief.md` / `report-summary.json`.
- Vista por ciclo de inyección / comparativo de ciclos OK vs. NOK (opcional del prompt; solo si F3 queda estable).
- ~~Importación offline por lotes para archivos de decenas de millones de filas~~ Hecho en F10 para exports largos de señales (`long_signal_batch`); un export ancho de decenas de millones de filas seguiría necesitando su propio adaptador.
- **Vista A de F4** (mediciones dimensionales + sensores simulados unidos por tiempo, banner «Unión ilustrativa por tiempo; relación no validada»): ya es posible porque F5/F6 dan datasets dimensionales con marca de tiempo, pero no estaba en los entregables de F6. Candidata para F8; el panel de correlación sigue mostrando la tarjeta «Vista A pendiente».
- Ancho/largo es la única distinción de formato: archivos con varias filas de encabezado o tolerancias en filas aparte (exportaciones PolyWorks/Calypso típicas) requieren limpieza previa o un adaptador específico.
- Deuda previa (no introducida aquí): `ruff check app` reporta ~25 errores en archivos existentes (`demo_data.py`, `main.py`, `core/security.py`, `services/audit_service.py`…) y `ruff format` reformatearía ~15 archivos previos. Los archivos nuevos de IQ pasan ruff. El CI actual solo corre pruebas de `seed/`; los jobs backend/frontend siguen como comentario en `ci.yml`.
- ~~Aviso de Vite: bundle > 500 kB~~ Resuelto en F8 (lazy + chunk de Recharts).
- ESLint 9 sin `eslint.config.*` en `frontend/`: `npx eslint` no corre. Migrar la configuración (deuda previa).
- Vitest con todos los workers en paralelo da timeouts intermitentes en tests de UI (distintos en cada corrida, también en tests previos a F10) cuando la máquina está cargada; con `npx vitest run --maxWorkers=4` pasa todo. Valorar fijar `maxWorkers` en `vite.config.ts` o subir el timeout de `findBy*`.
- Verificación en navegador reutilizable: no hay skill de proyecto para levantar la app. Receta usada (F3/F4): BD desechable migrada + usuario metrólogo ficticio, `uvicorn` con `APP_EDITION=industrial POSTGRES_DB=<desechable>`, `npx vite`, `playwright-core` con `channel: "msedge"`; la sesión vive en memoria, así que se navega dentro de la SPA sin recargar. Considerar `/run-skill-generator` para guardarla como skill del proyecto.
- `.pyc` antiguos muestran rutas `C:\Users\renea\Proyectos\...` en tracebacks; es cosmético (borrar `__pycache__` si molesta).
