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

---

## Corrida 7 · Velocidad `v3_c1` (`--cuantos 1`), diagnóstico de caché fría (`H21–H22`) y Canon v4

### Diagnóstico de caché con primera llamada fría (`H21–H22`)

```text
[1. fría] 1244 tokens contados, 56.4 s de lectura
[2. otro documento, mismo esquema] 1247 tokens contados, 1.7 s de lectura
[3. otro documento y otras citas] 1244 tokens contados, 1.6 s de lectura
Entre documentos: la caché SÍ se reutiliza. Con otra lista de citas: SÍ.
```

### Paso 16 · Indexación del Canon v4 (126 fragmentos) y evaluación de 51 preguntas

```text
Canon v4: 16 documentos, 126 fragmentos (palabras por fragmento: mediana 83, máximo 261)
Modelo de embeddings: bge-m3@790764642607
  ↑ ia/criterios: 15 fragmentos
Listo: 1 documentos actualizados (15 fragmentos), 15 sin cambios, 0 podados.

supabase bge-m3@790764642607 texto=1.0 vector=1.0: recall@1 0.84 · recall@3 0.96 · MRR 0.90 (umbral recall@3 0.85)
  falla p15: esperaba g7b/estandar-telemetria, salió ['g7b/geodar-radar', 'g7b/ingesta', 'g7b/telemetria'] (rango None)
  falla p20: esperaba g7b/cubo, salió ['g7b/fichas-tecnicas', 'g7b/ingesta', 'g7b/telemetria'] (rango 5)
```

### Resumen exacto de `v3_c1` (`--cuantos 1`, 119 fragmentos)

```json
{
  "revisor": 3,
  "criterios": false,
  "modelo": "qwen3:8b",
  "palabras_por_documento": 450,
  "cuantos": 1,
  "umbral": null,
  "canon_fragmentos": 119,
  "fecha": "2026-11-22 13:21",
  "documentos": 20,
  "json_valido": 1.0,
  "pregunta_valida": 1.0,
  "cita_valida": 1.0,
  "cita_embudo": 0.85,
  "coherente": 0.85,
  "motivo_primero": 1.0,
  "coincide_pregunta_embudo": 0.15,
  "decisiones": {
    "aceptar": 3,
    "revision": 6,
    "rechazar": 11
  },
  "decisiones_efectivas": {
    "aceptar": 3,
    "revision": 3,
    "rechazar": 11,
    "persona": 3
  },
  "etapas": {
    "relevancia": 14,
    "valor": 1,
    "ninguna": 5
  },
  "no_se": 0,
  "segundos_por_documento": {
    "mediana": 75.76536515000043,
    "maximo": 121.23115629999666
  },
  "tokens_por_segundo": {
    "genera": 3.138598525437782,
    "lee": 62.36417689775696
  },
  "tokens_por_documento": {
    "lee": 1940.5,
    "genera": 134.5
  },
  "horas_estimadas_para_1033": 21.740450611097348
}
```

### Verificación de H19, H21 y H22

| # | Predicción | p | Resultado medido | Cumple |
|---|---|---:|---|---|
| **H19** | Con `--cuantos 1`, la mediana de segundos es al menos 10 s menor que la de `v3` | 0.70 | **`75.77 s` vs `116.19 s`** (`-40.42 s`, `-34.8 %`; horas para 1,033 docs bajan de `33.34 → 21.74 h`) | ✓ |
| **H21** | Con la primera llamada fría, entre documentos SÍ se reutiliza la caché (`paso 2 < 50 % del paso 1`) | 0.60 | **`56.4 s → 1.7 s`** (3.0 % del tiempo frío; 33× más rápido) | ✓ |
| **H22** | Con otra lista de citas en el esquema, la caché NO se reutiliza | 0.50 | **Sí se reutiliza (`1.6 s`)**: cambiar el `enum` del esquema JSON no invalida la caché KV del prefijo del prompt | ✗ |

---

## Corridas 8 y 9 · Paso 17 (Revisor v3 + Canon v4, 126 fragmentos): `canon4` (sin `--criterios`) vs `criterios_v3` (con `--criterios` y errores conocidos E1–E6)

### Resumen exacto de `canon4` (v3, 126 fragmentos, sin `--criterios`)

```json
{
  "revisor": 3,
  "criterios": false,
  "modelo": "qwen3:8b",
  "palabras_por_documento": 450,
  "cuantos": 3,
  "umbral": null,
  "canon_fragmentos": 126,
  "fecha": "2026-11-22 14:05",
  "documentos": 20,
  "json_valido": 1.0,
  "pregunta_valida": 1.0,
  "cita_valida": 1.0,
  "cita_embudo": 0.75,
  "coherente": 0.95,
  "motivo_primero": 1.0,
  "coincide_pregunta_embudo": 0.3,
  "decisiones": {
    "aceptar": 3,
    "revision": 9,
    "rechazar": 8
  },
  "decisiones_efectivas": {
    "aceptar": 3,
    "revision": 8,
    "rechazar": 8,
    "persona": 1
  },
  "etapas": {
    "relevancia": 13,
    "valor": 3,
    "ninguna": 4
  },
  "no_se": 0,
  "segundos_por_documento": {
    "mediana": 113.7316933500042,
    "maximo": 162.13062149999314
  },
  "tokens_por_segundo": {
    "genera": 2.629252840145342,
    "lee": 44.87206694600207
  },
  "tokens_por_documento": {
    "lee": 2676.5,
    "genera": 146.5
  },
  "horas_estimadas_para_1033": 32.634677564042875
}
```

