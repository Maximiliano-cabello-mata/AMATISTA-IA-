# Resultados de la prueba rápida del revisor (20 documentos)

Medido en la computadora del laboratorio (`Intel Core i3-10100`, 8 hilos, 40 GB DDR4, Windows 11, Ollama `0.40.16`, embeddings `bge-m3@790764642607`) sobre la misma muestra de 20 documentos de `conocimiento_3d.documentos` (todos de la fuente `blender-manual`) y el mismo canon de 108 fragmentos. Ningún texto crudo del lago ni archivo de `salidas/` se incluye aquí.

## Comparativa 1 a 1 (`codellama:latest` vs `qwen3:8b`)

| Métrica | `codellama:latest` (`8fdf8f752f6e`, 3.8 GB) | `qwen3:8b` (`500a1f067a9f`, 5.2 GB) |
|---|---:|---:|
| `documentos` | 20 | 20 |
| `json_valido` | **1.00** (20/20) | **1.00** (20/20) |
| `pregunta_valida` | **1.00** (20/20) | **1.00** (20/20) |
| `cita_valida` (estricto en `documento_id`) | **0.05** (1/20) | **0.15** (3/20; 17/20 incluyen el id del canon en `seccion`) |
| `datos_extraidos` | 73 | 19 |
| `datos_fieles` (solo en `titulo + texto`) | **0.205** (15/73) | **0.00** (0/19; 17/19 son la versión `5.2`/`4.5`/`3.6` tomada de `url`) |
| Datos contaminados desde el canon | **45 datos** (en 11 docs) | **2 datos** (en 2 docs: `Intel HD/UHD 620`) |
| `coincide_pregunta_embudo` | **0.75** (15/20) | **0.55** (11/20) |
| `decisiones` (`aceptar` / `revision` / `rechazar`) | 14 / 6 / 0 | 9 / 11 / 0 |
| `no_se` | 2 | 3 |
| `segundos_por_documento` (mediana / máx) | 149.1 s / 248.7 s | 154.5 s / 216.2 s |
| `tokens_por_segundo` en corrida (genera / lee) | 2.70 tok/s / 34.74 tok/s | 2.35 tok/s / 41.60 tok/s |
| `tokens_por_segundo` aislado (`laboratorio.verificar`) | 6.3 tok/s / 16.3 tok/s (carga 23.1 s) | 4.4 tok/s / 15.9 tok/s (carga 5.1 s) |
| `horas_estimadas_para_1033` | 42.77 h | 44.33 h |

### Hallazgos clave de la comparación

1. **Calidad de los motivos (`ia_motivo`):**
   - `codellama:latest` respondió con una plantilla genérica en casi todos los documentos (*«El texto cumple con todas las etapas del embudo»* o *«El texto no cumple con las reglas del embudo»*), sin mencionar de qué trata la página.
   - `qwen3:8b` justificó cada decisión citando el contenido concreto de la página revisada (por ejemplo, las opciones `'UV Map'`, `'Aspect X/Y'`, `'Scale X/Y'` y `'Projectors'` en `UV Project Modifier`, o `'Shutter'` y `'Rolling Shutter'` en `Motion Blur`) y explicó por qué mandó a `revision` páginas introductorias o generales (`Limitations`, `Group`, `Introduction`, `Select All by Trait`, `Deleting & Dissolving`, `World Settings`, `Startup 4.5`, `Input`, `Light Probes Introduction`, `Structure`, `Ocean Modifier`).
2. **Contaminación de datos (`datos_fieles`):**
   - `codellama:latest` extrajo 73 datos, de los cuales **45 eran alucinaciones copiadas de los ejemplos del canon** (`RTX 3060`, `Ryzen`, `UHD 620`, `Blender 3.0.1`, `fps`, `ms`, `GB`, `%`).
   - `qwen3:8b` extrajo 19 datos en total: **17 son la versión real de Blender del documento (`5.2`, `4.5`, `3.6`) leída del campo `- url:`** que el propio prompt le muestra en `DOCUMENTO A REVISAR`, y solo **2 datos** en toda la corrida (`Intel HD Graphics 620` e `Intel UHD 620`) vinieron de ejemplos del canon. Como `validar()` en `revisor/revisar.py` busca únicamente en `titulo + texto` y no incluye `url`, las 17 versiones de la URL se contabilizaron como no fieles (`0/19`), pero si se incluye `url` la fidelidad real de `qwen3:8b` sube de `0.00` a **`0.895` (17/19)**.
