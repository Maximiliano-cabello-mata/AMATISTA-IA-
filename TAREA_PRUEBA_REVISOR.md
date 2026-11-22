# Tarea: prueba rápida del revisor

**Para el agente de la computadora del laboratorio.** Antes de empezar, lee [`AGENTS.md`](AGENTS.md). La instalación de [`LABORATORIO.md`](LABORATORIO.md) ya está hecha: Ollama, `bge-m3`, `.env` y el canon indexado.

**Objetivo:** un modelo local de unos 8B revisa 20 documentos del lago con los estándares del canon. Queremos saber dos cosas:
1. **qué tan rápido es** en esta computadora;
2. **qué tan bien revisa:** JSON válido, citas reales, datos sin inventar, y después el acuerdo con una persona.

**Qué toca y qué no:**
- Solo **lee** de MongoDB y solo **escribe** archivos en `salidas/`.
- No cambia nada en el lago, en MongoDB ni en Supabase.
- Ningún texto del lago sale de la computadora: el canon se descarga y se busca localmente.

## Paso 0 · Lo que hace una persona antes

1. **Un usuario de MongoDB de solo lectura.** En MongoDB Atlas → Database Access, crea un usuario con el rol **`read`** sobre la base `conocimiento_3d`, y solo ese. No uses el usuario que publica: ese escribe.
2. **Permitir esta computadora en Atlas.** En Network Access, agrega la IP pública del laboratorio. Si no, la conexión se queda esperando y falla.
3. **Escribir en `.env`:**

   ```ini
   MONGO_URI_LECTURA=mongodb+srv://<usuario>:<contraseña>@<cluster>/
   ```

   `MONGO_DATABASE` es opcional; por omisión es `conocimiento_3d`.

## Paso 1 · Actualizar

```bash
git pull
```

```bash
python -m pip install pymongo
```

Comprueba que todo siga bien:

```bash
python -m laboratorio.verificar
```

Debe decir `LISTO para indexar.`

## Paso 2 · El modelo revisor

```bash
ollama pull qwen3:8b
```

Si ese nombre no existe, busca en <https://ollama.com/library> el nombre exacto de un Qwen 3 de 8B. Si tampoco está, usa `llama3.1:8b` y anota cuál usaste. Pesa unos 5 GB.

Mide su velocidad:

```bash
python -m laboratorio.verificar --revisor qwen3:8b
```

Anota la línea `revisor`.

## Paso 3 · La muestra

```bash
python -m revisor.muestra --n 20
```

Saca 20 documentos al azar de los 1,033 de `conocimiento_3d.documentos` y los guarda en `salidas/muestra.jsonl`. Ese archivo no se sube. Anota de qué fuentes salieron.

## Paso 4 · Revisar

```bash
python -m revisor.revisar salidas/muestra.jsonl --modelo qwen3:8b
```

Cada documento imprime una línea con tiempo, decisión, pregunta y título. Se estima **1–2 minutos por documento**, así que la corrida completa tarda 20–40 minutos. Esa estimación no está medida: el número real es parte del resultado.

- No cambies `--palabras` ni las instrucciones del revisor para que salga mejor.
- Si el modelo es demasiado lento (más de 5 minutos por documento), detente con Ctrl+C y repórtalo.
- Si la corrida falla, repórtalo con la salida exacta.

Al terminar escribe dos archivos:
- `salidas/prueba_revisor.json`: todo, con el resumen al principio;
- `salidas/prueba_revisor.csv`: una fila por documento, para que una persona marque.

## Paso 5 · Reportar

Entrega a la persona el bloque `resumen` que imprime al final, tal cual. Explica en palabras simples:

