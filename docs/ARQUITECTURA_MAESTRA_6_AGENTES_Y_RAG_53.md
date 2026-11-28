# Arquitectura Maestra Amatista IA + G7B: Qué tenemos, qué planteamos, cómo y por qué

**Última actualización:** 2026-11-28

Este documento consolida la arquitectura distribuida de **Amatista IA** y **G7B** para construir, auditar y mantener un **Núcleo RAG especializado en Blender 5.3 y gráficos 3D en tiempo real**, operando 24/7 con hardware modesto, licencias verificadas y cero alucinaciones de APIs obsoletas.

---

## 1. Qué planteamos (La tesis central)

Los modelos locales pequeños (`8B`, como `qwen3:8b`) fallan al generar escenas o código de Blender por tres razones concretas:
1. **Obsolescencia de API (`2.79 / 3.x / 4.x` vs `5.3`):** inventan propiedades eliminadas (`use_auto_smooth`, `Musgrave`, `action.fcurves`, `use_bloom`).
2. **Ceguera espacial:** no ven dónde terminan las paredes ni las cajas delimitadoras de los objetos, provocando colisiones o personajes atravesando mallas.
3. **Pérdida de continuidad entre tomas:** sin estado persistente ni editor NLA, sobrescriben animaciones o hacen desaparecer actores entre escenas.

