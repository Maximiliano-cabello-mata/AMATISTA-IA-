# Tarea: medir el revisor v4 (23 de noviembre de 2026)

**Para el agente de IA de la computadora del laboratorio.** Responde en español. Sigue los pasos en orden y reporta lo que salga, tal cual. Antes de empezar, lee [`AGENTS.md`](AGENTS.md): las reglas de claves y datos siguen igual.

## Qué se mide

La v4 del revisor (`--version 4`) cambia dos cosas respecto de la v3, que es la que usa la consola:
- ya no recupera fragmentos del canon por parecido: las citas permitidas son siempre las mismas, la regla del embudo y la regla de utilidad;
- el código busca dos errores conocidos en el motivo (E3 y E1). Si encuentra uno, el modelo vuelve a decidir una vez; si el error sigue, la decisión va a una persona.

Se corre en dos conjuntos:
1. **El lote 1 de la consola:** los mismos 100 documentos que ya revisó la v3.
2. **El conjunto de control C1** (`control/conjunto_c1.jsonl`): 35 documentos públicos que no vienen del lago. Se corre con la v3 y con la v4.

## Reglas de esta prueba

- **No cambies nada a mitad de la prueba:** ni el modelo, ni las instrucciones, ni el número de palabras, ni el canon. No uses `--refrescar-canon`.
- **No edites `control/conjunto_c1.jsonl`.** Si un comando falla, detente y reporta el error exacto.
- **Solo la consola o la prueba:** las dos usan el mismo Ollama y, juntas, irían al doble de lento.
- Los resultados del lote 1 son del lago: se quedan en `salidas/` y no se suben. Los del conjunto de control sí se suben (paso 8).

## Pasos

**1. Actualizar y comprobar.** Deben pasar todas las pruebas (59 o más):

```bash
git pull
```

```bash
python -m pytest -q pruebas
```

```bash
python -m laboratorio.verificar
```

**2. Anotar el estado de la consola y detenerla.** Copia la salida completa para el reporte:

```bash
python -m consola estado
```

En la ventana de la consola, presiona **Ctrl+C** y espera el mensaje «Deteniendo… (termina el documento en curso)». La ventana se cierra cuando termina el documento en curso, y no se pierde nada.

**3. Sacar de MongoDB los 100 documentos del lote 1.** Es solo lectura y debe decir `100 de … documentos`:

```bash
python -m revisor.muestra --de-lote 1 --salida salidas/lote001.jsonl
```

**4. Conjunto de control con la v3**, igual que la consola: unas 1.5 horas.

```bash
python -m revisor.revisar control/conjunto_c1.jsonl --criterios --nombre v3_control
```

**5. Conjunto de control con la v4:** unas 1–1.5 horas.

```bash
python -m revisor.revisar control/conjunto_c1.jsonl --version 4 --criterios --nombre v4_control
```

**6. Lote 1 con la v4:** unas 3–4 horas.

```bash
python -m revisor.revisar salidas/lote001.jsonl --version 4 --criterios --nombre v4_lote001
```

**7. Comparar la v4 con la v3 en el lote 1.** Si la persona ya marcó la planilla del lote 1 (en la carpeta del escritorio `lote_001`), agrega `--planilla` con su ruta:

```bash
python -m revisor.comparar_versiones 1 salidas/prueba_revisor_v4_lote001.json
```

**8. Reanudar la consola** con el acceso del escritorio, «Iniciar Amatista IA». Luego copia los dos resultados del conjunto de control:

```bash
cp salidas/prueba_revisor_v3_control.json salidas/prueba_revisor_v4_control.json control/resultados/
```

En Windows, si `cp` no existe, usa `copy`.

**9. Reportar** en una sección nueva de `revisor/RESULTADOS_PRUEBA.md`, «Corridas 10–12 · Revisor v4 y conjunto de control C1», con:
- la salida del paso 2;
- **el resumen exacto** (el JSON que imprime cada corrida) de los pasos 4, 5 y 6;
- una tabla del conjunto de control, documento por documento: `#`, título, fuente, v3 (decisión → efectiva), v4 (decisión → efectiva), errores del reintento (`reintento.errores`) y si cambió la decisión;
- la salida completa del paso 7;
- cualquier error o aviso, tal cual.

No juzgues si las decisiones son correctas: eso lo hace una persona. Agrega también una corrida a `revisor/comportamiento.yml` por cada uno de los pasos 4, 5 y 6, con `json`, `cita` y `coherente` del resumen, contados como `[éxitos, total]`.

**10. Subir:**

```bash
python -m pytest -q pruebas
```

```bash
git add revisor/RESULTADOS_PRUEBA.md revisor/comportamiento.yml control/resultados/
```

```bash
git commit -m "ia(revisor): corridas v4 en el lote 1 y en el conjunto de control C1"
```

```bash
git push
```

No subas nada de `salidas/`.
