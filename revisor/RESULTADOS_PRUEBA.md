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

---

## Desempeño documento por documento (20 documentos)

| # | Título | Versión (URL) | Preguntas embudo | `codellama:latest` (decisión · preg · s · lee/gen tok) | `qwen3:8b` (decisión · preg · s · lee/gen tok) |
|---:|---|---|---|---|---|
| 1 | `Limitations` | 5.2 | P6 P1 P2 | revision · ninguna · 248.7 s (3161/159 tok) | revision · ninguna · 216.2 s (2777/185 tok) |
| 2 | `Group` | 5.2 | P6 P1 | aceptar · P6 · 152.0 s (2883/175 tok) | revision · P6 · 145.0 s (2528/195 tok) |
| 3 | `Startup ` | 3.6 | P2 | aceptar · P2 · 127.5 s (2815/169 tok) | aceptar · P2 · 130.3 s (2465/202 tok) |
| 4 | `Is Edge Manifold Node` | 5.2 | P6 | aceptar · P6 · 114.9 s (2889/130 tok) | aceptar · P6 · 131.2 s (2518/196 tok) |
| 5 | `Introduction` | 4.5 | P6 P5 | aceptar · P6 · 146.1 s (3163/161 tok) | revision · ninguna · 157.9 s (2793/211 tok) |
| 6 | `Displace Hair Curves ` | 3.6 | P6 | aceptar · P6 · 179.7 s (3111/213 tok) | aceptar · P6 · 163.3 s (2678/211 tok) |
| 7 | `Select All by Trait` | 4.5 | P6 P1 | revision · ninguna · 139.3 s (3283/152 tok) | revision · ninguna · 153.8 s (2848/211 tok) |
| 8 | `Deleting & Dissolving` | 5.2 | P6 P1 | revision · P6 · 172.0 s (3646/135 tok) | revision · P6 · 183.6 s (3177/211 tok) |
| 9 | `Set ID Node` | 5.2 | P6 | aceptar · P6 · 128.2 s (2719/152 tok) | aceptar · P6 · 121.6 s (2363/173 tok) |
| 10 | `World Settings` | 4.5 | P1 P6 | revision · ninguna · 219.1 s (3888/162 tok) | revision · ninguna · 205.8 s (3444/191 tok) |
| 11 | `Startup` | 4.5 | P2 | aceptar · P2 · 128.9 s (2922/162 tok) | revision · ninguna · 129.6 s (2569/180 tok) |
| 12 | `Input` | 5.2 | P6 P1 P2 P4 | aceptar · P6 · 184.1 s (3773/172 tok) | revision · ninguna · 179.5 s (3323/201 tok) |
| 13 | `Instance Bounds Node` | 5.2 | P1 | aceptar · P1 · 154.4 s (3018/165 tok) | aceptar · P1 · 152.1 s (2637/200 tok) |
| 14 | `Select Sharp Edges` | 5.2 | P6 | aceptar · P6 · 123.0 s (2559/174 tok) | aceptar · P6 · 117.0 s (2236/183 tok) |
| 15 | `Introduction ` | 3.6 | P6 | aceptar · P6 · 120.0 s (2601/155 tok) | revision · ninguna · 118.0 s (2240/184 tok) |
| 16 | `Structure ` | 3.6 | P6 P1 P5 | revision · ninguna · 185.0 s (3701/120 tok) | revision · ninguna · 195.1 s (3230/202 tok) |
| 17 | `UV Project Modifier` | 5.2 | P6 | revision · ninguna · 138.4 s (3230/128 tok) | aceptar · P6 · 161.4 s (2830/220 tok) |
| 18 | `Motion Blur` | 4.5 | P6 | aceptar · P6 · 156.1 s (3032/168 tok) | aceptar · P6 · 155.1 s (2656/205 tok) |
| 19 | `Ocean Modifier` | 5.2 | P6 P5 P1 | aceptar · P6 · 196.9 s (3534/172 tok) | revision · ninguna · 188.0 s (3114/203 tok) |
| 20 | `Mesh to Curve Node` | 5.2 | P6 | aceptar · P6 · 134.6 s (3042/170 tok) | aceptar · P6 · 133.6 s (2640/194 tok) |

---

## Análisis (22 de noviembre)

**Decisión: `codellama` se descarta; `qwen3:8b` es el candidato.**
- Sus motivos hablan del contenido real de cada página.
- Solo contaminó 2 datos con los ejemplos del canon (contra 45 de `codellama`).
- En 14 de 20 documentos entendió qué citar, pero lo puso en el campo equivocado.

