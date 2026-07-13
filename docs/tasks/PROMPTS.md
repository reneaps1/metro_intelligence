# Prompts listos para ejecutar cada tarea pendiente

Copia y pega uno de estos prompts en una ventana/sesión nueva de Claude Code (u otro agente) para arrancar esa tarea desde cero, sin depender de ninguna conversación previa. Cada prompt apunta a su archivo de handoff en `docs/tasks/`.

Úsalos de uno en uno por ventana — no pegues varios en la misma sesión (rompería el aislamiento entre tareas que persigue este esquema).

---

### F3.3 — Generador de series de medición (ya tiene PR abierto, no usar prompt de implementación)

No ejecutes esta como las demás: ya existe una implementación completa en el PR #7 (`feat/mi-18-seed-measurement-series`), sin verificar contra Postgres real. Si quieres una ventana dedicada a esto:

```
Revisa el PR #7 (https://github.com/reneaps1/metro_intelligence/pull/7) del repo metro_intelligence. Corre los tests de seed/tests/test_measurement_series_generator.py contra una base PostgreSQL real (necesitas METRO_TEST_DATABASE_URL) y confirma si pasan. Reporta resultados; no mergees sin autorización explícita del usuario.
```

---

### F3.4 — Eventos de proceso, usuarios demo, historial de decisiones

```
Lee y ejecuta completa la tarea descrita en docs/tasks/F3.4.md del repo metro_intelligence. Sigue el workflow ahí descrito: crea la rama, implementa el alcance completo, escribe los tests indicados, y al terminar haz commit + push + abre el PR (referenciando MI-19) + actualiza la página de Notion correspondiente con el link del PR. No mergees el PR sin autorización explícita del usuario.
```

### F3.5 — Suite de validación de seed + archivos de muestra

```
Lee y ejecuta completa la tarea descrita en docs/tasks/F3.5.md del repo metro_intelligence. Sigue el workflow ahí descrito: crea la rama, implementa el alcance completo, escribe los tests indicados, y al terminar haz commit + push + abre el PR (referenciando MI-20) + actualiza la página de Notion correspondiente con el link del PR. No mergees el PR sin autorización explícita del usuario.
```

### F4.1 — Esqueleto FastAPI

```
Lee y ejecuta completa la tarea descrita en docs/tasks/F4.1.md del repo metro_intelligence. Sigue el workflow ahí descrito: crea la rama, implementa el alcance completo, escribe los tests indicados, y al terminar haz commit + push + abre el PR (referenciando MI-21) + actualiza la página de Notion correspondiente con el link del PR. No mergees el PR sin autorización explícita del usuario.
```

### F4.2 — Autenticación JWT + RBAC + rate limiting

```
Lee y ejecuta completa la tarea descrita en docs/tasks/F4.2.md del repo metro_intelligence. Esta es una tarea de seguridad crítica: sigue el workflow ahí descrito, crea la rama, implementa el alcance completo, escribe la suite de abuso indicada, y al terminar haz commit + push + abre el PR (referenciando MI-22) + actualiza Notion. Pide explícitamente revisión humana en la descripción del PR. No mergees bajo ninguna circunstancia sin que el usuario lo revise línea por línea.
```

### F4.3 — Servicio de auditoría

```
Lee y ejecuta completa la tarea descrita en docs/tasks/F4.3.md del repo metro_intelligence. Sigue el workflow ahí descrito: crea la rama, implementa el alcance completo, escribe los tests indicados, y al terminar haz commit + push + abre el PR (referenciando MI-23) + actualiza la página de Notion correspondiente con el link del PR. No mergees el PR sin autorización explícita del usuario.
```

### F4.4 — API CRUD de catálogo maestro + admin de usuarios

```
Lee y ejecuta completa la tarea descrita en docs/tasks/F4.4.md del repo metro_intelligence. Sigue el workflow ahí descrito: crea la rama, implementa el alcance completo, escribe los tests indicados, y al terminar haz commit + push + abre el PR (referenciando MI-24) + actualiza la página de Notion correspondiente con el link del PR. No mergees el PR sin autorización explícita del usuario.
```

### F4.5 — Pipeline de importación de archivos

```
Lee y ejecuta completa la tarea descrita en docs/tasks/F4.5.md del repo metro_intelligence. Esta es una tarea de seguridad crítica (parsea contenido externo): sigue el workflow ahí descrito, crea la rama, implementa el alcance completo, escribe la suite de abuso indicada, y al terminar haz commit + push + abre el PR (referenciando MI-25) + actualiza Notion. No mergees el PR sin autorización explícita del usuario.
```

### F4.6 — API de mediciones (runs, resultados, series temporales)

```
Lee y ejecuta completa la tarea descrita en docs/tasks/F4.6.md del repo metro_intelligence. Sigue el workflow ahí descrito: crea la rama, implementa el alcance completo, escribe los tests indicados (incluye el de performance), y al terminar haz commit + push + abre el PR (referenciando MI-26) + actualiza la página de Notion correspondiente con el link del PR. No mergees el PR sin autorización explícita del usuario.
```

### F4.8 — API de recomendaciones y decisiones