**Nuestra solución:** en lugar de depender de un modelo gigante de pago o inferir videos costosos, armamos una **fábrica distribuida de 6 agentes** (4 nubes gratuitas/existentes + disco local `D:\`) que cosecha documentación viva, decompila escenas reales `.blend` `CC0` y repos `GPL/MIT`, traduce todo a **Blender 5.3 (Piedra Rosetta)** y usa modelos **Maestro** (Google AI Studio en rotación) para destilar **recetas técnicas ejecutables** que consumirá el **Estudiante `8B` local**.

---

## 2. Qué tenemos hoy (Estado operativo verificado)

| Componente | Dónde vive | Qué aporta hoy |
| :--- | :--- | :--- |
| **Núcleo RAG Local (`D:\`)** | `D:\Amatista_Nucleo_RAG\indices\nucleo_conocimiento.sqlite` | **`5,323+` documentos curados**, **`22,036+` fragmentos `FTS5`** (BM25 + vectorial), **`524+` recetas `5.3`** destiladas por Gemini, **`78` escenas `.blend` decompiladas** (`4,735` enlaces `socket → socket` en `decompilaciones_blend.parquet`) y **`241` algoritmos AST** (`GPLv3/MIT`). |
| **Piedra Rosetta 5.3** | `amatista-nucleo-blender/nucleo_rag/piedra_rosetta_53.py` | Diccionario con `24,700` símbolos vigentes de Blender 5.3, `3,298` eliminados y 14 reglas de migración automática (`Smooth by Angle`, `Principled BSDF v2`, `Slotted Actions`, `EEVEE Raytracing`, `gpu`). |
| **Búsqueda Híbrida en la Nube** | MongoDB Atlas `Cluster1` (`conocimiento_3d.conocimiento_auditado`) | `1,182` documentos auditados con **`vec_auditado`** (`autoEmbed` `voyage-4-lite`) + **`busqueda_auditado`** (`lucene.standard` + `autocomplete` + sinónimos `equivalencias_3d`) fusionados con **`$rankFusion`**. |
| **Base Telemetría Geoda (aislada)** | `amatista-g7b-etl#telemetria-vm-24h` | **`351,141` benchmarks** históricos de Blender Open Data (`2022-03` → `2026-11-27`) en `23` lotes comprimidos (`104.5 MB` `.gz`), completamente separados del RAG documental. |
| **Backend Producción Amatista** | Oracle VM (`158.101.118.222`) · `api.amatista-3dt.tech` | `amatista-api` (`a19b46e`) + `amatista-motor` (`45ee7ec`), **`536` pruebas en verde**, Oracle 23ai (`31` tablas, `0.2 %` de 20 GB). |

---

## 3. Los 6 Agentes: Qué hacemos, cómo y por qué

### Agente 1 — Cosechador Documental 5.3 en RAM (`recolector_vm_24h.py` en VM Oracle)
- **Qué hace:** extrae cada `120 s` páginas nuevas del **Manual Oficial de Blender 5.3** (`objects.inv`, `2,077` docs), **Referencia API Python 5.3** (`objects.inv`, `2,216` módulos), **Release Notes 4.0–5.3** (`140/140` ya completadas) y 5 redes de **Stack Exchange** (`blender`, `stackoverflow [blender/three.js/gltf]`, `computergraphics`, `gamedev`).
- **Cómo lo hace:** corre en `/dev/shm` (RAM de la VM ARM64) con prioridad baja (`nice -n 15`) y carga `5,026+` URLs existentes en `D:\` para **cero duplicados**.
- **Por qué lo hacemos así:** la VM tiene IP fija y ancho de banda 24/7 sin gastar CPU de la PC local ni tocar la base Oracle ni afectar `uvicorn` (`0.1 %` CPU). Todo se borra de la VM tras verificar `SHA-256`.

### Agente 2 — Radar Geodar + Arañas Zyte (`amatista-g7b-etl` + GitHub Actions → Azure)
- **Qué hace:** vigila `27` sensores oficiales (`blender-manual` con soporte `5.3`, `blender-notas-version`, `arxiv-cs-gr`, feeds RSS y `caniuse-web3d`) y dispara arañas en Zyte Scrapy Cloud (`blender_docs` / `paginas`).
- **Cómo lo hace:** lee inventarios `objects.inv` y cabeceras `ETag`/`Last-Modified` en GitHub Actions; si hay cambios, extrae solo el `<article>` principal (sin sidebars de MkDocs/Sphinx) y deposita crudos con licencia verificada en Azure `bronce`.
- **Por qué lo hacemos así:** mantiene trazabilidad legal (`CC-BY-SA-4.0`, `CC0`, `MIT`, `GPLv3`) y evita re-rastrear manuales completos sin cambios.

### Agente 3 — Aduanero Local + Piedra Rosetta 5.3 (`relevo_github_24h.py` + `agente_curador.py`)
- **Qué hace:** cada `60 s` recoge por SSH/SCP los lotes emitidos por la VM, valida `SHA-256`, filtra ruido con el curador, aplica la **Piedra Rosetta 5.3**, fragmenta por secciones y actualiza `SQLite WAL + FTS5` en `D:\` (y elimina el archivo remoto).
- **Por qué lo hacemos así:** separa estrictamente **telemetría de hardware** (rama GitHub `telemetria-vm-24h`) de **conocimiento documental** (`D:\`), garantizando cero contaminación de datos y cero uso de GPU local.

### Agente 4 — Destilador Maestro Multi-Pool (`banco_limites.py` en Google AI Studio)
- **Qué hace:** toma documentos nuevos de `D:\` sin receta (priorizando lo recién llegado de la VM) y genera síntesis originales en español (`receta_53`: *Problema → Herramienta/Nodo/API en Blender 5.3 → Parámetros clave*, peso `1.35`).
- **Cómo lo hace:**
  - **Rotación de 4 cubetas independientes:** `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite-preview`, `gemini-3-flash-preview` y `gemma-4-31b-it` (con enfriamiento individual si alguno devuelve `429`/`503`).
  - **Empaquetado `×8` documentos por llamada:** en lugar de mandar 1 doc por petición (desperdiciando el techo diario `RPD`), empaca `8` docs (`~11.5k` tokens entrada, `~5.5 s` por paquete = **`0.69 s/doc`**), multiplicando por `8×` la capacidad diaria gratuita.
- **Por qué lo hacemos así:** el cuello de botella de la capa gratuita es `RPD` (peticiones/día), no `TPM` (tokens/minuto). Empacar ×8 y rotar 4 pools lleva la destilación a **`~1,000+` docs/hora** sin costo ni carga en GPU local.

### Agente 5 — Ingeniero Inverso 3D (`decompilador_blend_53.py` + `extractor_repos_bpy.py`)
- **Qué hace:** por tandas en Blender 5.3 Headless (`entorno_aislado()`), decompila escenas `.blend` `CC0` (Poly Haven) y analiza AST de extensiones `GPLv3/MIT` para extraer grafos reales (`socket → socket`), materiales y funciones `bmesh`/`bpy`.
- **Por qué lo hacemos así:** el manual explica nodos sueltos, pero las escenas reales muestran **cómo se conectan entre sí** en producción.

### Agente 6 — Indexador Híbrido Cloud (MongoDB Atlas `Cluster1` + Voyage AI)
- **Qué hace:** combina búsqueda vectorial multilingüe automática (`vec_auditado` con `voyage-4-lite`) y búsqueda léxica + autocompletado + sinónimos 3D (`busqueda_auditado` + `sinonimos_3d`) mediante **`$rankFusion`** nativo en `MongoDB 8.0.39`.
- **Por qué lo hacemos así:** `Cluster1` genera los embeddings en el servidor al insertar o consultar (`autoEmbed`), evitando consumir RAM/CPU de la VM de Oracle o del PC local.

---

## 4. Siguiente evolución planificada (Del RAG textual al Agente 3D espacial)

A partir del análisis técnico de pipelines RAG para Blender + modelos `8B`:
1. **Radiografía Espacial Viva (`BVHTree` + `bound_box`):** pasarle al modelo `8B` un JSON con las cajas delimitadoras reales en espacio mundial y validar intersecciones con `mathutils.bvhtree.BVHTree.overlap` + `scene.ray_cast()` para eliminar objetos atravesando muros o pisos.
2. **Biblia de Escena Persistente + NLA 5.3:** mantener un inventario estricto (`estado_mundo.json`), exportar poses de anclaje entre tomas, encapsular acciones en tiras **NLA** y pasar un validador AST pre-ejecución antes de correr cualquier script en Blender.
3. **Principios de optimización AAA abiertos:** recetas RAG para separar malla visual vs. colisión (`_bounds`) y escaleras de 4 LODs exportables a `glTF` / Web3D (`Geoda`), con renderizado final 100 % local en Cycles/EEVEE (sin artefactos ni marcas `C2PA` de video generativo).