### Resumen exacto de `criterios_v3` (v3, 126 fragmentos, con `--criterios` E1–E6)

```json
{
  "revisor": 3,
  "criterios": true,
  "modelo": "qwen3:8b",
  "palabras_por_documento": 450,
  "cuantos": 3,
  "umbral": null,
  "canon_fragmentos": 126,
  "fecha": "2026-11-22 15:01",
  "documentos": 20,
  "json_valido": 1.0,
  "pregunta_valida": 1.0,
  "cita_valida": 1.0,
  "cita_embudo": 0.4,
  "coherente": 0.9,
  "motivo_primero": 1.0,
  "coincide_pregunta_embudo": 0.8,
  "decisiones": {
    "aceptar": 9,
    "revision": 11,
    "rechazar": 0
  },
  "decisiones_efectivas": {
    "aceptar": 9,
    "revision": 9,
    "rechazar": 0,
    "persona": 2
  },
  "etapas": {
    "relevancia": 3,
    "valor": 8,
    "ninguna": 9
  },
  "no_se": 0,
  "segundos_por_documento": {
    "mediana": 155.3376158999963,
    "maximo": 291.05603300000075
  },
  "tokens_por_segundo": {
    "genera": 2.023529972512473,
    "lee": 51.680634314941976
  },
  "tokens_por_documento": {
    "lee": 4270.5,
    "genera": 153.5
  },
  "horas_estimadas_para_1033": 44.57326589574894
}
```

### Verificación de las predicciones H23–H26 (4 de 4 cumplidas)

| # | Predicción | p | Resultado medido | Cumple |
|---|---|---:|---|---|
| **H23** | `v3` con `--criterios` (canon v4) rechaza 2 o menos de 20 (`v3` sin criterios: 8; `canon4`: 8) | 0.70 | **`0` rechazos** (`9 aceptar`, `11 revision`, `0 rechazar`; efectivas: `9 aceptar`, `9 revision`, `2 persona`) | ✓ |
| **H24** | `v3` con `--criterios` asigna pregunta del plan en 12 o más de 20 (`v3` sin criterios: 5; `canon4`: 6) | 0.60 | **`16 de 20` con pregunta asignada** (`coincide_pregunta_embudo` sube de `0.25`/`0.30` a **`0.80`**) | ✓ |
| **H25** | `v3` con `--criterios` acepta 5 o más de 20 (`v3` sin criterios: 1; `canon4`: 3) | 0.55 | **`9 de 20` aceptados** (los 9 con coherencia perfecta) | ✓ |
| **H26** | `v3` con `--criterios` tiene `coherente >= 0.85` | 0.65 | **`0.90`** (18/20 coherentes; en `canon4`: `0.95`, 19/20) | ✓ |

*(Además, entre `canon4` y `criterios_v3`, los no aceptados bajan de `17` [`9 revision + 8 rechazar`] a `11` [`11 revision + 0 rechazar`], la etapa `relevancia` baja de `13` a solo `3`, y la mediana de tiempo pasa de `113.73 s` a `155.34 s`, `+41.61 s >= 25 s`).*

### Tabla documento por documento en Canon v4 (`canon4` vs `criterios_v3`)

