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
| F20 | Dataset sintético con cavidades de molde (patrón real, valores ficticios) | ✅ Hecho | `claude/gifted-cannon-5rrp1j` | Pedido por el usuario el 29/oct: que la matriz nido × cavidad se vea también sin datos reales |
| F21 | Barandales de confidencialidad + registro privado + resolvedor único + manifest extendido (backend) | ✅ Hecho | `claude/affectionate-meitner-30c3ud` → PR a `feat/industrial-quality-demo` | Sin datos reales; comportamiento público idéntico. Tipos y MSW del frontend movidos a F22 |
| F22 | Selector global «Pieza» y propagación (frontend) | ✅ Hecho (versión rápida) | ídem | Paralelizable con F23 tras F21 |
| F23 | Perfil declarativo + lector CSV ancho + unión por serie + ventana e histórico (Línea B) | ⬜ Pendiente | ídem | Incluye verificación local con datos reales, fuera de CI |
| F24 | Lector de flujo de tokens + unión por posición/lado/vuelta (Línea A) | ⬜ Pendiente | ídem | Mayor incertidumbre técnica; no bloquea F23 |
| F25 | Vocabulario, capacidades y bloques privados por dataset (pasos 2, 3, 6 y panel de línea) | ⬜ Pendiente | ídem | Barrido de etiquetas |
| F26 | Gemelos ficticios en el demo público (mismo pipeline) | ✅ Hecho (generados en memoria) | ídem | El merge cambia el sitio público: OK del dueño |
| F27 | Fiabilidad del día de la demo: preflight, precarga, e2e y guía de alta | ⬜ Pendiente | ídem | Cierra DoD |
| F28 | (Opcional) Especificación privada con origen y vigencia | 🟨 En curso | ídem | Solo si hay límites de plano o se aceptan rotulados |
| F29 | (Opcional) Pareto por característica sobre veredicto reportado (`pieces-v3`) | ⬜ Pendiente | ídem | Cambio de motor con vectores a mano |
| F30 | (Condicionada) Datos reales en un host privado autorizado | 🟨 En curso | `claude/affectionate-meitner-30c3ud` | Autorización escrita del cliente confirmada por el usuario el 11/nov/2026 (D29) |

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

**D29 — Host privado autorizado (F30): decidido por el usuario (11/nov/2026)** tras confirmar la autorización escrita del cliente. Ver bitácora y `docs/deployment-editions.md` §6.

**D14–D28 — Selector de pieza sobre datos reales y demo adaptable (F21+): propuestas el 11/nov/2026, ver §8.5.** El usuario confirmó el 11/nov/2026: «pieza» = cada tipo que registra la máquina (D14); empezar por la Línea B (con serie); entrega por rama + PR por fase (D25). Pidió además mostrar datos reales en el sitio alojado: **no se aplica** — choca con CLAUDE.md §7/§16 y con D8 y el sitio se construye desde un repositorio público; queda en F30 (bloqueada) hasta tener autorización **escrita** del cliente. Mientras tanto: datos reales solo en local y gemelos ficticios en el sitio público (D15, D23).

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

### F20 — Cavidades de molde en el dataset sintético ✅

**Objetivo:** que la matriz nido × cavidad (F18) y la vista por cavidad (F19) funcionen en cualquier despliegue (Render, VPS) sin datos del cliente. Se copia la **estructura** observada en el export real; todos los valores son ficticios.

Entregables (hechos):
- `synthetic.py`: 32 cavidades en 8 grupos de 4 (`MOLD_GROUPS`), con el orden de llegada fijo, mientras los nidos giran del 1 al 12.
  - Como 8 y 12 comparten el factor 4, cada grupo pasa solo por 3 nidos separados de 4 en 4.
  - El ciclo se desfasa una visita en `CYCLE_SLIPS_S` (días 1.1, 3.2 y 5.2), y el trío de nidos cambia.
  - La combinación crítica es el nido crítico × cavidades 5, 10 y 15: posición X +0.025 mm, con alrededor de 40–45 % NOK en esas celdas. Solo aparece en los periodos en que esas cavidades llegan a ese nido.
- La asignación de cavidad no consume números aleatorios: los demás valores del dataset no cambian (`dim-sim-1.1.0`). El mecanismo nuevo queda listado en «verdad conocida».
- Gráfica X/Y: en el panel ampliado se rotulan solo los grupos que se separan (máx. 8, el peor primero); los demás tienen tooltip y aparecen en la tabla. La etiqueta del círculo sintético ya no repite el diámetro.