**Lo que no era culpa del modelo y se corrigió en la versión 2 del revisor:**
- **La comprobación de datos no miraba la URL.** La versión de una página del manual (`5.2`, `4.5`, `3.6`) es un dato real. Con la URL incluida, la fidelidad de `qwen3` pasa de 0.00 a 0.89 (17 de 19).
- **La cita era un campo libre.** Ahora es una lista cerrada.
- **La extracción de datos no le tocaba al modelo**, según la regla del proyecto: lo exacto se hace por código. Ahora la hace el código.

**La velocidad es el límite real.** En `qwen3`, cada documento se va en partes casi iguales entre leer unos 2,700 tokens (unos 64 s) y generar unos 200 (unos 85 s). La versión 2 recorta la parte de generar. Leer solo baja si Ollama reutiliza las instrucciones fijas (diagnóstico del paso 7), si se muestran menos palabras o si se usa un modelo más chico. Cada uno de esos cambios es una corrida aparte.

**Lo que todavía no se sabe:** si `qwen3` acierta.
- Mandó a revisión 11 de 20 páginas del manual, casi todas por «relevancia».
- La pregunta P6 («cómo se hace algo en una versión concreta») cubre casi cualquier página del manual. `qwen3` la interpreta de forma más estrecha que el embudo.
- No sabemos si es demasiado estricto o si tiene razón. Lo dice la persona que marque los 20.

---

## Corrida 3 · Versión 2 del revisor con `qwen3:8b` (`500a1f067a9f`, 108 fragmentos)

### Paso 7 · Diagnóstico de la caché (`--diagnostico-cache`)

```text
Tokens leídos: primera llamada 1173, segunda 1176. La caché NO se reutiliza: cada documento relee las instrucciones.
```

### Paso 8 · Resumen exacto (`revisor.revisar` v2)

```json
{
  "revisor": 2,
  "modelo": "qwen3:8b",
  "palabras_por_documento": 450,
  "canon_fragmentos": 108,
  "fecha": "2026-11-22 01:19",
  "documentos": 20,
  "json_valido": 1.0,
  "pregunta_valida": 1.0,
  "cita_valida": 1.0,
  "cita_embudo": 0.5,
  "coherente": 0.55,
  "coincide_pregunta_embudo": 0.75,
  "decisiones": {
    "aceptar": 6,
    "revision": 14,
    "rechazar": 0
  },
  "no_se": 0,
  "segundos_por_documento": {
    "mediana": 124.47994835000281,
    "maximo": 198.4852652000045
  },
  "tokens_por_segundo": {
    "genera": 2.3645411871950284,
    "lee": 37.85668911925164
  },
  "tokens_por_documento": {
    "lee": 2726.0,
    "genera": 116.5
  },
  "horas_estimadas_para_1033": 35.71882962376469
}
```

### Verificación de las predicciones H1–H7 (escritas antes de correr en `9b49e3f`)

| # | Predicción | p | Resultado medido | Cumple |
|---|---|---:|---|---|
| **H1** | `cita_valida` = 1.00 (la lista cerrada lo garantiza) | 0.95 | **`1.00`** (20/20; `cita_embudo = 0.50`) | ✓ |
| **H2** | `coherente` ≥ 0.90 | 0.60 | **`0.55`** (11/20 coherentes; 9 con `asigna una pregunta pero dice que falla la relevancia`) | ✗ |
| **H3** | Tokens generados por documento (mediana) ≤ 120 (antes, 200) | 0.70 | **`116.5`** tokens generados (mediana; leídos: `2726.0`) | ✓ |
| **H4** | Segundos por documento (mediana) entre 90 y 125 (antes, 154) | 0.60 | **`124.48 s`** (máximo `198.49 s`; horas para 1,033 docs: `44.33 → 35.72 h`, −19.4 %) | ✓ |
| **H5** | El diagnóstico dice que la caché NO se reutiliza | 0.60 | **No se reutiliza** (`1173` vs `1176` tokens leídos) | ✓ |
| **H6** | `qwen3:8b` v2 manda a revisión entre 6 y 12 de los 20 (antes, 11) | 0.65 | **`14` a revisión** (`6 aceptar`, `14 revision`, `0 rechazar`, `no_se = 0`) | ✗ |
| **H7** | La decisión de v2 coincide con la de v1 en al menos 15 de los 20 documentos | 0.65 | **`17 de 20` coinciden** (los 11 de `revision` de v1 siguen en `revision`, y 6 de `aceptar` siguen en `aceptar`) | ✓ |

