# Reglas para agentes de IA en este repositorio

Este repositorio construye la IA que revisa los datos del lago de G7B. Para instalarla en la computadora del laboratorio, sigue [`LABORATORIO.md`](LABORATORIO.md) paso por paso. Las tareas vigentes, en orden: [`TAREA_REGISTRO.md`](TAREA_REGISTRO.md) (reiniciar la consola con el registro de estados y el reintento) y después [`TAREA_PROMOCION.md`](TAREA_PROMOCION.md) (la puerta: lo aprobado entra a MongoDB). El veredicto del lote 1 ([`TAREA_VEREDICTO_LOTE_1.md`](TAREA_VEREDICTO_LOTE_1.md)) ya se hizo. **El agente nunca escribe las columnas `humano_*` de una planilla.** La consola ([`TAREA_CONSOLA.md`](TAREA_CONSOLA.md)) sigue trabajando 24/7 con la v3. La medición de la v4 ([`TAREA_V4.md`](TAREA_V4.md)) ya terminó. Las pruebas anteriores del revisor están en [`TAREA_PRUEBA_REVISOR.md`](TAREA_PRUEBA_REVISOR.md) y [`TAREA_SEGUNDA_REVISION.md`](TAREA_SEGUNDA_REVISION.md). Responde en español.

## Lugar de este repositorio en la base

**Leer primero la [base oficial del proyecto](https://github.com/Maximiliano-cabello-mata/amatista-recuperada-20261106/blob/recuperacion/BASE.md)** (versión 1, congelada el 22 de noviembre de 2026). Manda sobre cualquier otro plan.

> **Amatista** enseña y mide; **G7B** extrae y guarda; **Amatista IA** audita; **Geoda** adapta; **Amatista Machine Learning** crea.

- **Amatista IA es el auditor:** decide qué datos son buenos y cuáles no antes de que entren al cubo o a MongoDB. Para documentos usa el revisor local (`qwen3:8b` con el canon); para mediciones, el criterio de pares y teoría.
- **Una sola puerta:** lo aprobado entra al cubo o a MongoDB. Nunca se escribe directo en Geoda: Geoda siempre lee del cubo.
- **La prioridad 1 de la base es este repositorio:** encender el flujo diario de auditoría, con cierre de 20 muestras y freno automático. No se agregan herramientas fuera de ese flujo. Una idea nueva va al estacionamiento de la base.

## Claves

- **Nunca imprimas, copies, subas ni pidas por chat una clave ni el `GITHUB_TOKEN`.** Las claves viven solo en `.env` (excluido por `.gitignore`), y las escribe una persona.
- No abras `.env` para leerlo ni lo muestres. Para saber si las claves funcionan, usa `python -m laboratorio.verificar`, que no muestra valores.
- No pases claves como argumentos de línea de comandos: quedan en el historial. Solo como variables de entorno o en `.env`.
- La clave secreta solo la usa `indexador/indexar.py`. Todo lo que solo lee usa la publicable.

## Datos

- **Ningún dato del lago ni de estudiantes sale de esta computadora** hacia servicios de IA en la nube (Gemini, OpenAI, etc.). La IA es local: Ollama.
  - **Única excepción (aprobada por el responsable el 22 de noviembre de 2026):** la persona puede pasarle al asistente las 20 muestras de un cierre (`para_segunda_opinion.md`) para una segunda opinión. Solo documentos de fuentes públicas (manual de Blender y foros con licencia), nunca datos de estudiantes. La consola no envía nada sola: siempre lo hace la persona.
- El canon solo tiene estándares del proyecto. No agregues datos del lago al canon: es lo que la IA va a revisar.
- Ollama escucha solo en `127.0.0.1`. No lo expongas a la red.
- **El revisor solo propone.** Lee de MongoDB con un usuario de solo lectura y escribe en `salidas/`, que no se sube. Nunca cambia el lago, MongoDB ni Supabase.
- **La única escritura es la puerta:** `python -m consola promover`.
  - Copia a la colección `conocimiento_auditado` solo los documentos en estado «aprobado»: la IA los aceptó y una persona aprobó su lote.
  - Usa su propio usuario (`MONGO_URI_PROMOCION`), con `readWrite` solo en esa colección.
  - Nunca escribe en `documentos`, que es de G7B, ni borra: lo que deja de estar aprobado se marca `vigente: false`.
  - Ese usuario lo crea una persona en Atlas y lo escribe en `.env`.
- No cambies las instrucciones del revisor, el número de palabras ni el modelo a mitad de una prueba para que salga mejor. Si quieres probar otra cosa, es otra corrida y se reporta aparte.

## Qué no se toca para que algo «salga bien»

- `canon/canon.yml`: los commits fijados y la lista de documentos cambian solo por decisión de una persona.
- `evaluacion/preguntas.yml`: las preguntas no se ajustan para subir el recall.
- `supabase/migrations/`: el agente no aplica migraciones ni ejecuta SQL que cambie tablas. Si la migración falta, se reporta.
- Los pesos de búsqueda por omisión y el modelo `bge-m3`.
- `revisor/pesos_teoricos.yml`: son lo que se creía antes de ver resultados. Lo observado va en `revisor/comportamiento.yml` y en las etiquetas humanas, nunca en los pesos teóricos.
- `canon/criterios/criterios_revision.md`: un criterio nuevo lo escribe y aprueba una persona, con su evidencia.

Si una medición sale mal, se reporta tal cual, con la salida exacta. No afirmes nada que no hayas corrido y visto.

## Antes de entregar un cambio de código

```bash
python -m pytest -q pruebas
```

- Commits con la forma `<dominio>(<lote>): <acción>`, por ejemplo `ia(laboratorio): …`.
- Nunca subas directo a `main`: trabaja en una rama y abre un PR.
