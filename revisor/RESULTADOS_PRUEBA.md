# Resultados de la prueba rápida del revisor (20 documentos)

Medido en la computadora del laboratorio (`Intel Core i3-10100`, 8 hilos, 40 GB DDR4, Windows 11, Ollama `0.40.16`, embeddings `bge-m3@790764642607`) sobre la misma muestra de 20 documentos de `conocimiento_3d.documentos` (todos de la fuente `blender-manual`). Ningún texto crudo del lago ni archivo de `salidas/` se incluye aquí.

## Comparativa de corridas

| Métrica | `codellama:latest` (`8fdf8f752f6e`, 3.8 GB) | `qwen3:8b` |
|---|---:|---:|
| `documentos` | 20 | *(en curso)* |
| `json_valido` | **1.00** (20/20) | — |
| `pregunta_valida` | **1.00** (20/20) | — |
| `cita_valida` | **0.05** (1/20) | — |
| `datos_fieles` | **0.205** (15/73) | — |
| `coincide_pregunta_embudo` | **0.75** (15/20) | — |
| `decisiones` (`aceptar` / `revision` / `rechazar`) | 14 / 6 / 0 | — |
| `no_se` | 2 | — |
| `segundos_por_documento` (mediana / máx) | 149.1 s / 248.7 s | — |
| `tokens_por_segundo` (genera / lee) | 2.70 tok/s / 34.74 tok/s | — |
| `horas_estimadas_para_1033` | 42.77 h | — |

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

### Documentos enviados a `revision` (6 de 20; 0 `rechazar`)

| # | Título | URL | `ia_etapa` | `ia_pregunta` | `ia_cita` | Motivo propuesto por el modelo |
|---:|---|---|---|---|---|---|
| 1 | `Limitations` | `https://docs.blender.org/manual/en/5.2/render/eevee/limitations/limitations.html` | `ninguna` | `ninguna` | `6 · 4. Limitaciones` | El texto no cumple con las etapas del embudo, ya que no menciona la fuente de la información ni proporciona evidencia concreta para respaldar las afirmaciones. |
| 7 | `Select All by Trait` | `https://docs.blender.org/manual/en/4.5/modeling/meshes/selecting/all_by_trait.html` | `relevancia` | `ninguna` | `plata/revision/1 · 4. El embudo` | El documento no cumple con la relevancia mínima establecida en el canon, ya que no menciona ninguna pregunta del plan. |
| 8 | `Deleting & Dissolving` | `https://docs.blender.org/manual/en/5.2/modeling/meshes/editing/mesh/delete.html` | `ninguna` | `P6` | `123456789 · 4. El embudo` | El documento no cumple con las reglas del embudo |
| 10 | `World Settings` | `https://docs.blender.org/manual/en/4.5/render/cycles/world_settings.html` | `ninguna` | `ninguna` | `blender-manual · render/cycles/world_settings` | El texto no cumple con las reglas del embudo, no menciona las preguntas del plan y no proporciona suficiente información para tomar una decisión confiable. |
| 16 | `Structure ` | `https://docs.blender.org/manual/en/3.6/modeling/meshes/structure.html` | `ninguna` | `ninguna` | `g7b/estandar-telemetria/1 · 4. El embudo` | El texto no cumple con las reglas del embudo |
| 17 | `UV Project Modifier` | `https://docs.blender.org/manual/en/5.2/modeling/modifiers/modify/uv_project.html` | `ninguna` | `ninguna` | `blender-manual · 5.2` | El texto no cumple con las reglas del embudo |

### Hallazgos sobre `cita_valida` (0.05) y `datos_fieles` (0.205) en `codellama:latest`

1. **Citas (`cita_valida = 0.05`, 1/20):**
   - Solo en `Ocean Modifier` citó un `documento_id` exacto del canon mostrado (`g7b/vision · 3`).
   - En las demás 19 respuestas puso la fuente/ruta del propio documento revisado (`blender-manual · ...`), le agregó `/1` al id del canon (`g7b/estandar-telemetria/1`), citó un contrato (`g7b.perfil/1`) o escribió números (`6`, `123456789`).
2. **Fidelidad de datos (`datos_fieles = 0.205`, 15/73):**
   - En los 6 documentos en `revision` y en `Is Edge Manifold Node` no inventó datos (0 inventados).
   - En los otros 13 documentos contaminó el campo `datos` con ejemplos de hardware y unidades que aparecían en los **fragmentos del canon** dentro del mismo prompt (`UHD 620`, `RTX 3060`, `NVIDIA GeForce RTX 3060 Laptop GPU`, `Ryzen`, `Ryzen 5 3600`, `Blender 3.0.1`, `2.80`, `8 GB`, `12 GB`, `N0`, `N4`, `fps`, `ms`, `GB`, `%`, `samples/min`), además de extraer la versión de Blender desde la URL (`5.2`, `4.5`, `3.6`), que no aparece en el cuerpo `texto`.