**Resultado de predicciones v2:** **5 de 7 cumplidas** (`H1`, `H3`, `H4`, `H5`, `H7`).

### Por qué fallaron H2 (`coherente = 0.55`) y H6 (`14 en revisión`)

Las dos fallas tienen la misma causa en los 9 documentos marcados con la incoherencia `asigna una pregunta pero dice que falla la relevancia` (`Limitations`, `Group`, `Deleting & Dissolving`, `World Settings`, `Startup 4.5`, `Input`, `Instance Bounds Node`, `Select Sharp Edges`, `Ocean Modifier`):
1. **Orden de campos en el esquema JSON con `think: false`:** en `ESQUEMA`, el modelo está obligado a emitir `"decision"` y `"etapa"` en los primeros tokens (antes de `"pregunta"` y `"motivo"`). Sin cadena de pensamiento previa (`think: false`), empieza por `"decision": "revision", "etapa": "relevancia"`, pero al llegar a `"pregunta"` y `"motivo"` redacta una justificación positiva con `"confianza": "alta"` explicando que el documento **sí** responde a `P6`/`P2`/`P1`.
2. **Ambigüedad en la instrucción de `etapa`:** `hoja_fija` define `- etapa: la etapa que falla, o la que más pesa en tu decisión. Si acepta, «ninguna».` Cuando el modelo elige `revision`, interpreta que debe indicar *«la etapa que más pesa en su decisión»* (`relevancia`) aunque haya asignado una pregunta válida.

### Tabla documento por documento (v1 `codellama` · v1 `qwen3:8b` · v2 `qwen3:8b`)

| # | Título | Ver | Embudo | v1 `codellama` (dec · preg · s) | v1 `qwen3:8b` (dec · preg · s) | v2 `qwen3:8b` (dec · etapa · preg · s · lee/gen tok · coherente) |
|---:|---|---|---|---|---|---|
| 1 | `Limitations` | 5.2 | P6 P1 P2 | revision · ninguna · 248.7s | revision · ninguna · 216.2s | revision · relevancia · P6 · 138.6s (2834/119) · ✗ |
| 2 | `Group` | 5.2 | P6 P1 | aceptar · P6 · 152.0s | revision · P6 · 145.0s | revision · relevancia · P6 · 111.2s (2574/106) · ✗ |
| 3 | `Startup ` | 3.6 | P2 | aceptar · P2 · 127.5s | aceptar · P2 · 130.3s | revision · relevancia · ninguna · 104.2s (2502/127) · ✓ |
| 4 | `Is Edge Manifold Node` | 5.2 | P6 | aceptar · P6 · 114.9s | aceptar · P6 · 131.2s | aceptar · ninguna · P6 · 102.0s (2582/114) · ✓ |
| 5 | `Introduction` | 4.5 | P6 P5 | aceptar · P6 · 146.1s | revision · ninguna · 157.9s | revision · relevancia · ninguna · 125.8s (2854/129) · ✓ |
| 6 | `Displace Hair Curves ` | 3.6 | P6 | aceptar · P6 · 179.7s | aceptar · P6 · 163.3s | aceptar · ninguna · P6 · 135.3s (2739/139) · ✓ |
| 7 | `Select All by Trait` | 4.5 | P6 P1 | revision · ninguna · 139.3s | revision · ninguna · 153.8s | revision · relevancia · ninguna · 116.1s (2930/113) · ✓ |
| 8 | `Deleting & Dissolving` | 5.2 | P6 P1 | revision · P6 · 172.0s | revision · P6 · 183.6s | revision · relevancia · P6 · 141.1s (3235/101) · ✗ |
| 9 | `Set ID Node` | 5.2 | P6 | aceptar · P6 · 128.2s | aceptar · P6 · 121.6s | aceptar · ninguna · P6 · 101.4s (2412/107) · ✓ |
| 10 | `World Settings` | 4.5 | P1 P6 | revision · ninguna · 219.1s | revision · ninguna · 205.8s | revision · relevancia · P6 · 198.5s (3521/161) · ✗ |
| 11 | `Startup` | 4.5 | P2 | aceptar · P2 · 128.9s | revision · ninguna · 129.6s | revision · relevancia · P2 · 99.3s (2603/105) · ✗ |
| 12 | `Input` | 5.2 | P6 P1 P2 P4 | aceptar · P6 · 184.1s | revision · ninguna · 179.5s | revision · relevancia · P6 · 137.0s (3392/97) · ✗ |
| 13 | `Instance Bounds Node` | 5.2 | P1 | aceptar · P1 · 154.4s | aceptar · P1 · 152.1s | revision · relevancia · P1 · 123.7s (2701/119) · ✗ |
| 14 | `Select Sharp Edges` | 5.2 | P6 | aceptar · P6 · 123.0s | aceptar · P6 · 117.0s | revision · relevancia · P6 · 106.2s (2321/136) · ✗ |
| 15 | `Introduction ` | 3.6 | P6 | aceptar · P6 · 120.0s | revision · ninguna · 118.0s | revision · relevancia · ninguna · 83.2s (2297/113) · ✓ |
| 16 | `Structure ` | 3.6 | P6 P1 P5 | revision · ninguna · 185.0s | revision · ninguna · 195.1s | revision · relevancia · ninguna · 148.4s (3292/126) · ✓ |
| 17 | `UV Project Modifier` | 5.2 | P6 | revision · ninguna · 138.4s | aceptar · P6 · 161.4s | aceptar · ninguna · P6 · 114.0s (2895/97) · ✓ |
| 18 | `Motion Blur` | 4.5 | P6 | aceptar · P6 · 156.1s | aceptar · P6 · 155.1s | aceptar · ninguna · P6 · 125.2s (2702/122) · ✓ |
| 19 | `Ocean Modifier` | 5.2 | P6 P5 P1 | aceptar · P6 · 196.9s | revision · ninguna · 188.0s | revision · relevancia · P6 · 147.9s (3183/102) · ✗ |
| 20 | `Mesh to Curve Node` | 5.2 | P6 | aceptar · P6 · 134.6s | aceptar · P6 · 133.6s | aceptar · ninguna · P6 · 131.0s (2713/134) · ✓ |

