# Amatista IA

La IA que revisa los datos del lago de G7B «a la manera de G7B». Primero tiene que **conocer el proyecto**: sus estándares, sus reglas y sus contratos. Este repositorio construye ese conocimiento como un RAG en Supabase, y después alojará al revisor.

**Estado (22 de noviembre de 2026):** el canon, el esquema de Supabase, el indexador y la prueba de recuperación están listos y probados aquí. Falta:
- aplicar la migración en Supabase;
- correr el indexador en la computadora del laboratorio con Ollama;
- medir la recuperación con vectores.

## Qué sabe y qué no

- **Sabe los estándares, no los datos.** El canon tiene 13 documentos de G7B y Amatista, fijados a un commit ([`canon/canon.yml`](canon/canon.yml)). No incluye telemetría, foros ni documentos de conocimiento: eso es lo que va a revisar. Juzgarlo con sus propios datos sería circular.
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
| Híbrido con `bge-m3` | — | — | **Pendiente:** se mide en el laboratorio |

Las fallas de texto que se esperan:
- una pregunta en español sobre un documento en inglés (C2);
- preguntas con sinónimos.

Son justo lo que deben arreglar los vectores. Si el híbrido no supera al texto solo, no se usa.

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