Pruebas: ajustes en `test_line_panel.py`, `test_quality_analytics_api.py`, `test_real_dataset_service.py` y `test_position_xy.py` (el desplazamiento esperado del nido crítico ahora incluye la combinación). Backend 1271 passed / 4 skipped. Verificado en navegador en claro y oscuro, sin errores de consola.

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
| 2026-10-29 | F20 | Hecho. El usuario pidió que la agrupación nido × cavidad se basara en los datos reales; como esos datos no pueden ir a un servidor ni al repo (D8), se acordó copiar el patrón real con valores ficticios. Pie del login cambiado a «Powered by OnKaizen» y prueba de CI que impide el nombre de marca anterior (PR #45, mergeado). |
| 2026-11-11 | F21+ (plan) | El usuario entregó exports reales de dos líneas (fuera del repo, analizados solo en el contenedor de la sesión) y pidió un desplegable para elegir la pieza, con datos reales y un demo adaptable. Plan F21–F30 y decisiones D14–D28 en §8 (diseño por un flujo de 3 propuestas + síntesis; las rutas y afirmaciones de código se verificaron a mano). Cifras y correspondencias reales solo en notas privadas, no versionadas. Datos reales en el sitio alojado: rechazado hasta autorización escrita del cliente (F30). F21 en curso. |
| 2026-11-11 | F21 | Hecho (backend). `core/private_data.py`: triple barrera en ejecución (no producción, todos los orígenes CORS loopback, sin variable de plataforma alojada), aplicada también al dataset heredado. `services/dataset_registry.py`: una carpeta privada por pieza (`real-<slug>`), catálogo solo con manifests, carga perezosa con LRU, carpetas inválidas omitidas y contadas, resolvedor único usado por `quality-analytics`, `predictive` y `line-panel`. `services/dataset_cache.py`: las cachés derivadas (overview, panel, estudios, Vista A) olvidan un dataset al expulsarlo o recargarlo (antes, claves por `id()` podían servir resultados de otro objeto). Manifest con bloques opcionales (`display`, `groups`, `time_basis`, `window`, `history`, `views`, `assumptions`), compatibles hacia atrás; `read_pieces` recibe la procedencia del llamador y deja `mold_cavities=None` sin agrupación secundaria. Endpoints nuevos `GET /quality-analytics/catalog` y `/datasets/{id}`; `report-summary` y `model-lab` aceptan `dataset` y sirven solo el bloque propio de la pieza (404 si no tiene); Vista A opt-in por pieza (D27). `.gitignore` + `tests/seed_validation/test_no_data_files.py` (sin `.zip`, `.csv.gz`, `.bmp`, `.parquet` versionados); prueba de despliegue explícita para la variable nueva. Pruebas: backend 1295 passed (24 nuevas en `test_dataset_registry.py`; las 4 de migraciones se corren aparte en este entorno), `tests/deploy` + `tests/seed_validation` (sin BD) 24 passed / 1 skipped; ruff limpio en archivos tocados. **Movido a F22:** tipos `fetchCatalog`/`fetchDataset` y manejadores MSW del frontend (F21 quedó solo backend). Sin datos reales en esta fase. Siguiente: **F22** (selector) y **F23** (lector de la Línea B). |
| 2026-11-11 | F26 + F22 | Adelantadas a petición del usuario: presenta solo desde el sitio alojado y los datos reales no pueden ir ahí sin autorización escrita del cliente (F30). **F26:** cinco gemelos ficticios `demo-<slug>` (`engines/quality_analytics/twins.py`; dos líneas: pruebas de fin de línea con serie y mesa indexada sin serie) generados en memoria de forma determinista en vez de archivos versionados (enmienda a 8.3-j: nada que commitear, ~15 000 piezas cada uno); siempre SIMULADO y rotulados como gemelos; precarga al arrancar. **F22 (versión rápida):** control «Pieza» en la barra, agrupado por línea; fija el dataset de los pasos 2, 3, 6 y del panel de línea (recordado en el navegador); el paso 6 pierde su conmutador y corre los estudios por pieza en cualquier dataset con veredicto de máquina; procedencia de los paneles derivada del dataset (un gemelo nunca dice REAL); vocabulario de agrupación en KPIs, títulos, filtros, agrupación y alarmas. **Pendiente:** el resto del barrido de etiquetas (F25), el endpoint `/catalog` aún no lo usa el frontend (usa `/datasets`), y las pruebas de componente de `PartControl`. Pruebas: backend 1301 passed; frontend 216 passed, `tsc -b` y `npm run build` limpios; recorrido en navegador (Chromium) sin errores de consola sobre sintético, MI-DEMO-B1 y MI-DEMO-A1. |
| 2026-11-11 | F22 (catálogo) + verificación con datos reales | El selector y los pasos 2, 3, 6 y el panel leen `/catalog` y piden `/datasets/{id}` bajo demanda, así que las piezas del registro privado aparecen sin cargarlas todas. Verificado en local (fuera del repo, carpeta privada, barreras D15 activas) con los logs reales de la Línea B convertidos por un script privado del operador (no versionado): una entrada por tipo de pieza, ventana de las 150 000 piezas más recientes por tipo; recorrido en navegador sin errores. El lector genérico de F23 sigue pendiente (el script privado no lo sustituye). Pruebas: frontend 216 passed, build OK. |
| 2026-11-11 | F30 (D29) | El usuario confirmó que el cliente autorizó **por escrito** alojar sus datos convertidos en un servidor de OnKaizen y eligió un servicio privado de pago en la cuenta de Render. **D29 (enmienda a D8/D15):** solo un host con `DEMO_PRIVATE_HOST_AUTHORIZATION` (referencia de la autorización escrita, sin datos personales) y fuera de producción levanta las barreras de origen loopback y de plataforma alojada; el sitio público y el repositorio siguen sin datos reales. Los datos se suben convertidos por HTTPS con `PUT /api/v1/private-datasets/<slug>` (solo administradores, limitado, auditado, desactivado por defecto), nunca por git; retirada con `DELETE` + borrar el servicio. El nombre del archivo de piezas del manifest ya no puede empezar con punto. Pruebas: backend 1304 passed (3 nuevas). |
| 2026-11-11 | F28 (parte 1) | El usuario pidió que el sistema se adapte a cada producto y que el desplegable muestre el nombre del producto; enviará los planos. Hecho: archivo privado `product.json` por pieza (`connectors/product_spec.py`, `product-spec-v1`): nombre, número de parte, plano y programa del producto; por característica nombre del plano, globo, nominal, LIE/LSE, unidad y clase. El registro lo aplica al cargar (límites en las variables ⇒ Cpk y líneas de especificación; la base NOK sigue siendo el veredicto de la máquina), lo incluye en la firma de caché y nunca aplica un archivo de otra pieza. Catálogo y detalle exponen `product`; el desplegable muestra plano y número de características con tolerancia; subida privada acepta `product`. Los nombres de producto/cliente solo viven en los archivos privados del servidor autorizado. **Pendiente:** vigencias por fecha (`valid_from`), concordancia máquina vs plano y barrido de vocabulario (F25), a completar con los planos. Pruebas: backend 1310 passed; frontend 217 passed, build OK. |
| 2026-11-11 | F28 (parte 2) + F25 (parcial) | Llegó el primer plano del cliente (carcasa de una de las líneas, dos variantes coinciden con dos tipos de pieza por el número de parte del código DMC); sus datos van solo al `product.json` privado. Hecho: en datasets con veredicto de máquina y límites del plano, el diagnóstico agrega **concordancia máquina vs plano** (2×2 en piezas, resalta las aprobadas por la máquina fuera del plano) y **Pareto «fuera de plano» por característica**; el Pareto oficial y la base NOK no cambian. Vocabulario por pieza en mapa de calor, matriz de agrupaciones (Izq/Der para lados), ejes de tasas y textos R2/R4 del panel de línea. Pruebas: backend 1313 passed (vector a mano de concordancia); frontend 218 passed, build OK. Pendiente: vigencias por fecha, planos de los demás tipos, resto del barrido de vocabulario (respuesta guiada del panel). |

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

---

## 8. Actualización F21+: selector de pieza sobre datos reales y demo adaptable

> Bloque para anexar a este plan (11/nov/2026). Las filas del tablero van a «Tablero de estado», las decisiones a §2 y las fases a §3. Solo planificación: nada de esto está implementado. Alias usados en todo texto versionado (código, pruebas, docs, commits, este plan): **Línea A** = logger por estaciones en flujo de tokens, sin número de serie (mesa indexada, dos lados por ciclo); **Línea B** = pruebas de fin de línea con número de serie (un CSV ancho por estación y día). Los nombres reales de líneas, estaciones, carpetas, códigos de tipo, cadenas de marcado y cualquier cifra de producción viven solo en archivos privados (D1, D8, D13).

### 8.1 Objetivo y alcance

**Objetivo.** En la edición industrial, el presentador elige la **pieza** en un único desplegable de la barra del banco de trabajo y los pasos 2, 3, 5 (Vista A), 6 y el panel de línea trabajan sobre esa pieza. Las piezas reales salen de un **registro privado** en disco, alimentado por un convertidor offline guiado por un **perfil declarativo**: dar de alta otra pieza, máquina o cliente = escribir un perfil privado + ejecutar un comando + dejar una carpeta; sin tocar código.

**Dentro de alcance.** Registro de N datasets reales (solo local), barandales de confidencialidad reforzados, resolvedor único de dataset, dos lectores de origen (CSV ancho por estación unido por serie; flujo de tokens unido por posición+lado+vuelta), selector global, etiquetas y capacidades por dataset, gemelos ficticios para el demo público, verificación previa a la demo, guía de alta.

**Fuera de alcance.** Dimensión «pieza» dentro del motor (no hay comparación entre piezas en una misma pantalla); tablas o migraciones (D2, D3, D6 intactas); permisos nuevos (D4); datos reales en cualquier servidor (D8 no se reabre; solo la fase condicionada F30 lo haría); paso 4 (laboratorio IIoT), Vista B, what-if y estudio de falla de máquina siguen SIMULADOS y genéricos; imágenes de cámara, registros de prueba eléctrica por excepción, estudios de repetibilidad y carpetas de archivo de los orígenes no se convierten; numpy/Parquet; perfiles editables en la UI.

### 8.2 Qué existe hoy y qué falta

| Hoy | Evidencia | Falta |
|---|---|---|
| Un solo dataset REAL: una variable, un id constante, una caché de un hueco; nombre fijo a partir de `DEMO_CLIENT_LABEL` | `backend/app/services/real_dataset_service.py:32-83`, `backend/app/core/config.py:52-58` | Registro de N entradas con carga perezosa |
| Resolución de dataset repetida en 3 routers + 1 comprobación en línea, por igualdad de id | `backend/app/api/v1/quality_analytics.py:75-86, 302-304`, `line_panel.py:65-72`, `predictive.py:94-112` | Un resolvedor |
| `GET /quality-analytics/datasets` necesita cada dataset cargado para describirlo | `quality_analytics.py:151-198` | Catálogo ligero leído solo de manifests |
| Manifest sin nombre de pieza/línea, sin etiquetas de agrupación, sin ventana; `read_pieces` fija REAL / `reported` / sin tolerancias y `mold_cavities` nunca es `None` | `backend/app/connectors/pieces_file.py:51-62, 199-228` | Bloques opcionales en el manifest |
| Convertidor solo para export largo `id,address,timestamp,value` (coma, UTF-8) | `backend/app/connectors/long_signal_batch.py:301-366, 432-452, 615-765` | Lectores para los dos orígenes nuevos; escritor compartido |
| Guardas D8: `APP_ENV == "production"`, prueba que busca el literal `DEMO_REAL_DATASET` en compose/script/workflow, `_guard_output` | `real_dataset_service.py:56-58`, `tests/deploy/test_vps_compose.py:137-140`, `long_signal_batch.py:602-612` | Los hosts de demo corren con `APP_ENV` distinto de producción (`backend/app/main.py:63`): la guarda en ejecución es inerte allí. `.gitignore:33-40` no ignora `*.zip`, `*.csv.gz`, `*.bmp` |
| Cuatro mecanismos sueltos para elegir datos: select en pasos 2-3, `?datos=sintetico` en paso 6, id fijo en Vista A y en el panel de línea | `frontend/src/features/demo/steps/QualitySteps.tsx:51-161`, `AiStep.tsx:39-67, 95-114`, `frontend/src/lib/quality-analytics/processJoin.ts:7`, `frontend/src/features/line-panel/LinePanelPage.tsx:35-36, 66-71` | Un selector global; el panel de línea está fuera de `DemoSessionProvider` (`frontend/src/App.tsx:53-71`) |
| Informe privado y laboratorio de modelos: un JSON por despliegue, sin `dataset` | `quality_analytics.py:279-281`, `predictive.py:125-127` | Por dataset, ocultos si faltan |
| Cachés con clave `id(ds)`; unión proceso-calidad con un solo calendario | `real_dataset_service.py:110-123`, `backend/app/services/real_predictive_service.py:41-55`, `process_join_service.py:98-120` | Claves por id de dataset + generación de carga |
| Vocabulario fijo «Nido» / «Cavidad de molde»; tope de 400 días en el filtro de fechas | ~90 apariciones en 22 archivos; `frontend/src/lib/quality-analytics/filters.ts:108` | Etiquetas por dataset |

Lo que **no** cambia: `DimensionalDataset` y los motores ya son agnósticos del origen (estaciones en orden de proceso, dos agrupaciones, banderas, base NOK); el contrato `manifest.json` + `pieces.csv.gz` es la frontera estable.

### 8.3 Diseño

**a) Qué es una «pieza».** Una entrada del desplegable = **un dataset convertido por (línea, valor de pieza)**. La llave de pieza es el tipo que la propia máquina registra, declarado en el perfil privado: en Línea B, el número de programa del registro de verificación de tipo unido por serie; en Línea A, el token de tipo de una estación de visión. Las estaciones que no registran el tipo lo heredan (por la unión; si la pieza fue rechazada antes, por el registro de tipo más cercano en el tiempo dentro de la misma agrupación primaria). El perfil decide la granularidad (`part.datasets[].values` agrupa varios valores en una entrada), así que «variantes» frente a «familias» es configuración. El dataset real anterior sigue como entrada heredada `real-dimensional`.