---

## Corridas 4 y 5 · Canon v3 (119 fragmentos, revisor v2): `canon3` (sin `--criterios`) vs `criterios` (con `--criterios`)

### Paso 10 · Indexación del Canon v3 y evaluación de 51 preguntas

```text
Canon v3: 16 documentos, 119 fragmentos (palabras por fragmento: mediana 93, máximo 261)
Modelo de embeddings: bge-m3@790764642607
  ↑ ia/criterios: 8 fragmentos
Listo: 1 documentos actualizados (8 fragmentos), 15 sin cambios, 0 podados.

supabase bge-m3@790764642607 texto=1.0 vector=1.0: recall@1 0.80 · recall@3 0.96 · MRR 0.88 (umbral recall@3 0.85)
  falla p15: esperaba g7b/estandar-telemetria, salió ['g7b/geodar-radar', 'g7b/ingesta', 'g7b/telemetria'] (rango None)
  falla p20: esperaba g7b/cubo, salió ['g7b/fichas-tecnicas', 'g7b/ingesta', 'g7b/telemetria'] (rango 5)
```

### Paso 11 · Resumen exacto de `canon3` (sin `--criterios`)

```json
{
  "revisor": 2,
  "criterios": false,
  "modelo": "qwen3:8b",
  "palabras_por_documento": 450,
  "canon_fragmentos": 119,
  "fecha": "2026-11-22 02:13",
  "documentos": 20,
  "json_valido": 1.0,
  "pregunta_valida": 1.0,
  "cita_valida": 1.0,
  "cita_embudo": 0.55,
  "coherente": 0.5,
  "coincide_pregunta_embudo": 0.8,
  "decisiones": {
    "aceptar": 6,
    "revision": 13,
    "rechazar": 1
  },
  "no_se": 1,
  "segundos_por_documento": {
    "mediana": 106.09193985000093,
    "maximo": 186.61912920000032
  },
  "tokens_por_segundo": {
    "genera": 2.3521637855365096,
    "lee": 46.24045376407613
  },
  "tokens_por_documento": {
    "lee": 2641.5,
    "genera": 113.0
  },
  "horas_estimadas_para_1033": 30.442492740291932
}
```

### Paso 11 · Resumen exacto de `criterios` (con `--criterios`)

```json
{
  "revisor": 2,
  "criterios": true,
  "modelo": "qwen3:8b",
  "palabras_por_documento": 450,
  "canon_fragmentos": 119,
  "fecha": "2026-11-22 03:00",
  "documentos": 20,
  "json_valido": 1.0,
  "pregunta_valida": 1.0,
  "cita_valida": 1.0,
  "cita_embudo": 0.15,
  "coherente": 0.7,
  "coincide_pregunta_embudo": 0.9,
  "decisiones": {
    "aceptar": 6,
    "revision": 14,
    "rechazar": 0
  },
  "no_se": 0,
  "segundos_por_documento": {
    "mediana": 134.69468054999743,
    "maximo": 222.67488669999875
  },
  "tokens_por_segundo": {
    "genera": 1.9824913098569177,
    "lee": 46.43646587068822
  },
  "tokens_por_documento": {
    "lee": 3589.5,
    "genera": 115.0
  },
  "horas_estimadas_para_1033": 38.64989028004093
}
```