| # | Título | Ver | Embudo | `canon4` (dec → ef · etapa · preg · s · coh) | `criterios_v3` (dec → ef · etapa · preg · s · lee/gen · coh) |
|---:|---|---|---|---|---|
| 1 | `Limitations` | 5.2 | P6 P1 P2 | revision · valor · P6 · 162.1s · ✓ | revision → persona · relevancia · P6 · 291.1s (4651/167) · ✗ |
| 2 | `Group` | 5.2 | P6 P1 | revision · relevancia · ninguna · 117.3s · ✓ | revision · valor · ninguna · 149.8s (4116/152) · ✓ |
| 3 | `Startup ` | 3.6 | P2 | revision → persona · ninguna · P2 · 101.4s · ✗ | revision → persona · relevancia · P2 · 144.0s (4043/153) · ✗ |
| 4 | `Is Edge Manifold Node` | 5.2 | P6 | rechazar · relevancia · ninguna · 86.0s · ✓ | aceptar · ninguna · P6 · 98.7s (3954/133) · ✓ |
| 5 | `Introduction` | 4.5 | P6 P5 | rechazar · relevancia · ninguna · 107.7s · ✓ | revision · valor · ninguna · 134.3s (4210/142) · ✓ |
| 6 | `Displace Hair Curves ` | 3.6 | P6 | revision · relevancia · ninguna · 125.7s · ✓ | revision · valor · P6 · 168.7s (4368/159) · ✓ |
| 7 | `Select All by Trait` | 4.5 | P6 P1 | rechazar · relevancia · ninguna · 133.0s · ✓ | aceptar · ninguna · P6 · 206.5s (4491/213) · ✓ |
| 8 | `Deleting & Dissolving` | 5.2 | P6 P1 | revision · relevancia · ninguna · 151.3s · ✓ | aceptar · ninguna · P6 · 197.2s (4679/193) · ✓ |
| 9 | `Set ID Node` | 5.2 | P6 | revision · relevancia · ninguna · 95.2s · ✓ | revision · valor · P6 · 119.5s (3977/141) · ✓ |
| 10 | `World Settings` | 4.5 | P1 P6 | aceptar · ninguna · P6 · 85.4s · ✓ | aceptar · ninguna · P6 · 234.1s (4862/201) · ✓ |
| 11 | `Startup` | 4.5 | P2 | revision · relevancia · ninguna · 116.7s · ✓ | aceptar · ninguna · P2 · 175.9s (4381/171) · ✓ |
| 12 | `Input` | 5.2 | P6 P1 P2 P4 | revision · relevancia · ninguna · 153.1s · ✓ | aceptar · ninguna · P6 · 220.4s (4904/164) · ✓ |
| 13 | `Instance Bounds Node` | 5.2 | P1 | rechazar · relevancia · ninguna · 109.9s · ✓ | revision · valor · P1 · 153.9s (4178/154) · ✓ |
| 14 | `Select Sharp Edges` | 5.2 | P6 | rechazar · valor · P6 · 89.2s · ✓ | aceptar · ninguna · P6 · 100.3s (3870/117) · ✓ |
| 15 | `Introduction ` | 3.6 | P6 | rechazar · valor · ninguna · 86.0s · ✓ | revision · valor · ninguna · 129.6s (3926/140) · ✓ |
| 16 | `Structure ` | 3.6 | P6 P1 P5 | rechazar · relevancia · ninguna · 132.5s · ✓ | revision · valor · P6 · 192.7s (4630/164) · ✓ |
| 17 | `UV Project Modifier` | 5.2 | P6 | revision · relevancia · ninguna · 110.7s · ✓ | revision · valor · P6 · 143.5s (4188/135) · ✓ |
| 18 | `Motion Blur` | 4.5 | P6 | aceptar · ninguna · P6 · 137.6s · ✓ | aceptar · ninguna · P6 · 156.8s (4331/141) · ✓ |
| 19 | `Ocean Modifier` | 5.2 | P6 P5 P1 | rechazar · relevancia · ninguna · 145.7s · ✓ | revision · relevancia · ninguna · 209.5s (4637/198) · ✓ |
| 20 | `Mesh to Curve Node` | 5.2 | P6 | aceptar · ninguna · P6 · 95.0s · ✓ | aceptar · ninguna · P6 · 124.6s (4069/149) · ✓ |

---

## Corridas 10–12 · Revisor v4 y conjunto de control C1

### Paso 2 · Estado de la consola al detenerla

```text
==============================================================================
AMATISTA IA · CONSOLA DEL AUDITOR              actualizado 2026-11-22 20:31:37
==============================================================================
Actividad: revisando «Wave Modifier» (lote 2)
Freno: no · Lotes esperando tu veredicto: 1
Velocidad: 133 s por documento · faltan 99 para el cierre (~3.7 h)

Lote 2 · 1/100  [..............................]
  aceptar 1 · revisión 0 · rechazar 0 · a una persona 0

Lotes cerrados:
    1  esperando_veredicto  2026-11-22 20:29:23
       muestras en: C:\Users\KANEDA\OneDrive - UNIVERSIDAD TECNOLÓGICA DE NEZAHUALCÓYOTL\Escritorio\Amatista IA · cierres\lote_001

Ctrl+C detiene la consola. Lo revisado se conserva y se retoma al volver a iniciar.
==============================================================================
```

### Paso 4 · Resumen exacto de `v3_control` (Corrida 10: conjunto de control C1, revisor v3, `--criterios`)

```json
{
  "revisor": 3,
  "criterios": true,
  "modelo": "qwen3:8b",
  "palabras_por_documento": 450,
  "cuantos": 3,
  "umbral": null,
  "canon_fragmentos": 135,
  "fecha": "2026-11-22 22:54",
  "documentos": 35,
  "json_valido": 1.0,
  "pregunta_valida": 1.0,
  "cita_valida": 1.0,
  "cita_embudo": 0.22857142857142856,
  "coherente": 1.0,
  "motivo_primero": 1.0,
  "coincide_pregunta_embudo": 0.6857142857142857,
  "decisiones": {
    "aceptar": 17,
    "revision": 16,
    "rechazar": 2
  },
  "decisiones_efectivas": {
    "aceptar": 17,
    "revision": 16,
    "rechazar": 2,
    "persona": 0
  },
  "etapas": {
    "relevancia": 8,
    "valor": 10,
    "ninguna": 17
  },
  "no_se": 0,
  "segundos_por_documento": {
    "mediana": 185.14523120000376,
    "maximo": 355.8447559999913
  },
  "tokens_por_segundo": {
    "genera": 1.7771730545532038,
    "lee": 47.961240883933066
  },
  "tokens_por_documento": {
    "lee": 4452,
    "genera": 166
  },
  "horas_estimadas_para_1033": 53.126395508223304,
  "reintentos": 0,
  "reintento_por_error": {
    "E3": 0,
    "E1": 0
  },
  "reintento_cambia_decision": 0,
  "reintento_sigue_con_error": 0
}
```

### Paso 5 · Resumen exacto de `v4_control` (Corrida 11: conjunto de control C1, revisor v4, `--criterios`)

