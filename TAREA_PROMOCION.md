# Tarea: la puerta, lo aprobado entra a MongoDB (24 de noviembre de 2026)

**Para la persona y para el agente de IA de la computadora del laboratorio.** Responde en español. Haz primero [`TAREA_REGISTRO.md`](TAREA_REGISTRO.md). Antes de empezar, lee [`AGENTS.md`](AGENTS.md).

## Qué es

`python -m consola promover` copia los documentos **aprobados** a una colección nueva de MongoDB, `conocimiento_auditado`. Aprobado quiere decir que la IA los aceptó y que una persona aprobó su lote.
- **Qué se escribe:** cada documento original completo, más un bloque `auditoria` con su rastro.
- **Qué nunca hace:** escribir en `documentos` (es de G7B), duplicar lo que ya copió ni borrar.
- **Con el lote 1** se esperan unos **39 documentos**.

## Lo que hace la persona: el usuario de escritura

El agente no crea usuarios ni ve contraseñas.

1. En **MongoDB Atlas → Database Access → Add New Database User**, crea un usuario con contraseña.
2. En **Database User Privileges**, elige **Specific Privileges** y agrega un solo privilegio:
   - rol: `readWrite`;
   - base: `conocimiento_3d`;
   - colección: `conocimiento_auditado`.

   **Nada más.** No le des acceso a `documentos` ni a otras bases.
3. En el archivo `.env` de la computadora del laboratorio, agrega una línea con la cadena de conexión de ese usuario, igual que `MONGO_URI_LECTURA` pero con el usuario nuevo:

   ```text
   MONGO_URI_PROMOCION=mongodb+srv://<usuario>:<contraseña>@<cluster>/
   ```

4. Avísale al agente.

## Lo que hace el agente

**1. Actualizar y comprobar.** Deben pasar 72 pruebas o más:

```bash
git pull
```

```bash
python -m pytest -q pruebas
```

**2. Simular.** Usa solo el usuario de lectura y no escribe nada. Copia la salida:

```bash
python -m consola promover --simular
```

**3. Promover** (solo después del aviso de la persona). Si dice «Falta MONGO_URI_PROMOCION», detente y avísale a la persona: nunca escribas `.env` tú.

```bash
python -m consola promover
```

**4. Ver el estado.** Copia la salida:

```bash
python -m consola estado
```

**5. Reportar** en una sección nueva de `revisor/RESULTADOS_PRUEBA.md`, «Primera promoción», con la salida exacta de los pasos 2, 3 y 4 y cualquier error. Si Atlas rechaza la escritura (por ejemplo, «not authorized»), repórtalo tal cual: es el permiso del usuario, no el código.

**6. Subir:**

```bash
git add revisor/RESULTADOS_PRUEBA.md
```

```bash
git commit -m "ia(consola): primera promoción de lo aprobado a conocimiento_auditado"
```

```bash
git push
```

Desde ahora, cada vez que una persona apruebe un lote, se corre `python -m consola promover` para que lo aprobado entre.