```
Lee y ejecuta completa la tarea descrita en docs/tasks/F4.8.md del repo metro_intelligence. Sigue el workflow ahí descrito: crea la rama, implementa el alcance completo, escribe los tests indicados, y al terminar haz commit + push + abre el PR (referenciando MI-28) + actualiza la página de Notion correspondiente con el link del PR. No mergees el PR sin autorización explícita del usuario.
```

### F5.1 — Setup Vite + Tailwind + tokens (revisar qué falta sobre el mock existente)

```
Lee y ejecuta completa la tarea descrita en docs/tasks/F5.1.md del repo metro_intelligence. Nota: gran parte del scaffold ya existe en frontend/ (construido en F5.M) — revisa primero qué falta antes de reconstruir nada. Sigue el workflow del archivo: crea la rama, implementa solo lo que realmente falta, escribe los tests indicados, y al terminar haz commit + push + abre el PR (referenciando MI-30) + actualiza Notion. No mergees sin autorización explícita del usuario.
```

### F5.3 — Shell de navegación (revisar qué falta sobre el mock existente)

```
Lee y ejecuta completa la tarea descrita en docs/tasks/F5.3.md del repo metro_intelligence. Nota: ya existe un shell funcional en frontend/src/layouts/ y components/ui/ (F5.M) — revisa primero qué falta antes de reconstruir nada. Sigue el workflow del archivo: crea la rama, implementa lo que falta, escribe los tests indicados, y al terminar haz commit + push + abre el PR (referenciando MI-32) + actualiza Notion. No mergees sin autorización explícita del usuario.
```

### F5.4 — Login real, sesión JWT, guards por rol

```
Lee y ejecuta completa la tarea descrita en docs/tasks/F5.4.md del repo metro_intelligence. Esta tarea reemplaza el login mockeado existente en frontend/src/lib/auth/AuthProvider.tsx por uno real — es seguridad crítica (el token nunca debe tocar localStorage). Sigue el workflow del archivo: crea la rama, implementa el alcance completo, escribe los tests indicados, y al terminar haz commit + push + abre el PR (referenciando MI-33) + actualiza Notion. Pide revisión humana explícita en el PR. No mergees sin autorización explícita del usuario.
```

### F5.5 — Pantallas de catálogo maestro (wire a API real)

```
Lee y ejecuta completa la tarea descrita en docs/tasks/F5.5.md del repo metro_intelligence. Nota: la UI de lectura ya existe en frontend/src/features/catalog/ (F5.M, datos mock) — reemplaza useDemoData() por la API real y añade lo que falta (búsqueda/filtros, formularios de edición, timeline de versiones). Sigue el workflow del archivo: crea la rama, escribe los tests indicados, y al terminar haz commit + push + abre el PR (referenciando MI-34) + actualiza Notion. No mergees sin autorización explícita del usuario.
```

### F5.6 — Pantalla de importación de archivos (wire a API real)

```
Lee y ejecuta completa la tarea descrita en docs/tasks/F5.6.md del repo metro_intelligence. Nota: ya existe una versión funcional simulada en frontend/src/features/imports/ImportPage.tsx (F5.M) — reemplaza la simulación por un dropzone real subiendo a la API de F4.5. Sigue el workflow del archivo: crea la rama, escribe los tests indicados, y al terminar haz commit + push + abre el PR (referenciando MI-35) + actualiza Notion. No mergees sin autorización explícita del usuario.
```

### F5.7 — Pantallas de mediciones (wire a API real)

```
Lee y ejecuta completa la tarea descrita en docs/tasks/F5.7.md del repo metro_intelligence. Nota: la UI y los gráficos ya existen en frontend/src/features/measurements/ (F5.M) — reemplaza useDemoData().getSeries() por la API real y añade lo que falta (eventos de proceso, zoom, downsampling). Sigue el workflow del archivo: crea la rama, escribe los tests indicados, y al terminar haz commit + push + abre el PR (referenciando MI-36) + actualiza Notion. No mergees sin autorización explícita del usuario.
```

### F5.9 — Bandeja de recomendaciones (wire a API real)

```
Lee y ejecuta completa la tarea descrita en docs/tasks/F5.9.md del repo metro_intelligence. Nota: el flujo completo ya existe contra datos mock en frontend/src/features/risk/RiskPage.tsx (F5.M) — reemplaza el estado en memoria por la API real de F4.8 y añade lo que falta (modal de confirmación, historial de ActionTaken, links de evidencia). Sigue el workflow del archivo: crea la rama, escribe los tests indicados, y al terminar haz commit + push + abre el PR (referenciando MI-38) + actualiza Notion. No mergees sin autorización explícita del usuario.
```

### F6.1 — Componentes de gráficas SPC (revisar qué falta sobre el mock existente)

```
Lee y ejecuta completa la tarea descrita en docs/tasks/F6.1.md del repo metro_intelligence. Nota: la mayoría de estos componentes ya existen y están validados en frontend/src/components/charts/ (F5.M) — revisa primero qué falta (principalmente ControlChart X̄-R, UCL/LCL, Storybook) antes de reconstruir nada. Sigue el workflow del archivo: crea la rama, implementa lo que falta, y al terminar haz commit + push + abre el PR (referenciando MI-39) + actualiza Notion. No mergees sin autorización explícita del usuario.
```

