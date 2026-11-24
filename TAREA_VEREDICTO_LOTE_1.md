# Tarea: veredicto del lote 1 (24 de noviembre de 2026)

**Para el agente de IA de la computadora del laboratorio.** Responde en español. Antes de empezar, lee [`AGENTS.md`](AGENTS.md).

## Qué es

Es la primera vez que una persona revisa a la IA.
- **La persona** (Maximiliano) marca las 20 muestras del cierre del lote 1 en `planilla.csv`.
- **El agente** espera a que termine, corre el veredicto y las comparaciones, guarda las etiquetas y reporta.

**La regla más importante de esta tarea:** el agente **nunca escribe, corrige ni completa** las columnas `humano_decision` ni `humano_nota`. Tampoco «arregla» una marca que parezca rara. Si falta alguna marca o una no se entiende, se lo dice a la persona y espera. Unas etiquetas escritas por el agente no serían de una persona y echarían a perder la prueba.

## Dónde está la planilla

```text
C:\Users\KANEDA\OneDrive - UNIVERSIDAD TECNOLÓGICA DE NEZAHUALCÓYOTL\Escritorio\Amatista IA · cierres\lote_001\planilla.csv
```

En la misma carpeta están `muestras.html`, con el extracto de cada documento, y `LEEME.txt`.

## Instrucciones para la persona (muéstraselas tal cual)

1. Abre `muestras.html` para leer cada documento, y `planilla.csv` en Excel.
2. En la columna `humano_decision` de cada una de las 20 filas, escribe tu decisión: `aceptar`, `revision` o `rechazar`.
   - Se vale con acento o con mayúsculas.
   - Decide qué harías tú con el documento, sin ver qué dijo la IA en `ia_decision`.
3. En `humano_nota` puedes escribir el porqué. Es opcional, pero muy útil cuando no coincides con la IA.
4. No cambies las demás columnas. Guarda como **CSV** (si Excel pregunta, «CSV UTF-8»). Con coma o con punto y coma, las dos funcionan.
5. Avísale al agente que terminaste.

## Pasos del agente (solo después del aviso de la persona)

**1. Actualizar y comprobar.** Deben pasar 63 pruebas o más:

```bash
git pull
```

```bash
python -m pytest -q pruebas
```

**2. Veredicto.** Si responde «faltan N muestras por marcar», detente y díselo a la persona; no completes nada.

```bash
python -m consola veredicto 1
```

**3. Ver el estado.** La consola aplica el veredicto en su siguiente vuelta, en unos 10 minutos como máximo. Copia la salida:

```bash
python -m consola estado
```

**4. Comparar a la IA con la persona:**

```bash
python -m revisor.comparar "C:\Users\KANEDA\OneDrive - UNIVERSIDAD TECNOLÓGICA DE NEZAHUALCÓYOTL\Escritorio\Amatista IA · cierres\lote_001\planilla.csv"
```

**5. Comparar la v3 y la v4 con la persona,** sobre las mismas 20 muestras:

```bash
python -m revisor.comparar_versiones 1 salidas/prueba_revisor_v4_lote001.json --planilla "C:\Users\KANEDA\OneDrive - UNIVERSIDAD TECNOLÓGICA DE NEZAHUALCÓYOTL\Escritorio\Amatista IA · cierres\lote_001\planilla.csv"
```

**6. Guardar las etiquetas en el repositorio.** El comando escribe `revisor/etiquetas/lote_001.yml` con título, URL pública, fuente y las dos decisiones. No guarda el texto de los documentos.

```bash
python -m consola etiquetas 1
```

**7. Reportar** en una sección nueva de `revisor/RESULTADOS_PRUEBA.md`, «Veredicto del lote 1», con:
- la salida exacta de los pasos 2, 3, 4 y 5;
- cualquier error o aviso, tal cual.

Si el resultado es «no aprobado» o «aviso», es un resultado válido: se reporta igual, sin cambiar nada. El freno solo se activa con dos lotes seguidos no aprobados.

**8. Subir.** No subas `planilla.csv` ni nada de `salidas/`.

```bash
python -m pytest -q pruebas
```

```bash
git add revisor/RESULTADOS_PRUEBA.md revisor/etiquetas/lote_001.yml
```

```bash
git commit -m "ia(consola): veredicto del lote 1 y primeras etiquetas humanas"
```

```bash
git push
```
