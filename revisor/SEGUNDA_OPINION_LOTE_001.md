# Segunda opinión del lote 1 (23 de noviembre de 2026)

Es la opinión del asistente sobre las 20 muestras del primer cierre de la consola. La persona se las pasó, según la excepción aprobada en `AGENTS.md`: todas vienen del manual público de Blender.

**Esto no es una etiqueta humana.** La consola no lo lee y no cuenta para el veredicto. El veredicto sale solo de la columna `humano_decision` de `planilla.csv`, que marca una persona. Si todavía no marcaste la planilla, márcala antes de leer la tabla, para que esta opinión no te influya.

## La muestra

| | |
|---|---|
| Revisor | v3 con criterios y errores conocidos (C1–C7, E1–E6), `qwen3:8b`, canon v5 |
| Muestra | 20 de 100, estratificada: 14 aceptados y 6 no aceptados (los 6 son «revisión»; no hubo rechazos) |
| Fuente | Las 20 son del manual de Blender: 11 de la 5.2, 3 de la 4.5 y 6 de la 3.6 |

## Documento por documento

«Clara» quiere decir que la página no deja duda; «discutible» quiere decir que depende de una regla todavía por decidir.

| # | Página | IA | Asistente | Seguridad | Por qué |
|---:|---|---|---|---|---|
| 1 | Smooth Vertices | revisión | aceptar | clara | El motivo dice que la página tiene valor y la decisión es «revisión»: la contradicción de E1 y E4, con confianza alta |
| 2 | Simulation Zone (3.6) | aceptar | aceptar | clara | Explica evaluación, subpasos, caché y horneado. Sirve a Geoda: «desactiva la caché para ahorrar memoria» |
| 3 | Volumes (4.5) | aceptar | aceptar | clara | La mejor de las 20: el tamaño de paso cambia el tiempo de render por el detalle |
| 4 | Endpoint Selection Node | aceptar | aceptar | clara | Referencia completa de un nodo |
| 5 | Sample Grid Node | revisión | aceptar | clara | Dice que no menciona versiones (la URL dice 5.2, C2) ni ajustes de rendimiento, pero compara el costo de las tres interpolaciones. Es el error E3 |
| 6 | Attribute Node | aceptar | aceptar | clara | Explica cómo se buscan las propiedades y qué pasa si faltan |
| 7 | Get Geometry Bundle Node | aceptar | aceptar | clara | Corta, pero con un ajuste de rendimiento: «Remove» evita copias |
| 8 | Volume Scatter (3.6) | revisión | aceptar | clara | El motivo pide versiones, hardware o medidas: es E3 |
| 9 | Rip (UV, 3.6) | aceptar | aceptar | discutible | Dos frases: es la página más delgada de las aceptadas |
| 10 | Snap to Symmetry | aceptar | aceptar | clara | Opciones con su efecto |
| 11 | Select Loops | aceptar | aceptar | clara | Modos, atajos y cuándo se cierra un bucle |
| 12 | Motion Blur | revisión | aceptar | clara | El motivo dice «le da valor» y la decisión es «revisión». En las 5 corridas de prueba siempre se aceptó |
| 13 | Retopology (3.6) | aceptar | aceptar | clara | El remallado por vóxeles tiene ajustes con efecto. Tiene un hueco («Todo 2.81») que la IA no vio |
| 14 | Mesh Circle Node | aceptar | aceptar | clara | Tipos de relleno y el límite de 3 vértices |
| 15 | Merge | aceptar | aceptar | clara | Seis modos con su efecto y sus opciones |
| 16 | Mapping Node | aceptar | aceptar | clara | Explica el orden de las transformaciones según el tipo de vector |
| 17 | Point Density Node (3.6) | aceptar | aceptar | clara | Radio, interpolación y resolución con su efecto |
| 18 | Clamp Node (3.6) | revisión | aceptar o revisión | discutible | «Min: the minimum value» es justo lo que C5 dice que no sirve. Pero el modo «Range» y el ejemplo sí tienen efecto |
| 19 | Triangulate Node | aceptar | aceptar | clara | Bien decidida, aunque el motivo se contradice: «no menciona versiones… en una versión concreta» |
| 20 | Split Edges Node | revisión | aceptar o revisión | discutible | Delgada. El motivo vuelve a pedir hardware y medidas (E3) |

