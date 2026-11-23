# Amatista IA

**Lugar en la base del proyecto:** Amatista IA es el **auditor**. Decide qué datos de G7B son buenos antes de que entren al cubo o a MongoDB; Geoda solo lee lo aprobado. Piezas, flujo y prioridades: [base oficial](https://github.com/Maximiliano-cabello-mata/amatista-recuperada-20261106/blob/recuperacion/BASE.md).

La IA que revisa los datos del lago de G7B «a la manera de G7B». Conoce el proyecto por un canon de estándares en Supabase (RAG), decide cada documento con un revisor local (`qwen3:8b` en Ollama) y trabaja 24/7 desde una consola con cierres de 20 muestras para una persona. **Cómo se construyó, versión por versión: [`docs/HISTORIA.md`](docs/HISTORIA.md).**

**Estado (22 de noviembre de 2026):**

| Pieza | Estado |
|---|---|
| Canon | **v5**: 17 documentos, 135 fragmentos. En Supabase está indexada la v3; la v5 se indexa al arrancar la consola. Recall@3 híbrido de 0.96 medido con la v3 |
| Revisor | **v3 con criterios** (C1–C7, E1–E6): primero el motivo, cita de lista cerrada, datos por código, coherencia revisada. Su criterio todavía no está validado: no hay etiquetas humanas |
| Revisor v4 | Implementada (`--version 4`): citas fijas y reintento ante E3 o E1. Se mide con [`TAREA_V4.md`](TAREA_V4.md) |
| Consola 24/7 | En marcha en el laboratorio. Lote 1 cerrado el 23 de noviembre, esperando el veredicto de la persona ([segunda opinión](revisor/SEGUNDA_OPINION_LOTE_001.md)) |
| Pesos de confianza | En uso: 25 predicciones resueltas, Brier 0.197 |
| Segunda revisión de Site 4.1 | Lista, sin correr |

## Qué sabe y qué no

- **Sabe los estándares, no los datos.** El canon tiene 17 documentos de G7B, Amatista y este repositorio, fijados a un commit ([`canon/canon.yml`](canon/canon.yml)). No incluye telemetría, foros ni documentos de conocimiento: eso es lo que va a revisar. Juzgarlo con sus propios datos sería circular.
- **No copia documentos.** El indexador los lee del repositorio de origen en el commit fijado. Hay una sola fuente de verdad.
- **Las consultas exactas van por código, no por RAG:** la tabla de hardware, la taxonomía de preguntas y el catálogo de fuentes. Es más rápido y no tiene errores de recuperación.
- [`canon/INVENTARIO.md`](canon/INVENTARIO.md) dice qué entra, qué no y qué conflictos hay que resolver (C1–C5).

## Lo que la IA puede y no puede decidir

| Puede | No puede |
|---|---|
| Proponer un motivo de revisión con la regla que lo respalda (cita a documento y sección) | Aceptar un registro en el lago: eso sigue siendo revisión humana |
| Clasificar contra listas cerradas (taxonomía, niveles N0–N4) | Inventar categorías, motivos o niveles fuera de esas listas |
| Proponer un nombre de hardware que la tabla oficial no reconoce | Cambiar la tabla oficial |
| Decir «no sé» si el canon no cubre el caso | Usar datos de estudiantes fuera de la computadora local ([decisión de IA](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/blob/main/docs/investigacion/2026-11-17_decision_ia.md)) |

## Estructura

```
canon/canon.yml              qué documentos, de qué repositorio, en qué commit y qué secciones
canon/INVENTARIO.md          lo que entra, lo que no y los conflictos por resolver
supabase/migrations/         tablas, índice HNSW, búsqueda híbrida buscar_canon() y seguridad (RLS)
indexador/indexar.py         lee el canon, fragmenta, calcula vectores con Ollama y sube a Supabase
evaluacion/preguntas.yml     46 preguntas, cada una con su documento esperado
evaluacion/evaluar.py        recall@1, recall@3 y MRR, contra Supabase o sin red (BM25)
laboratorio/verificar.py     comprueba Ollama, bge-m3 y Supabase sin mostrar claves
revisor/                     prueba del revisor: muestra de MongoDB, revisión local con un 8B, comparación con una persona
consola/                     consola del auditor 24/7: lotes de 100, cierre con 20 muestras al escritorio, veredicto y freno
control/                     conjunto de control C1: documentos públicos para comparar versiones del revisor
docs/HISTORIA.md             cómo se construyó: canon v1–v5, revisor v1–v3, herramientas y decisiones
TAREA_CONSOLA.md             la tarea vigente para el agente del laboratorio
TAREA_PRUEBA_REVISOR.md      la tarea para el agente del laboratorio
TAREA_SEGUNDA_REVISION.md    segunda opinión, a ciegas, sobre los 70 bloques de la auditoría de Site 4.1
canon/criterios/             criterios de revisión que aprendimos probando (canon v3)
revisor/confianza.py         pesos de confianza: de lo teórico a lo observado, y orden de trabajo para la persona
LABORATORIO.md, AGENTS.md    guía de instalación y reglas para el agente de la computadora del laboratorio
pruebas/                     pruebas del indexador, de la evaluación y de la migración (Postgres local)
```

## Cómo funciona la búsqueda

`buscar_canon(consulta, consulta_embedding, cuantos, …)` combina dos listas por **fusión de rangos recíprocos (RRF)**: solo cuenta el orden en cada lista, así que no hay que calibrar escalas.

- **Texto:** configuración `simple`, sin raíces, porque el canon mezcla español e inglés y tiene identificadores exactos (`g7b.hardware/1`). La consulta es un **OR** de las palabras de 4 letras o más y de los identificadores. Un AND de todas las palabras casi nunca encontraba nada con una pregunta normal.
- **Significado:** `bge-m3` (multilingüe, 1024 dimensiones), con distancia coseno sobre un índice HNSW.

## Resultados de la prueba de recuperación

46 preguntas escritas antes de medir. Cada documento del canon tiene al menos una. Umbral: recall@3 ≥ 0.85.

| Búsqueda | recall@1 | recall@3 | Dónde |
|---|---:|---:|---|
| Texto con AND (diseño inicial) | 0.17 | 0.17 | Postgres local, fragmentos reales |
| **Texto con OR, función real de la migración** | **0.70** | **0.89** | Postgres local, fragmentos reales |
| BM25 de referencia (sin red) | 0.72 | 0.93 | `evaluar.py --lexico` |
| **Híbrido con `bge-m3@790764642607`** | **0.83** | **0.96** | Supabase, medido en el laboratorio el 22 de noviembre (MRR 0.89) |
| Solo texto, la misma función en Supabase | 0.70 | 0.89 | Supabase (MRR 0.80); igual que en Postgres local |

El híbrido supera al texto solo: 6 preguntas más con el documento correcto en primer lugar y 3 más entre los tres primeros. Es la búsqueda que se usa.

**Las dos fallas del híbrido no son errores de búsqueda: son problemas del canon.** No se ajustaron las preguntas.

- **p15, agregar una fuente de telemetría.**
  - Esperado: `g7b/estandar-telemetria`, §6, en inglés. No aparece en los 10 primeros.
  - Salen antes `g7b/ingesta` y `g7b/geodar-radar`, en español: los tres documentos explican cómo agregar una fuente.
  - Solo el estándar dice que las mediciones de fuera de G7B entran a `revision` y que el hardware se normaliza con `g7b_telemetria.hardware`. Un revisor que citara los otros dos se perdería esas reglas.
  - Causas: el idioma (C2) y la duplicación.
- **p20, si se pueden sumar FPS con muestras por minuto.**
  - Esperado: `g7b/cubo`. Sale quinto.
  - La regla es una sola frase dentro de un fragmento del cubo.
  - `g7b/fichas-tecnicas` gana con fragmentos que hablan de fps y muestras. Tiene 26 de los 108 fragmentos, y su §5.3 todavía describe el cubo como pendiente y con otro diseño (C3).

Mientras se resuelven, el revisor pide **5 fragmentos** (`cuantos = 5`) en lugar de 3: con eso p20 entra y p15 sigue fuera.

## Resultados de la prueba rápida del revisor (20 documentos)

Detalle completo en [`revisor/RESULTADOS_PRUEBA.md`](revisor/RESULTADOS_PRUEBA.md).

| Modelo | `json_valido` | `pregunta_valida` | `cita_valida` | `datos_fieles` / `coherente` | `coincide_pregunta_embudo` | Decisiones (`aceptar`/`revision`/`rechazar`) | Mediana s/doc | Genera / Lee (tok/s) | Horas est. (1,033 docs) |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|
| `codellama:latest` (v1, `8fdf8f752f6e`) | 1.00 | 1.00 | 0.05 | datos 0.21 | 0.75 | 14 / 6 / 0 | 149.1 s | 2.7 / 34.7 | 42.8 h |
| `qwen3:8b` (v1, `500a1f067a9f`) | 1.00 | 1.00 | 0.15 | datos 0.00* | 0.55 | 9 / 11 / 0 | 154.5 s | 2.3 / 41.6 | 44.3 h |
| `qwen3:8b` (v2, 108 frags) | 1.00 | 1.00 | **1.00** | coherente 0.55 | 0.75 | 6 / 14 / 0 | 124.5 s | 2.4 / 37.9 | 35.7 h |
| `qwen3:8b` (v2 `canon3`, 119 frags, sin `--criterios`) | 1.00 | 1.00 | **1.00** | coherente 0.50 | 0.80 | 6 / 13 / 1 | **106.1 s** | 2.4 / 46.2 | **30.4 h** |
| `qwen3:8b` (v2 `criterios`, 119 frags, con `--criterios`) | 1.00 | 1.00 | **1.00** | coherente 0.70 | **0.90** | 6 / 14 / 0 | 134.7 s | 2.0 / 46.4 | 38.6 h |
| `qwen3:8b` (v3, 119 frags, razona antes de decidir) | 1.00 | 1.00 | **1.00** | **coherente 0.90** | 0.25 | 1 / 11 / 8 *(efectivas: 1 / 9 / 8 + 2 persona)* | 116.2 s | 2.7 / 42.0 | 33.3 h |
| `qwen3:8b` (v3 `--cuantos 1`, 119 frags) | 1.00 | 1.00 | **1.00** | coherente 0.85 | 0.15 | 3 / 6 / 11 *(efectivas: 3 / 3 / 11 + 3 persona)* | **75.8 s** | 3.1 / 62.4 | **21.7 h** |
| `qwen3:8b` (v3 `canon4`, 126 frags, sin `--criterios`) | 1.00 | 1.00 | **1.00** | **coherente 0.95** | 0.30 | 3 / 9 / 8 *(efectivas: 3 / 8 / 8 + 1 persona)* | 113.7 s | 2.6 / 44.9 | 32.6 h |
| `qwen3:8b` (v3 `criterios_v3`, 126 frags, con `--criterios` E1–E6) | 1.00 | 1.00 | **1.00** | **coherente 0.90** | **0.80** | **9 / 11 / 0** *(efectivas: 9 / 9 / 0 + 2 persona)* | 155.3 s | 2.0 / 51.7 | 44.6 h |

*\*En `qwen3:8b`, 17 de los 19 datos extraídos son la versión real de Blender (`5.2`, `4.5`, `3.6`) leída de `url` (que `validar` no incluye en `titulo + texto`; si se incluye `url`, la fidelidad es 17/19 = 0.895, con solo 2 datos contaminados del canon frente a 45 en `codellama:latest`).*

## En la computadora del laboratorio

**La guía completa, paso a paso, está en [`LABORATORIO.md`](LABORATORIO.md).** Está pensada para que la siga un agente de IA o una persona, con [`AGENTS.md`](AGENTS.md) como reglas. Lo de abajo es el resumen.

Requisitos: Python 3.11+, `pip install pyyaml` y [Ollama](https://ollama.com/download).

1. Instala el modelo de embeddings (unos 1.2 GB):

   ```bash
   ollama pull bge-m3
   ```

2. Clona este repositorio y, para trabajar sin red hacia GitHub, también los dos de origen.

3. Copia `.env.ejemplo` como `.env` y llena los valores. Los scripts lo leen solos y `.gitignore` lo excluye:
   - `SUPABASE_URL=https://<proyecto>.supabase.co`;
   - `SUPABASE_SECRET_KEY`: la clave secreta, **solo para indexar**;
   - `SUPABASE_PUBLISHABLE_KEY`: la publicable, para la prueba, que solo lee.

4. Verifica Ollama, el modelo y Supabase. No muestra claves:

   ```bash
   python -m laboratorio.verificar
   ```

5. Prueba sin subir nada:

   ```bash
   python -m indexador.indexar canon/canon.yml --simulacro
   ```

6. Indexa. Es incremental: solo recalcula los documentos cuyo hash cambió.

   ```bash
   python -m indexador.indexar canon/canon.yml
   ```

7. Mide la recuperación con vectores:

   ```bash
   python -m evaluacion.evaluar evaluacion/preguntas.yml
   ```

Con `--local g7b=RUTA,amatista=RUTA` el indexador lee de clones locales (`git show <commit>:<ruta>`) en vez de GitHub.

## Claves y seguridad

- **La clave secreta nunca va al repositorio ni a un chat.** Solo vive en la computadora del laboratorio y, si se automatiza, en un secreto de GitHub.
- La publicable solo lee: RLS permite `select` a `anon` y no tiene políticas de escritura.
- Ninguna clave está escrita en este repositorio.

## Pruebas

```bash
python -m pytest -q pruebas
```

```bash
bash pruebas/probar_migracion.sh
```

El segundo comando necesita PostgreSQL 16+ con pgvector. Crea y borra una base local; no toca Supabase.