| Campo | Qué significa | Qué esperar |
|---|---|---|
| `json_valido` | Respuestas que cumplieron el formato | 1.0; menos indica un problema del modelo |
| `cita_valida` | Citas a fragmentos que de verdad se le mostraron | Cerca de 1.0; si no, inventa fuentes |
| `pregunta_valida` | Preguntas dentro de la lista P1–P6 o «ninguna» | 1.0 |
| `datos_fieles` | Datos extraídos (versiones, hardware, medidas) que aparecen en el texto | Cerca de 1.0; lo demás es inventado |
| `coincide_pregunta_embudo` | Veces que la IA eligió una pregunta que el embudo de palabras clave también asignó | No es acierto ni error: el embudo también se equivoca |
| `decisiones` | Cuántos acepta, manda a revisión o rechaza | Los documentos ya pasaron el embudo, así que lo esperable es que acepte casi todos |
| `segundos_por_documento`, `tokens_por_segundo` | Velocidad real | — |
| `horas_estimadas_para_1033` | Cuánto tardaría con todos los documentos | — |

Añade también:
- el modelo exacto (`ollama list`);
- los documentos que la IA mandó a `revision` o `rechazar`, con su motivo, que salen en el CSV;
- los `datos_inventados` que haya.

## Paso 6 · La persona marca y se compara

1. La persona abre `salidas/prueba_revisor.csv` en Excel o LibreOffice.
2. Por cada fila, abre la URL y llena `humano_decision` con `aceptar`, `revision` o `rechazar`. `humano_pregunta` es opcional.
3. Después:

   ```bash
   python -m revisor.comparar salidas/prueba_revisor.csv
   ```

Lo que más importa del resultado:
- **`detecta_problemas`:** de lo que la persona sacaría o revisaría, cuánto marcó la IA;
- **`falsas_alarmas`:** de lo que marcó la IA, cuánto estaba bien.

**Con 20 documentos es una prueba rápida, no una conclusión.** La decisión de usar la IA en serio sale del conjunto de 150–200 documentos marcados a mano.

---

## Versión 2 del revisor (22 de noviembre)

Lo que cambió, por lo que mostraron `codellama` y `qwen3:8b`:
- **La cita es una lista cerrada** para cada documento. El modelo ya no puede citar el propio documento ni inventar ids.
- **Los datos los extrae el código**, con `hardware.yml`, la versión del texto o de la URL del manual, y las medidas con unidad. El modelo copiaba los ejemplos del embudo («UHD 620»).
- **La respuesta es más corta** y no puede pasar de 300 tokens.
- **El código revisa la coherencia.** Marca, por ejemplo, cuando asigna P6 y a la vez dice que falla la relevancia, como pasó con `qwen3` en «Group» y en «Deleting & Dissolving».

### Paso 7 · Diagnóstico de la caché

```bash
git pull
```

```bash
python -m revisor.revisar salidas/muestra.jsonl --modelo qwen3:8b --diagnostico-cache
```

Dice si Ollama reutiliza las instrucciones fijas entre documentos. En la versión 1, cada documento leyó entre 2,236 y 3,444 tokens, lo que sugiere que no las reutiliza. Anota la línea completa.

### Paso 8 · Corrida v2 con la misma muestra y el mismo canon

```bash
python -m revisor.revisar salidas/muestra.jsonl --modelo qwen3:8b
```

- **No uses `--refrescar-canon`**: la comparación con la versión 1 tiene que ser con el mismo canon de 108 fragmentos. El resumen ahora dice `canon_fragmentos`, y debe ser 108.
- La segunda revisión de Site usa su propio archivo de canon (`salidas/canon_rubrica.json`), así que no lo altera.
- Entrega el `resumen` y la tabla documento por documento, igual que antes.

### Predicciones, escritas antes de correr