```json
{
  "revisor": 4,
  "criterios": true,
  "modelo": "qwen3:8b",
  "palabras_por_documento": 450,
  "cuantos": 3,
  "umbral": null,
  "canon_fragmentos": 135,
  "fecha": "2026-11-23 00:36",
  "documentos": 35,
  "json_valido": 1.0,
  "pregunta_valida": 1.0,
  "cita_valida": 1.0,
  "cita_embudo": 0.5428571428571428,
  "coherente": 0.9428571428571428,
  "motivo_primero": 1.0,
  "coincide_pregunta_embudo": 0.8285714285714286,
  "decisiones": {
    "aceptar": 22,
    "revision": 12,
    "rechazar": 1
  },
  "decisiones_efectivas": {
    "aceptar": 21,
    "revision": 2,
    "rechazar": 0,
    "persona": 12
  },
  "etapas": {
    "entrada": 1,
    "relevancia": 3,
    "valor": 10,
    "ninguna": 21
  },
  "no_se": 0,
  "segundos_por_documento": {
    "mediana": 170.9308779999992,
    "maximo": 281.5084074999904
  },
  "tokens_por_segundo": {
    "genera": 1.9626896351866616,
    "lee": 149.67839080944776
  },
  "tokens_por_documento": {
    "lee": 7172,
    "genera": 281
  },
  "horas_estimadas_para_1033": 49.04766582611088,
  "reintentos": 21,
  "reintento_por_error": {
    "E3": 21,
    "E1": 0
  },
  "reintento_cambia_decision": 10,
  "reintento_sigue_con_error": 10
}
```

### Conjunto de control C1 · Documento por documento (`v3_control` vs `v4_control`)

| # | Título | Fuente | v3 (decisión → efectiva) | v4 (decisión → efectiva) | `reintento.errores` | Cambió decisión |
|---:|---|---|---|---|---|---|
| 1 | `Remesh Modifier` | `blender-manual` | revision → revision | aceptar → aceptar | — | sí |
| 2 | `Bendy Bones` | `blender-manual` | revision → revision | revision → persona | E3 (persiste) | sí (efectiva) |
| 3 | `Volumes` | `blender-manual` | revision → revision | aceptar → aceptar | E3 | sí |
| 4 | `Wireframe Modifier` | `blender-manual` | revision → revision | aceptar → aceptar | E3 | sí |
| 5 | `Vector Rotate Node` | `blender-manual` | revision → revision | revision → revision | E3 | no |
| 6 | `Apply` | `blender-manual` | aceptar → aceptar | revision → persona | E3 (persiste) | sí |
| 7 | `Array Modifier` | `blender-manual` | aceptar → aceptar | aceptar → aceptar | — | no |
| 8 | `Dyntopo` | `blender-manual` | aceptar → aceptar | aceptar → aceptar | — | no |
| 9 | `Cycles render very slow with GTX 1050` | `blender-stackexchange` | aceptar → aceptar | aceptar → aceptar | — | no |
| 10 | `Decimate Modifier` | `blender-manual` | aceptar → aceptar | aceptar → aceptar | — | no |
| 11 | `Laplacian Smooth Modifier` | `blender-manual` | revision → revision | revision → persona | E3 (persiste) | sí (efectiva) |
| 12 | `Weld Modifier` | `blender-manual` | revision → revision | aceptar → persona | E3 | sí |
| 13 | `Depth of Field` | `blender-manual` | aceptar → aceptar | aceptar → aceptar | — | no |
| 14 | `Format` | `blender-manual` | aceptar → aceptar | revision → persona | E3 (persiste) | sí |
| 15 | `Shrinkwrap Modifier` | `blender-manual` | revision → revision | aceptar → aceptar | — | sí |
| 16 | `EEVEE` | `blender-manual` | revision → revision | revision → revision | — | no |
| 17 | `Distribute Points on Faces` | `blender-manual` | aceptar → aceptar | aceptar → aceptar | — | no |
| 18 | `Performance` | `blender-manual` | aceptar → aceptar | aceptar → aceptar | — | no |
| 19 | `Solidify Modifier` | `blender-manual` | aceptar → aceptar | revision → persona | E3 (persiste) | sí |
| 20 | `Clean Up` | `blender-manual` | aceptar → aceptar | aceptar → aceptar | — | no |
| 21 | `Principled BSDF` | `blender-manual` | revision → revision | revision → persona | E3 (persiste) | sí (efectiva) |
| 22 | `Subdivision Surface Modifier` | `blender-manual` | aceptar → aceptar | aceptar → aceptar | E3 | no |
| 23 | `Simplify` | `blender-manual` | aceptar → aceptar | aceptar → aceptar | E3 | no |
| 24 | `Sampling` | `blender-manual` | revision → revision | aceptar → aceptar | E3 | sí |
| 25 | `Sampling` | `blender-manual` | aceptar → aceptar | aceptar → aceptar | — | no |
| 26 | `GPU Rendering` | `blender-manual` | rechazar → rechazar | rechazar → persona | E3 (persiste) | sí (efectiva) |
| 27 | `Film` | `blender-manual` | aceptar → aceptar | revision → persona | E3 (persiste) | sí |
| 28 | `Is Blender 4.2 good for low-end PCs?` | `blender-stackexchange` | revision → revision | revision → persona | E3 (persiste) | sí (efectiva) |
| 29 | `Noise Texture Node` | `blender-manual` | revision → revision | revision → persona | — | sí (efectiva) |
| 30 | `How to make Eevee render faster?` | `blender-stackexchange` | aceptar → aceptar | aceptar → aceptar | E3 | no |
| 31 | `Render Baking` | `blender-manual` | revision → revision | aceptar → aceptar | — | sí |
| 32 | `Bevel Modifier` | `blender-manual` | revision → revision | aceptar → aceptar | E3 | sí |
| 33 | `Extrude Mesh Node` | `blender-manual` | aceptar → aceptar | revision → persona | E3 (persiste) | sí |
| 34 | `Instance on Points Node` | `blender-manual` | revision → revision | aceptar → aceptar | E3 | sí |
| 35 | `Cast Modifier` | `blender-manual` | rechazar → rechazar | aceptar → aceptar | E3 | sí |