### Paso 13 · Diagnóstico de la caché con 4 variantes (`--diagnostico-cache --variantes`)

```text
[como hoy: formato + sin pensar] tokens leídos: primera 1208 (2.3 s), segunda 1211 (1.6 s). La caché NO se reutiliza.
[sin formato obligatorio] tokens leídos: primera 1208 (1.5 s), segunda 1211 (1.6 s). La caché NO se reutiliza.
[sin el parámetro think] tokens leídos: primera 1202 (1.0 s), segunda 1205 (1.1 s). La caché NO se reutiliza.
[el mismo mensaje dos veces] tokens leídos: primera 1208 (1.5 s), segunda 1208 (0.3 s). La caché SÍ se reutiliza.
```

### Verificación de las predicciones H8–H10 y H17–H18

| # | Predicción | p | Resultado medido | Cumple |
|---|---|---:|---|---|
| **H8** | `coherente` de `criterios` ≥ `coherente` sin criterios | 0.70 | **`0.70` ≥ `0.50`** (`14/20` vs `10/20`, +20 pp de coherencia) | ✓ |
| **H9** | `criterios` manda a revisión menos documentos que sin criterios | 0.55 | **`14` vs `13` en `revision`** (`canon3` tuvo `13 revision + 1 rechazar = 14` no aceptados; `criterios` tuvo `14 revision + 0 rechazar`) | ✗ |
| **H10** | La mediana de s/doc de `criterios` es al menos 25 s mayor (antes, 10 s) | 0.75 | **`134.69 s` vs `106.09 s`** (`+28.60 s ≥ 25 s`, por leer `3589.5` vs `2641.5` tokens) | ✓ |
| **H17** | Al menos una de las 4 variantes del diagnóstico reutiliza la caché | 0.55 | **Sí (por tiempo):** `[el mismo mensaje dos veces]` baja de `1.5 s → 0.3 s` (Ollama sigue reportando `1208` en `prompt_eval_count` aunque tome de la caché) | ✓ |
| **H18** | «El mismo mensaje dos veces» reutiliza la caché | 0.50 | **Sí la reutiliza** (`1.5 s → 0.3 s`, 5× más rápido) | ✓ |

### Comparación documento por documento en Canon v3 (`canon3` vs `criterios`)

