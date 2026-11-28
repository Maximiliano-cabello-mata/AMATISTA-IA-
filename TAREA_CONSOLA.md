# Tarea: dejar la consola de Amatista IA trabajando 24/7

**Para el agente de la computadora del laboratorio.** Antes de empezar, lee [`AGENTS.md`](AGENTS.md). Esta es la **prioridad 1 de la base del proyecto**: el flujo diario de auditoría.

**Qué hace la consola:**
- revisa uno por uno los documentos de MongoDB con el revisor v3 y deja cada decisión **en cuarentena**;
- al llegar a **100 documentos**, cierra el lote sola y deja **20 muestras al azar** en una carpeta del escritorio;
- espera el veredicto de la persona;
- **nunca escribe en MongoDB, el cubo, el lago ni Supabase.**

## Paso 1 · Actualizar e indexar el canon v5

```bash
git pull
```

```bash
python -m pip install pymongo pyyaml
```

```bash
python -m indexador.indexar canon/canon.yml
```

El canon v5 agrega los errores conocidos (E1–E6) y la base oficial. La consola usa `--criterios`, que los incluye en las instrucciones. Se espera que la indexación actualice `ia/criterios`, `amatista/base` y `amatista/direccion`.

## Paso 2 · Verificar

```bash
python -m laboratorio.verificar
```

```bash
python -m pytest -q pruebas
```

Deben pasar las 53 pruebas, y `.env` debe tener `MONGO_URI_LECTURA`, `SUPABASE_URL` y `SUPABASE_PUBLISHABLE_KEY`. **No abras `.env` ni muestres su contenido**; si falta algo, avísale a la persona.

## Paso 3 · El botón

```bash
python -m consola instalar-acceso
```

Crea **`Iniciar Amatista IA.bat`** en el escritorio. Con doble clic:
- arranca el trabajo;
- muestra la consola en vivo: qué documento revisa, cómo va el lote, la velocidad, cuánto falta para el cierre, los lotes que esperan veredicto, el freno y el último error.

Ctrl+C la detiene. Lo revisado se conserva y se retoma al volver a iniciar.

## Paso 4 · Que trabaje 24/7

Pide permiso a la persona antes de cambiar la configuración de Windows. Los dos cambios son:

1. **No suspender la computadora** cuando está conectada:

   ```powershell
   powercfg /change standby-timeout-ac 0
   ```

2. **Arrancar la consola al iniciar sesión**, con el Programador de tareas:

   ```powershell
   schtasks /create /tn "Amatista IA" /tr "\"%USERPROFILE%\Desktop\Iniciar Amatista IA.bat\"" /sc onlogon /rl limited
   ```

   Si el escritorio está en OneDrive, usa la ruta que imprimió el paso 3.

Ollama ya arranca con Windows.

## Paso 5 · El primer lote (la prueba real)

Doble clic en el botón. Con `--criterios`, cada documento tarda unos 2 minutos, así que **el primer lote de 100 tarda unas 3–4 horas**.

**Al cerrarse,** aparece en el escritorio la carpeta **`Amatista IA · cierres\lote_001\`** con:

| Archivo | Para qué |
|---|---|
| `muestras.html` | Las 20 muestras, legibles: título, enlace, decisión de la IA, motivo, cita y extracto |
| `planilla.csv` | Donde la persona escribe su decisión (`humano_decision`: aceptar, revision o rechazar) |
| `para_segunda_opinion.md` | Las mismas muestras en texto, para que la persona se las pase al asistente. Son documentos de fuentes públicas |
| `LEEME.txt` | Los pasos |

La muestra trae unas 14 de lo que la IA aceptó y 6 de lo que no aceptó. Mientras la persona revisa, la consola sigue con el lote 2 en cuarentena. Si 2 lotes esperan veredicto, se pausa sola.

## Paso 6 · El veredicto (lo hace la persona)

Después de marcar la planilla:

```bash
python -m consola veredicto 1
```

| Bien de 20 | Resultado |
|---|---|
| 19–20 | Aprobado |
| 17–18 | Aprobado con aviso |
| 16 o menos | No aprobado |

**Dos lotes no aprobados seguidos ponen el freno.** La consola deja de trabajar hasta que alguien lo quite, después de corregir lo que falló:

```bash
python -m consola quitar-freno "motivo"
```

## Paso 7 · Qué subir al repositorio

Al cerrarse cada lote, y después de cada veredicto, sube solo el resumen en `revisor/RESULTADOS_PRUEBA.md`:
- conteos de decisiones;
- velocidad;
- resultado del veredicto.

Copia lo que muestra `python -m consola estado`. **No subas** `salidas/`, la carpeta de cierres ni ningún texto de los documentos.

## Lo que no se hace

- No cambiar `consola/config.yml` a mitad de un lote. Un cambio se decide antes del lote siguiente y se anota.
- No escribir en MongoDB, el cubo ni el lago. Promover lo aprobado es otro paso, que se construye después.
- No mandar documentos a ningún servicio en la nube. Solo la persona decide pasarle las muestras al asistente.
