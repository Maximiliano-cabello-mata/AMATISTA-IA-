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