## Lo que dice

**Lo que la IA acepta está bien: 14 de 14.** Ningún documento malo pasó la puerta. El límite inferior de Wilson al 95 % con 14 de 14 es 0.84, pero la cifra solo cuenta hacia el lote si la confirma una persona.

**Lo que manda a revisión casi nunca debía ir ahí:**
- 4 de 6 son errores claros (1, 5, 8 y 12);
- 2 son discutibles (18 y 20).

Con la regla del cierre, la IA coincide con el asistente en 14 a 16 de 20. Eso queda **por debajo de 17: «no aprobado»**. Pero falla del lado seguro: manda trabajo a una persona y no deja pasar basura.

**Los errores que ya estaban escritos se repiten:**
- E3, «valor no exige medidas ni hardware», aparece en 4 motivos (5, 8, 18 y 20);
- E1 y E4, motivo positivo con «revisión» y confianza alta, aparecen en 2 (1 y 12).

Los dos errores están en las instrucciones fijas desde la v3 con criterios. **Al modelo de 8B no le basta con que se le diga el error.** Lo que se puede comprobar por código debería comprobarse por código.

## Lo que el código puede medir

| Señal | Lote 1 |
|---|---|
| JSON válido | 20/20 |
| Cita de la lista cerrada | 20/20 |
| Cita que de verdad respalda una decisión sobre un documento (el embudo o la rúbrica de selección) | 7/20; 9 son de telemetría, fichas o la conexión con Geoda |
| Coherencia según el código | 20/20 (el código no ve las dos contradicciones del motivo) |
| Motivo de 40 palabras o menos, como piden las instrucciones | **0/20** (entre 43 y 79 palabras; la mediana es 54) |
| Motivo que repite la frase de P6 casi tal cual | 13/20 |
| Confianza «alta» | 18/20, incluidas 4 de las 6 revisiones mal decididas: no informa |

## Límite de esta prueba

El lote solo trae páginas del manual de Blender que el embudo de G7B ya había aceptado. Casi todas son buenas de entrada, así que **la muestra no puede decir si la IA detecta un documento malo**: no hubo ninguno que rechazar. Una IA que aceptara todo sacaría unos 18 de 20.

## Qué sirve a cada pieza

- **A Geoda, por el rendimiento, le sirven 7 de 20:** Volumes, Simulation Zone, Motion Blur, Retopology, Sample Grid, Get Geometry Bundle y Point Density.
- **El resto es referencia de modelado:** sirve para enseñar en Amatista y, después, a Amatista ML.
- Separarlas por pieza sería una herramienta nueva, así que va al estacionamiento de la base.

## Propuestas, para que decida una persona

Se hacen después de ver el lote 1. Por eso el lote 1 se califica con la regla vigente, y lo que se apruebe se aplica desde el lote 2.

1. **La regla del cierre** (`BASE.md`; se cambia con su regla de cambio). Contar dos cosas por separado:
   - los aceptados que no debían entrar: lo que protege al cubo, que debería ser 0 o 1 de 14;
   - los buenos retenidos: el trabajo que le cuesta a la persona.

   Hoy las dos valen igual, y la consola podría frenar con 0 documentos malos admitidos.
2. **Revisor v4, como corrida aparte, sobre los mismos 100 documentos y calificada con las mismas etiquetas:**
   - quitar los fragmentos recuperados por parecido. Para un documento, la regla que respalda la decisión es siempre el embudo o la rúbrica. Además lee menos y tarda menos;
   - que el código detecte E3: un motivo que dice que «no menciona versiones» cuando la URL trae la versión, o que pide hardware o medidas para P6. Esa decisión iría a una persona.
3. **Una prueba con documentos malos sembrados.** Mezclar páginas que no deberían entrar, por ejemplo páginas a medio escribir, plantillas o páginas truncadas, para medir si la IA las detecta. Es lo mismo que se hizo con el criterio de mediciones. *(Se hizo como el conjunto de control C1: ver el análisis de las corridas 10–12 en RESULTADOS_PRUEBA.md.)*
4. **Por decidir en los criterios: las páginas de referencia delgadas** (Rip, Clamp, Split Edges). ¿Entran como referencia o van a revisión? Es la misma pregunta que ya está abierta para las páginas introductorias.