**b) Perfil privado `station-logs-v1`** (JSON, nunca versionado salvo ejemplos ficticios). Ejemplo ficticio:

```json
{
  "format": "station-logs-v1",
  "line": {"slug": "linea-demo-b", "label": "Línea demo B"},
  "time": {"format": "%Y%m%d-%H:%M:%S", "basis": "plant_wall_clock", "utc_offset_minutes": 0},
  "source": {"exclude": ["**/archivo/**", "**/*estudio*"], "skip_identical_members": true},
  "groupings": {
    "primary": {"label": "Cavidad", "prefix": "C", "valid": [1, 12], "ignore": [0]},
    "secondary": null
  },
  "join": {"kind": "key", "ignore_keys": ["0"], "keep": "last"},
  "stations": [
    {"key": "altura_a", "name": "Altura lado A", "reader": "wide_csv",
     "files": "altura_a/registro_*.csv", "encoding": "cp1252", "delimiter": ";",
     "decimal": "auto", "expect_columns": 9,
     "columns": {"ts": 0, "key": 1, "primary": 2, "verdict": 3},
     "verdict": {"ok": ["true"], "nok": ["false"]}},
    {"key": "tipo", "name": "Verificación de tipo", "reader": "wide_csv",
     "files": "tipo/registro_*.csv", "encoding": "cp1252", "delimiter": ";",
     "expect_columns": 5, "columns": {"ts": 0, "key": 1, "primary": 2, "part": 3, "verdict": 4}}
  ],
  "variables": [
    {"key": "altura_a_1", "name": "Altura A · pin 1", "unit": "mm", "station": "altura_a",
     "at": 5, "missing_if": {"eq": 0}},
    {"key": "giro_b_1", "name": "Giro B · pin 1", "unit": "mm", "station": "giro_b",
     "at": 6, "missing_if": {"abs_ge": 5}}
  ],
  "part": {
    "from": {"station": "tipo"},
    "inherit": {"nearest_in_time": true, "max_gap_minutes": 30, "restrict_by_primary": true},
    "datasets": [
      {"slug": "mi-demo-b1", "label": "MI-DEMO-B1", "values": ["1"], "primary_valid": [7, 12]},
      {"slug": "mi-demo-b2", "label": "MI-DEMO-B2", "values": ["2", "3"], "primary_valid": [1, 6],
       "exclude_variables": ["altura_a_9"]}
    ]
  },
  "window": {"max_pieces": 250000, "align": "production_day"},
  "history": {"daily": true},
  "views": {"process_join": false},
  "assumptions": ["Hora según el reloj de la máquina; la fuente no trae zona horaria."]
}
```

Para un logger en flujo de tokens cambian solo el lector y la unión:

```json
{
  "groupings": {
    "primary": {"label": "Nido", "prefix": "N", "valid": [1, 10]},
    "secondary": {"label": "Lado", "prefix": "L", "values": {"1": "Izq", "2": "Der"}}
  },
  "join": {"kind": "carrier_window", "anchor": "longitud", "keys": ["primary", "secondary"],
           "lead_s": 3, "min_match_rate": 0.98},
  "stations": [
    {"key": "vision_b", "name": "Visión lado B", "reader": "token_stream",
     "files": "vision_b_*.csv", "encoding": "cp1252", "delimiter": ";", "grain": "side",
     "fields": {"ts": {"index": 0}, "primary": {"after": ["Pos:", "Pos Nr.:"]},
                "secondary": {"labels": {"Izq:": 1, "Der:": 2}}, "part": {"after": "Tipo:"},
                "verdict": {"after": "Pieza:", "ok": ["OK"], "nok": ["NOK"]}},
     "skip_texts": ["Rechazada en estación previa"], "invalid_texts": ["Imagen no plausible"]}
  ],
  "variables": [
    {"key": "giro_1", "name": "Giro 1", "station": "vision_b", "after": "Giro1:", "missing_if": {"eq": 999}},
    {"key": "long_1", "name": "Longitud pin 1", "station": "longitud", "side_offset": 1}
  ]
}
```

Reglas del perfil: columnas por **índice** + `expect_columns` (los encabezados del cliente, sus erratas y diéresis son irrelevantes; un cambio de layout da error explícito, no lecturas falsas); estaciones en **orden de proceso** (D10); toda regla de limpieza se **cuenta** en el informe del manifest (D13). Exactamente dos lectores y dos uniones, porque las dos líneas prueban exactamente esos; un tercer formato necesitará un lector nuevo cuando exista (CLAUDE.md §4).

**c) Contrato de ejecución.** Se mantiene `pieces-v2` (las columnas del CSV no cambian) y el manifest gana bloques **opcionales**, compatibles hacia atrás:

