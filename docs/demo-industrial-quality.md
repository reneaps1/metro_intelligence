# Demo Industrial Quality — guía de uso y guion

> Guía para quien presenta y para quien levanta la demo. Está en español porque la demo y su público lo están
> (excepción a CLAUDE.md §10). Ningún dato de cliente vive en el repositorio: las cifras reales se cargan desde
> archivos privados en el servidor (ver «Configuración privada»).

La demo recorre, en 7 pasos, cómo Metro Intelligence pasa de **visualizar NOK** a **investigar patrones, formular
hipótesis y evaluar riesgos con anticipación**, siendo explícita en cada pantalla sobre qué es real, simulado,
precalculado o experimental.

## 1. Levantar la demo

La demo solo existe en la **edición industrial** (`APP_EDITION=industrial`). En `metrology` (valor por defecto) el
menú, las rutas y los endpoints de la demo no existen (404).

### Con Docker Compose

```bash
cp .env.example .env            # completar valores locales; nunca commitear .env
# en .env: APP_EDITION=industrial, SEED_DEMO_USER_PASSWORD=<contraseña local>
docker compose up -d
docker compose exec backend python -m seed   # usuarios y catálogo ficticios (.demo.local)
```

### En desarrollo (sin contenedores)

1. PostgreSQL local migrado (`alembic upgrade head`) y usuarios ficticios (`python -m seed`).
2. Backend: `APP_EDITION=industrial uvicorn app.main:app --port 8000` desde `backend/`.
3. Frontend: `npx vite` desde `frontend/` (por defecto llama a `http://localhost:8000/api/v1`; otra URL con
   `VITE_API_BASE_URL`).

### Usuarios

Todos son ficticios, con la contraseña de `SEED_DEMO_USER_PASSWORD`:

| Usuario | Rol | Para qué |
|---|---|---|
| `ana.garcia@demo.local` | Metrólogo | **Recomendado para presentar**: ve todo y puede importar CSV (paso 2/3 y página de importación). |
| `sofia.mendez@demo.local` | Ingeniería de calidad | Ve toda la demo; no importa archivos. |
| `karla.jimenez@demo.local` | Consulta | No accede a la analítica de la demo (sin permiso de lectura de mediciones). |

## 2. Configuración privada (solo en el servidor de la demo)

Variables de entorno; los archivos viven fuera del repositorio y de la imagen. Sin ellas, la demo muestra ejemplos
ficticios rotulados «Ejemplo ilustrativo».

| Variable | Qué hace |
|---|---|
| `DEMO_CLIENT_LABEL` | Nombre que aparece como «Cliente». Por defecto «Cliente demo». |
| `DEMO_CRITICAL_NEST` | Nido donde el dataset sintético concentra los NOK. Debe coincidir con el nido crítico del informe; si no, el sintético y el informe señalan nidos distintos. |
| `DEMO_REPORT_SUMMARY_PATH` | JSON con el resumen del informe histórico (paso 2). |
| `DEMO_MODEL_LAB_PATH` | JSON con los resultados del estudio ML/DL (paso 6). Si las métricas reportadas no cuadran con la matriz de confusión, la pantalla lo avisa. |
| `DIMENSIONAL_IMPORT_MAX_ROWS` / `_MAX_MB` / `_TTL_MINUTES` | Topes de la importación exploratoria de CSV. |

Los formatos de ambos JSON están en `backend/app/schemas/quality_analytics.py` (`ReportSummary`) y
`backend/app/schemas/predictive.py` (`ModelLabIn`).

## 3. Guion (7–10 minutos)

Entrada: menú **Demo industrial** → «Iniciar demo». El selector de pasos de arriba permite saltar; «Restaurar
escenario demo» deja todo como al inicio sin tocar la base de datos.

| Paso | Tiempo | Qué mostrar | Qué decir |
|---|---|---|---|
| 1. Contexto industrial | 0:45 | Flujo inyección → nido → pieza → inspección → OK/NOK y la tabla de fuentes. | «Cada pantalla dice de dónde salen sus números: real, histórico, simulado, precalculado o experimental.» |
| 2. Diagnóstico de calidad | 1:30 | KPIs con denominadores, tasa NOK con IC 95 %, nido de mayor riesgo con riesgo relativo, Pareto, heatmap nido × cota, resumen del informe histórico. | «El riesgo relativo indica asociación, no causa.» Mostrar el filtro por nido y por cota. |
| 3. Exploración dimensional | 1:00 | Histograma con tolerancias, boxplot por nido/turno/lote, Cp/Cpk e I-MR, Cpk diario. | «Cp no aplica a tolerancias unilaterales; se explica en pantalla.» |
| 4. Laboratorio IIoT | 1:30 | Árbol de señales, arrastrar 2–3 señales, cursores A/B con Δt, escenario «deriva térmica». | «Estas señales son simuladas: así se vería conectar un PLC o iba.» |
| 5. Relación proceso–calidad | 1:00 | Preset de presión de mantenimiento → longitud (r, R², ecuación) y el preset de control (humedad, r≈0). | «Aquí la relación está impuesta a propósito para demostrar el método (Vista B).» |
| 6. IA predictiva y oleadas NOK | 2:00 | Pestañas: Modelos ML/DL → Oleadas NOK → (opcional CUSUM / What-if) → Fallas de máquina. | Ver mensajes clave abajo. |
| 7. Integración real | 0:45 | Cadena máquina → decisión humana y la tabla «hoy vs. con integración». | Mensaje central (abajo). |