| # | Predicción | Probabilidad |
|---|---|---:|
| H1 | `cita_valida` = 1.00 (la lista cerrada lo garantiza) | 0.95 |
| H2 | `coherente` ≥ 0.90 | 0.60 |
| H3 | Tokens generados por documento (mediana) ≤ 120 (antes, 200) | 0.70 |
| H4 | Segundos por documento (mediana) entre 90 y 125 (antes, 154). Sin caché, la v2 sola no llega a 60 s | 0.60 |
| H5 | El diagnóstico dice que la caché NO se reutiliza | 0.60 |
| H6 | `qwen3:8b` v2 manda a revisión entre 6 y 12 de los 20 (antes, 11) | 0.65 |
| H7 | La decisión de v2 coincide con la de v1 en al menos 15 de los 20 documentos | 0.65 |

### Paso 9 · Lo que de verdad decide: una persona marca los 20

Los modelos ya dieron dos opiniones sobre los mismos 20 documentos. Coincidieron en 13: 8 aceptados y 5 a revisión.
- **Ambos a revisión:** Limitations, Select All by Trait, Deleting & Dissolving, World Settings y Structure.
- **No coinciden en 7:** Group, Introduction (grupos de vértices), Startup 4.5, Input, Introduction (Light Probes), UV Project Modifier y Ocean Modifier.

Sin la opinión de una persona no sabemos cuál acierta. Que una persona llene `humano_decision` en `salidas/prueba_revisor.csv` de la corrida v2; son unos 20–30 minutos. Después:

```bash
python -m revisor.comparar salidas/prueba_revisor.csv
```

Así se sabe qué tan seguido acierta la IA en lo que importa: los documentos que una persona sí sacaría del lago.

---

## Criterios aprendidos y pesos de confianza (22 de noviembre)

El canon v3 agrega **`ia/criterios`**: siete criterios que aprendimos probando, cada uno con su evidencia. Está en `canon/criterios/criterios_revision.md` de este repositorio. El revisor puede usarlos como instrucciones fijas con `--criterios`.

### Paso 10 · Volver a indexar (canon v3)

Hazlo **después** de la corrida v2 del paso 8: esa corrida necesita el canon de 108 fragmentos.

```bash
python -m indexador.indexar canon/canon.yml
```

Se espera:
- si ya indexaste la v2: `1 documentos actualizados (8 fragmentos)`;
- si no: `3 documentos actualizados (11 fragmentos)`.

En los dos casos, los demás salen `sin cambios`.

Mide de nuevo la recuperación. Ahora son 51 preguntas. Solo con texto, el canon v3 da 0.902.

```bash
python -m evaluacion.evaluar evaluacion/preguntas.yml
```

### Paso 11 · Dos corridas con el mismo canon v3: sin y con criterios

Así lo único distinto entre las dos son los criterios:

```bash
python -m revisor.revisar salidas/muestra.jsonl --modelo qwen3:8b --refrescar-canon --nombre canon3
```

```bash
python -m revisor.revisar salidas/muestra.jsonl --modelo qwen3:8b --criterios --nombre criterios
```

- `--refrescar-canon` solo va en la primera; la segunda reutiliza ese canon.
- Los criterios agregan unas 520 palabras a cada prompt. Sin caché, eso son unos 20 s más por documento.
- Las predicciones H8–H10 están en `revisor/predicciones.yml`, escritas antes de correr.

### Paso 12 · Pesos de confianza

```bash
python -m revisor.confianza --corridas salidas/prueba_revisor_canon3.json salidas/prueba_revisor_criterios.json
```

Qué hace:
1. **Parte de los pesos teóricos** de `revisor/pesos_teoricos.yml`, escritos antes de ver etiquetas humanas. **No se editan después de ver resultados.**
2. **Los actualiza con el comportamiento real** de `revisor/comportamiento.yml`.
3. **Combina las opiniones de los modelos** en una probabilidad de que cada documento tenga un problema, y ordena el trabajo de la persona:
   - menos de 0.20: se propone dejar;
   - más de 0.80: se propone revisar;
   - en medio: lo decide la persona.

Cuando una persona marque la planilla, agrega `--etiquetas salidas/prueba_revisor_criterios.csv`. Con eso los pesos dejan de ser teóricos: se vuelven la sensibilidad y la especificidad reales de cada modelo.