```json
{
  "display": {"label": "MI-DEMO-B1", "line": "Línea demo B", "description": "…", "order": 10},
  "groups": {"primary": {"label": "Cavidad", "prefix": "C"},
             "secondary": {"label": "Lado", "prefix": "L", "values": {"1": "Izq", "2": "Der"}}},
  "time_basis": "plant_wall_clock",
  "window": {"from_ms": 0, "to_ms": 0, "source_pieces": 0},
  "history": {"granularity": "day", "columns": ["day", "pieces", "nok"], "rows": []},
  "views": {"process_join": false},
  "assumptions": ["…"]
}
```

El backend **nunca lee el perfil**; solo manifests. `pieces-v3` queda reservado para cuando cambien columnas (F29).

**d) Registro de datasets** (`backend/app/services/dataset_registry.py`). Raíz privada `DEMO_REAL_DATASETS_DIR`; cada subcarpeta `^[a-z0-9][a-z0-9-]{0,39}$` con `manifest.json` es una entrada `real-<slug>` (prefijo que el frontend ya reconoce; `dimensional` reservado a la entrada heredada de `DEMO_REAL_DATASET_PATH`). Junto al manifest pueden vivir, opcionales, `report-summary.json`, `model-lab.json`, `spec.json`, `panel-rules.json`. Catálogo **ligero** construido solo con manifests (sin cargar piezas); carga **perezosa** con LRU (`DEMO_REAL_DATASETS_MAX_LOADED`, por defecto 2); clave por entrada (ruta, mtime, tamaño, stat de extras); entradas inválidas se omiten y se cuentan, nunca se listan; jamás se registran rutas ni contenidos. La procedencia la decide **la raíz**, no el manifest: raíz privada ⇒ REAL; piezas ficticias empaquetadas ⇒ SIMULATED.

**e) Lectores y ensamblador** (`backend/app/connectors/station_logs/`). `wide_csv` (cabecera, delimitador, codificación, marca decimal por archivo) y `token_stream` (sin cabecera; grano por ciclo o por lado; campos por `after: <etiqueta>` o `side_offset: n`; textos de salto ⇒ estación no probada; textos inválidos ⇒ NOK sin valores). Unión `key` (última fila por llave y estación, llaves ignoradas, partición por hash con memoria acotada) y `carrier_window` (sin serial: el registro de una estación posterior pertenece al registro ancla de la misma posición+lado cuya ventana lo contiene; cero o varios candidatos ⇒ estación no probada + bandera 16 «unión incierta», contados; por debajo de `min_match_rate` la conversión termina con error). Escritor, manifest, `_guard_output` y checksum se extraen a `backend/app/connectors/pieces_writer.py` y los usan ambos convertidores. Entrada = carpeta **o .zip** leído con `zipfile` sin extraer; miembros idénticos por (CRC, tamaño, nombre base) se leen una vez. CLI: `python -m app.connectors.station_logs inventory | convert | check` (salida solo con conteos; nunca valores, llaves ni nombres de archivo de origen).

**f) Selector y propagación.** Un único control «Pieza» en `frontend/src/features/demo/workbench/Toolbar.tsx:78-80` (antes de `ScenarioControl`, mismo patrón popover + radiogroup + Aplicar) con su entrada en la barra de menús (`DemoShell.tsx:143-181`); entradas agrupadas por línea con prefijo Real / Demo / Importado. El estado vive en un `DatasetCatalogProvider` montado en `frontend/src/layouts/WorkbenchLayout.tsx` para que el recorrido y el panel de línea lo compartan; el `Outlet` se re-monta con clave `${resetCount}:${datasetId}` (`DemoShell.tsx:287`); «Restaurar escenario» conserva la pieza. El select de los pasos 2-3 y el conmutador Reales/Sintéticos del paso 6 pasan a resumen de solo lectura («cada hecho vive en un solo lugar»). Regla de selección inicial: primera entrada REAL si existe; si no, el dataset sintético.

| Sigue la pieza | Genérico (no cambia) |
|---|---|
| Paso 2 Diagnóstico, paso 3 Exploración dimensional, paso 5 Vista A (solo si el dataset declara `views.process_join`), paso 6 oleadas NOK / CUSUM / alarma por grupo / riesgo por pieza (si hay agrupación secundaria), panel de línea, inspector «Sesión», árbol «Activos» | Paso 1 (añade una tira de solo lectura con las estaciones de la pieza), paso 4 Laboratorio IIoT (siempre SIMULADO), paso 5 Vista B, what-if, estudio de falla de máquina, paso 7 |

**g) Procedencia y etiquetas.** Las insignias salen de `source_type`, no del prefijo del id. `DatasetOut` gana `display`, `groups`, `window`, `assumptions` y un bloque `capabilities` **derivado en ejecución** (xy, índices de capacidad, agrupación secundaria, riesgo por pieza, Vista A, informe privado, estudio de modelos). Lo que una pieza no soporta se oculta o se sustituye por una tarjeta con el motivo, nunca por un panel vacío. Un helper `groupLabel(dataset, 'primary' | 'secondary')` reemplaza «Nido» / «Cavidad de molde» fijos. El informe y el estudio de modelos del primer cliente no se muestran junto a otra pieza.

**h) Límites de especificación.** La base NOK sigue siendo el veredicto de la máquina (D10) con atribución a la primera estación que falla. Los límites entran solo por un `spec.json` privado por dataset (`dataset-spec-v1`, generaliza `pin-spec-v1`) con **origen** (`drawing` | `source` | `empirical`) y **vigencia** (`valid_from`), porque en ambas líneas los límites cambiaron durante el período. `empirical` solo dibuja líneas de referencia rotuladas «inferido de los datos, no es especificación»; nunca Cp/Cpk ni veredictos recalculados.

**i) Volumen y memoria.** El modelo actual (listas de Python) cuesta del orden de 0,4 KB por pieza con ~15 variables y 0,9 KB con ~50; cargar ≈17 µs por pieza y un resumen sin caché ≈10 µs por pieza. Por eso: un dataset por pieza; **ventana** por pieza resuelta en el convertidor (por defecto las 250 000 piezas más recientes en días de producción completos, o un rango de fechas; una campaña concreta puede registrarse como otra entrada); el convertidor imprime la memoria estimada y se niega a superar el presupuesto sin `--allow-large`; el manifest lleva el **histórico diario agregado de toda la fuente** para mostrar la tendencia completa junto a la ventana cargada; LRU de 2 datasets cargados; solo se precarga la entrada inicial. La conversión es offline y no afecta al proceso web.

**j) Qué muestra el demo público.** Nunca datos reales. El mismo desplegable ofrece el dataset sintético actual más **piezas ficticias «gemelas»** (precedente F20): misma forma que las líneas reales, valores inventados, etiquetas `MI-DEMO-*`, insignia SIMULADO y aviso «gemelo sintético: estructura de una línea real, valores ficticios». Se generan con un script determinista **a través de los mismos lectores y perfiles** (perfiles de ejemplo versionados) y se empaquetan en la imagen (`backend/app/demo_parts/`), de modo que el arranque en el plan gratuito no paga conversión.

### 8.4 Fases

