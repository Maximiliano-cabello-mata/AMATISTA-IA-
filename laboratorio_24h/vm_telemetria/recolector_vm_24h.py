"""Recolector documental en RAM (/dev/shm) para la VM de Oracle (Modo 100 % Documentación 5.3).

Opera con cero llaves de bases de datos en la VM y cero retención permanente:
1. **Modo por defecto (100 % Documentación 3D y Blender 5.3 -> Núcleo RAG en D:\\):**
   Recolecta de forma continua y deduplicada en ``/dev/shm`` desde fuentes abiertas verificadas:
   - **Manual Oficial de Blender 5.3** (``docs.blender.org/manual/en/latest/objects.inv``, ``CC-BY-SA-4.0``).
   - **Referencia Oficial de API Python 5.3** (``docs.blender.org/api/current/objects.inv``, ``GPL-3.0-or-later``).
   - **Notas de Versión Oficiales 4.0 -> 5.3** (``developer.blender.org/docs/release_notes/``, ``CC-BY-SA-4.0``).
   - **Q&A Técnico Verificado Stack Exchange** (``blender``, ``stackoverflow [blender/web3d]``,
     ``computergraphics``, ``gamedev``, ``CC-BY-SA-4.0``).
   Emite lotes ``lote_vm_NNNN_documentacion_53.jsonl.gz`` firmados con ``SHA-256`` hacia ``/tmp/g7b-bandeja-salida``.
2. **Carril Telemetría (desactivado por defecto; activable solo con ``--incluir-telemetria``):**
   Conservado únicamente para uso futuro bajo demanda.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import gzip
import hashlib
import html
import json
import os
import re
import shutil
import statistics
import sys
import time
import zlib
from collections import Counter, defaultdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from uuid import UUID

import requests

RAIZ_G7B = Path("/home/opc/g7b-telemetria-vm/amatista-g7b-etl")
sys.path.insert(0, str(RAIZ_G7B))

ESTADO_DIR = Path("/home/opc/g7b-telemetria-vm/estado")
BANDEJA = Path("/tmp/g7b-bandeja-salida")
SHM_BASE = Path("/dev/shm") if Path("/dev/shm").is_dir() else Path("/tmp")
TRABAJO = SHM_BASE / "g7b-work"
ZIP_RAM = SHM_BASE / "g7b-opendata-ram.zip"
CACHE_INV_SHM = SHM_BASE / "g7b-sphinx-inv"
RUTA_URLS_SEMILLA_GZ = ESTADO_DIR / "urls_existentes_d.txt.gz"
RUTA_URLS_EMITIDAS = ESTADO_DIR / "urls_emitidas_vm.txt"

HEADERS_HTTP = {"User-Agent": "Amatista-G7B-OracleVM/2.2 (+https://amatista-3dt.tech)"}

FUENTES_SE_DOCUMENTAL = (
    {"id": "blender-stackexchange", "site": "blender", "tagged": "", "min_score": 3},
    {"id": "stackoverflow-blender", "site": "stackoverflow", "tagged": "blender", "min_score": 3},
    {"id": "stackoverflow-web3d", "site": "stackoverflow", "tagged": "three.js", "min_score": 4},
    {"id": "stackoverflow-web3d", "site": "stackoverflow", "tagged": "gltf", "min_score": 3},
    {"id": "computergraphics-stackexchange", "site": "computergraphics", "tagged": "", "min_score": 3},
    {"id": "gamedev-stackexchange", "site": "gamedev", "tagged": "blender", "min_score": 3},
)

PRIORIDAD_MANUAL_53 = (
    "modeling/geometry_nodes/",
    "render/shader_nodes/",
    "render/cycles/",
    "render/eevee/",
    "compositing/",
    "modeling/modifiers/",
    "modeling/meshes/",
    "sculpt_paint/",
    "grease_pencil/",
    "animation/",
    "physics/",
    "files/import_export/",
    "advanced/",
    "render/",
    "modeling/",
    "scene_layout/",
    "editors/",
    "troubleshooting/",
)

PRIORIDAD_API_53 = (
    "info_quickstart",
    "info_overview",
    "info_api_reference",
    "info_best_practice",
    "info_gotcha",
    "bmesh.",
    "mathutils",
    "gpu.",
    "bpy.context",
    "bpy.data",
    "bpy.ops.mesh",
    "bpy.ops.object",
    "bpy.ops.node",
    "bpy.ops.uv",
    "bpy.ops.curve",
    "bpy.ops.sculpt",
    "bpy.ops.render",
    "bpy.ops.anim",
    "bpy.ops.wm",
    "bpy.ops.import_scene",
    "bpy.ops.export_scene",
    "bpy.types.GeometryNode",
    "bpy.types.ShaderNode",
    "bpy.types.CompositorNode",
    "bpy.types.FunctionNode",
    "bpy.types.Node",
    "bpy.types.Mesh",
    "bpy.types.Object",
    "bpy.types.Material",
    "bpy.types.Modifier",
    "bpy.types.Action",
    "bpy.types.Scene",
    "bpy_extras.",
)

PAGINAS_RELEASE_NOTES_53 = [
    (ver, sec)
    for ver in ("5.3", "5.2", "5.1", "5.0", "4.5", "4.4", "4.3", "4.2", "4.1", "4.0")
    for sec in (
        "geometry_nodes",
        "shading",
        "eevee",
        "cycles",
        "modeling",
        "sculpt",
        "grease_pencil",
        "animation_rigging",
        "python_api",
        "compositor",
        "pipeline_assets_io",
        "import_export",
        "add_ons",
        "core",
    )
]


class _HTMLATexto(HTMLParser):
    """Convierte HTML de Sphinx (Furo), Stack Exchange y Release Notes a Markdown técnico limpio."""

    _VOID_TAGS = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"})

    def __init__(self) -> None:
        super().__init__()
        self.partes: list[str] = []
        self._en_pre = False
        self._en_code = False
        self._en_dt = False
        self._pila_ignorar: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        if t in self._VOID_TAGS:
            if not self._pila_ignorar and t == "br":
                self.partes.append("\n")
            return
        if self._pila_ignorar:
            self._pila_ignorar.append(t)
            return
        clases = dict(attrs).get("class") or ""
        if t in ("script", "style", "nav", "header", "footer", "svg", "button") or "headerlink" in clases:
            self._pila_ignorar.append(t)
            return
        if t == "pre":
            self._en_pre = True
            self.partes.append("\n\n```python\n")
        elif t == "code" and not self._en_pre:
            self._en_code = True
            self.partes.append("`")
        elif t == "dt":
            self._en_dt = True
            self.partes.append("\n\n### ")
        elif t == "dd":
            self.partes.append("\n")
        elif t in ("p", "div", "section", "article", "tr"):
            self.partes.append("\n\n")
        elif t in ("td", "th"):
            self.partes.append(" | ")
        elif t == "li":
            self.partes.append("\n- ")
        elif t in ("h1", "h2", "h3", "h4"):
            self.partes.append("\n\n" + ("#" * int(t[1])) + " ")

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if self._pila_ignorar:
            if t in self._pila_ignorar:
                while self._pila_ignorar:
                    sacado = self._pila_ignorar.pop()
                    if sacado == t:
                        break
            return
        if t == "pre":
            self._en_pre = False
            self.partes.append("\n```\n\n")
        elif t == "code" and self._en_code:
            self._en_code = False
            self.partes.append("`")
        elif t == "dt" and self._en_dt:
            self._en_dt = False
            self.partes.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._pila_ignorar:
            self.partes.append(data)

    def obtener_markdown(self) -> str:
        bruto = html.unescape("".join(self.partes)).replace("¶", "").replace("#\n", "\n")
        bruto = re.sub(r"[ \t]+\n", "\n", bruto)
        bruto = re.sub(r"\n{3,}", "\n\n", bruto)
        return bruto.strip()


def html_a_md_limpio(fragmento_html: str) -> str:
    p = _HTMLATexto()
    p.feed(fragmento_html or "")
    return p.obtener_markdown()


def extraer_articulo_principal(html_completo: str) -> tuple[str, str]:
    """Extrae título limpio y cuerpo exclusivo del <article> principal en O(N) sin backtracking."""
    i_t1 = html_completo.find("<title")
    titulo = ""
    if i_t1 != -1:
        i_t_gt = html_completo.find(">", i_t1)
        i_t2 = html_completo.find("</title>", i_t_gt)
        if i_t_gt != -1 and i_t2 != -1:
            titulo = html.unescape(html_completo[i_t_gt + 1 : i_t2]).strip()
            titulo = re.sub(r"\s*[—\-|]\s*Blender.*$", "", titulo).strip()

    lower_html = html_completo.lower()
    idx_art = lower_html.find('id="furo-main-content"')
    if idx_art != -1:
        idx_open = lower_html.rfind("<article", 0, idx_art)
    else:
        idx_open = lower_html.find("<article")
    if idx_open != -1:
        idx_gt = html_completo.find(">", idx_open)
        idx_close = lower_html.find("</article>", idx_gt)
        if idx_gt != -1 and idx_close != -1:
            return titulo, html_a_md_limpio(html_completo[idx_gt + 1 : idx_close])

    return titulo, html_a_md_limpio(html_completo[:120000])


def ahora_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def guardar_json_atomico(ruta: Path, datos: dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(".tmp")
    tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, ruta)


def sha256_archivo(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        while bloque := f.read(1024 * 1024):
            h.update(bloque)
    return h.hexdigest()


def comprimir_lineas_bytes(lineas: list[bytes], destino_gz: Path) -> int:
    with gzip.open(destino_gz, "wb", compresslevel=5) as fout:
        for l in lineas:
            fout.write(l + b"\n")
    return len(lineas)


def normalizar_url_clave(url: str) -> str:
    u = (url or "").strip().split("#", 1)[0].rstrip("/")
    u = re.sub(r"/manual/en/(?:latest|dev|5\.\d|4\.\d|3\.\d)/", "/manual/en/_ver_/", u)
    return u.lower()


def cargar_urls_vistas() -> set[str]:
    """Carga URLs ya existentes en D:\\ más las ya emitidas por la VM para evitar duplicados."""
    vistas: set[str] = set()
    if RUTA_URLS_SEMILLA_GZ.is_file():
        try:
            with gzip.open(RUTA_URLS_SEMILLA_GZ, "rt", encoding="utf-8", errors="ignore") as f:
                for l in f:
                    if l.strip():
                        vistas.add(l.strip())
                        vistas.add(normalizar_url_clave(l.strip()))
        except Exception:
            pass
    if RUTA_URLS_EMITIDAS.is_file():
        try:
            for l in RUTA_URLS_EMITIDAS.read_text(encoding="utf-8", errors="ignore").splitlines():
                if l.strip():
                    vistas.add(l.strip())
                    vistas.add(normalizar_url_clave(l.strip()))
        except Exception:
            pass
    return vistas


def registrar_urls_emitidas(urls: list[str]) -> None:
    if not urls:
        return
    ESTADO_DIR.mkdir(parents=True, exist_ok=True)
    with RUTA_URLS_EMITIDAS.open("a", encoding="utf-8") as f:
        for u in urls:
            f.write(u.strip() + "\n")


def obtener_paginas_sphinx(nombre_cache: str, url_inv: str, prefijos_prioridad: tuple[str, ...]) -> list[str]:
    """Descarga y cachea en /dev/shm el inventario Sphinx v2 (objects.inv) ordenado por prioridad."""
    CACHE_INV_SHM.mkdir(parents=True, exist_ok=True)
    archivo_cache = CACHE_INV_SHM / f"{nombre_cache}.json"
    if archivo_cache.is_file() and (time.time() - archivo_cache.stat().st_mtime < 12 * 3600):
        try:
            return json.loads(archivo_cache.read_text(encoding="utf-8"))
        except Exception:
            pass

    r = requests.get(url_inv, headers=HEADERS_HTTP, timeout=25)
    if r.status_code != 200:
        return []
    lineas = r.content.split(b"\n", 4)
    if len(lineas) < 5 or not lineas[0].startswith(b"# Sphinx inventory version 2"):
        return []
    cuerpo = zlib.decompress(lineas[4]).decode("utf-8", errors="ignore")
    paginas_set: set[str] = set()
    for l in cuerpo.splitlines():
        partes = l.split(" ", 4)
        if len(partes) < 4 or partes[1] != "std:doc":
            continue
        nombre, uri = partes[0], partes[3]
        if uri.endswith("$"):
            uri = uri[:-1] + nombre
        uri = uri.split("#", 1)[0]
        if not uri or uri.endswith("/index.html") or uri in ("index.html", "copyright.html", "genindex.html", "search.html"):
            continue
        paginas_set.add(uri)

    def clave_orden(uri: str) -> tuple[int, str]:
        for idx, pref in enumerate(prefijos_prioridad):
            if uri.startswith(pref):
                return (idx, uri)
        return (len(prefijos_prioridad), uri)

    ordenadas = sorted(paginas_set, key=clave_orden)
    archivo_cache.write_text(json.dumps(ordenadas, ensure_ascii=False), encoding="utf-8")
    return ordenadas


def emitir_lote_documentacion_53(num_lote: int, cursor_doc: dict, urls_vistas: set[str]) -> dict:
    """Cosecha un lote 100 % documental (Manual 5.3 + API Python 5.3 + Release Notes + StackExchange)."""
    t0 = time.perf_counter()
    shutil.rmtree(TRABAJO, ignore_errors=True)
    TRABAJO.mkdir(parents=True, exist_ok=True)
    nuevo_cursor = json.loads(json.dumps(cursor_doc or {}))
    paginas_se: dict[str, int] = nuevo_cursor.setdefault("paginas_se", {})
    idx_rn = int(nuevo_cursor.get("idx_release_notes", 0))
    idx_manual = int(nuevo_cursor.get("idx_manual_53", 0))
    idx_api = int(nuevo_cursor.get("idx_api_53", 0))

    docs_emitidos: list[dict] = []
    nuevas_urls: list[str] = []
    por_fuente: Counter = Counter()

    try:
        # 1. Manual Oficial de Blender 5.3 via Sphinx objects.inv (8 páginas limpias por lote)
        uris_manual = obtener_paginas_sphinx(
            "manual_53",
            "https://docs.blender.org/manual/en/latest/objects.inv",
            PRIORIDAD_MANUAL_53,
        )
        cosechadas_man = 0
        while idx_manual < len(uris_manual) and cosechadas_man < 8:
            uri_m = uris_manual[idx_manual]
            idx_manual += 1
            url_m = f"https://docs.blender.org/manual/en/latest/{uri_m}"
            if url_m in urls_vistas or normalizar_url_clave(url_m) in urls_vistas:
                continue
            try:
                rm = requests.get(url_m, headers=HEADERS_HTTP, timeout=20)
                if rm.status_code == 200:
                    tit_m, md_m = extraer_articulo_principal(rm.text)
                    if len(md_m.split()) >= 55:
                        slug_id = uri_m.replace("/", "::").removesuffix(".html")
                        docs_emitidos.append(
                            {
                                "contrato": "g7b.documentacion_53/1",
                                "doc_id": f"vmman53::{slug_id}",
                                "fuente": "blender-manual",
                                "titulo": tit_m or f"Blender 5.3 Manual — {uri_m}",
                                "url": url_m,
                                "licencia": "CC-BY-SA-4.0",
                                "version_blender": "5.3",
                                "puntajes": {"valor": 6.0},
                                "texto": md_m[:22000],
                            }
                        )
                        urls_vistas.add(url_m)
                        urls_vistas.add(normalizar_url_clave(url_m))
                        nuevas_urls.append(url_m)
                        por_fuente["blender-manual"] += 1
                        cosechadas_man += 1
                time.sleep(0.35)
            except Exception:
                continue
        nuevo_cursor["idx_manual_53"] = idx_manual if idx_manual < len(uris_manual) else 0

        # 2. Referencia Oficial de API Python de Blender 5.3 via objects.inv (6 módulos/tipos por lote)
        uris_api = obtener_paginas_sphinx(
            "api_53",
            "https://docs.blender.org/api/current/objects.inv",
            PRIORIDAD_API_53,
        )
        cosechadas_api = 0
        while idx_api < len(uris_api) and cosechadas_api < 6:
            uri_a = uris_api[idx_api]
            idx_api += 1
            url_a = f"https://docs.blender.org/api/current/{uri_a}"
            if url_a in urls_vistas or normalizar_url_clave(url_a) in urls_vistas:
                continue
            try:
                ra_doc = requests.get(url_a, headers=HEADERS_HTTP, timeout=20)
                if ra_doc.status_code == 200:
                    tit_a, md_a = extraer_articulo_principal(ra_doc.text)
                    if len(md_a.split()) >= 50:
                        slug_a = uri_a.replace("/", "::").removesuffix(".html")
                        docs_emitidos.append(
                            {
                                "contrato": "g7b.documentacion_53/1",
                                "doc_id": f"vmapi53::{slug_a}",
                                "fuente": "blender-api-python",
                                "titulo": tit_a or f"Blender 5.3 Python API — {slug_a}",
                                "url": url_a,
                                "licencia": "GPL-3.0-or-later",
                                "version_blender": "5.3",
                                "puntajes": {"valor": 6.0},
                                "texto": md_a[:24000],
                            }
                        )
                        urls_vistas.add(url_a)
                        urls_vistas.add(normalizar_url_clave(url_a))
                        nuevas_urls.append(url_a)
                        por_fuente["blender-api-python"] += 1
                        cosechadas_api += 1
                time.sleep(0.35)
            except Exception:
                continue
        nuevo_cursor["idx_api_53"] = idx_api if idx_api < len(uris_api) else 0

        # 3. Notas de Versión Oficiales de Blender (4.0 -> 5.3, CC-BY-SA-4.0, hasta 2 secciones nuevas)
        cosechadas_rn = 0
        intentos_rn = 0
        while idx_rn < len(PAGINAS_RELEASE_NOTES_53) and cosechadas_rn < 2 and intentos_rn < 8:
            ver_rn, sec_rn = PAGINAS_RELEASE_NOTES_53[idx_rn]
            idx_rn += 1
            intentos_rn += 1
            url_rn = f"https://developer.blender.org/docs/release_notes/{ver_rn}/{sec_rn}/"
            if url_rn in urls_vistas or normalizar_url_clave(url_rn) in urls_vistas:
                continue
            try:
                rr = requests.get(url_rn, headers=HEADERS_HTTP, timeout=18)
                if rr.status_code == 200:
                    _, md_rn = extraer_articulo_principal(rr.text)
                    if len(md_rn.split()) >= 65:
                        docs_emitidos.append(
                            {
                                "contrato": "g7b.documentacion_53/1",
                                "doc_id": f"vmrn::{ver_rn}::{sec_rn}",
                                "fuente": "blender-notas-version",
                                "titulo": f"Blender {ver_rn} Release Notes — {sec_rn.replace('_', ' ').title()}",
                                "url": url_rn,
                                "licencia": "CC-BY-SA-4.0",
                                "version_blender": ver_rn,
                                "puntajes": {"valor": 5.5},
                                "texto": md_rn[:20000],
                            }
                        )
                        urls_vistas.add(url_rn)
                        urls_vistas.add(normalizar_url_clave(url_rn))
                        nuevas_urls.append(url_rn)
                        por_fuente["blender-notas-version"] += 1
                        cosechadas_rn += 1
            except Exception:
                continue
        nuevo_cursor["idx_release_notes"] = idx_rn

        # 4. Q&A Técnico Verificado Stack Exchange (CC-BY-SA-4.0, deduplicado contra D:\)
        idx_sitio = int(nuevo_cursor.get("turno_sitio", 0)) % len(FUENTES_SE_DOCUMENTAL)
        nuevo_cursor["turno_sitio"] = idx_sitio + 1
        cfg_se = FUENTES_SE_DOCUMENTAL[idx_sitio]
        clave_pag = f"{cfg_se['id']}:{cfg_se['tagged'] or 'all'}"
        pag = int(paginas_se.get(clave_pag, int(paginas_se.get(cfg_se["id"], 1))))

        params_q = {
            "page": pag,
            "pagesize": 25,
            "order": "desc",
            "sort": "votes",
            "site": cfg_se["site"],
            "filter": "withbody",
        }
        if cfg_se["tagged"]:
            params_q["tagged"] = cfg_se["tagged"]

        rq = requests.get("https://api.stackexchange.com/2.3/questions", params=params_q, headers=HEADERS_HTTP, timeout=25)
        if rq.status_code == 200:
            payload_q = rq.json()
            preguntas = [
                q for q in payload_q.get("items", [])
                if q.get("accepted_answer_id")
                and int(q.get("score") or 0) >= cfg_se["min_score"]
                and normalizar_url_clave(str(q.get("link") or "")) not in urls_vistas
            ]
            ans_ids = [str(q["accepted_answer_id"]) for q in preguntas[:20]]
            mapa_resp: dict[int, dict] = {}
            if ans_ids:
                ra = requests.get(
                    f"https://api.stackexchange.com/2.3/answers/{';'.join(ans_ids)}",
                    params={"site": cfg_se["site"], "filter": "withbody"},
                    headers=HEADERS_HTTP,
                    timeout=25,
                )
                if ra.status_code == 200:
                    for a in ra.json().get("items", []):
                        mapa_resp[int(a["answer_id"])] = a

            for q in preguntas[:20]:
                aid = int(q["accepted_answer_id"])
                ans = mapa_resp.get(aid)
                if not ans:
                    continue
                q_md = html_a_md_limpio(q.get("body") or "")
                a_md = html_a_md_limpio(ans.get("body") or "")
                if len(a_md.split()) < 45:
                    continue
                etiquetas = ", ".join(q.get("tags") or [])
                titulo = html.unescape(str(q.get("title") or "")).strip()
                url_q = str(q.get("link") or f"https://{cfg_se['site']}.stackexchange.com/q/{q['question_id']}")
                texto_doc = (
                    f"## Problema Técnico ({etiquetas})\n\n{q_md}\n\n"
                    f"## Solución Verificada por la Comunidad (Score {ans.get('score', 0)})\n\n{a_md}"
                )
                docs_emitidos.append(
                    {
                        "contrato": "g7b.documentacion_53/1",
                        "doc_id": f"vmse::{cfg_se['site']}::{q['question_id']}",
                        "fuente": cfg_se["id"],
                        "titulo": titulo,
                        "url": url_q,
                        "licencia": "CC-BY-SA-4.0",
                        "version_blender": "",
                        "puntajes": {"valor": float(ans.get("score") or 5)},
                        "texto": texto_doc,
                    }
                )
                urls_vistas.add(url_q)
                urls_vistas.add(normalizar_url_clave(url_q))
                nuevas_urls.append(url_q)
                por_fuente[cfg_se["id"]] += 1

            paginas_se[clave_pag] = (pag + 1) if payload_q.get("has_more") and pag < 80 else 1

        if not docs_emitidos:
            return {"vacio": True, "cursor_com": nuevo_cursor}

        BANDEJA.mkdir(parents=True, exist_ok=True)
        nombre_base = f"lote_vm_{num_lote:04d}_documentacion_53"
        tmp_gz = BANDEJA / f".{nombre_base}.jsonl.gz.part"
        lineas_b = [json.dumps(d, ensure_ascii=False).encode("utf-8") for d in docs_emitidos]
        n_lin = comprimir_lineas_bytes(lineas_b, tmp_gz)
        final_gz = BANDEJA / f"{nombre_base}.jsonl.gz"
        os.replace(tmp_gz, final_gz)
        registrar_urls_emitidas(nuevas_urls)

        dt = round(time.perf_counter() - t0, 2)
        informe = {
            "lote_vm": num_lote,
            "tipo": "documentacion_53",
            "generado_en": ahora_iso(),
            "segundos_procesamiento": dt,
            "licencia": "CC-BY-SA-4.0 / GPL-3.0-or-later",
            "archivo": final_gz.name,
            "bytes_gz": final_gz.stat().st_size,
            "sha256_gz": sha256_archivo(final_gz),
            "filas": n_lin,
            "por_fuente": dict(por_fuente),
            "progreso_sphinx": {
                "manual_53": f"{idx_manual}/{len(uris_manual)}",
                "api_53": f"{idx_api}/{len(uris_api)}",
                "release_notes": f"{idx_rn}/{len(PAGINAS_RELEASE_NOTES_53)}",
            },
            "sitio_se": clave_pag,
            "pagina_se": pag,
        }
        guardar_json_atomico(BANDEJA / f"{nombre_base}.informe.json", informe)
        return {"vacio": False, "informe": informe, "cursor_com": nuevo_cursor}
    finally:
        shutil.rmtree(TRABAJO, ignore_errors=True)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--horas", type=float, default=24.0)
    p.add_argument("--nucleos", type=int, default=2)
    p.add_argument("--intervalo-doc-s", "--intervalo-comunidad-s", dest="intervalo_doc_s", type=int, default=120)
    p.add_argument("--max-bandeja", type=int, default=8)
    p.add_argument("--incluir-telemetria", action="store_true", help="Desactivado por defecto: hoy 100 % documentación")
    p.add_argument("--una-vez-doc", "--una-vez-comunidad", dest="una_vez_doc", action="store_true")
    a = p.parse_args()

    ESTADO_DIR.mkdir(parents=True, exist_ok=True)
    BANDEJA.mkdir(parents=True, exist_ok=True)
    ZIP_RAM.unlink(missing_ok=True)

    ruta_cursor = ESTADO_DIR / "cursor_vm.json"
    estado = json.loads(ruta_cursor.read_text(encoding="utf-8")) if ruta_cursor.is_file() else {
        "siguiente_lote": 1,
        "lotes_emitidos": 0,
        "lotes_comunidad_emitidos": 0,
        "docs_documentacion_emitidos": 0,
        "benchmarks_acumulados": 0,
        "comunidad_53": {},
    }
    estado.pop("ultimo_error", None)
    estado["modo_operacion"] = "solo_documentacion_53" if not a.incluir_telemetria else "mixto"

    urls_vistas = cargar_urls_vistas()

    if a.una_vez_doc:
        n = int(estado["siguiente_lote"])
        res_d = emitir_lote_documentacion_53(n, estado.get("comunidad_53") or {}, urls_vistas)
        estado["comunidad_53"] = res_d["cursor_com"]
        if not res_d.get("vacio"):
            inf = res_d["informe"]
            estado["siguiente_lote"] = n + 1
            estado["lotes_emitidos"] = int(estado["lotes_emitidos"]) + 1
            estado["lotes_comunidad_emitidos"] = int(estado.get("lotes_comunidad_emitidos", 0)) + 1
            estado["docs_documentacion_emitidos"] = int(estado.get("docs_documentacion_emitidos", 0)) + int(inf["filas"])
            estado["ultimo_lote"] = inf
            print(json.dumps(inf, ensure_ascii=False, indent=2), flush=True)
        guardar_json_atomico(ruta_cursor, estado)
        return 0

    fin_ts = time.time() + a.horas * 3600.0
    print(
        f"[{ahora_iso()}] Motor 100 % Documentación 5.3 ARM64 (RAM={SHM_BASE}, deduplicadas={len(urls_vistas)} claves, intervalo={a.intervalo_doc_s}s)",
        flush=True,
    )

    try:
        while time.time() < fin_ts:
            pendientes_gz = sorted(p.name for p in BANDEJA.glob("lote_vm_*.jsonl.gz"))
            if len(pendientes_gz) >= a.max_bandeja:
                estado["actividad"] = f"esperando vaciado de bandeja documental ({len(pendientes_gz)} lotes listos)"
                estado["actualizado_en"] = ahora_iso()
                guardar_json_atomico(ruta_cursor, estado)
                time.sleep(20)
                continue

            try:
                n = int(estado["siguiente_lote"])
                estado["actividad"] = f"cosechando lote documental {n} (Manual 5.3 + API 5.3 + Release Notes + SE en /dev/shm)"
                guardar_json_atomico(ruta_cursor, estado)

                res_doc = emitir_lote_documentacion_53(n, estado.get("comunidad_53") or {}, urls_vistas)
                estado["comunidad_53"] = res_doc["cursor_com"]
                if not res_doc.get("vacio"):
                    inf_d = res_doc["informe"]
                    estado["siguiente_lote"] = n + 1
                    estado["lotes_emitidos"] = int(estado["lotes_emitidos"]) + 1
                    estado["lotes_comunidad_emitidos"] = int(estado.get("lotes_comunidad_emitidos", 0)) + 1
                    estado["docs_documentacion_emitidos"] = int(estado.get("docs_documentacion_emitidos", 0)) + int(inf_d["filas"])
                    estado["ultimo_lote"] = inf_d
                    estado["actividad"] = (
                        f"lote documental {n} listo ({inf_d['filas']} docs · {inf_d['por_fuente']}); pausa {a.intervalo_doc_s}s"
                    )
                    print(
                        f"[{ahora_iso()}] Emitido {inf_d['archivo']} ({inf_d['filas']} docs · {inf_d['por_fuente']} · {inf_d['bytes_gz']} B)",
                        flush=True,
                    )
                estado["actualizado_en"] = ahora_iso()
                guardar_json_atomico(ruta_cursor, estado)
                time.sleep(min(float(a.intervalo_doc_s), max(fin_ts - time.time(), 1.0)))

            except Exception as exc:
                shutil.rmtree(TRABAJO, ignore_errors=True)
                estado["ultimo_error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
                estado["actualizado_en"] = ahora_iso()
                guardar_json_atomico(ruta_cursor, estado)
                time.sleep(30)
    finally:
        ZIP_RAM.unlink(missing_ok=True)
        shutil.rmtree(TRABAJO, ignore_errors=True)

    estado["actividad"] = "ciclo documental 24h completado"
    estado["actualizado_en"] = ahora_iso()
    guardar_json_atomico(ruta_cursor, estado)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
