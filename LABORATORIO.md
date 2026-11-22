# Instalación en la computadora del laboratorio

Guía para el agente de IA, o la persona, que prepara la computadora donde va a vivir la IA de Amatista. Al final:
- Ollama corre con el modelo de embeddings `bge-m3`;
- el canon está indexado en Supabase;
- hay una medición de qué tan bien recupera.

**Antes de empezar, lee [`AGENTS.md`](AGENTS.md).** Tiene las reglas que no se rompen: claves, datos y qué no tocar.

Cada paso dice cómo comprobar que salió bien. **Si una comprobación falla, detente y repórtalo con la salida exacta.** No improvises un arreglo que cambie el diseño.

## La computadora

| Pieza | Valor | Qué implica |
|---|---|---|
| Procesador | Intel Core i3-10100 (4 núcleos, 8 hilos, AVX2) | Todo corre en CPU |
| Memoria | 40 GB DDR4 (3 × 8 GB + 1 × 16 GB) | Sobra para `bge-m3` (≈ 1.2 GB) y un modelo de 8B en Q4 (≈ 5 GB) |
| Gráfica | Integrada | Ollama no la usa: no instales controladores ni CUDA |
| Disco | SSD de 256 GB y disco duro de 500 GB | **Modelos en el SSD:** cargan mucho más rápido que desde el disco duro |

## Paso 0 · Lo que hace una persona antes (no el agente)

1. **La migración de Supabase debe estar aplicada.** Hay dos caminos:
   - fusionar este repositorio a `main` con la integración de GitHub de Supabase activa;
   - pegar [`supabase/migrations/20261122000000_canon_rag.sql`](supabase/migrations/20261122000000_canon_rag.sql) en el editor SQL del proyecto.

   El agente no aplica migraciones: la API REST no puede y la clave secreta no es para eso.
2. **Las claves las escribe la persona** en el archivo `.env` de esta computadora (paso 5). Nunca se pegan en un chat con el agente.

## Paso 1 · Python y Git

Python 3.10 o más reciente y Git.

- **Windows** (PowerShell):

  ```powershell
  winget install -e --id Python.Python.3.12
  ```

  ```powershell
  winget install -e --id Git.Git
  ```

  Cierra y abre la terminal después de instalar.
- **Linux (Debian/Ubuntu):**

  ```bash
  sudo apt-get install -y python3 python3-venv git
  ```

Comprueba con `python --version` (en Linux, `python3 --version`) y con `git --version`.

## Paso 2 · Ollama

- **Windows:** descarga el instalador de <https://ollama.com/download>, o usa:

  ```powershell
  winget install -e --id Ollama.Ollama
  ```

  Ollama queda como aplicación en la bandeja y arranca con Windows.
- **Linux:** el script instala Ollama y lo deja como servicio.

  ```bash
  curl -fsSL https://ollama.com/install.sh | sh
  ```

**Dónde se guardan los modelos.** Por omisión, en la carpeta del usuario (`%USERPROFILE%\.ollama\models` en Windows, `/usr/share/ollama/.ollama/models` en Linux). Si esa carpeta está en el disco duro y no en el SSD, define `OLLAMA_MODELS` con una carpeta del SSD **antes** de descargar el modelo y reinicia Ollama.
- En Windows, como variable de entorno del usuario.
- En Linux, con `sudo systemctl edit ollama` y estas líneas; luego `sudo systemctl restart ollama`:

  ```ini
  [Service]
  Environment="OLLAMA_MODELS=/ruta/en/el/ssd"
  ```

**No expongas Ollama a la red.** Déjalo en `127.0.0.1:11434`, que es lo predeterminado. No definas `OLLAMA_HOST=0.0.0.0`.

Comprueba con `ollama --version` y con `ollama list`. La lista vacía está bien.

## Paso 3 · El modelo de embeddings

```bash
ollama pull bge-m3
```

Comprueba que `ollama list` muestre `bge-m3:latest`. Usa ese modelo, no otro: la base espera vectores de 1024 dimensiones y el modelo queda registrado con su digest en cada fragmento.

## Paso 4 · El repositorio

```bash
git clone https://github.com/Maximiliano-cabello-mata/AMATISTA-IA-.git amatista-ia
```

```bash
cd amatista-ia
```

Si el repositorio todavía no tiene `main`, usa la rama de trabajo:

```bash
git checkout claude/determined-wright-x8ba42
```

Crea un entorno virtual e instala la única dependencia.

- **Windows:**

  ```powershell
  python -m venv .venv
  ```

  ```powershell
  .venv\Scripts\Activate.ps1
  ```

- **Linux:**

  ```bash
  python3 -m venv .venv
  ```

  ```bash
  source .venv/bin/activate
  ```

Después, en los dos:

```bash
python -m pip install pyyaml
```

## Paso 5 · Conectar con Supabase

Copia la plantilla. En Windows es `Copy-Item .env.ejemplo .env`; en Linux:

```bash
cp .env.ejemplo .env
```