| Fase | Nombre | Estado | Rama / PR | Notas |
|---|---|---|---|---|
| F21 | Barandales de confidencialidad + registro privado + resolvedor único + manifest extendido (backend) | ✅ Hecho | `claude/affectionate-meitner-30c3ud` → PR a `feat/industrial-quality-demo` | Sin datos reales; comportamiento público idéntico. Tipos y MSW del frontend movidos a F22 |
| F22 | Selector global «Pieza» y propagación (frontend) | ✅ Hecho (versión rápida) | ídem | Paralelizable con F23 tras F21 |
| F23 | Perfil declarativo + lector CSV ancho + unión por serie + ventana e histórico (Línea B) | ⬜ Pendiente | ídem | Incluye verificación local con datos reales, fuera de CI |
| F24 | Lector de flujo de tokens + unión por posición/lado/vuelta (Línea A) | ⬜ Pendiente | ídem | Mayor incertidumbre técnica; no bloquea F23 |
| F25 | Vocabulario, capacidades y bloques privados por dataset (pasos 2, 3, 6 y panel de línea) | ⬜ Pendiente | ídem | Barrido de etiquetas |
| F26 | Gemelos ficticios en el demo público (mismo pipeline) | ✅ Hecho (generados en memoria) | ídem | El merge cambia el sitio público: OK del dueño |
| F27 | Fiabilidad del día de la demo: preflight, precarga, e2e y guía de alta | ⬜ Pendiente | ídem | Cierra DoD |
| F28 | (Opcional) Especificación privada con origen y vigencia | 🟨 En curso | ídem | Solo si hay límites de plano o se aceptan rotulados |
| F29 | (Opcional) Pareto por característica sobre veredicto reportado (`pieces-v3`) | ⬜ Pendiente | ídem | Cambio de motor con vectores a mano |
| F30 | (Condicionada) Datos reales en un host privado autorizado | 🟨 En curso | `claude/affectionate-meitner-30c3ud` | Autorización escrita del cliente confirmada por el usuario el 11/nov/2026 (D29) |

#### F21 — Barandales, registro privado, resolvedor único y manifest extendido (backend)

- **Objetivo.** Retirar antes de cualquier lector los dos riesgos irreversibles (datos reales ofrecidos en un host o colados en git) y permitir N datasets reales sin entradas muertas. Probable hoy con datos ficticios convertidos con el convertidor existente.
- **Archivos.** Nuevos: `backend/app/services/dataset_registry.py`, `backend/tests/test_dataset_registry.py`, `tests/seed_validation/test_no_data_files.py`. Tocados: `backend/app/core/config.py`, `backend/app/services/real_dataset_service.py`, `real_predictive_service.py`, `process_join_service.py`, `report_summary_service.py`, `model_lab_service.py`, `backend/app/connectors/pieces_file.py`, `backend/app/api/v1/quality_analytics.py`, `predictive.py`, `line_panel.py`, `backend/app/schemas/quality_analytics.py`, `backend/app/main.py`, `.gitignore`, `.env.example`, `backend/.env.example`, `docker-compose.override.yml.example`, `tests/deploy/test_vps_compose.py`, docs (`docs/deployment-editions.md` §6, `docs/demo-industrial-quality.md`, `docs/security/rbac.md`, `backend/app/connectors/README.md`).
- **Backend.** (1) Ajustes `demo_real_datasets_dir` y `demo_real_datasets_max_loaded` (1..8, por defecto 2); el nombre contiene el literal que la prueba de despliegue ya prohíbe. (2) `private_data_allowed()` = `APP_ENV != production` **y** todos los orígenes de `CORS_ORIGINS` son loopback **y** no hay marcador de plataforma alojada en el entorno (lista constante; confirmar en la fase el nombre exacto de la variable del proveedor); se aplica también a la ruta heredada. (3) Registro según 8.3-d; `real_dataset_service` queda como adaptador de la entrada heredada conservando `REAL_DATASET_ID`, `load_real_dataset` y `cached_overview` para las pruebas existentes. (4) `resolve_dataset(dataset_id, user, *, allow_imports)` = sintético → registro → importación del usuario → 404; sustituye las cuatro resoluciones; los estudios «solo real» pasan a comprobar capacidad/`source_type`, no igualdad de id. (5) Cachés por `(ds.id, generación de carga)` con purga al expulsar del LRU; `process_join_service._current` pasa a diccionario pequeño por dataset. (6) `Manifest` acepta los bloques opcionales de 8.3-c; `read_pieces` recibe `source_type` del llamador y deja `mold_cavities=None` cuando ninguna fila trae agrupación secundaria. (7) `GET /quality-analytics/catalog` (ligero: id, etiqueta, línea, procedencia, piezas, período, ventana, cargado, `omitted`) y `GET /quality-analytics/datasets/{id}` (completo; dispara la carga); mismo permiso `measurement.measurement_result:read` y compuerta de edición; `/datasets` conserva su forma actual. (8) `/quality-analytics/report-summary` y `/predictive/model-lab` aceptan `dataset`: entrada del registro ⇒ su JSON vecino o 404; rutas heredadas por variable solo para `real-dimensional`; sintético ⇒ el marcador ilustrativo actual. (9) Precarga solo de la entrada inicial.
- **Frontend.** Solo tipos, `fetchCatalog` / `fetchDataset` y manejadores MSW por defecto para los dos endpoints nuevos (`onUnhandledRequest: 'error'`).
- **Datos.** Ninguno real. `.gitignore`: `*.zip`, `*.csv.gz`, `*.bmp`. Variables documentadas como «SOLO USO LOCAL» con marcadores. Limpiar la entrada obsoleta «Vista A pendiente» de §7.
- **Pruebas.** pytest: dos datasets ficticios (fixtures de `backend/tests/test_long_signal_batch.py:48-101`) ⇒ el catálogo lista ambos sin cargar piezas; carga perezosa; expulsión LRU y nueva petición devuelven el dataset correcto (regresión de claves `id()`); recarga por mtime; producción ⇒ ninguno; origen CORS no loopback ⇒ ninguno; marcador de host ⇒ ninguno; checksum malo / manifest inválido / nombre de carpeta inválido ⇒ omitido y contado; nunca se sigue una ruta de la petición; la ruta heredada sigue dando `real-dimensional`; informe y estudio por dataset (presente, ausente, heredado, marcador). Actualizar `test_real_dataset_service.py`, `test_line_panel.py`, `test_real_predictive.py`, `test_process_join.py` con una fixture de registro. `tests/deploy`: prohibir explícitamente la variable nueva. `tests/seed_validation/test_no_data_files.py`: falla si `git ls-files` contiene `.zip`, `.bmp`, `.csv.gz`. Vitest completo en verde con `--maxWorkers=4`.
- **Aceptación.** Sin la variable, en producción, con origen no loopback o con marcador de host no se lista ni resuelve ningún dataset privado (cuatro pruebas independientes). Dos datasets ficticios responden por id en todos los endpoints con `dataset`; cambiar de id nunca devuelve la caché del otro. Ninguna ruta, nombre de archivo ni contenido de manifest en logs o errores. Edición metrology sin cambios; sin tabla ni migración. Tablero, bitácora y D14, D15, D20, D22, D25, D26 registradas.
- **Riesgos.** Refactor de tres módulos de prueba que parchean el cargador por router (deben seguir siendo significativos, no solo verdes). La barrera loopback bloquea una demo servida a otro equipo de la red: documentado y decisión del usuario. Un operador siempre puede configurar un servidor a mano: lo impide la norma D8, no el código.

#### F22 — Selector global «Pieza» y propagación (frontend)