| # | Título | Ver | Embudo | `canon3` (dec · etapa · preg · s · lee/gen · coh) | `criterios` (dec · etapa · preg · s · lee/gen · coh) |
|---:|---|---|---|---|---|
| 1 | `Limitations` | 5.2 | P6 P1 P2 | revision · relevancia · P6 · 140.0s (3022/122) · ✗ | revision · valor · P6 · 222.7s (3970/128) · ✓ |
| 2 | `Group` | 5.2 | P6 P1 | revision · relevancia · P6 · 107.6s (2487/105) · ✗ | revision · valor · P6 · 123.7s (3435/110) · ✓ |
| 3 | `Startup ` | 3.6 | P2 | revision · relevancia · P2 · 101.0s (2414/104) · ✗ | revision · relevancia · P2 · 124.0s (3362/117) · ✗ |
| 4 | `Is Edge Manifold Node` | 5.2 | P6 | aceptar · ninguna · P6 · 81.8s (2325/117) · ✓ | revision · valor · P6 · 89.0s (3273/115) · ✓ |
| 5 | `Introduction` | 4.5 | P6 P5 | revision · relevancia · ninguna · 108.5s (2581/124) · ✓ | revision · relevancia · P6 · 121.5s (3529/122) · ✗ |
| 6 | `Displace Hair Curves ` | 3.6 | P6 | aceptar · ninguna · P6 · 118.9s (2739/139) · ✓ | revision · relevancia · P6 · 145.8s (3687/122) · ✗ |
| 7 | `Select All by Trait` | 4.5 | P6 P1 | rechazar · relevancia · ninguna · 122.6s (2862/115) · ✓ | revision · relevancia · ninguna · 152.1s (3810/117) · ✓ |
| 8 | `Deleting & Dissolving` | 5.2 | P6 P1 | revision · relevancia · P6 · 129.6s (3050/104) · ✗ | revision · valor · P6 · 156.4s (3998/126) · ✓ |
| 9 | `Set ID Node` | 5.2 | P6 | revision · relevancia · P6 · 86.4s (2348/105) · ✗ | revision · relevancia · P6 · 97.7s (3296/102) · ✗ |
| 10 | `World Settings` | 4.5 | P1 P6 | revision · relevancia · P6 · 186.6s (3233/172) · ✗ | revision · relevancia · P6 · 215.2s (4181/182) · ✗ |
| 11 | `Startup` | 4.5 | P2 | revision · relevancia · ninguna · 103.7s (2752/126) · ✓ | aceptar · ninguna · P2 · 149.0s (3700/125) · ✓ |
| 12 | `Input` | 5.2 | P6 P1 P2 P4 | revision · relevancia · P6 · 112.2s (3275/106) · ✗ | revision · valor · P6 · 179.7s (4223/105) · ✓ |
| 13 | `Instance Bounds Node` | 5.2 | P1 | aceptar · ninguna · P1 · 104.6s (2549/119) · ✓ | aceptar · ninguna · P1 · 129.6s (3497/114) · ✓ |
| 14 | `Select Sharp Edges` | 5.2 | P6 | revision · relevancia · P6 · 76.9s (2241/99) · ✗ | aceptar · ninguna · P6 · 94.2s (3189/110) · ✓ |
| 15 | `Introduction ` | 3.6 | P6 | revision · relevancia · P6 · 79.2s (2297/103) · ✗ | revision · relevancia · P6 · 109.9s (3245/108) · ✗ |
| 16 | `Structure ` | 3.6 | P6 P1 P5 | revision · relevancia · ninguna · 128.4s (3001/122) · ✓ | revision · valor · ninguna · 157.1s (3949/113) · ✓ |
| 17 | `UV Project Modifier` | 5.2 | P6 | aceptar · ninguna · P6 · 93.7s (2559/97) · ✓ | aceptar · ninguna · P6 · 130.2s (3507/115) · ✓ |
| 18 | `Motion Blur` | 4.5 | P6 | aceptar · ninguna · P6 · 49.1s (2702/115) · ✓ | aceptar · ninguna · P6 · 139.2s (3650/114) · ✓ |
| 19 | `Ocean Modifier` | 5.2 | P6 P5 P1 | revision · relevancia · P6 · 119.7s (3008/103) · ✗ | revision · valor · P6 · 164.2s (3956/125) · ✓ |
| 20 | `Mesh to Curve Node` | 5.2 | P6 | aceptar · ninguna · P6 · 77.3s (2440/111) · ✓ | aceptar · ninguna · P6 · 103.2s (3388/112) · ✓ |

---

## Corrida 6 · Versión 3 del revisor (`--nombre v3`, 119 fragmentos, razona antes de decidir)

### Paso 14 · Resumen exacto (`revisor: 3`)

```json
{
  "revisor": 3,
  "criterios": false,
  "modelo": "qwen3:8b",
  "palabras_por_documento": 450,
  "cuantos": 3,
  "umbral": null,
  "canon_fragmentos": 119,
  "fecha": "2026-11-22 12:47",
  "documentos": 20,
  "json_valido": 1.0,
  "pregunta_valida": 1.0,
  "cita_valida": 1.0,
  "cita_embudo": 0.7,
  "coherente": 0.9,
  "motivo_primero": 1.0,
  "coincide_pregunta_embudo": 0.25,
  "decisiones": {
    "aceptar": 1,
    "revision": 11,
    "rechazar": 8
  },
  "decisiones_efectivas": {
    "aceptar": 1,
    "revision": 9,
    "rechazar": 8,
    "persona": 2
  },
  "etapas": {
    "relevancia": 15,
    "valor": 3,
    "ninguna": 2
  },
  "no_se": 0,
  "segundos_por_documento": {
    "mediana": 116.18949450000218,
    "maximo": 241.70526889999746
  },
  "tokens_por_segundo": {
    "genera": 2.652759657373647,
    "lee": 42.03604055898492
  },
  "tokens_por_documento": {
    "lee": 2676.5,
    "genera": 146.5
  },
  "horas_estimadas_para_1033": 33.33992994958396
}
```

### Verificación de las predicciones H11–H16 (Revisor v3)