**La persona** abre `.env` y escribe:
- `SUPABASE_URL`: la URL del proyecto (`https://<proyecto>.supabase.co`);
- `SUPABASE_PUBLISHABLE_KEY`: la clave publicable (`sb_publishable_…`), que solo lee;
- `SUPABASE_SECRET_KEY`: la clave secreta (`sb_secret_…`), que escribe. Está en Supabase → Project Settings → API Keys.
- `GITHUB_TOKEN`: un token de **solo lectura**.
  - Para qué: 2 de los 13 documentos del canon viven en `amatista-recuperada-20261106`, que es **privado**. Sin token, GitHub responde 404. Los 11 de G7B son públicos y no lo necesitan.
  - Cómo crearlo: en GitHub → Settings → Developer settings → Fine-grained tokens.
  - Alcance: solo ese repositorio, permiso **Contents: Read-only** y fecha de vencimiento.
  - Alternativa: clonar los dos repositorios y usar `--local` (paso 7).

`.env` está en `.gitignore` y nunca se sube. Los scripts lo leen solos. El agente no abre ni imprime este archivo, ni pide las claves por chat.

## Paso 6 · Verificar todo

```bash
python -m laboratorio.verificar
```

Debe terminar en **`LISTO para indexar.`** con todas las líneas en ✔. El script dice qué falta sin mostrar las claves:

| Mensaje | Qué hacer |
|---|---|
| `github_amatista … falta GITHUB_TOKEN` | La persona crea el token de solo lectura (paso 5) |
| `github_… el token no tiene acceso` | El token venció o no incluye ese repositorio |
| `ollama no responde` | Abre la aplicación de Ollama (Windows) o corre `sudo systemctl start ollama` (Linux) |
| `falta bge-m3` | Vuelve al paso 3 |
| `rechazó la clave (401)` | La persona revisa la clave en `.env` |
| `parece una clave secreta, no publicable` | Las dos claves están intercambiadas en `.env` |
| `la migración no está aplicada` | Paso 0: lo resuelve una persona |
| `sin conexión con Supabase` | Red, proxy o firewall de la escuela |

Si Supabase todavía no tiene documentos, `documentos del canon en la base: 0` es lo normal antes del paso 8.

## Paso 7 · Simulacro (no sube nada)

```bash
python -m indexador.indexar canon/canon.yml --simulacro
```

Se espera: `Canon v1: 13 documentos, 108 fragmentos`. Esto también prueba que el token de GitHub funciona.

Sin token, con clones locales en los commits fijados:

```bash
python -m indexador.indexar canon/canon.yml --simulacro --local g7b=../amatista-g7b-etl,amatista=../amatista-recuperada-20261106
```

Si usas `--local`, úsalo también en el paso 8. Los documentos se leen de GitHub en el commit fijado, así que el número no cambia mientras no cambie `canon/canon.yml`. Si da otro número, detente y repórtalo.

## Paso 8 · Indexar

```bash
python -m indexador.indexar canon/canon.yml
```

Se espera: `Listo: 13 documentos actualizados (108 fragmentos)`. En esta CPU, calcular 108 vectores debería tardar del orden de minutos, no horas. Anota cuánto tardó.

**Córrelo una segunda vez.** Debe decir `0 documentos actualizados … 13 sin cambios`. Eso prueba que es incremental.

## Paso 9 · Medir la recuperación

```bash
python -m evaluacion.evaluar evaluacion/preguntas.yml
```

```bash
python -m evaluacion.evaluar evaluacion/preguntas.yml --peso-vector 0 --salida salidas/evaluacion_texto.json
```

```bash
python -m evaluacion.evaluar evaluacion/preguntas.yml --peso-texto 0 --salida salidas/evaluacion_vector.json
```

El primero es el híbrido, que es el que se usará. Los otros dos sirven para comparar: solo texto y solo vectores.

- **El umbral es recall@3 ≥ 0.85.** La búsqueda solo de texto ya dio 0.89 en las pruebas.
- **Si el híbrido no supera al texto solo, se reporta así.** No se cambian las preguntas, los pesos ni el canon para que salga bien: esa decisión es de una persona.

## Paso 10 (opcional) · Velocidad de un modelo revisor

Solo si la persona lo pide. Todavía **no se elige** el modelo revisor: primero va el conjunto de prueba de 150–200 registros etiquetados a mano ([decisión de IA](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/blob/main/docs/investigacion/2026-11-17_decision_ia.md)). Esto solo mide qué tan rápido corre un candidato de unos 8B en esta CPU.

1. Busca el nombre exacto en <https://ollama.com/library>, por ejemplo `qwen3:8b` o `llama3.1:8b`.
2. Descárgalo; usa el nombre exacto del paso anterior:

   ```bash
   ollama pull qwen3:8b
   ```

3. Mide:

   ```bash
   python -m laboratorio.verificar --revisor qwen3:8b
   ```

La línea `revisor` da tokens por segundo al generar y al leer. La estimación previa para esta CPU, que **no está medida**, es de unos 4–7 tok/s al generar con un 8B en Q4. Reporta el número real.

## Qué entregar al terminar

A la persona:
- `salidas/verificacion_laboratorio.json`;
- `salidas/evaluacion.json`, `salidas/evaluacion_texto.json` y `salidas/evaluacion_vector.json`.

Ninguno contiene claves. Añade un resumen corto:
- versión de Ollama y digest de `bge-m3` (sale en la evaluación como `bge-m3@…`);
- cuánto tardó la indexación;
- recall@1, recall@3 y MRR de las tres búsquedas;
- las preguntas que fallaron;
- si se hizo, la velocidad del revisor.

`salidas/` no se sube al repositorio. Si los resultados se van a guardar, una persona decide cómo.