Después, una persona marca en `revisor/predicciones.yml` qué predicciones se cumplieron (`resultado: true` o `false`) y agrega los conteos nuevos a `revisor/comportamiento.yml`. El algoritmo calcula el puntaje de Brier.

---

## Versión 3 del revisor y canon v4 (22 de noviembre)

**Esta sección reemplaza los pasos 10 a 12 anteriores.** Esos pasos se escribieron para el revisor v2 y el canon v3; no los corras.

**Qué cambió en el revisor v3.** Todo viene de lo que mostró la v2:
- **Razona antes de decidir.** El modelo escribe primero el motivo y al final la decisión. En la v2, 9 de 20 decisiones contradecían su propio motivo.
- **«Etapa» es solo la que falla.** En la v2, las 14 revisiones decían «relevancia».
- **Una decisión incoherente no cuenta: va a una persona.** El resumen trae `decisiones_efectivas`, con la categoría `persona`.
- **Opciones de velocidad**, cada una para una corrida aparte: `--cuantos`, `--umbral`, `--palabras`, `--modelo qwen3:4b` y el diagnóstico de la caché con `--variantes`.

**Qué cambió en el canon v4.** `ia/criterios` ahora incluye **los errores conocidos del revisor** (E1–E6): lo que hacía mal, con sus números, y qué hacer en su lugar. Entra a Supabase al volver a indexar y a las instrucciones del modelo con `--criterios`.

Las predicciones H8–H20 están en `revisor/predicciones.yml`, escritas antes de correr.

### Paso 13 · Actualizar y diagnosticar la caché con 4 variantes

```bash
git pull
```

```bash
python -m revisor.revisar salidas/muestra.jsonl --modelo qwen3:8b --diagnostico-cache --variantes
```

Prueba la caché de cuatro formas: como hoy, sin formato obligatorio, sin el parámetro `think` y con el mismo mensaje dos veces. Copia las 4 líneas completas.

### Paso 14 · Corrida v3, con la misma muestra y el mismo canon de 108 fragmentos

```bash
python -m revisor.revisar salidas/muestra.jsonl --modelo qwen3:8b --nombre v3
```

**Todavía sin `--refrescar-canon`:** el resumen debe decir `canon_fragmentos: 108` y `revisor: 3`. Así se compara directo con la v1 y la v2, y lo único que cambia es cómo razona el revisor. Cada línea muestra ahora la etapa, y marca `⚠ incoherente → persona` cuando el modelo se contradice.

### Paso 15 · Corridas de velocidad, una por una y con el mismo canon de 108

```bash
python -m revisor.revisar salidas/muestra.jsonl --modelo qwen3:8b --cuantos 1 --nombre v3_c1
```

```bash
python -m revisor.revisar salidas/muestra.jsonl --modelo qwen3:8b --palabras 300 --nombre v3_p300
```

```bash
ollama pull qwen3:4b
```

```bash
python -m revisor.revisar salidas/muestra.jsonl --modelo qwen3:4b --nombre v3_4b
```

Si el tiempo no alcanza, el orden de prioridad es `v3_c1`, luego `v3_4b` y al final `v3_p300`.

`--umbral` todavía no: cada resultado guarda ahora la similitud de cada fragmento mostrado (`similitudes`). Con eso se elige un umbral razonable después de ver la corrida v3.

### Paso 16 · Volver a indexar (canon v4) y medir la recuperación

Hazlo después de los pasos 14 y 15.

```bash
python -m indexador.indexar canon/canon.yml
```

Se espera, según lo último que indexaste:
- desde el canon v1 (13 documentos): `3 documentos actualizados (18 fragmentos)`;
- desde el v2: `1 documentos actualizados (15 fragmentos)`.

Los demás salen `sin cambios`.