- **Objetivo.** Entregar el desplegable pedido, en un solo lugar, sin opciones muertas ni paneles muertos.
- **Archivos.** Nuevos: `frontend/src/lib/demo/DatasetCatalogProvider.tsx`, `frontend/src/features/demo/workbench/PartControl.tsx` (+ prueba), `frontend/src/lib/quality-analytics/labels.ts`. Tocados: `layouts/WorkbenchLayout.tsx`, `features/demo/workbench/Toolbar.tsx`, `features/demo/DemoShell.tsx`, `lib/demo/DemoSessionProvider.tsx`, `features/demo/steps/QualitySteps.tsx`, `AiStep.tsx`, `lib/demo/aiViews.ts`, `lib/quality-analytics/processJoin.ts`, `features/industrial-analytics/QualityJoinPanel.tsx`, `features/line-panel/LinePanelPage.tsx`, `lib/demo/stepOrigins.ts`, `lib/quality-analytics/filters.ts`, `features/quality-analytics/QualityOverview.tsx`, `features/predictive/ModelLab.tsx`, `features/demo/workbench/ProjectTree.tsx`, `test/server.ts`, `test/predictiveFixtures.ts`, `test/linePanelFixtures.ts`, `docs/design/design-system.md` §4.1, `docs/design/decisions.md`.
- **Frontend.** Proveedor: pide el catálogo una vez, guarda `selectedId`, pide el dataset completo de la selección, expone carga/error; ante id desconocido o error de carga vuelve al sintético con aviso neutro y marca la entrada como no disponible en la sesión. `PartControl` según 8.3-f (objetivos ≥ 32 px, se envuelve con la barra, accesible desde el menú). `reset()` conserva la pieza; se eliminan `datasetChosen` y `aiDatasetId`. Pasos 2-3: resumen de solo lectura + «Importar CSV» (la importación aparece como entrada «Importado» y queda seleccionada); el enlace `?dataset=` fija la selección global. Paso 6: fuente = dataset activo; desaparecen el conmutador y `?datos=sintetico`; pestañas según `capabilities`. Vista A y panel de línea: dataset del proveedor; el panel muestra la pieza en su barra. Insignias por `source_type`. `ReportCard` y `ModelLab` ocultos con una línea de motivo cuando el endpoint responde 404. `groupLabel` aplicado ya a cabecera, KPI y barra de filtros de los pasos 2-3 (el resto en F25). Tope de 400 días sustituido por los días con producción del dataset. Estado de carga visible al cambiar de pieza.
- **Backend.** Ninguno, salvo decidir si `/datasets` queda como alias del catálogo o se elimina al perder su último consumidor (anotar en bitácora).
- **Datos.** Fixtures ficticias: segunda entrada REAL (solo estaciones, una agrupación) y los manejadores honran `dataset`.
- **Pruebas.** Vitest nuevo: `PartControl` (lista por línea, Aplicar cambia el dataset del paso 2, teclado/ARIA, degrada a una sola entrada), proveedor (restaurar conserva la pieza; id guardado desconocido ⇒ sintético), re-montaje al cambiar. Reescribir, no borrar: `RealDataset.test.tsx`, `RealPredictive.test.tsx`, `QualityJoinPanel.test.tsx`, pruebas de `LinePanelPage`, `DemoShell.test.tsx`. Con dos fixtures REAL, elegir la segunda dirige overview, variable, xy, oleadas, cusum, alarmas, riesgo y panel de línea a ese id (aserciones sobre peticiones MSW). `npm run build`. Comprobación en navegador con la receta de §7 sobre dos datasets ficticios convertidos, claro y oscuro; sin capturas en el repo.
- **Aceptación.** Exactamente un control editable de pieza (barra + menú). Cambiar la pieza cambia pasos 2, 3, 5-Vista A (o su tarjeta explicativa), 6 y panel de línea; pasos 1, 4, 7 y vistas simuladas no cambian. Con catálogo privado vacío (demo público) el control muestra la entrada sintética y todo funciona como hoy. Insignias de procedencia en cada panel (DoD 11). Edición metrology intacta.
- **Riesgos.** Mayor reescritura de pruebas del plan. Densidad de la barra por debajo de 1280 px. El merge cambia la UI pública: requiere OK del dueño.

#### F23 — Perfil declarativo, lector CSV ancho y unión por serie (Línea B)

- **Objetivo.** Convertidor genérico para «un CSV con cabecera por estación y día, unido por una columna de serie», que emite una carpeta por pieza con el contrato de 8.3-c, con ventana e histórico.
- **Archivos.** Nuevos: `backend/app/connectors/station_logs/{__init__,profile,sources,wide_csv,assemble,__main__}.py`, `backend/app/connectors/pieces_writer.py`, `backend/tests/station_logs_fixtures.py`, `backend/tests/test_station_logs_wide.py`, perfil de ejemplo ficticio en `seed/sample_files/station_logs/`. Tocados: `backend/app/connectors/long_signal_batch.py` (usa el escritor compartido; salida byte a byte idéntica), `backend/app/connectors/README.md`.
- **Backend.** Esquema pydantic del perfil; `sources` (carpeta o zip, globs de inclusión/exclusión, miembros idénticos una sola vez, zips anidados ignorados y contados); `WideStationCsvConnector(ImportConnector)` (validación de codificación, delimitador, número de columnas, marca decimal por archivo; endurecimiento compartido con `dimensional_csv`); ensamblador `key` (ignora llaves declaradas, última fila por llave y estación, hora de la pieza = primera estación, estación `None` si la pieza no llegó, bandera 16 para cadenas incompletas sin NOK registrado); asignación de pieza + herencia; variables excluidas por pieza; reglas `missing_if`; filas de referencia fallida ⇒ valores ausentes con veredicto NOK; ventana (`max_pieces` en días de producción completos o `from`/`to`) con estimación de memoria y negativa sobre presupuesto; `history` diario de toda la fuente; CLI `inventory` (conteos + esqueleto de perfil a una ruta privada), `convert`, `check`.
- **Frontend.** Ninguno.
- **Datos.** Ninguno versionado salvo el perfil de ejemplo ficticio. El perfil real se redacta fuera del repo y se entrega como archivo privado; la conversión real se ejecuta en el equipo del presentador hacia la raíz privada.
- **Pruebas.** Generador ficticio en `tmp_path` (cp1252, `;`, CRLF, cabecera con diéresis y una columna con errata, 5 estaciones, 2 piezas, llave 0, llave duplicada, carpeta duplicada, archivo de estudio, carpeta de archivo, un archivo con coma decimal, canal inactivo en una pieza, valor de detección fuera de rango, pieza rechazada antes de la estación de tipo, pieza que cruza la medianoche): una carpeta por pieza; mapeo por índice independiente del texto de cabecera; atribución a la primera estación que falla = verdad del generador; herencia de pieza; ventana conserva días completos y lo más reciente; `history` cubre toda la fuente; sin llaves, rutas ni nombres de origen en la salida; negativa dentro de un checkout; bytes idénticos para cualquier número de particiones y para zip frente a carpeta; errores de perfil específicos y sin valores. `test_long_signal_batch.py` sin cambios y en verde. Integración: la salida carga por el registro de F21 y sirve resumen, variable y panel de línea.
- **Aceptación.** Cambiar solo el perfil (reordenar estaciones, renombrar, reagrupar valores de pieza, cambiar la ventana) cambia la salida sin tocar código. Verificación local (fuera de CI, se anota como pendiente en el tablero si la sesión no tiene los datos): la conversión real termina en minutos con memoria acotada y sus conteos concilian con los agregados privados; el desplegable lista las piezas reales de Línea B. Ningún identificador real en archivos versionados, pruebas ni logs.
- **Riesgos.** Fase grande: si no cabe, `inventory` y `history` pasan a F24 explícitamente. La semántica «fila ausente = no llegó» es del perfil; una línea con huecos de registro aleatorios parecería tener rechazos (lo delatan la bandera 16 y el conteo). Los rechazos anteriores a la primera estación unida son invisibles en estos datasets: debe decirse en «Calidad del dato».

#### F24 — Lector de flujo de tokens y unión por posición/lado/vuelta (Línea A)

