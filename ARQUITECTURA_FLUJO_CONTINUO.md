# Arquitectura del Flujo Continuo y Separación de Colas (Amatista IA)

Este documento explica cómo opera la consola local de **Amatista IA** dentro de la estructura distribuida de 24 horas junto con G7B, MongoDB Atlas Flex, Supabase y el banco aislado de Gemini API.

---

## 1. Reglas de oro que nunca cambian

1. **Una sola fuente del Canon (`Supabase`):** tanto el revisor local (`qwen3:8b` + `bge-m3`) como el banco externo leen el Canon v5 usando únicamente `SUPABASE_PUBLISHABLE_KEY` (solo lectura).
2. **`conocimiento_3d.documentos` no se toca desde Amatista IA:** la consola lee `documentos` con `MONGO_URI_LECTURA` (usuario de solo lectura). Lo único que Amatista IA escribe en MongoDB es `conocimiento_3d.conocimiento_auditado` mediante `python -m consola promover` (`MONGO_URI_PROMOCION`), solo para lotes con veredicto humano aprobatorio.
3. **Muro de privacidad:** cero datos de alumnos o telemetría personal salen de la infraestructura autorizada. El banco de Gemini API únicamente lee fuentes públicas con licencia abierta verificada (`CC0`, `CC-BY`, `CC-BY-SA`).

---

## 2. Lotes continuos sin bloqueo humano (`max_lotes_esperando: 50`)

En `consola/config.yml`:
- `tamano_lote: 100`: al llegar a 100 documentos evaluados, la consola genera automáticamente la carpeta de cierre en el Escritorio (`Amatista IA · cierres/lote_NNN`) con `muestras.html` y `planilla.csv` (20 muestras estratificadas: ~14 aceptadas y ~6 retenidas/descartadas).
- `max_lotes_esperando: 50`: permite que la consola **abra y procese de inmediato el lote siguiente (`N+1`) sin detenerse** aunque haya varios lotes cerrados esperando revisión humana.
- `espera_s: 120`: cuando agota la cola actual, vuelve a consultar MongoDB cada 2 minutos para absorber los lotes nuevos que publica `Ciclo G7B`.
- **Calificación con pureza separada (`Consola.resumen_calificacion`):** al correr `python -m consola veredicto N`, además del conteo global sobre 20 muestras, reporta por separado cuántos **aceptados fueron buenos** (pureza en la puerta) y cuántos **buenos quedaron retenidos** en `revision`/`persona` (falsas alarmas que no contaminan `conocimiento_auditado`).

---

## 3. Blindaje anti-cruce entre Auditor Local y Gemini API

Para garantizar que el modelo local (`qwen3:8b`) y el demonio de baja frecuencia de Gemini API **nunca revisen los mismos documentos**:

1. **Exclusión desde la consola local (`consola/config.yml` → `excluir_carpetas`):**
   - `Trabajo.excluidos_externos()` en `consola/__main__.py` lee todos los `doc_id` presentes en `../lab-limites-gemini/resultados/ciclo_24h/*.jsonl` y los une a `self.c.revisados()`.
2. **Exclusión recíproca desde Gemini API (`banco_limites.py`):**
   - En cada recarga de cola, `cargar_ya_vistos()` lee todos los `doc_id` de `amatista-ia/salidas/consola/lote_*.jsonl` y los descarta antes de pedir documentos.
3. **Orden de recorrido opuesto:**
   - **Local (`qwen3:8b`):** recorre `doc_id` en orden ascendente (`sort('doc_id', 1)`), ideal para flujo constante de foros y páginas medianas (extracto de 450 palabras).
   - **Gemini API (`ciclo-24h`):** ordena en round-robin por fuente priorizando los **documentos más extensos** (hasta 1,800 palabras enviadas por documento), a baja frecuencia (`24–30 s` de pausa ≈ 2–2.5 RPM).

---

## 4. Comandos habituales de operación

```powershell
cd C:\Users\KANEDA\.gemini\antigravity\scratch\amatista-ia

# Ver foto en vivo del lote actual, velocidad y pendientes en MongoDB
.\.venv\Scripts\python.exe -m consola estado

# Registrar el veredicto de una planilla ya marcada en el Escritorio
.\.venv\Scripts\python.exe -m consola veredicto 2

# Simular o ejecutar la promoción a conocimiento_auditado en MongoDB Atlas
.\.venv\Scripts\python.exe -m consola promover --simular
.\.venv\Scripts\python.exe -m consola promover

# Generar las listas por estado (aprobado, en_cuarentena, por_revisar, descartado)
.\.venv\Scripts\python.exe -m consola registro
```