### F6.2 — Dashboard operativo (wire a API real)

```
Lee y ejecuta completa la tarea descrita en docs/tasks/F6.2.md del repo metro_intelligence. Nota: ya existe una versión completa contra datos mock en frontend/src/features/dashboards/OperationalDashboard.tsx (F5.M) — reemplaza useDemoData() por la API real y añade estados empty/loading/error explícitos. Sigue el workflow del archivo: crea la rama, y al terminar haz commit + push + abre el PR (referenciando MI-40) + actualiza Notion. No mergees sin autorización explícita del usuario.
```

### F6.3 — Dashboard ejecutivo (wire a API real)

```
Lee y ejecuta completa la tarea descrita en docs/tasks/F6.3.md del repo metro_intelligence. Nota: ya existe una versión contra datos mock en frontend/src/features/dashboards/ExecutiveDashboard.tsx (F5.M) — reemplaza los cálculos del cliente por datos reales del backend y construye el widget central de "estrategia de inspección" (ahorro + riesgo siempre juntos, nunca uno sin el otro). Sigue el workflow del archivo: crea la rama, y al terminar haz commit + push + abre el PR (referenciando MI-41) + actualiza Notion. No mergees sin autorización explícita del usuario.
```

### F7.D — Compliance engine (demo)

```
Lee y ejecuta completa la tarea descrita en docs/tasks/F7.D.md del repo metro_intelligence. Nota: la página de Notion de esta tarea estaba vacía, el alcance detallado en el archivo fue derivado por un agente anterior de CLAUDE.md — confirma que tiene sentido antes de implementar a ciegas, y sé explícito en el PR sobre cualquier decisión de diseño que tomes. Sigue el workflow del archivo: crea la rama, implementa el engine como función pura, escribe los tests con vectores calculados a mano, y al terminar haz commit + push + abre el PR (referenciando MI-44) + actualiza Notion. No mergees sin autorización explícita del usuario.
```

### F8.D — SPC engine (demo)

```
Lee y ejecuta completa la tarea descrita en docs/tasks/F8.D.md del repo metro_intelligence. Nota: la página de Notion de esta tarea estaba vacía, el alcance fue derivado de CLAUDE.md y docs/testing-strategy.md — confirma que tiene sentido antes de implementar a ciegas. Sigue el workflow del archivo: crea la rama, implementa Cp/Cpk y límites de control I-MR como funciones puras, verifica contra vectores calculados a mano, y al terminar haz commit + push + abre el PR (referenciando MI-45) + actualiza Notion. No mergees sin autorización explícita del usuario.
```

### F9.D — Risk engine (demo)

```
Lee y ejecuta completa la tarea descrita en docs/tasks/F9.D.md del repo metro_intelligence. Nota: la página de Notion de esta tarea estaba vacía, el alcance fue derivado de CLAUDE.md y docs/domain/conceptual-model.md — confirma que tiene sentido antes de implementar a ciegas. Sigue el workflow del archivo: crea la rama, implementa el score de riesgo explicable como función pura, escribe los tests con casos sintéticos, y al terminar haz commit + push + abre el PR (referenciando MI-46) + actualiza Notion. No mergees sin autorización explícita del usuario.
```

### F10.D — Adaptive inspection engine (demo)

```
Lee y ejecuta completa la tarea descrita en docs/tasks/F10.D.md del repo metro_intelligence. Nota crítica de seguridad de producto: este motor NUNCA debe escribir cambios operativos automáticamente, solo generar recomendaciones en estado pending (CLAUDE.md §2). La página de Notion estaba vacía, el alcance fue derivado — confirma que tiene sentido antes de implementar a ciegas. Sigue el workflow del archivo: crea la rama, implementa el motor, escribe los tests (incluyendo uno que verifique que nunca se salta el estado pending), y al terminar haz commit + push + abre el PR (referenciando MI-47) + actualiza Notion. No mergees sin autorización explícita del usuario.
```

---

## Orden sugerido si vas a ir ventana por ventana

1. **F4.1** primero — desbloquea todo F4.
2. **F3.4** y **F3.5** en paralelo (no dependen de F4).
3. **F4.2** justo después de F4.1 — desbloquea F4.3–F4.9 y F5.4.
4. **F4.3** después de F4.2.
5. **F4.4, F4.5, F4.6, F4.8** en paralelo entre sí, todos después de F4.2+F4.3.
6. **F5.1, F5.3** (mayormente ya hechos por el mock) en paralelo a lo anterior — no dependen del backend.
7. **F5.4** después de F4.2.
8. **F5.5, F5.6, F5.7, F5.9** cada uno después de su API correspondiente (F4.4, F4.5, F4.6, F4.8) y de F5.4.
9. **F6.1** en paralelo a lo anterior (mayormente ya hecho por el mock).
10. **F6.2, F6.3** después de F6.1 + sus APIs.
11. **F7.D → F8.D → F9.D → F10.D**, en ese orden estricto (cada uno consume la salida del anterior).