3. **Formato de la cita (`cita_valida`):**
   - `qwen3:8b` acertó el `documento_id` exacto en 3/20 (`0.15`), pero en otros **14 documentos** sí citó el fragmento real del canon mostrado (`g7b/estandar-telemetria · ...` o `g7b/ingesta, sección 4. El embudo`) colocándolo dentro de `cita.seccion` y poniendo la URL del documento revisado en `cita.documento_id`.

---

## Corrida 1 · `codellama:latest` (`8fdf8f752f6e`, 7B Q4, 3.8 GB)

### Velocidad aislada (`laboratorio.verificar --revisor codellama:latest`)
- `codellama:latest`: genera **6.3 tok/s**, lee **16.3 tok/s**, carga **23.1 s**.

### Resumen exacto (`revisor.revisar`)

```json
{
  "modelo": "codellama:latest",
  "palabras_por_documento": 450,
  "fecha": "2026-11-21 22:44",
  "documentos": 20,
  "json_valido": 1.0,
  "pregunta_valida": 1.0,
  "cita_valida": 0.05,
  "datos_fieles": 0.2054794520547945,
  "datos_extraidos": 73,
  "coincide_pregunta_embudo": 0.75,
  "decisiones": {
    "aceptar": 14,
    "revision": 6,
    "rechazar": 0
  },
  "no_se": 2,
  "segundos_por_documento": {
    "mediana": 149.05966699999954,
    "maximo": 248.71451140000136
  },
  "tokens_por_segundo": {
    "genera": 2.7013520530610533,
    "lee": 34.73524843824167
  },
  "horas_estimadas_para_1033": 42.771843336388756
}
```

### Documentos enviados a `revision` por `codellama:latest` (6 de 20; 0 `rechazar`)

| # | Título | URL | `ia_etapa` | `ia_pregunta` | `ia_cita` | Motivo propuesto por el modelo |
|---:|---|---|---|---|---|---|
| 1 | `Limitations` | `https://docs.blender.org/manual/en/5.2/render/eevee/limitations/limitations.html` | `ninguna` | `ninguna` | `6 · 4. Limitaciones` | El texto no cumple con las etapas del embudo, ya que no menciona la fuente de la información ni proporciona evidencia concreta para respaldar las afirmaciones. |
| 7 | `Select All by Trait` | `https://docs.blender.org/manual/en/4.5/modeling/meshes/selecting/all_by_trait.html` | `relevancia` | `ninguna` | `plata/revision/1 · 4. El embudo` | El documento no cumple con la relevancia mínima establecida en el canon, ya que no menciona ninguna pregunta del plan. |
| 8 | `Deleting & Dissolving` | `https://docs.blender.org/manual/en/5.2/modeling/meshes/editing/mesh/delete.html` | `ninguna` | `P6` | `123456789 · 4. El embudo` | El documento no cumple con las reglas del embudo |
| 10 | `World Settings` | `https://docs.blender.org/manual/en/4.5/render/cycles/world_settings.html` | `ninguna` | `ninguna` | `blender-manual · render/cycles/world_settings` | El texto no cumple con las reglas del embudo, no menciona las preguntas del plan y no proporciona suficiente información para tomar una decisión confiable. |
| 16 | `Structure ` | `https://docs.blender.org/manual/en/3.6/modeling/meshes/structure.html` | `ninguna` | `ninguna` | `g7b/estandar-telemetria/1 · 4. El embudo` | El texto no cumple con las reglas del embudo |
| 17 | `UV Project Modifier` | `https://docs.blender.org/manual/en/5.2/modeling/modifiers/modify/uv_project.html` | `ninguna` | `ninguna` | `blender-manual · 5.2` | El texto no cumple con las reglas del embudo |

---

## Corrida 2 · `qwen3:8b` (`500a1f067a9f`, 8B Q4, 5.2 GB)

### Velocidad aislada (`laboratorio.verificar --revisor qwen3:8b`)
- `qwen3:8b`: genera **4.4 tok/s**, lee **15.9 tok/s**, carga **5.1 s**.

### Resumen exacto (`revisor.revisar`)

```json
{
  "modelo": "qwen3:8b",
  "palabras_por_documento": 450,
  "fecha": "2026-11-22 00:18",
  "documentos": 20,
  "json_valido": 1.0,
  "pregunta_valida": 1.0,
  "cita_valida": 0.15,
  "datos_fieles": 0.0,
  "datos_extraidos": 19,
  "coincide_pregunta_embudo": 0.55,
  "decisiones": {
    "aceptar": 9,
    "revision": 11,
    "rechazar": 0
  },
  "no_se": 3,
  "segundos_por_documento": {
    "mediana": 154.47976774999916,
    "maximo": 216.15462839999964
  },
  "tokens_por_segundo": {
    "genera": 2.3468531229167846,
    "lee": 41.59681522797065
  },
  "horas_estimadas_para_1033": 44.32711113493031
}
```