```bash
python -m evaluacion.evaluar evaluacion/preguntas.yml
```

Son 51 preguntas. Solo con texto, el canon v4 da 0.902.

### Paso 17 · Criterios y errores conocidos: dos corridas con el mismo canon v4

```bash
python -m revisor.revisar salidas/muestra.jsonl --modelo qwen3:8b --refrescar-canon --nombre canon4
```

```bash
python -m revisor.revisar salidas/muestra.jsonl --modelo qwen3:8b --criterios --nombre criterios
```

Con `--criterios`, las instrucciones fijas pasan de unas 640 a unas 1,530 palabras. Si la caché no se reutiliza, eso son unos 30–40 s más por documento (predicción H10).

### Paso 18 · Pesos de confianza y reporte

```bash
python -m revisor.confianza --corridas salidas/prueba_revisor_v3.json salidas/prueba_revisor_criterios.json
```

Para el reporte:
- agrega a `revisor/comportamiento.yml` los conteos de cada corrida nueva;
- marca en `revisor/predicciones.yml` cuáles de H8–H20 se cumplieron;
- sube los resúmenes y la tabla documento por documento, con la etapa y la `decision_efectiva`, igual que en la v2.

---

## Ajuste a los pasos 14–18 (22 de noviembre, después de las corridas `canon3` y `criterios`)

Se corrieron los pasos 10–11 viejos, con el revisor v2 y el canon v3. Sus resultados valen y quedan registrados, pero el canon guardado en `salidas/canon_local.json` ya tiene **119 fragmentos**. Por eso la v3 se compara ahora con `canon3`: **mismo canon, solo cambia el revisor.**

Antes de correr cualquier cosa:

```bash
git pull
```

Comprueba que el resumen de cada corrida diga **`revisor: 3`**. Si dice 2, el código no se actualizó.

1. **Paso 13 bis · diagnóstico con tiempos.** Ahora muestra también los segundos. Con 0 de 4 variantes reutilizando la caché, falta confirmar que de verdad vuelve a leer todo.

   ```bash
   python -m revisor.revisar salidas/muestra.jsonl --modelo qwen3:8b --diagnostico-cache --variantes
   ```

2. **Paso 14 · v3 con el canon de 119**, sin `--refrescar-canon`:

   ```bash
   python -m revisor.revisar salidas/muestra.jsonl --modelo qwen3:8b --nombre v3
   ```

3. **Paso 15 · velocidad**, igual que antes, con el mismo canon de 119: `v3_c1`, después `v3_4b` y al final `v3_p300`.
4. **Pasos 16–18** sin cambios: volver a indexar a v4, correr `canon4` y `criterios` con `--refrescar-canon` en la primera, y calcular la confianza.

---

## Siguiente (22 de noviembre, después de la v3)

La v3 confirmó que razonar antes de decidir quita las contradicciones. Pero sin criterios se volvió demasiado dura: 8 rechazos. Por eso **las corridas con criterios van antes que las de velocidad.**

```bash
git pull
```

1. **Diagnóstico de caché nuevo**, con la primera llamada fría y una variante con otra lista de citas (H21–H22):

   ```bash
   python -m revisor.revisar salidas/muestra.jsonl --modelo qwen3:8b --diagnostico-cache
   ```

2. **Volver a indexar el canon v4**, que agrega los errores conocidos (paso 16):

   ```bash
   python -m indexador.indexar canon/canon.yml
   ```

   Se espera `1 documentos actualizados (15 fragmentos)`.
3. **Las dos corridas del paso 17:** `canon4` con `--refrescar-canon` y después `criterios` (H8–H10 y H23–H26).
4. **Después, la velocidad:** `v3_c1` y `v3_4b`.

**Lo que más destraba, y no lo puede hacer la IA:** que una persona marque los 20 documentos en `salidas/prueba_revisor_v3.csv` y decida si las páginas del manual que explican un nodo o una operación responden a P6.
