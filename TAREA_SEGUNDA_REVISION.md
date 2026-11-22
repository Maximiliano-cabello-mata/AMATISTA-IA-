# Tarea: segunda revisión de la auditoría de Site 4.1

**Para el agente de la computadora del laboratorio.** Antes de empezar, lee [`AGENTS.md`](AGENTS.md). Ya deben estar hechos [`LABORATORIO.md`](LABORATORIO.md) y el paso 2 de [`TAREA_PRUEBA_REVISOR.md`](TAREA_PRUEBA_REVISOR.md), que descarga el modelo revisor.

## Por qué

La araña de documentación **Site 4.1** de G7B se auditó con 70 bloques del capítulo de composición del manual de Blender 4.5. **Todas las etiquetas las puso Codex, sin una segunda revisión humana.**
- En las 24 muestras de páginas que la araña no había visto, Codex marcó 20 como útiles.
- Con eso, el límite inferior de Wilson da 67.6 %, debajo del 80 % necesario para publicar sola esa fuente.

Esta tarea da una **segunda opinión independiente**: un modelo local juzga los mismos 70 bloques con la rúbrica del canon, **sin ver lo que dijo Codex**. Después, una persona decide solo los desacuerdos.

**Qué toca y qué no:**
- No se cambia nada en G7B, en el lago ni en Azure.
- El texto de los bloques se reconstruye del manual público de Blender.
- Los resultados quedan en `salidas/`.

## Paso 1 · Actualizar y volver a indexar el canon (versión 2)

El canon ahora incluye la rúbrica de utilidad de las arañas:
- `g7b/seleccion-documental`;
- `g7b/site`.

```bash
git pull
```

```bash
python -m indexador.indexar canon/canon.yml
```

Se espera `Listo: 2 documentos actualizados (3 fragmentos) … 13 sin cambios`. Si dice otra cosa, detente y repórtalo.

Mide de nuevo la recuperación. Ahora son 49 preguntas, con 3 nuevas de la rúbrica:

```bash
python -m evaluacion.evaluar evaluacion/preguntas.yml
```

Antes, con 46 preguntas, el híbrido daba recall@3 de 0.96. Solo con texto, el canon v2 da 0.898. Reporta el número tal cual, aunque baje.

## Paso 2 · Reconstruir los 70 bloques

Necesitas un clon de G7B que tenga el commit fijado del canon (`81104a1`) y Scrapy, el mismo extractor que usa la araña.

```bash
git clone https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl.git ../amatista-g7b-etl
```

```bash
python -m pip install scrapy
```

```bash
python -m revisor.segunda_revision reconstruir --g7b ../amatista-g7b-etl
```

Qué hace:
1. Crea una copia aparte de G7B en el commit fijado, dentro de `salidas/`. No cambia la rama de tu clon.
2. Descarga las 46 páginas del manual.
3. Extrae los bloques con el código de G7B.
4. Solo acepta un bloque si su `id` es **idéntico** al de la auditoría: así se garantiza que el texto es exactamente el que juzgó Codex.

Se espera:

```
Reconstruidos con id idéntico: 70 de 70
Muestras inéditas: 24 (útiles según Codex: 20; publicado: 20 de 24)
```

En la computadora de desarrollo dio exactamente esto. Si da menos de 70, el manual cambió desde la auditoría: **repórtalo y no sigas**.

## Paso 3 · La segunda revisión

```bash
python -m revisor.segunda_revision revisar --modelo qwen3:8b
```

Usa el mismo modelo de la prueba rápida y anota cuál fue. Cada bloque imprime una línea:
- el tiempo;
- lo que dijo la IA;
- lo que dijo Codex;
- `≠` si no coinciden.

Las instrucciones fijas miden unas 770 palabras y se reutilizan; cada bloque agrega unas 86. Se estima **20–45 minutos** para los 70, pero no está medido.

No cambies la rúbrica, las instrucciones ni el modelo a mitad de la corrida.

Al terminar quedan dos archivos:
- `salidas/segunda_revision.json`: todo, con el resumen al principio;
- `salidas/segunda_revision.csv`: una fila por bloque. Los desacuerdos llevan `SÍ` en la columna `desacuerdo`.

## Paso 4 · Reportar

Entrega el bloque `resumen` tal cual y explícalo:

| Campo | Qué significa |
|---|---|
| `acuerdo` | Fracción de bloques en que la IA y Codex dijeron lo mismo |
| `kappa` | El acuerdo descontando el que se daría por azar. Sobre 0.6 es bueno. Con tan pocos bloques no útiles (6 de 70), puede salir bajo aunque el acuerdo sea alto |
| `matriz_codex_vs_ia` | Cuántos útil→útil, útil→no, no→útil y no→no |
| `ineditas` | En las 24 muestras que cuentan para habilitar: útiles según Codex, útiles según la IA, y el Wilson de cada uno |
| `desacuerdos` | Cuántos bloques tiene que decidir una persona |
| `segundos_por_bloque` | Velocidad real |

## Paso 5 · Una persona decide los desacuerdos

1. La persona abre `salidas/segunda_revision.csv` y filtra la columna `desacuerdo = SÍ`.
2. Por cada fila, lee el texto o abre la URL y escribe en `humano_util` **sí** o **no**. Puede anotar el porqué en `humano_nota`.
3. Después:

   ```bash
   python -m revisor.segunda_revision adjudicar salidas/segunda_revision.csv
   ```

Resultado:
- La etiqueta final es la de la persona en los desacuerdos, y la compartida donde la IA y Codex coinciden.
- Se recalculan el censo y el **límite inferior de Wilson de las 24 muestras inéditas**.
- `habilitada` solo es `true` si ese límite llega a 0.80 y no queda ninguna muestra inédita pendiente.

**Qué hace falta para habilitar la fuente.** Con 24 muestras, el límite llega a 0.80 solo si al menos 23 son útiles:

| Útiles de 24 | Límite inferior de Wilson | ¿Habilita? |
|---:|---:|---|
| 24 | 0.899 | Sí |
| 23 | 0.833 | Sí |
| 22 | 0.777 | No |
| 20 (lo publicado) | 0.676 | No |

Es decir, la persona tendría que convertir en útiles al menos 3 de los 4 que Codex marcó como no útiles. Lo más probable es que la fuente siga sin habilitarse. Lo que cambia es que cada etiqueta tendrá dos revisiones y una persona detrás. Para tener un margen real hay que medir con más capítulos o versiones del manual. Esa decisión es del proyecto.