### Documentos enviados a `revision` por `qwen3:8b` (11 de 20; 0 `rechazar`)

| # | Título | URL | `ia_etapa` | `ia_pregunta` | Motivo propuesto por el modelo |
|---:|---|---|---|---|---|
| 1 | `Limitations` | `https://docs.blender.org/manual/en/5.2/render/eevee/limitations/limitations.html` | `relevancia` | `ninguna` | El documento describe limitaciones técnicas de EEVEE, pero no responde directamente a las preguntas del plan. No aborda ajustes para trabajar con fluidez (P1), versiones recomendadas (P2) ni técnicas aplicables con herramientas libres (P5). |
| 2 | `Group` | `https://docs.blender.org/manual/en/5.2/render/shader_nodes/groups.html` | `relevancia` | `P6` | El documento responde a la pregunta P6 sobre cómo se hace algo en una versión concreta de un programa libre, ya que explica el uso de los nodos de grupo en Blender 5.2. |
| 5 | `Introduction` | `https://docs.blender.org/manual/en/4.5/modeling/meshes/properties/vertex_groups/introduction.html` | `relevancia` | `ninguna` | El documento describe la función general de los grupos de vértices en Blender, pero no responde directamente a las preguntas del plan (P6 o P5) ni proporciona información específica sobre versiones, configuraciones, o técnicas aplicables en la industria con herramientas libres. |
| 7 | `Select All by Trait` | `https://docs.blender.org/manual/en/4.5/modeling/meshes/selecting/all_by_trait.html` | `relevancia` | `ninguna` | El documento describe herramientas de selección en Blender, pero no responde directamente a las preguntas del plan (P1, P2, P6) ni proporciona información sobre ajustes, versiones, hardware o técnicas aplicables con herramientas libres. |
| 8 | `Deleting & Dissolving` | `https://docs.blender.org/manual/en/5.2/modeling/meshes/editing/mesh/delete.html` | `relevancia` | `P6` | El documento responde a la pregunta P6 sobre cómo se hace algo en una versión concreta de un programa libre, pero su contenido es muy general y no incluye medidas, versiones específicas de Blender ni ajustes concretos que cumplan con el criterio de valor. |
| 10 | `World Settings` | `https://docs.blender.org/manual/en/4.5/render/cycles/world_settings.html` | `relevancia` | `ninguna` | El documento describe configuraciones de renderizado en Blender, pero no responde directamente a las preguntas del plan (P1, P6) ni aborda temas como versiones de Blender, hardware, ajustes concretos o equivalencias con herramientas libres. |
| 11 | `Startup` | `https://docs.blender.org/manual/en/4.5/troubleshooting/startup.html` | `relevancia` | `ninguna` | El documento aborda problemas de inicio de Blender y mensajes de consola, pero no responde directamente a la pregunta P2 sobre qué versión de Blender conviene en cada equipo. No proporciona información específica sobre compatibilidad de versiones con hardware. |
| 12 | `Input` | `https://docs.blender.org/manual/en/5.2/editors/preferences/input.html` | `relevancia` | `ninguna` | El documento describe configuraciones de entrada en Blender pero no responde directamente a las preguntas del plan, especialmente P6, P1, P2 y P4. No menciona versiones concretas de Blender ni técnicas aplicables con herramientas libres. |
| 15 | `Introduction ` | `https://docs.blender.org/manual/en/3.6/render/eevee/light_probes/introduction.html` | `relevancia` | `ninguna` | El documento describe la función general de los objetos de proyección en Eevee, pero no responde específicamente a la pregunta P6 sobre cómo se hace algo en una versión concreta de Blender. No incluye instrucciones detalladas ni ejemplos de configuración para una versión específica. |
| 16 | `Structure ` | `https://docs.blender.org/manual/en/3.6/modeling/meshes/structure.html` | `relevancia` | `ninguna` | El documento describe la estructura básica de los meshes en Blender, pero no responde directamente a ninguna de las preguntas del plan. No menciona ajustes concretos, versiones de Blender, técnicas industriales ni equivalencias con herramientas libres. |
| 19 | `Ocean Modifier` | `https://docs.blender.org/manual/en/5.2/modeling/modifiers/physics/ocean.html` | `relevancia` | `ninguna` | El documento describe el modificador Ocean en Blender, pero no responde directamente a las preguntas del plan (P1, P2, P3, P4, P5, P6) ni proporciona datos cuantitativos o comparativos que permitan inferir información relevante para el plan. |
