# Laboratorio Aislado: Gemini API (Baja Frecuencia) + Relevo Telemetría VM Oracle

Entorno aislado en `scratch/lab-limites-gemini` que agrupa dos herramientas auxiliares de potencia controlada sin tocar el código ni las colecciones protegidas de `amatista-ia`:

1. **`banco_limites.py`:** auditor secundario de **baja frecuencia (`--modo ciclo-24h`)** conectado en **solo lectura** al Canon v5 vivo de Supabase y a las fuentes públicas abiertas de `conocimiento_3d.documentos` en MongoDB Atlas Flex.
2. **`vm_telemetria/`:** motor multinúcleo sin estado para la **VM de Oracle (`158.101.118.222`)** y su relevo automático hacia GitHub (`rama telemetria-vm-24h`).

---

## 1. Auditor de baja frecuencia con Gemini API (`banco_limites.py`)

- **Qué revisa:** únicamente fuentes públicas abiertas (`blender-manual`, `blender-compositor-45`, `blender-stackexchange*`, `computergraphics-stackexchange*`, `stackoverflow-*`, `gamedev-stackexchange`, `arxiv-cs-gr`), intercaladas en round-robin y priorizando los documentos más largos (envía hasta `1,800` palabras por documento).
- **Sin cruce con el auditor local:** antes de cada tanda lee `../amatista-ia/salidas/consola/lote_*.jsonl` y sus propios `lote_api_*.jsonl` para nunca repetir un `doc_id`. A su vez, `amatista-ia` excluye esta carpeta mediante `excluir_carpetas`.
- **Cascada ante límites `429`:** intenta `gemini-3.5-flash` → `gemini-3.5-flash-lite` → `gemini-3.1-flash-lite`, con pausa de `24–30 s` entre documentos (~2–2.5 RPM).

```powershell
cd C:\Users\KANEDA\.gemini\antigravity\scratch\lab-limites-gemini
$py = "C:\Users\KANEDA\.gemini\antigravity\scratch\amatista-ia\.venv\Scripts\python.exe"

# Ping rápido y pruebas unitarias sin gastar cuota
& $py -m pytest -q test_banco_limites.py
& $py banco_limites.py --modo ping

# Consultar al Canon v5 vivo de Supabase
& $py banco_limites.py --modo preguntar --pregunta "¿Cuándo se aprueba un lote?"

# Ciclo desatendido de baja frecuencia (lotes de 40 docs sin pausa)
& $py banco_limites.py --modo ciclo-24h --modelo gemini-3.5-flash --horas 24 --tamano-lote 40 --pausa-ms 30000
```

Estado y salidas en `resultados/ciclo_24h/estado_ciclo_24h.json` y `lote_api_NNN.jsonl`.

---

## 2. Motor multinúcleo en RAM de la VM Oracle y relevo a GitHub (`vm_telemetria/`)

- **`recolector_vm_24h.py` (corre en la VM como `g7b-telemetria-24h.service`):**
  - Trabaja **100 % en RAM (`/dev/shm`, tmpfs de 8.3 GB)** usando los **3 núcleos ARM64 (`ProcessPoolExecutor`)** para procesar hasta **50,000 benchmarks (~150,000 mediciones)** por lote en ~50–58 segundos.
  - Normaliza cada equipo con el estándar `g7b.hardware/1` (`N0–N4`) y genera al vuelo tanto el `.jsonl.gz` de mediciones como la matriz agregada `.matriz.json.gz` (percentiles `p25 / mediana / p75 / p90` por GPU × backend × versión × escena).
  - **Contrapresión y cero retención:** si hay `>= 4` lotes esperando en `/tmp/g7b-bandeja-salida`, borra el ZIP de `/dev/shm` y espera a que el relevo vacíe la bandeja.
- **`relevo_github_24h.py` (corre en PC local):**
  - Vigila `/tmp/g7b-bandeja-salida` por SSH, descarga cada lote a `../puente-telemetria-vm` (rama huérfana `telemetria-vm-24h` con `[skip ci]`), comprueba los hashes `SHA-256`, hace `git push` a GitHub y ejecuta de inmediato `rm -f` en la VM para dejar **0 bytes retenidos en la instancia de Oracle**.

```powershell
# Vaciar una vez la bandeja de la VM hacia GitHub o dejar el relevo continuo
& $py vm_telemetria\relevo_github_24h.py --una-vez
& $py vm_telemetria\relevo_github_24h.py --horas 24 --intervalo-s 15
```