| # | Predicción | p | Resultado medido | Cumple |
|---|---|---:|---|---|
| **H11** | `motivo_primero = 1.00` (Ollama respeta el orden del esquema) | 0.85 | **`1.00`** (20/20 empiezan por `motivo`) | ✓ |
| **H12** | `coherente >= 0.85` (v2: 0.55; `canon3`: 0.50) | 0.60 | **`0.90`** (18/20 coherentes; +40 pp frente a `canon3`) | ✓ |
| **H13** | Manda a revisión (decisión del modelo) 11 o menos de 20 (v2: 14) | 0.60 | **`11` en `revision`** (`9` en `decisiones_efectivas`, más `2` en `persona` y `8` en `rechazar`) | ✓ |
| **H14** | Los 6 que v2 aceptó siguen aceptados | 0.70 | **Solo 1 sigue en `aceptar`** (`Motion Blur`); de los otros 5, 3 pasaron a `revision` (`Displace Hair Curves`, `Set ID Node`, `UV Project Modifier`, `Mesh to Curve Node`) y 1 a `rechazar` (`Is Edge Manifold Node`) | ✗ |
| **H15** | `relevancia` es la etapa en menos de la mitad de las revisiones (v2: 14 de 14) | 0.60 | **`9 de 11` revisiones tienen `relevancia`** (`1` tiene `valor` y `1` tiene `ninguna`; en toda la muestra, `etapas: {"relevancia": 15, "valor": 3, "ninguna": 2}`) | ✗ |
| **H16** | Mediana de tokens generados <= 140 (el motivo puede ser más largo) | 0.65 | **`146.5` tokens generados** (mediana; tiempo mediano `116.19 s`, `33.34 h` para 1,033 docs) | ✗ |

### Hallazgos de la Corrida 6 (`revisor: 3` sin `--criterios`)

1. **Razonar antes de decidir corrigió las contradicciones (`coherente: 0.50 → 0.90`):**
   - Al emitir primero `motivo → pregunta → cita → etapa → decision`, las incoherencias bajaron de 10/20 en `canon3` (9/20 en `v2`) a solo **2/20** (`Limitations` y `Startup 3.6`, ambos derivados automáticamente a `decision_efectiva: persona`).
2. **Sin `--criterios`, el modelo cae en los Errores Conocidos E2 y E3:**
   - Al tener que alinear la decisión final con su propio `motivo` y no tener los criterios `C2`/`E2`/`E3` en la hoja fija, el modelo evalúa las páginas de referencia del manual como si no tuvieran versión (ignorando que la versión `5.2`/`4.5`/`3.6` viene en la URL) o exige que tengan mediciones de hardware/FPS para pasar la etapa de `valor` (por ejemplo en `Select Sharp Edges` y `Mesh to Curve Node`, donde asigna `P6` pero marca `etapa: valor`), mandando 8 páginas a `rechazar` y 11 a `revision`.

### Tabla documento por documento (`canon3` v2 vs `v3` sobre los mismos 119 fragmentos)