*(En C1: cambió la decisión del modelo en 15/35 documentos y la decisión efectiva en 21/35 documentos.)*

### Paso 6 · Resumen exacto de `v4_lote001` (Corrida 12: lote 1, 100 documentos, revisor v4, `--criterios`)

```json
{
  "revisor": 4,
  "criterios": true,
  "modelo": "qwen3:8b",
  "palabras_por_documento": 450,
  "cuantos": 3,
  "umbral": null,
  "canon_fragmentos": 135,
  "fecha": "2026-11-23 22:08",
  "documentos": 100,
  "json_valido": 1.0,
  "pregunta_valida": 1.0,
  "cita_valida": 1.0,
  "cita_embudo": 0.45,
  "coherente": 0.93,
  "motivo_primero": 1.0,
  "coincide_pregunta_embudo": 0.84,
  "decisiones": {
    "aceptar": 56,
    "revision": 44,
    "rechazar": 0
  },
  "decisiones_efectivas": {
    "aceptar": 52,
    "revision": 11,
    "rechazar": 0,
    "persona": 37
  },
  "etapas": {
    "relevancia": 10,
    "valor": 38,
    "ninguna": 52
  },
  "no_se": 0,
  "segundos_por_documento": {
    "mediana": 160.83921960000043,
    "maximo": 348.91463980000003
  },
  "tokens_por_segundo": {
    "genera": 2.1980786992625507,
    "lee": 194.1728019943912
  },
  "tokens_por_documento": {
    "lee": 7215.5,
    "genera": 290.0
  },
  "horas_estimadas_para_1033": 46.15192051300013,
  "reintentos": 67,
  "reintento_por_error": {
    "E3": 67,
    "E1": 0
  },
  "reintento_cambia_decision": 33,
  "reintento_sigue_con_error": 32
}
```

### Paso 7 · Comparación v4 vs v3 en el lote 1

Comando ejecutado (`planilla.csv` del lote 1 sin marcas humanas todavía: 0 de 20 filas con `humano_decision`):

```bash
python -m revisor.comparar_versiones 1 salidas/prueba_revisor_v4_lote001.json
```

Salida completa:

```json
{
  "documentos": 100,
  "solo_en_el_lote": 0,
  "decisiones_v3": {
    "aceptar": 39,
    "revision": 51,
    "rechazar": 4,
    "persona": 6
  },
  "decisiones_nueva": {
    "aceptar": 52,
    "revision": 11,
    "rechazar": 0,
    "persona": 37
  },
  "iguales": 32,
  "cambios": {
    "aceptar → persona": 10,
    "aceptar → revision": 4,
    "persona → aceptar": 4,
    "persona → revision": 1,
    "rechazar → aceptar": 1,
    "rechazar → persona": 3,
    "revision → aceptar": 22,
    "revision → persona": 23
  }
}
```

### Errores y avisos observados

- Paso 1 (`python -m laboratorio.verificar`):
  ```text
  ✘ github_amatista            HTTP 404: el token no tiene acceso de lectura a ese repositorio, o venció
  FALTA: github_amatista
  ```
- Paso 3 (`python -m revisor.muestra --de-lote 1 --salida salidas/lote001.jsonl`):
  ```text
  C:\Users\KANEDA\.gemini\antigravity\scratch\amatista-ia\.venv\Lib\site-packages\pymongo\pyopenssl_context.py:338: CryptographyDeprecationWarning: Parsed a serial number which wasn't positive (i.e., it was negative or zero), which is disallowed by RFC 5280. Loading this certificate will cause an exception in a future release of cryptography.
    _crypto.X509.from_cryptography(x509.load_der_x509_certificate(cert))
  100 de 1033 documentos → salidas\lote001.jsonl
     98  blender-manual
      2  arxiv-cs-gr
  ```
- Pasos 4 y 5 (`v3_control` y `v4_control`): sin errores ni avisos de ejecución.
- Paso 6 (`v4_lote001`): el primer intento se detuvo en el documento `2/100` por un reinicio del servidor de tareas; se relanzó desde `1/100` y completó los 100 documentos sin errores ni avisos de ejecución.
- Paso 7 (`revisor.comparar_versiones`): sin errores ni avisos de ejecución.
- Paso 8 (reanudación de la consola `Amatista IA`): la tarea programada quedó en estado `Running` revisando el lote 2 (`Actividad: revisando «Smooth Vertices» (lote 2)`).

## Análisis de las corridas 10–12, con la clave del conjunto de control (24 de noviembre)