Mensajes clave del paso 6:

- **Modelos ML/DL**: el deep learning no superó al ML tabular; con decenas de falsas alarmas por NOK detectado, el
  modelo sirve para priorizar revisión, **no** para rechazar piezas automáticamente.
- **Oleadas NOK**: la regla detecta las oleadas a los pocos minutos de empezar y aún protege la mayor parte de cada
  una, pero **no anticipa ninguna**: detectar una racha iniciada no es predecir su inicio.
- **Fallas de máquina**: con precursores (vibración/corriente) un modelo simple anticipa casi todas las fallas;
  sin precursor, casi ninguna. «Un modelo solo es tan bueno como las señales que avisan.»

Mensaje central (paso 7):

> Metro Intelligence conecta mediciones dimensionales y contexto de proceso en un mismo lugar para pasar de
> visualizar los NOK a investigar sus patrones, generar hipótesis y evaluar anticipadamente riesgos. La capa IIoT
> mostrada aquí es simulada: para validar causalidad y predicción necesitamos capturar señales reales de máquina,
> vincularlas a cada ciclo/pieza y evaluar modelos prospectivamente.

## 4. Cargar un CSV propio

En el paso 2 o 3: «Importar CSV propio» (o en la página **Import File**, bloque «Análisis dimensional con mapeo de
columnas»).

1. Soltar el archivo. Se detectan codificación, delimitador, decimal, tipos y un mapeo sugerido; todo se puede
   corregir.
2. Elegir formato **largo** (una fila por medición) o **ancho** (una fila por pieza) y revisar los roles: fecha/hora,
   pieza, ciclo, nido, máquina, turno, lote, OK/NOK de la fuente, variable/valor/límites.
3. «Validar y analizar»: informe de filas aceptadas y en cuarentena (con motivo). Los archivos grandes se analizan
   por muestra y el informe dice qué porcentaje.
4. «Ver analíticas de este archivo»: los pasos 2 y 3 pasan a ese dataset (insignia «Histórico»). «Descartar archivo»
   vuelve al demo.

Ejemplos ficticios: `seed/sample_files/mi_demo_dimensional_long.csv` (listo para usar) y `_wide.csv` (teclear las
tolerancias de `seed/sample_files/README.md`).

El archivo **no se guarda**: vive en memoria del servidor, solo para quien lo importó, y caduca
(`DIMENSIONAL_IMPORT_TTL_MINUTES`). Solo se audita el evento (usuario, hash, conteos). No subir CSV reales a un
servidor público sin autorización del cliente.

## 5. Procedencia por pantalla

| Pantalla | Procedencia |
|---|---|
| Paso 2–3 con el dataset demo | SIMULADO (mecanismos de defecto listados en «Verdad conocida») + resumen PRECALCULADO del informe |
| Paso 2–3 con un CSV importado | HISTÓRICO (archivo de un período cerrado, no verificado por la plataforma) |
| Paso 4 y 5 | SIMULADO; Vista B con causalidad impuesta |
| Paso 6 · Modelos ML/DL | PRECALCULADO (estudio histórico cerrado) |
| Paso 6 · Oleadas, CUSUM, What-if, Fallas | SIMULADO + EXPERIMENTAL; What-if además HIPOTÉTICO |
| Paso 7 | Propuesta; cada fila indica la procedencia de lo que hay hoy |

## 6. Límites de interpretación

- Nada en la demo actúa sobre producción: no libera, no rechaza, no ajusta máquinas.
- Asociación no es causalidad. La única causalidad que se muestra es la impuesta en el simulador (Vista B).
- Las cifras de estudios históricos no son predicciones en línea.
- Sin resultados por umbral, el laboratorio no dibuja curvas ROC/PR ni ofrece umbral: no se muestra lo que el
  estudio no produjo.
- Las cifras privadas del informe y del estudio deben verificarse contra el documento original antes de presentarlas.

## 7. Problemas frecuentes

| Síntoma | Causa probable |
|---|---|
| No aparece «Demo industrial» en el menú | `APP_EDITION` no es `industrial`. |
| «Ejemplo ilustrativo (cifras ficticias)» en el paso 2 o 6 | Falta o es inválido `DEMO_REPORT_SUMMARY_PATH` / `DEMO_MODEL_LAB_PATH` (el log del backend lo avisa sin mostrar la ruta). |
| El nido del sintético no coincide con el del informe | `DEMO_CRITICAL_NEST` distinto al nido crítico del informe. |
| Un CSV importado desaparece | Caducó (TTL) o el servidor se reinició: la importación es exploratoria y no se persiste. |
| «Importar CSV propio» no aparece | El usuario no tiene permiso de importación (usar el metrólogo). |