- **Objetivo.** Segundo lector genérico y unión para máquinas sin serial, con exactitud medida y exigida.
- **Archivos.** Nuevos: `backend/app/connectors/station_logs/token_stream.py`, `backend/tests/test_station_logs_tokens.py`, perfil de ejemplo ficticio. Tocados: `assemble.py`, `profile.py`, `__main__.py`.
- **Backend.** `TokenStreamConnector(ImportConnector)` según 8.3-e (coincidencia tolerante de etiquetas con o sin dos puntos y con espacio inicial; variantes de fila de salto con rellenos distintos); unión `carrier_window`; autocomprobación en el informe y como compuerta (tasa de coincidencia uno-a-uno por estación y coherencia de la propagación de rechazos); pieza leída en la estación que la registra y heredada; las cadenas de marcado no se mapean ni se escriben jamás; estaciones sin veredicto no son estaciones; estación eléctrica multi-par aporta solo su veredicto; cero-como-no-medido y topes de saturación como ausentes; cortes de registro de una estación ⇒ estación no probada, no NOK; `side_swap` por estación disponible y **desactivado**; las tolerancias que la fuente trae por fila se vuelcan a un borrador de `spec.json` (origen `source`) para F28. Agrupación: posición ⇒ primaria; lado ⇒ secundaria con etiquetas.
- **Frontend.** Ninguno obligatorio; «Calidad del dato» muestra el conteo de unión incierta por `data_quality`.
- **Datos.** Perfil real fuera del repo; conversión local por el usuario. Las imágenes del archivo no se leen ni se referencian.
- **Pruebas.** Generador ficticio de mesa indexada (posiciones, dos lados, estaciones con desfase de índice, paro de horas, corte de registro del ancla, filas de salto con ambos estilos de relleno, estación por lado, cambio de tipo, estación con lados cruzados): cadenas recuperadas = verdad del generador por encima del umbral; inciertas con bit 16; la conversión falla si los desfases del perfil son erróneos; sin cadenas de identidad en la salida; el lado llega a la ranura secundaria con etiquetas. La salida funciona con la matriz primaria × secundaria, alarmas por ambos grupos y el panel de línea. Una sola diferencia entre convertir una línea u otra: el perfil.
- **Aceptación.** La fixture se convierte solo con perfil; la calidad de unión se imprime y se exige. Verificación local: la conversión real pasa la compuerta y concilia en privado. Ningún código de tipo, etiqueta ni nombre de estación del cliente en código, pruebas o docs.
- **Riesgos.** Gramática irregular: las primitivas deben seguir siendo pocas; lo no expresable va a §7, no a casos especiales del cliente. La unión es identidad estadística: el residuo se cuenta, no se oculta. Una atribución de lado aparentemente cruzada en una estación no se corrige por código: se reporta y se consulta a planta.

#### F25 — Vocabulario, capacidades y bloques privados por dataset

- **Objetivo.** Que las pantallas hablen el vocabulario de cada pieza y muestren solo lo que sus datos soportan.
- **Archivos.** Backend: `api/v1/line_panel.py`, `services/line_panel_service.py`, `api/v1/predictive.py`, `services/real_predictive_service.py`, `schemas/*`. Frontend: `QualityOverview.tsx`, `QualityCharts.tsx`, `QualityFilterBar.tsx`, `DimensionalExplorer.tsx`, `CavityAlarms.tsx`, `PieceRisk.tsx`, `NokWaves.tsx`, `CusumPanel.tsx`, `lib/line-panel/model.ts`, `features/line-panel/views/*`, `lib/quality-analytics/export.ts`, `ContextStep.tsx`.
- **Backend.** Textos de reglas y acciones construidos con las etiquetas del dataset (redacción neutra y de sugerencia cuando no es el sintético de inyección); agrupación por defecto de alarmas = secundaria si existe, si no primaria; riesgo por pieza con motivo tipado (sin agrupación secundaria / menos de dos días de planta); validación de `machine` solo en la ruta sintética; `history` expuesto en el detalle. **Condicional:** si en la verificación local la frecuencia de alarmas de prioridad 2 queda fuera de una banda razonable, leer `panel-rules.json` por dataset hacia `evaluate_line(config=…)` (ya lo admite), eco de la configuración efectiva e inclusión en la clave de caché; si no, queda en §7.
- **Frontend.** Barrido completo de `groupLabel` (el sintético conserva sus textos byte a byte); mapa de proceso con los ids secundarios observados en vez de 1..N en 8 columnas fijas; compuertas por capacidad con explicación; sin código de máquina sintético ni preajustes sintéticos para datasets no sintéticos; tira «Historia completa (agregada)» en el paso 2 con la ventana cargada resaltada y los huecos de campaña visibles; tarjeta «Calidad del dato» con `assumptions` y los conteos nuevos; tira de estaciones de la pieza en el paso 1.
- **Pruebas.** pytest: agrupación por defecto por capacidad, motivos tipados, textos desde etiquetas, eco de reglas. Vitest: fixture con primaria «Cavidad» sin secundaria no renderiza «Nido» y oculta riesgo por pieza con su motivo; fixture con secundaria «Lado» renderiza la matriz y sus etiquetas; sintético sin cambios; mapa con ids no contiguos; tira de historia.
- **Aceptación.** Ningún vocabulario fijo de agrupación en pantallas cuya pieza declara otro. Lenguaje D12 intacto. Los textos siguen siendo sugerencias para decisión humana (CLAUDE.md §2, §24).
- **Riesgos.** Fase de mayor cambio de texto; riesgo de regresión visual en el sintético.

#### F26 — Gemelos ficticios en el demo público

- **Objetivo.** Que el sitio alojado también «se adapte», sin datos del cliente y por el mismo pipeline.
- **Archivos.** Nuevos: `seed/scripts/generate_demo_parts.py`, `seed/tests/test_demo_parts.py`, perfiles ficticios en `seed/sample_files/station_logs/`, `backend/app/demo_parts/<slug>/{manifest.json,pieces.csv.gz}`. Tocados: `dataset_registry.py`, `predictive.py`, `quality_analytics.py`, `line_panel_service.py`, `.gitignore` (excepción exacta), guarda de binarios (lista blanca exacta), `frontend/src/lib/predictive/source.ts`, `PartControl`.
- **Cambios.** Generador determinista de logs ficticios en ambos formatos (estaciones inventadas, olas NOK localizadas por grupo, un grupo persistentemente malo, paros, un cambio de tipo) ⇒ `station_logs convert` ⇒ copia a `backend/app/demo_parts/` (≤ 25 000 piezas, ≤ ~20 variables y ≤ ~1 MB por pieza). Registro: raíz empaquetada siempre activa en edición industrial, ids `demo-<slug>`, `source_type='SIMULATED'`. Estudios de secuencia de piezas habilitados por capacidad (`nok_basis == 'reported'`), no por REAL; umbrales del panel por número de piezas. Ningún valor se calcula a partir de estadísticas reales.
- **Pruebas.** Regenerar reproduce los archivos versionados byte a byte; etiquetas pasan `check_identifier`; tamaño acotado; gemelos listados como SIMULATED en todo `APP_ENV`; el registro privado sigue apagado en producción; todos los endpoints responden para un gemelo; Vitest: ningún panel de gemelo lleva insignia REAL. Receta de navegador sobre una pila sin datos privados. (No verificado: que el job de CI que corre `seed/tests` tenga las dependencias del backend; ajustarlo en la fase.)
- **Aceptación.** Despliegue sin ruta privada ⇒ el desplegable ofrece el sintético original más los gemelos y pasos 2, 3, 6 y panel de línea se adaptan a cada uno. Memoria del proceso con todo cargado holgada en una instancia de 512 MB (medida en la fase).
- **Riesgos.** Versionar gzip generados es nuevo en el repo (pequeños, ficticios, deterministas; alternativa: generarlos en el build de la imagen). La forma de la línea podría considerarse confidencial: fallo del dueño (D23).

#### F27 — Fiabilidad del día de la demo

- **Objetivo.** Arranque, memoria y cada entrada del desplegable comprobados antes de presentar.
- **Cambios.** `python -m app.demo_preflight`: recorre el catálogo como la app, carga cada entrada una vez y muestra una tabla (slug, estado, piezas, segundos de carga, memoria estimada, capacidades, omitidas con motivo); sale con error si la entrada inicial no está lista; sin rutas ni valores. Precarga del resumen y del panel de la entrada inicial. Ajuste para desactivar la importación CSV exploratoria en instancias públicas + aviso en el diálogo. Spec e2e del recorrido con selector solo sobre gemelos (`@playwright/test` como devDependency si `npm audit` queda limpio; si no, la receta manual). `docs/demo-industrial-quality.md`: «Alta de una pieza o línea nueva» (inventario → borrador de perfil → editar → convertir → aparece) y guía del presentador (modo local con datos reales / modo público con gemelos); `docs/deployment-editions.md` §6: qué sale de la red del cliente = nada.
- **Pruebas.** pytest del preflight (tabla, códigos de salida, sin fugas); la precarga no bloquea el arranque y sobrevive a una entrada rota; e2e por cada entrada de un catálogo ficticio y el caso de catálogo vacío; regresión completa.
- **Aceptación.** Corromper una carpeta antes del arranque quita exactamente esa entrada. Un tercero da de alta una pieza solo con perfil siguiendo la guía. DoD 1, 11, 12, 13 y 14 re-verificados.
- **Riesgos.** Suspensión/arranque en frío del plan gratuito fuera de nuestro control: paso de guion «abrir y esperar `/health`».