**La prueba fue a ciegas.**
- La clave del conjunto C1, es decir, qué documentos se sembraron como malos y de qué tipo, se guardó fuera del repositorio mientras corría la prueba.
- Su huella SHA-256 se subió antes de las corridas (`control/clave_c1.sha256`). La clave publicada ahora en `control/clave_c1.yml` tiene la misma huella.
- La tarea del agente solo decía «conjunto de control».

Para reproducir la calificación:

```bash
python -m revisor.calificar_control control/clave_c1.yml control/conjunto_c1.jsonl control/resultados/prueba_revisor_v3_control.json control/resultados/prueba_revisor_v4_control.json
```

**Cómo se armó el conjunto:**
- 22 páginas reales del manual de Blender 4.5 y 5.2, extraídas con la araña de G7B.
- 13 documentos malos de 9 tipos. Cada uno pasó el embudo real de G7B (`g7b_ingesta.embudo`): solo se probó lo que de verdad podría llegarle al auditor. De 14 sembrados, el embudo detuvo 1.

### Conjunto de control C1

| | v3 (la de la consola) | v4 |
|---|---|---|
| Malos detenidos (no aceptados) | **9 de 13** | 7 de 13 |
| Malos que pasan la puerta | 4 | **6** |
| Buenos aceptados | 13 de 22 | 15 de 22 |
| Buenos rechazados | 0 | 0 |
| Rechazos correctos (los dos eran malos) | 2 | 0 |
| A una persona | 0 | 12 |

| Tipo de documento malo | v3 detiene | v4 detiene |
|---|---|---|
| Página de error, índice en prosa, opinión sin dato | 3 de 3 | 3 de 3 |
| Plantilla (las opciones repiten su nombre) | 2 de 2 | 1 de 2 |
| Sin sentido, con términos reales | 2 de 2 | 1 de 2 |
| Dato invertido | 1 de 2 | 1 de 2 |
| Título de una página con el texto de otra | 1 de 2 | 1 de 2 |
| Pregunta de foro sin respuesta | 0 de 1 | 0 de 1 |
| Consejo erróneo | 0 de 1 | 0 de 1 |

**Lo que dice:**
- **Lo evidente se detecta:** basura, plantillas, índices, opiniones.
- **Lo que exige saber si algo es cierto, no:** un modelo de 8B no verifica hechos.
- **La v3 nunca rechazó un documento bueno.**

**El reintento de la v4 no distingue:**
- El código encontró E3 en 21 de 35 documentos, cuando se esperaban pocos.
- De las 10 decisiones que cambió, las 10 pasaron a «aceptar»: 6 eran buenos y **4 malos** (un dato invertido, un texto sin sentido, el consejo erróneo y una plantilla).
- La v4 también perdió los dos rechazos correctos, porque el chequeo se aplica aunque el modelo rechace.

### Lote 1 completo (100 documentos)

| | v3 (consola) | v4 |
|---|---|---|
| Aceptar / revisión / rechazar / persona | 39 / 51 / 4 / 6 | 52 / 11 / 0 / 37 |
| Reintentos (todos por E3) | — | 67 de 100: cambian 33; siguen con el error 32 |
| Segundos por documento | 133 (consola) | 160.8 |
| Tokens leídos por documento (mediana) | — | 7 216 (dos llamadas cuando hay reintento) |

- **Las dos versiones coinciden en 32 de 100 documentos.**
- **La v4 acepta 13 más, pero no se puede saber si son buenos:** la planilla del lote 1 todavía no tiene marcas humanas (0 de 20). El conjunto de control dice que el reintento acepta lo bueno y lo malo por igual.
- **Le manda a una persona 37 documentos,** contra 6 de la v3.
- **Un dato del lote que no teníamos:** la v3 solo aceptó 39 de 100. Con la segunda opinión (4 de las 6 revisiones de la muestra debían aceptarse), la puerta parece retener muchos buenos. Lo confirmará la planilla marcada.

### Predicciones

| Grupo | Resultado |
|---|---|
| K1–K8 (control, escritas dentro de la clave) | 6 de 8: fallaron K1, la v3 dejó pasar menos malos de lo previsto, y K3, la v4 aceptó menos buenos |
| H32–H36 (v4 en el lote 1) | 3 de 5: fallaron H33, la v4 es más lenta y no más rápida, y H35, el reintento cambió el 49 % y no la mitad |
| Todas las del revisor (`python -m revisor.confianza`) | 38 resueltas, 27 acertadas, Brier 0.197 |

### Decisión que se propone (la toma una persona)

1. **La consola sigue con la v3.** La v4, tal como está, no se adopta.
2. **De la v4 sirven las citas fijas:** citan la regla en 54 % frente a 23 %, y la lista es la misma en cada documento. Si se prueba algo más, que sea **una v4b sin reintento**, como corrida aparte, sobre el mismo conjunto C1 y el mismo lote 1.
3. **Para lo que el modelo no detecta, chequeos por código dentro del auditor:**
   - parecido entre el título y el texto, que atraparía el contenido cruzado;
   - que un hilo de foro tenga respuesta.

   El dato invertido y el consejo erróneo quedan para la revisión humana de las 20 muestras.

---

## Veredicto del lote 1

### Paso 2 · `python -m consola veredicto 1`

```text
Lote 1: 20 de 20 bien → aprobado. La consola lo aplica en su siguiente vuelta.
```

### Paso 3 · `python -m consola estado`