| # | Título | Ver | Embudo | `canon3` v2 (dec · etapa · preg · s · coh) | `v3` (dec → efectiva · etapa · preg · s · lee/gen · coh) |
|---:|---|---|---|---|---|
| 1 | `Limitations` | 5.2 | P6 P1 P2 | revision · relevancia · P6 · 140.0s · ✗ | revision · relevancia · P6 · 241.7s (3057/167) · ✗ |
| 2 | `Group` | 5.2 | P6 P1 | revision · relevancia · P6 · 107.6s · ✗ | revision · relevancia · ninguna · 119.3s (2522/150) · ✓ |
| 3 | `Startup ` | 3.6 | P2 | revision · relevancia · P2 · 101.0s · ✗ | revision · ninguna · P2 · 99.5s (2449/146) · ✗ |
| 4 | `Is Edge Manifold Node` | 5.2 | P6 | aceptar · ninguna · P6 · 81.8s · ✓ | rechazar · relevancia · ninguna · 80.5s (2360/144) · ✓ |
| 5 | `Introduction` | 4.5 | P6 P5 | revision · relevancia · ninguna · 108.5s · ✓ | rechazar · relevancia · ninguna · 105.5s (2616/130) · ✓ |
| 6 | `Displace Hair Curves ` | 3.6 | P6 | aceptar · ninguna · P6 · 118.9s · ✓ | revision · relevancia · ninguna · 143.7s (2774/164) · ✓ |
| 7 | `Select All by Trait` | 4.5 | P6 P1 | rechazar · relevancia · ninguna · 122.6s · ✓ | rechazar · relevancia · ninguna · 134.2s (2897/153) · ✓ |
| 8 | `Deleting & Dissolving` | 5.2 | P6 P1 | revision · relevancia · P6 · 129.6s · ✗ | revision · relevancia · ninguna · 146.7s (3085/154) · ✓ |
| 9 | `Set ID Node` | 5.2 | P6 | revision · relevancia · P6 · 86.4s · ✗ | revision · relevancia · ninguna · 90.2s (2383/127) · ✓ |
| 10 | `World Settings` | 4.5 | P1 P6 | revision · relevancia · P6 · 186.6s · ✗ | revision · relevancia · ninguna · 199.5s (3268/219) · ✓ |
| 11 | `Startup` | 4.5 | P2 | revision · relevancia · ninguna · 103.7s · ✓ | revision · relevancia · ninguna · 113.0s (2787/128) · ✓ |
| 12 | `Input` | 5.2 | P6 P1 P2 P4 | revision · relevancia · P6 · 112.2s · ✗ | revision · relevancia · ninguna · 175.1s (3310/147) · ✓ |
| 13 | `Instance Bounds Node` | 5.2 | P1 | aceptar · ninguna · P1 · 104.6s · ✓ | rechazar · relevancia · ninguna · 108.3s (2584/139) · ✓ |
| 14 | `Select Sharp Edges` | 5.2 | P6 | revision · relevancia · P6 · 76.9s · ✗ | rechazar · valor · P6 · 86.7s (2276/138) · ✓ |
| 15 | `Introduction ` | 3.6 | P6 | revision · relevancia · P6 · 79.2s · ✗ | rechazar · valor · ninguna · 82.8s (2332/125) · ✓ |
| 16 | `Structure ` | 3.6 | P6 P1 P5 | revision · relevancia · ninguna · 128.4s · ✓ | rechazar · relevancia · ninguna · 132.3s (3036/144) · ✓ |
| 17 | `UV Project Modifier` | 5.2 | P6 | aceptar · ninguna · P6 · 93.7s · ✓ | revision · relevancia · ninguna · 107.7s (2594/143) · ✓ |
| 18 | `Motion Blur` | 4.5 | P6 | aceptar · ninguna · P6 · 49.1s · ✓ | aceptar · ninguna · P6 · 136.7s (2737/156) · ✓ |
| 19 | `Ocean Modifier` | 5.2 | P6 P5 P1 | revision · relevancia · P6 · 119.7s · ✗ | rechazar · relevancia · ninguna · 142.9s (3043/166) · ✓ |
| 20 | `Mesh to Curve Node` | 5.2 | P6 | aceptar · ninguna · P6 · 77.3s · ✓ | revision · valor · P6 · 100.7s (2475/158) · ✓ |

---

## Análisis de la corrida v3 (22 de noviembre)

**1. La coherencia subió por el camino equivocado.** El revisor razona antes de decidir (`motivo_primero` = 1.00) y la coherencia pasó de 0.50 a 0.90. Pero de los 8 documentos que dejaron de ser incoherentes, **7 lo lograron cambiando la pregunta a «ninguna»**; ninguno pasó a aceptado. Los documentos con pregunta del plan asignada bajaron de 16 a 5 de 20.

El modelo resolvió la contradicción declarando irrelevantes las páginas, en vez de reconocer que respondían a P6. La comprobación de coherencia por código se cumple, pero no garantiza que la decisión sea buena.

**2. La v3 sin criterios es la más dura de todas:** 1 aceptado, 11 a revisión y **8 rechazados**. Antes: 6 aceptados y 0–1 rechazos. Rechaza páginas de nodos y modificadores concretos («Is Edge Manifold Node», «Instance Bounds Node», «Select Sharp Edges»). Por la regla del embudo, esas páginas tienen ajustes concretos y responden a P6.

Dos causas probables:
- la instrucción del motivo pide decir «si alguna etapa del embudo falla», y eso empuja a buscar fallas;
- sin los criterios, falta C6: no rechazar sin una regla concreta.

**3. Las decisiones en páginas limítrofes cambian mucho entre versiones.** De los 6 que aceptó la v2, la v3 solo mantuvo 1. Sin etiquetas de una persona no se puede saber qué versión acierta. **La decisión sobre P6 y las páginas del manual («Por decidir» en los criterios) es la que más mueve el resultado.**

**4. Caché: el diagnóstico tenía un defecto.** Su primera llamada ya estaba tibia: 1,208 tokens en 1.5 s, cuando en frío tomarían unos 30 s. En realidad, las instrucciones fijas **sí** quedaban en caché en el diagnóstico. Pero en las corridas, agregar 950 tokens de criterios costó unos 20 s más de lectura por documento, así que algo de la corrida real impide reutilizarlas. Una causa candidata es que el esquema cambia con cada documento, porque la lista de citas es distinta. El diagnóstico nuevo parte de una llamada fría y prueba ese caso.
