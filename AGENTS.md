# Reglas para agentes de IA en este repositorio

Este repositorio construye la IA que revisa los datos del lago de G7B. Para instalarla en la computadora del laboratorio, sigue [`LABORATORIO.md`](LABORATORIO.md) paso por paso. Las tareas del revisor están en [`TAREA_PRUEBA_REVISOR.md`](TAREA_PRUEBA_REVISOR.md) y [`TAREA_SEGUNDA_REVISION.md`](TAREA_SEGUNDA_REVISION.md). Responde en español.

## Claves

- **Nunca imprimas, copies, subas ni pidas por chat una clave ni el `GITHUB_TOKEN`.** Las claves viven solo en `.env` (excluido por `.gitignore`), y las escribe una persona.
- No abras `.env` para leerlo ni lo muestres. Para saber si las claves funcionan, usa `python -m laboratorio.verificar`, que no muestra valores.
- No pases claves como argumentos de línea de comandos: quedan en el historial. Solo como variables de entorno o en `.env`.
- La clave secreta solo la usa `indexador/indexar.py`. Todo lo que solo lee usa la publicable.

## Datos

- **Ningún dato del lago ni de estudiantes sale de esta computadora** hacia servicios de IA en la nube (Gemini, OpenAI, etc.). La IA es local: Ollama.
- El canon solo tiene estándares del proyecto. No agregues datos del lago al canon: es lo que la IA va a revisar.
- Ollama escucha solo en `127.0.0.1`. No lo expongas a la red.
- **El revisor solo propone.** Lee de MongoDB con un usuario de solo lectura y escribe en `salidas/`, que no se sube. Nunca cambia el lago, MongoDB ni Supabase.
- No cambies las instrucciones del revisor, el número de palabras ni el modelo a mitad de una prueba para que salga mejor. Si quieres probar otra cosa, es otra corrida y se reporta aparte.

## Qué no se toca para que algo «salga bien»

- `canon/canon.yml`: los commits fijados y la lista de documentos cambian solo por decisión de una persona.
- `evaluacion/preguntas.yml`: las preguntas no se ajustan para subir el recall.
- `supabase/migrations/`: el agente no aplica migraciones ni ejecuta SQL que cambie tablas. Si la migración falta, se reporta.
- Los pesos de búsqueda por omisión y el modelo `bge-m3`.

Si una medición sale mal, se reporta tal cual, con la salida exacta. No afirmes nada que no hayas corrido y visto.

## Antes de entregar un cambio de código

```bash
python -m pytest -q pruebas
```

- Commits con la forma `<dominio>(<lote>): <acción>`, por ejemplo `ia(laboratorio): …`.
- Nunca subas directo a `main`: trabaja en una rama y abre un PR.
