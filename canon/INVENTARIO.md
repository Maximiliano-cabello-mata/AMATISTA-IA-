# Inventario del canon (22 de noviembre de 2026)

Qué documentos del proyecto aprende la IA, cuáles no y qué hay que resolver antes de indexar. El manifiesto que usa el indexador es [`canon.yml`](canon.yml).

**Commits fijados:**
- G7B: `main` en `81104a1`.
- Amatista: `recuperacion` en `b689c48`.

## 1. Lo que entra (13 documentos)

| Documento | Tipo | Para qué le sirve a la IA |
|---|---|---|
| G7B · `docs/VISION.md` | visión | Qué es G7B y para qué existe |
| G7B · `docs/FICHAS_TECNICAS.md` | glosario | Una sola definición por concepto (lago, embudo, cubo, N0–N4…) |
| G7B · `docs/ESTANDAR_TELEMETRIA.md` | estándar | `g7b.hardware/1` y cómo se representa una medición |
| G7B · `docs/CUBO.md` (sin las secciones de operación) | contrato | Entradas aceptado y revisión, vistas, calidad |
| G7B · `docs/TELEMETRIA.md` (sin automatización ni activación) | regla | Fuente pública frente a sonda propia; por qué lo público va a revisión |
| G7B · `docs/CONSENTIMIENTO_TELEMETRIA.md` | política | Qué se puede medir y guardar de una persona |
| G7B · `docs/INGESTA.md` (sin disparadores) | regla | **El embudo de cinco etapas:** la regla principal para revisar documentos |
| G7B · `docs/GEODAR_RADAR.md` | regla | Catálogo de fuentes y ruteo |
| G7B · `docs/GEODA.md` (sin «Lo que sigue») | contrato | Cómo usa Geoda lo revisado |
| G7B · `docs/GEODA_KERNEL.md` | contrato | Escalera de evidencia del núcleo |
| G7B · `docs/investigacion/2026-11-17_decision_ia.md` | política | La decisión vigente sobre IA |
| Amatista · `PROYECTO.md` (solo §1) | visión | Qué es Amatista y su relación con G7B |
| Amatista · `docs/arquitectura/2026-11-02_conexion_g7b_y_geoda.md` | contrato | La frontera de privacidad: solo Amatista guarda datos personales |

**Consultas exactas** (las usa el revisor por código, no por RAG):
- `fuentes/hardware.yml`: la tabla oficial de hardware;
- `fuentes/taxonomia.yml`: las preguntas del plan;
- `fuentes/catalogo.yml`: las fuentes, sus licencias y su destino.

## 2. Lo que no entra

| Qué | Por qué |
|---|---|
| Datos del lago: telemetría, foros, documentos de conocimiento | Son lo que la IA va a revisar |
| `PLAN.md`, `PLAN_MAESTRO.md` | Planeación del 3 de noviembre, superada |
| Operación 24/7, Azure, arañas por dentro | Infraestructura, no estándares de datos |
| Ofertas, estadía, Hack4Edu, historia | Contexto comercial, académico o histórico |
| Auditorías, bitácoras, reportes, investigación (salvo la decisión de IA) | Registros de un momento que pueden contradecir el presente |
| El resto de Amatista (plataforma, motor, rediseño) | No cambia cómo se juzga un dato de G7B |

## 3. Conflictos que hay que resolver antes de indexar

| # | Conflicto | Qué propongo |
|---|---|---|
| **C1** | **Hay 5 PR abiertos en G7B que cambian estándares:** el cubo /3 con la vigía (#26), otro cubo v2 (#27), las responsabilidades de Geoda y la IA (#28), una araña documental (#29) y el recolector de telemetría de Amatista (#35). En `main`, el código del cubo sigue en `g7b.cubo/1` | El canon toma solo `main`. **Decidir #26 frente a #27** y fusionar o cerrar #28: cambia directamente qué debe saber la IA |
| **C2** | **Idioma mezclado:** `ESTANDAR_TELEMETRIA.md` se tradujo al inglés el 21 de noviembre (#36); el resto está en español | Embeddings multilingües (bge-m3) y búsqueda de texto sin raíces de idioma (`simple`), que funciona igual en los dos |
| **C3** | **`FICHAS_TECNICAS.md` (1 de noviembre) se declara autoridad** sobre todos los documentos, pero es anterior al estándar de telemetría (17–21 de noviembre) y al cubo (17 de noviembre) | Revisar a mano sus definiciones contra esos dos. Mientras tanto, regla para la IA: **si chocan, manda el documento más reciente** |
| **C4** | `TELEMETRIA.md` (3 de noviembre) tiene «Criterios pendientes antes del cubo», pero el cubo ya existe | Entra, marcado como histórico en esa sección; actualizar el documento en G7B |
| **C5** | `CONSENTIMIENTO_TELEMETRIA.md` está marcado como **BORRADOR** | Entra con advertencia: la IA lo trata como propuesta, no como regla aprobada. Aprobarlo (o corregirlo) es decisión del proyecto |

## 4. Siguiente paso

1. Resolver C1, C3 y C5. Son decisiones del proyecto, no de la IA.
2. Aplicar la migración de Supabase (`supabase/migrations/`).
3. Correr el indexador en la computadora del laboratorio: Ollama con `bge-m3`.
4. Prueba de recuperación con vectores: las 46 preguntas de [`evaluacion/preguntas.yml`](../evaluacion/preguntas.yml). Solo con texto ya da recall@3 de 0.89.