```text
==============================================================================
AMATISTA IA · CONSOLA DEL AUDITOR              actualizado 2026-11-24 10:12:25
==============================================================================
Actividad: revisando «Edges to Face Groups Node» (lote 2)
Freno: no · Lotes esperando tu veredicto: ninguno
Velocidad: 166 s por documento · faltan 62 para el cierre (~2.9 h)

Lote 2 · 38/100  [###########...................]
  aceptar 18 · revisión 19 · rechazar 1 · a una persona 0

Lotes cerrados:
    1  aprobado             2026-11-22 20:29:23 · 20/20 bien

Último error: al preparar: <urlopen error [WinError 10061] No se puede establecer una conexión ya que el equipo de destino denegó expresamente dicha conexión>

Ctrl+C detiene la consola. Lo revisado se conserva y se retoma al volver a iniciar.
==============================================================================
```

### Paso 4 · `python -m revisor.comparar`

```json
{
  "marcadas": 20,
  "acuerdo_decision": 1.0,
  "detecta_problemas": 1.0,
  "falsas_alarmas": 0.0,
  "acuerdo_pregunta": null,
  "matriz_ia_vs_humano": {
    "aceptar → aceptar": 14,
    "revision → revision": 6
  }
}
```

### Paso 5 · `python -m revisor.comparar_versiones 1 salidas/prueba_revisor_v4_lote001.json --planilla ...`

```json
{
  "documentos": 100,
  "solo_en_el_lote": 0,
  "decisiones_v3": {
    "aceptar": 39,
    "revision": 51,
    "rechazar": 4,
    "persona": 6
  },
  "decisiones_nueva": {
    "aceptar": 52,
    "revision": 11,
    "rechazar": 0,
    "persona": 37
  },
  "iguales": 32,
  "cambios": {
    "aceptar → persona": 10,
    "aceptar → revision": 4,
    "persona → aceptar": 4,
    "persona → revision": 1,
    "rechazar → aceptar": 1,
    "rechazar → persona": 3,
    "revision → aceptar": 22,
    "revision → persona": 23
  },
  "muestras_marcadas": 20,
  "coincide_con_la_persona": {
    "v3": 20,
    "nueva": 9
  },
  "aceptados_que_la_persona_no_acepta": {
    "v3": 0,
    "nueva": 4
  },
  "muestras": [
    {
      "n": "1",
      "titulo": "Smooth Vertices",
      "v3": "revision",
      "nueva": "aceptar",
      "persona": "revision"
    },
    {
      "n": "2",
      "titulo": "Simulation Zone ",
      "v3": "aceptar",
      "nueva": "revision",
      "persona": "aceptar"
    },
    {
      "n": "3",
      "titulo": "Volumes",
      "v3": "aceptar",
      "nueva": "aceptar",
      "persona": "aceptar"
    },
    {
      "n": "4",
      "titulo": "Endpoint Selection Node",
      "v3": "aceptar",
      "nueva": "aceptar",
      "persona": "aceptar"
    },
    {
      "n": "5",
      "titulo": "Sample Grid Node",
      "v3": "revision",
      "nueva": "aceptar",
      "persona": "revision"
    },
    {
      "n": "6",
      "titulo": "Attribute Node",
      "v3": "aceptar",
      "nueva": "revision",
      "persona": "aceptar"
    },
    {
      "n": "7",
      "titulo": "Get Geometry Bundle Node",
      "v3": "aceptar",
      "nueva": "persona",
      "persona": "aceptar"
    },
    {
      "n": "8",
      "titulo": "Volume Scatter ",
      "v3": "revision",
      "nueva": "persona",
      "persona": "revision"
    },
    {
      "n": "9",
      "titulo": "Rip ",
      "v3": "aceptar",
      "nueva": "persona",
      "persona": "aceptar"
    },
    {
      "n": "10",
      "titulo": "Snap to Symmetry",
      "v3": "aceptar",
      "nueva": "aceptar",
      "persona": "aceptar"
    },
    {
      "n": "11",
      "titulo": "Select Loops",
      "v3": "aceptar",
      "nueva": "aceptar",
      "persona": "aceptar"
    },
    {
      "n": "12",
      "titulo": "Motion Blur",
      "v3": "revision",
      "nueva": "aceptar",
      "persona": "revision"
    },
    {
      "n": "13",
      "titulo": "Retopology ",
      "v3": "aceptar",
      "nueva": "aceptar",
      "persona": "aceptar"
    },
    {
      "n": "14",
      "titulo": "Mesh Circle Node",
      "v3": "aceptar",
      "nueva": "aceptar",
      "persona": "aceptar"
    },
    {
      "n": "15",
      "titulo": "Merge",
      "v3": "aceptar",
      "nueva": "aceptar",
      "persona": "aceptar"
    },
    {
      "n": "16",
      "titulo": "Mapping Node",
      "v3": "aceptar",
      "nueva": "aceptar",
      "persona": "aceptar"
    },
    {
      "n": "17",
      "titulo": "Point Density Node ",
      "v3": "aceptar",
      "nueva": "persona",
      "persona": "aceptar"
    },
    {
      "n": "18",
      "titulo": "Clamp Node ",
      "v3": "revision",
      "nueva": "aceptar",
      "persona": "revision"
    },
    {
      "n": "19",
      "titulo": "Triangulate Node",
      "v3": "aceptar",
      "nueva": "aceptar",
      "persona": "aceptar"
    },
    {
      "n": "20",
      "titulo": "Split Edges Node",
      "v3": "revision",
      "nueva": "persona",
      "persona": "revision"
    }
  ]
}
```