#### F28 — (Opcional) Especificación privada con origen y vigencia

`backend/app/connectors/dataset_spec.py` (`dataset-spec-v1` = `pin_pairs` actuales + `variables[{key, nominal?, lsl?, usl?, unit?, origin, valid_from?, note?}]`); spec inválida solo oculta vistas con límites; `Variable` gana períodos de límite; líneas de referencia rotuladas por origen y vigencia; Cp/Cpk solo para `drawing`/`source`, unilateral cuando solo hay un lado, sobre las piezas del período vigente; conteo de concordancia veredicto de máquina vs límite aparte. Pruebas: vectores Cp/Cpk calculados a mano con un cambio de límite (CLAUDE.md §11); los conteos NOK de un dataset REAL son idénticos con y sin spec.

#### F29 — (Opcional) Pareto por característica sobre veredicto reportado

`pieces-v3` con familia de columnas `r_<var>` (códigos de resultado por característica mapeados a ok/nok/no evaluado en el perfil); `value_nok` opcional en el dataset; con filtro de estación el Pareto pasa de estaciones a características, rotulado «veredicto reportado por la máquina». Vectores entrada→salida a mano; datasets sin `r_` no cambian. Prescindible sin afectar a F21-F27.

#### F30 — (Condicionada, no programada) Datos reales en un host privado autorizado

Solo con autorización **escrita** del cliente y autorización del dueño para cada paso de VPS/secretos/DNS: servir los datasets **convertidos** (nunca los orígenes ni imágenes) desde el montaje privado de solo lectura de la instancia industrial del VPS, con opt-in explícito y auditado, restricción de acceso delante de la instancia, aviso persistente en pantalla, enmienda registrada de D8 y procedimiento de retirada. El servicio público de demo no recibe datos reales bajo ninguna opción.

### 8.5 Decisiones nuevas (con valor por defecto)

| # | Decisión | Por defecto |
|---|---|---|
| D14 | «Pieza» = un dataset convertido por (línea, valor de pieza) declarado en el perfil privado; sin dimensión de pieza en el motor | Una entrada por tipo que la máquina identifica, agrupadas por línea; reagrupar es editar el perfil |
| D15 | (Extiende D8) Registro privado de N datasets, **solo local**; triple barrera en ejecución (no producción, orígenes loopback, sin marcador de host) + guarda de despliegue + guarda de binarios versionados | Activas; D8 no se reabre |
| D16 | (Extiende D13) Familia `station-logs` con perfil privado; todo vocabulario del cliente vive en el perfil; texto versionado solo con nombres neutros | Solo neutros |
| D17 | (Extiende D9) Fuentes sin zona: hora = reloj de la máquina, declarada como supuesto; cambio de horario no modelado | Reloj de máquina, offset 0, turnos de 8 h desde las 06:00 rotulados «supuesto de la demo» |
| D18 | (Extiende D10) Base NOK = veredicto de la máquina; límites solo por spec privada con origen y vigencia; `empirical` nunca da Cp/Cpk ni veredicto | Sin límites hasta F28 |
| D19 | Roles de agrupación primaria/secundaria con etiquetas por dataset | Línea B: cavidad ⇒ primaria; Línea A: posición ⇒ primaria, lado ⇒ secundaria; lados tal como se registran |
| D20 | Bloques privados por dataset junto al manifest (informe, estudio de modelos, spec, reglas del panel); se ocultan si faltan | Ocultar |
| D21 | Un único selector global «Pieza» (barra + menú); los pasos solo lo muestran | Sí |
| D22 | Ventana por pieza + histórico diario agregado; carga perezosa con LRU | 250 000 piezas más recientes; 2 cargados |
| D23 | Demo público = gemelos ficticios por el mismo pipeline; procedencia por raíz | Misma forma que las líneas reales, cardinalidades no necesariamente iguales, valores inventados |
| D24 | Identidad sintetizada (ancla, posición, lado) para líneas sin serial, con compuerta de calidad y bandera | Umbral 0,98 |
| D25 | Entrega: rama por fase + PR a `feat/industrial-quality-demo`; el dueño fusiona (cada push a esa rama redepliega el sitio público y la CI solo corre en PR y en `main`) | Rama + PR |
| D26 | Contrato: `pieces-v2` + bloques opcionales de manifest; `pieces-v3` solo si cambian columnas | v2 |
| D27 | Vista A es opt-in por dataset | Apagada para las líneas nuevas (las señales simuladas son de inyección); encendida para el dataset anterior |
| D28 | El dataset real anterior sigue seleccionable como entrada heredada con su id y sus archivos privados | Sí |

### 8.6 Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Fuga de datos o vocabulario del cliente al repo público (el lint de identificadores no marca nombres de línea, estación, tipo ni cadenas de marcado; el escaneo privado se omite en CI y en sesiones en la nube) | D16; `.gitignore` + guarda de binarios; lectores por índice y etiquetas del perfil; fixtures generadas en `tmp_path`; el dueño añade los términos nuevos a su lista privada antes de F23; revisión de `git diff --staged` |
| Datos reales ofrecidos en un host | Triple barrera D15 + la carpeta no existe allí + prueba de despliegue; F30 bloqueada |
| Memoria y latencia con historiales largos | Ventana en el convertidor, presupuesto de memoria, LRU, catálogo ligero, cachés, preflight |
| Opción muerta en plena demo | Solo se listan entradas validadas; el frontend valida la selección y cae al sintético |
| Límites ausentes o que cambiaron | Veredicto de máquina como base; spec con origen y vigencia; nada inferido se presenta como especificación |
| Unión sin serial mal emparejada | Compuerta, bandera 16, conteos en «Calidad del dato», prueba que falla con desfases erróneos |
| Reglas R1–R4 afinadas con el dataset anterior | Medición local; `panel-rules.json` condicional; nunca reajuste silencioso |
| Etiqueta «Nido» sobre una cavidad entre F23 y F25 | `groupLabel` en cabeceras ya en F22; descripción del dataset |
| Informe/estudio del primer cliente junto a otra pieza | Compuerta en F21 (backend) y F22 (frontend), antes de que exista la primera pieza nueva |
| Capturas o grabaciones con datos reales | Fuera del repo, docs y PRs |
| Fases demasiado grandes para una sesión | Cada fase declara qué se mueve y adónde |
| Pendientes heredados no resueltos aquí | DoD 14 (nombre del cliente en el historial de un commit antiguo), ejecución de F9, lint/pruebas de backend y frontend ausentes en CI |

### 8.7 Orden recomendado y mínimo presentable

1. **F21** (backend, sin datos reales).
2. **F22** y **F23** en paralelo (frontend / conectores, CLAUDE.md §15).
3. **F24**, **F25**, **F26**, **F27**.
4. Opcionales **F28**, **F29** cuando haya límites de plano o se pida el detalle por característica. **F30** solo con autorización escrita.

**Mínimo presentable (local): F21 + F22 + F23** — desplegable global con las piezas reales de Línea B, el dataset real anterior y el sintético; el sitio público muestra el mismo control con la entrada sintética. **Demo público adaptable: + F26.** **Segunda línea: + F24.** F25 y F27 mejoran honestidad y fiabilidad y son recortables si el tiempo aprieta, con una excepción: no presentar Línea A sin F25 (el lado necesita su etiqueta).
