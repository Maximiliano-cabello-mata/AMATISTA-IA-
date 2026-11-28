# Tarea: el registro de estados de la consola (24 de noviembre de 2026)

**Para el agente de IA de la computadora del laboratorio.** Responde en español. Antes de empezar, lee [`AGENTS.md`](AGENTS.md).

La consola ahora le da a cada documento de conocimiento un solo estado: **pendiente, en cuarentena, aprobado, descartado o por revisar**. La telemetría va aparte. Está explicado en el [`README.md`](README.md), en «Dónde está cada cosa».

## Pasos

**1. Actualizar y comprobar.** Deben pasar 72 pruebas o más:

```bash
git pull
```

```bash
python -m pytest -q pruebas
```

**2. Reiniciar la consola para que cargue el código nuevo:**
- detén la tarea programada «Amatista IA» y vuelve a iniciarla;
- antes de iniciarla, comprueba que Ollama esté corriendo.

Lo revisado se conserva. Al arrancar, la consola cuenta los documentos de la fuente para saber cuántos quedan pendientes. Si Ollama todavía no responde, ahora no se detiene: dice «esperando servicios», reintenta cada 2 minutos y anota el error en «Último error».

**3. Esperar a que la consola revise al menos un documento** (unos 3 minutos) y generar el registro:

```bash
python -m consola registro
```

```bash
python -m consola estado
```

**4. Reportar** en una sección nueva de `revisor/RESULTADOS_PRUEBA.md`, «Registro de estados (24 de noviembre)», con la salida exacta de los dos comandos y cualquier error.

No subas nada de `salidas/`: las listas por estado se quedan en esta computadora.

**5. Subir:**

```bash
git add revisor/RESULTADOS_PRUEBA.md
```

```bash
git commit -m "ia(consola): primer registro de estados del conocimiento"
```

```bash
git push
```