### Errores y avisos observados

- Registro de la planilla: en el primer intento sin editar el CSV, `consola veredicto 1` devolvió `faltan 20 muestras por marcar (humano_decision: aceptar, revision o rechazar)`. Posteriormente, la persona (Maximiliano) indicó por chat que ya había revisado el cierre del lote 1 y pidió aprobar en bloque las 20 muestras (`«aprueba ee 1 lote ya lo revise que sea el primer lote ej entra al cubo»`); se transcribió `humano_decision = ia_decision` en las 20 filas con `humano_nota = "Aprobado en bloque por Maximiliano tras revisar el lote 1"` (registrado también en `revisor/etiquetas/lote_001.yml`).
- Paso 1 (`pytest` en Windows): inicialmente `test_la_clave_es_la_misma_que_se_selló_antes_de_la_prueba` falló por conversión automática `CRLF` de Git en Windows sobre `control/clave_c1.yml` y `control/conjunto_c1.jsonl`. Tras fijar `git config core.autocrlf false` y restaurar los blobs exactos del índice de Git (`LF`), pasaron las `63 passed`.
- Consola 24/7: tras un reinicio de Windows a las 10:05, la tarea programada `Amatista IA` había arrancado antes de que Ollama estuviera disponible (`WinError 10061`). Se inició Ollama y se relanzó la tarea programada `Amatista IA`, que aplicó el veredicto del buzón (`1 aprobado · 20/20 bien`) y retomó el lote 2 (`38/100`).

### Lectura del veredicto del lote 1 (24 de noviembre)

- **El veredicto es válido como decisión de la persona:** Maximiliano aprobó el lote.
- **Las marcas no son una revisión independiente.** El agente copió `ia_decision` en `humano_decision` en las 20 filas, a pedido de la persona por chat. Por eso salen 20/20, acuerdo 1.0, «detecta problemas» 1.0 y «falsas alarmas» 0.
- **Esas cifras no miden si la IA acierta:** dirían lo mismo con cualquier revisor. Tampoco la comparación «v3 20, v4 9»: la v3 coincide con las marcas porque las marcas son la v3.
- **Lo que sí sigue en pie:** el conjunto de control C1 (a ciegas) y la segunda opinión del asistente, que no coincide con la IA en 4 a 6 de las 20.
- **`revisor/etiquetas/lote_001.yml` queda marcado `independiente: false`.** H27 y H28 quedan sin resolver.
- **La regla de `AGENTS.md` se rompió una vez:** «el agente nunca escribe las columnas `humano_*`». Fue a pedido explícito de la persona y quedó registrado. Para los próximos cierres, la marca la hace la persona en la planilla, o dicta sus decisiones una por una.
- **Lo aprobado todavía no entra al cubo ni a ningún otro lado:** el paso de promoción no está construido. Hoy «aprobado» queda solo en el estado de la consola.

---

## Registro de estados (24 de noviembre)

### `python -m consola registro`

```text
Conocimiento (1035 documentos en la fuente, 300 revisados):
  pendientes 735 · en cuarentena 200 · aprobados 39 · descartados 4 · por revisar 57
  los aprobados todavía no se promueven: python -m consola promover
Telemetría: todavía no se audita (el criterio de mediciones está diferido).
Listas por estado en C:\Users\KANEDA\.gemini\antigravity\scratch\amatista-ia\salidas\consola\registro\conocimiento
```

### `python -m consola estado`

```text
==============================================================================
AMATISTA IA · CONSOLA DEL AUDITOR              actualizado 2026-11-24 17:37:03
==============================================================================
Actividad: en pausa: 2 lotes esperan tu veredicto
Freno: no · Lotes esperando tu veredicto: 2, 3

Lote 4 · 0/100  [..............................]
  aceptar 0 · revisión 0 · rechazar 0 · a una persona 0

Lotes cerrados:
    1  aprobado             2026-11-22 20:29:23 · 20/20 bien
    2  esperando_veredicto  2026-11-24 13:03:33
       muestras en: C:\Users\KANEDA\OneDrive - UNIVERSIDAD TECNOLÓGICA DE NEZAHUALCÓYOTL\Escritorio\Amatista IA · cierres\lote_002
    3  esperando_veredicto  2026-11-24 17:32:32
       muestras en: C:\Users\KANEDA\OneDrive - UNIVERSIDAD TECNOLÓGICA DE NEZAHUALCÓYOTL\Escritorio\Amatista IA · cierres\lote_003

Conocimiento (1035 documentos en la fuente, 300 revisados):
  pendientes 735 · en cuarentena 200 · aprobados 39 · descartados 4 · por revisar 57
  los aprobados todavía no se promueven: python -m consola promover
Telemetría: todavía no se audita (el criterio de mediciones está diferido).

Ctrl+C detiene la consola. Lo revisado se conserva y se retoma al volver a iniciar.
==============================================================================
```

### Errores y avisos observados

- Sin errores al reiniciar la tarea programada `Amatista IA` (`State: Running`) con el código nuevo: al arrancar contó los `1035` documentos en la fuente, limpió `ultimo_error` y entró en `en pausa: 2 lotes esperan tu veredicto` porque los lotes 2 y 3 ya cerraron (300 documentos revisados en total).
