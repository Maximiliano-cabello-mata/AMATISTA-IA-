# Inventario del canon (22 de noviembre de 2026)

Qué documentos del proyecto aprende la IA, cuáles no y qué hay que resolver antes de indexar. El manifiesto que usa el indexador es [`canon.yml`](canon.yml).

**Commits fijados:**
- G7B: `main` en `81104a1`.
- Amatista: `recuperacion` en `b689c48`.

## 1. Lo que entra (16 documentos, versión 4)

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
| G7B · `algoritmos/documentacion/README.md` (solo «Objetivo de utilidad del 80 %») | regla | Qué es un bloque útil de documentación y la regla de Wilson para habilitar una fuente (**v2**) |
| G7B · `algoritmos/documentacion/site-4.md` (solo la rúbrica y los cambios del primer piloto) | regla | La rúbrica de la araña Site 4.1 y las fallas ya observadas, en inglés (**v2**) |
| Amatista IA · `canon/criterios/criterios_revision.md` (sin «Por decidir») | regla | Los 7 criterios que aprendimos probando (**v3**) y los 6 errores conocidos del revisor, con lo que tiene que hacer en su lugar (**v4**). Si chocan con un estándar de G7B, manda el estándar |
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
| Operación 24/7, Azure, arañas por dentro (salvo la rúbrica de utilidad) | Infraestructura, no estándares de datos |
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

## 4. Versión 2 (22 de noviembre)

**Qué se agregó.** La rúbrica de utilidad de las arañas de documentación, para que la IA juzgue los bloques con el mismo criterio que la auditoría de Site. Los resultados del piloto quedan fuera: son un registro de un momento.

**Qué cambia en las cifras:**
- 15 documentos y 111 fragmentos; los 108 anteriores no cambian.
- 3 preguntas nuevas, escritas antes de medir, para un total de 49.
- Solo con texto (función real, Postgres local): recall@3 de 0.898 (44/49). Las 3 nuevas salen entre los 3 primeros.
- La búsqueda híbrida se mide en el laboratorio después de volver a indexar.

## 5. Versión 3 (22 de noviembre)

**Qué se agregó.** `ia/criterios`, con lo que aprendimos de la prueba del revisor y de la auditoría de Site. Lo «por decidir» (P6 en páginas del manual y páginas introductorias) queda fuera hasta que una persona lo decida.

**Qué cambia en las cifras:**
- 16 documentos y 119 fragmentos.
- 2 preguntas nuevas, escritas antes de medir, para un total de 51.
- Solo con texto (función real): recall@3 de 0.902 (46/51). Las 2 nuevas salen entre los 3 primeros, y los criterios no le quitan el primer lugar a ninguna otra pregunta.
- En BM25, la referencia sin red, la p17 (cubo) baja al cuarto lugar por los criterios. En la función real, no.

## 6. Versión 4 (22 de noviembre)

**Qué se agregó.** `ia/criterios` incluye ahora los **errores conocidos del revisor** (E1–E6), medidos en las corridas v1 y v2: decidir antes de razonar, usar «relevancia» por defecto, leer «valor» como si exigiera medidas, declarar confianza alta en contradicciones, citar el propio documento y copiar ejemplos como datos.

**Qué cambia en las cifras:**
- 16 documentos y 126 fragmentos (`ia/criterios`: 15).
- Solo con texto (función real): sigue en 46 de 51 (0.902), y los errores conocidos no le quitan el primer lugar a ninguna otra pregunta.

## 7. Siguiente paso

1. Resolver C1, C3 y C5. Son decisiones del proyecto, no de la IA.
2. Aplicar la migración de Supabase (`supabase/migrations/`).
3. Correr el indexador en la computadora del laboratorio: Ollama con `bge-m3`.
4. ~~Prueba de recuperación con vectores~~ **Hecha el 22 de noviembre:** recall@3 de 0.96 con el híbrido, y de 0.89 solo con texto.

**Evidencia nueva para C2 y C3** (de las dos preguntas que fallan):
- **C2:** una pregunta en español sobre cómo agregar una fuente de telemetría no encuentra `ESTANDAR_TELEMETRIA.md` §6, que está en inglés. Encuentra `INGESTA.md` y `GEODAR_RADAR.md`, que explican lo mismo de forma más general y sin la regla de que lo externo entra a `revision`. Propuesta:
  - que una sola guía sea la oficial para agregar fuentes de telemetría;
  - que las otras dos la enlacen en vez de repetir los pasos.
- **C3:** `FICHAS_TECNICAS.md` §5.3 describe un cubo distinto del real (pendiente, `GROUP BY CUBE`, rebanadas en MongoDB) y le gana a `CUBO.md` en una pregunta sobre las vistas. Propuesta:
  - corregir §5.3 para que solo defina el concepto y enlace a `CUBO.md`;
  - o excluir esa sección del canon.
