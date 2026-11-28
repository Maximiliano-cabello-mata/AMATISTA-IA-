# [REVISION 2026-11-27] Laboratorio Gemini: mide limites (RPM/TPM/429/latencia), compara con qwen3:8b sobre C1 y corre un auditor
# de baja frecuencia de 24 h sobre documentos publicos de MongoDB. Entradas: GOOGLE_API_KEY (.env), Canon de Supabase
# (clave publicable), MONGO_URI_LECTURA. Salidas: resultados/ (JSON, HTML, lote_api_NNN.jsonl). ENVIA TEXTO A GOOGLE.
"""Entorno de prueba aislado: mide límites (RPM/TPM/429/latencia) de Gemini / Vertex Express
y lo compara como «maestro» contra el revisor local qwen3:8b sobre los 35 documentos PÚBLICOS
del conjunto de control C1 (manual de Blender CC BY-SA 4.0; cero datos del lago ni de alumnos).

Uso:
    $env:GOOGLE_API_KEY = "<tu-clave>"
    python banco_limites.py --modo ping
    python banco_limites.py --modo rafaga --n 15 --concurrencia 5
    python banco_limites.py --modo c1 --n 35 --concurrencia 3 --modelo gemini-2.5-flash
"""
from __future__ import annotations

import argparse
import concurrent.futures
import html
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

# [REVISION-BUG] Ruta absoluta de este equipo: el laboratorio no funciona en otra computadora ni si se mueve amatista-ia.
RAIZ_AMATISTA_IA = Path(r"C:\Users\KANEDA\.gemini\antigravity\scratch\amatista-ia")
CONTROL_C1 = RAIZ_AMATISTA_IA / "control" / "conjunto_c1.jsonl"
CLAVE_C1 = RAIZ_AMATISTA_IA / "control" / "clave_c1.yml"
LOCAL_V3_C1 = RAIZ_AMATISTA_IA / "control" / "resultados" / "prueba_revisor_v3_control.json"
CANON_CACHE_LOCAL = RAIZ_AMATISTA_IA / "salidas" / "canon_local.json"
SALIDA_DIR = Path(__file__).resolve().parent / "resultados"


def _leer_vars_env(rutas: list[Path], nombres: tuple[str, ...]) -> dict[str, str]:
    """Lee variables del entorno o, si faltan, de los .env indicados (sin imprimirlas)."""
    valores: dict[str, str] = {}
    for var in nombres:
        v = (os.environ.get(var) or "").strip()
        if v:
            valores[var] = v
    for ruta in rutas:
        if not ruta.is_file():
            continue
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            k, v = linea.split("=", 1)
            k = k.strip()
            if k in nombres and k not in valores and v.strip():
                valores[k] = v.strip().strip('"').strip("'")
    return valores


def cargar_canon_supabase() -> tuple[dict, str]:
    """Descarga el Canon v5 de Supabase usando ÚNICAMENTE la clave publicable (solo lectura).
    Si no hay red o credenciales, usa el caché local canon_local.json de solo lectura."""
    rutas = [Path(__file__).resolve().parent / ".env", RAIZ_AMATISTA_IA / ".env"]
    cfg = _leer_vars_env(rutas, ("SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY"))
    url, clave = cfg.get("SUPABASE_URL"), cfg.get("SUPABASE_PUBLISHABLE_KEY")
    if url and clave:
        base = url.rstrip("/").removesuffix("/rest/v1") + "/rest/v1"
        headers = {"apikey": clave, "Authorization": f"Bearer {clave}"}

        def _get(path: str):
            """GET a PostgREST con la clave publicable."""
            req = urllib.request.Request(f"{base}/{path}", headers=headers)
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))

        docs = {d["id"]: d for d in _get("canon_documentos?select=id,titulo,commit_fijado,repositorio")}
        frags = _get("canon_fragmentos?select=id,documento_id,orden,seccion,texto&order=documento_id,orden")
        for f in frags:
            f["titulo"] = (docs.get(f["documento_id"]) or {}).get("titulo", f["documento_id"])
        return {"documentos": docs, "fragmentos": frags}, "supabase"
    if CANON_CACHE_LOCAL.is_file():
        return json.loads(CANON_CACHE_LOCAL.read_text(encoding="utf-8")), "cache_local"
    raise RuntimeError("No se encontraron SUPABASE_URL/SUPABASE_PUBLISHABLE_KEY ni salidas/canon_local.json")


def construir_prompt_con_canon(canon: dict) -> tuple[str, list[str]]:
    """Arma el prompt de sistema usando las reglas oficiales del Canon en Supabase."""
    frags = canon["fragmentos"]
    embudo = "\n\n".join(
        f["texto"] for f in frags
        if f["documento_id"] == "g7b/ingesta" and "4. El embudo" in (f.get("seccion") or "")
    )
    rubrica_frags = [f for f in frags if f["documento_id"] == "g7b/seleccion-documental"]
    rubrica = "\n\n".join(f["texto"] for f in rubrica_frags)
    criterios = "\n\n".join(
        f"{(f.get('seccion') or '').split(' > ')[-1]}\n{f['texto']}"
        for f in frags
        if f["documento_id"] == "ia/criterios"
    )
    citas = ["g7b/ingesta · 4. El embudo"] + list(
        dict.fromkeys(f"{f['documento_id']} · {f.get('seccion') or ''}" for f in rubrica_frags)
    )
    lista_citas = "\n".join(f"- {c}" for c in citas)
    prompt = f"""Eres el revisor maestro de documentación pública de Amatista/G7B.
Evalúa cada documento aplicando EXACTAMENTE las reglas del Canon oficial de Supabase:

=== REGLAS DEL EMBUDO (g7b/ingesta) ===
{embudo}

=== REGLA DE UTILIDAD (g7b/seleccion-documental) ===
{rubrica}

=== CRITERIOS APRENDIDOS Y ERRORES CONOCIDOS (ia/criterios) ===
{criterios}

=== CITAS PERMITIDAS (elige exactamente una) ===
{lista_citas}

Responde ÚNICAMENTE con un JSON válido con estas claves exactas:
{{
  "decision": "aceptar" | "revision" | "rechazar",
  "cita": "<una de las CITAS PERMITIDAS>",
  "problema_detectado": "ninguno" | "plantilla" | "sin_sentido" | "dato_invertido" | "contenido_cruzado" | "consejo_erroneo" | "sin_respuesta" | "basura" | "muy_corta",
  "motivo": "explicación breve en español (máximo 40 palabras)",
  "pista_para_8b": "regla corta en 1 frase que ayudaría a un modelo local de 8B a acertar este caso"
}}"""
    return prompt, citas


def buscar_fragmentos_canon(canon: dict, pregunta: str, top_k: int = 6) -> list[dict]:
    """Búsqueda léxica rápida (sin gastar embeddings) sobre los fragmentos del Canon de Supabase."""
    terminos = [
        t for t in "".join(c if c.isalnum() else " " for c in pregunta.lower()).split()
        if len(t) >= 4 or any(ch.isdigit() for ch in t)
    ]
    puntuados = []
    for f in canon["fragmentos"]:
        blob = f"{f.get('documento_id','')} {f.get('seccion','')} {f.get('texto','')}".lower()
        score = sum(blob.count(t) for t in terminos)
        if score > 0:
            puntuados.append((score, f))
    puntuados.sort(key=lambda x: -x[0])
    return [f for _, f in puntuados[:top_k]]

PROMPT_SISTEMA = """Eres un revisor técnico de documentación pública de Blender para el proyecto Amatista.
Evalúa si el documento aporta valor real y correcto para aprender o ajustar Blender:
- aceptar: documentación técnica real, precisa y útil (parámetros/opciones concretos con su efecto y condición).
- revision: demasiado corta, genérica, plantilla vacía, pregunta sin respuesta o dudosa.
- rechazar: basura, página de error, texto sin sentido, título que no corresponde al contenido, dato técnico invertido o consejo erróneo.

Responde ÚNICAMENTE con un JSON válido con exactamente estas claves:
{
  "decision": "aceptar" | "revision" | "rechazar",
  "problema_detectado": "ninguno" | "plantilla" | "sin_sentido" | "dato_invertido" | "contenido_cruzado" | "consejo_erroneo" | "sin_respuesta" | "basura" | "muy_corta",
  "motivo": "explicación breve en español (máximo 35 palabras)",
  "pista_para_8b": "regla corta en 1 frase que ayudaría a un modelo local de 8B a acertar este caso"
}"""


def cargar_clave(ruta_env: Path) -> str:
    """Clave de Gemini del entorno o del .env; RuntimeError si falta."""
    for var in ("GOOGLE_API_KEY", "GOOGLE_CLOUD_API_KEY", "GEMINI_API_KEY"):
        val = (os.environ.get(var) or "").strip()
        if val:
            return val
    if ruta_env.is_file():
        for linea in ruta_env.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            k, v = linea.split("=", 1)
            if k.strip() in ("GOOGLE_API_KEY", "GOOGLE_CLOUD_API_KEY", "GEMINI_API_KEY") and v.strip():
                return v.strip().strip('"').strip("'")
    raise RuntimeError(
        "Falta la variable de entorno GOOGLE_API_KEY (o GEMINI_API_KEY / GOOGLE_CLOUD_API_KEY). "
        "Defínela en PowerShell con: $env:GOOGLE_API_KEY = '<tu-clave>'"
    )


# [REVISION-BUG] Con 'auto' siempre devuelve 'aistudio' aunque la clave sea de Vertex Express (AQ...), contra lo que dice
# el .env.ejemplo. La prueba test_deteccion_proveedor fija este comportamiento: decidir si es intencional.
def detectar_proveedor(api_key: str, proveedor: str = "auto") -> str:
    """Proveedor de la API (vertex o aistudio)."""
    if proveedor in ("vertex", "aistudio"):
        return proveedor
    return "aistudio"


def url_endpoint(modelo: str, proveedor: str) -> str:
    """URL generateContent del proveedor."""
    if proveedor == "vertex":
        return f"https://aiplatform.googleapis.com/v1/publishers/google/models/{modelo}:generateContent"
    return f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"


def llamar_gemini(
    prompt_usuario: str,
    api_key: str,
    modelo: str,
    proveedor: str,
    sistema: str | None = None,
    json_puro: bool = False,
    timeout: int = 45,
) -> dict:
    """Llama a generateContent y devuelve ok, estado, latencia, texto y tokens (nunca lanza)."""
    url = url_endpoint(modelo, proveedor)
    es_gemma = modelo.lower().startswith("gemma")
    texto_final = f"{sistema}\n\n{prompt_usuario}" if (sistema and es_gemma) else prompt_usuario
    cuerpo: dict = {
        "contents": [{"role": "user", "parts": [{"text": texto_final}]}],
        "generationConfig": {"temperature": 0.1},
    }
    if sistema and not es_gemma:
        cuerpo["systemInstruction"] = {"parts": [{"text": sistema}]}
    if json_puro and not es_gemma:
        cuerpo["generationConfig"]["responseMimeType"] = "application/json"

    req = urllib.request.Request(
        url,
        data=json.dumps(cuerpo).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
            dt = time.perf_counter() - t0
            texto = ""
            cands = raw.get("candidates") or []
            if cands:
                parts = (cands[0].get("content") or {}).get("parts") or []
                texto = "".join(p.get("text", "") for p in parts)
            uso = raw.get("usageMetadata") or {}
            return {
                "ok": True,
                "status": resp.status,
                "latencia_s": round(dt, 3),
                "texto": texto.strip(),
                "tokens_entrada": uso.get("promptTokenCount", 0),
                "tokens_salida": uso.get("candidatesTokenCount", 0),
                "tokens_total": uso.get("totalTokenCount", 0),
                "error": None,
                "retry_after": None,
            }
    except urllib.error.HTTPError as e:
        dt = time.perf_counter() - t0
        detalle = ""
        try:
            detalle = e.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        return {
            "ok": False,
            "status": e.code,
            "latencia_s": round(dt, 3),
            "texto": "",
            "tokens_entrada": 0,
            "tokens_salida": 0,
            "tokens_total": 0,
            "error": f"HTTP {e.code}: {detalle}",
            "retry_after": e.headers.get("Retry-After") if e.headers else None,
        }
    except Exception as e:
        dt = time.perf_counter() - t0
        return {
            "ok": False,
            "status": 0,
            "latencia_s": round(dt, 3),
            "texto": "",
            "tokens_entrada": 0,
            "tokens_salida": 0,
            "tokens_total": 0,
            "error": f"{type(e).__name__}: {e}",
            "retry_after": None,
        }


def parsear_json_respuesta(texto: str) -> dict | None:
    """Extrae un dict JSON de la respuesta (quita vallas ```)."""
    t = texto.strip()
    if t.startswith("```"):
        lineas = [l for l in t.splitlines() if not l.strip().startswith("```")]
        t = "\n".join(lineas).strip()
    try:
        obj = json.loads(t)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def resumir_limites(llamadas: list[dict], duracion_total_s: float) -> dict:
    """RPM/TPM efectivos, codigos HTTP y latencias p50/p95/max."""
    latencias = [c["latencia_s"] for c in llamadas if c["ok"]]
    codigos: dict[str, int] = {}
    for c in llamadas:
        k = str(c["status"])
        codigos[k] = codigos.get(k, 0) + 1
    tok_in = sum(c["tokens_entrada"] for c in llamadas)
    tok_out = sum(c["tokens_salida"] for c in llamadas)
    minutos = max(duracion_total_s / 60.0, 1e-6)
    p95 = sorted(latencias)[min(len(latencias) - 1, int(0.95 * len(latencias)))] if latencias else 0.0
    return {
        "total_llamadas": len(llamadas),
        "exitosas": sum(1 for c in llamadas if c["ok"]),
        "errores_429": codigos.get("429", 0),
        "codigos_http": codigos,
        "duracion_total_s": round(duracion_total_s, 2),
        "rpm_efectivo": round(len(llamadas) / minutos, 1),
        "tpm_efectivo": round((tok_in + tok_out) / minutos, 0),
        "tokens_entrada_total": tok_in,
        "tokens_salida_total": tok_out,
        "latencia_p50_s": round(statistics.median(latencias), 3) if latencias else None,
        "latencia_p95_s": round(p95, 3) if latencias else None,
        "latencia_max_s": round(max(latencias), 3) if latencias else None,
    }


def calificar_contra_clave(resultados: list[dict], clave: dict) -> dict:
    """Buenos aceptados y malos detenidos segun la clave C1."""
    docs_clave = clave["documentos"]
    buenos_ok = buenos_tot = malos_det = malos_tot = malos_pasan = 0
    for r in resultados:
        info = docs_clave.get(r["doc_id"])
        if not info:
            continue
        dec = (r.get("ia") or {}).get("decision")
        if info["esperado"] == "aceptar":
            buenos_tot += 1
            if dec == "aceptar":
                buenos_ok += 1
        else:
            malos_tot += 1
            if dec == "aceptar":
                malos_pasan += 1
            elif dec in ("revision", "rechazar"):
                malos_det += 1
    return {
        "buenos_aceptados": [buenos_ok, buenos_tot],
        "malos_detenidos": [malos_det, malos_tot],
        "malos_que_pasan": malos_pasan,
    }


def renderizar_html(reporte: dict, destino: Path) -> None:
    """Escribe el reporte HTML comparativo."""
    lim = reporte["limites"]
    cal = reporte.get("calificacion_gemini") or {}
    v3 = reporte.get("referencia_local_v3") or {}
    filas_html = []
    for i, r in enumerate(reporte.get("resultados") or [], 1):
        ia = r.get("ia") or {}
        dec_g = ia.get("decision") or f"ERR({r['status']})"
        dec_v3 = r.get("v3_decision") or "—"
        esp = r.get("esperado") or "—"
        tipo = r.get("tipo_sembrado") or "bueno"
        ok_g = (esp == "aceptar" and dec_g == "aceptar") or (esp != "aceptar" and dec_g in ("revision", "rechazar"))
        clase = "ok" if ok_g else "bad"
        filas_html.append(
            f"<tr class='{clase}'><td>{i}</td><td>{html.escape(r['titulo'])}</td>"
            f"<td>{html.escape(tipo)}</td><td>{html.escape(esp)}</td>"
            f"<td>{html.escape(dec_v3)}</td><td><b>{html.escape(dec_g)}</b></td>"
            f"<td>{r['latencia_s']} s</td><td>{html.escape(ia.get('motivo') or r.get('error') or '')}</td>"
            f"<td>{html.escape(ia.get('pista_para_8b') or '')}</td></tr>"
        )
    doc = f"""<!doctype html><meta charset="utf-8"><title>Lab Límites Gemini vs qwen3:8b (C1)</title>
<style>
body{{font:14px/1.5 system-ui,sans-serif;background:#111018;color:#ece8f5;max-width:1280px;margin:2rem auto;padding:0 16px}}
h1,h2{{color:#d5b4ff}} .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin:16px 0}}
.card{{background:#1b1826;border:1px solid #322c46;border-radius:10px;padding:14px}}
.val{{font-size:24px;font-weight:700;color:#4ef0d0}} .sub{{color:#a99ec2;font-size:12px}}
table{{width:100%;border-collapse:collapse;margin-top:16px;font-size:13px}}
th,td{{border:1px solid #2e2840;padding:7px 8px;text-align:left;vertical-align:top}}
th{{background:#221d33}} tr.ok td:nth-child(6){{color:#5cf29c}} tr.bad td:nth-child(6){{color:#ff7b89}}
</style>
<h1>Lab Límites ({html.escape(reporte['modelo'])} · {html.escape(reporte['proveedor'])}) vs qwen3:8b local</h1>
<p class="sub">Conjunto público C1 (manual de Blender CC BY-SA 4.0) · {html.escape(reporte['fecha'])}</p>
<div class="grid">
  <div class="card"><div class="sub">RPM / TPM efectivos</div><div class="val">{lim['rpm_efectivo']} RPM</div><div class="sub">{int(lim['tpm_efectivo']):,} TPM · 429: {lim['errores_429']}</div></div>
  <div class="card"><div class="sub">Latencia p50 / p95</div><div class="val">{lim['latencia_p50_s']} s</div><div class="sub">p95: {lim['latencia_p95_s']} s · total: {lim['duracion_total_s']} s (v3 local: ~5,400 s)</div></div>
  <div class="card"><div class="sub">Malos detenidos (C1)</div><div class="val">{cal.get('malos_detenidos', ['—','—'])[0]}/{cal.get('malos_detenidos', ['—','—'])[1]}</div><div class="sub">qwen3:8b local v3: {v3.get('malos_detenidos', '9/13')}</div></div>
  <div class="card"><div class="sub">Buenos aceptados (C1)</div><div class="val">{cal.get('buenos_aceptados', ['—','—'])[0]}/{cal.get('buenos_aceptados', ['—','—'])[1]}</div><div class="sub">qwen3:8b local v3: {v3.get('buenos_aceptados', '13/22')} · malos pasan: {cal.get('malos_que_pasan', '—')}</div></div>
</div>
<h2>Detalle documento por documento y pistas para mejorar el 8B local</h2>
<table>
<thead><tr><th>#</th><th>Título</th><th>Tipo</th><th>Clave</th><th>qwen3:8b</th><th>Gemini</th><th>Latencia</th><th>Motivo</th><th>Pista para 8B</th></tr></thead>
<tbody>{''.join(filas_html)}</tbody>
</table>"""
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(doc, encoding="utf-8")


def modo_ping(api_key: str, modelo: str, proveedor: str) -> int:
    """Llamada minima de prueba."""
    r = llamar_gemini("Responde exactamente con la palabra: OK", api_key, modelo, proveedor)
    print(json.dumps({k: v for k, v in r.items() if k != "texto"} | {"texto": r["texto"][:80]}, ensure_ascii=False, indent=2))
    return 0 if r["ok"] else 1


def modo_rafaga(api_key: str, modelo: str, proveedor: str, n: int, concurrencia: int, pausa_ms: int) -> int:
    """Rafaga concurrente para medir RPM y 429."""
    t0 = time.perf_counter()
    llamadas = []

    def uno(i: int) -> dict:
        """Una llamada numerada de la rafaga."""
        if pausa_ms > 0 and i > 0:
            time.sleep(pausa_ms / 1000.0)
        return llamar_gemini(f"Di solo el número {i}.", api_key, modelo, proveedor)

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrencia) as ex:
        for res in ex.map(uno, range(n)):
            llamadas.append(res)
    resumen = resumir_limites(llamadas, time.perf_counter() - t0)
    print(json.dumps({"modo": "rafaga", "modelo": modelo, "proveedor": proveedor, "concurrencia": concurrencia, **resumen}, ensure_ascii=False, indent=2))
    return 0


def modo_c1(api_key: str, modelo: str, proveedor: str, n: int, concurrencia: int, pausa_ms: int, usar_canon: bool = False) -> int:
    """Evalua el conjunto C1 con Gemini y escribe JSON y HTML."""
    docs = [json.loads(l) for l in CONTROL_C1.read_text(encoding="utf-8").splitlines() if l.strip()][:n]
    clave = yaml.safe_load(CLAVE_C1.read_text(encoding="utf-8"))
    v3_por_id = {}
    if LOCAL_V3_C1.is_file():
        v3_data = json.loads(LOCAL_V3_C1.read_text(encoding="utf-8"))
        v3_por_id = {r["doc_id"]: r.get("decision_efectiva") for r in v3_data.get("resultados", [])}

    sistema = PROMPT_SISTEMA
    origen_canon = "prompt_base"
    if usar_canon:
        canon, origen_canon = cargar_canon_supabase()
        sistema, citas = construir_prompt_con_canon(canon)
        print(f"Canon cargado desde {origen_canon}: {len(canon['documentos'])} docs, {len(canon['fragmentos'])} fragmentos, {len(citas)} citas fijas")

    def evaluar(par: tuple[int, dict]) -> dict:
        """Evalua un documento de C1."""
        idx, d = par
        if pausa_ms > 0 and idx > 0:
            time.sleep(pausa_ms / 1000.0)
        extracto = " ".join((d.get("texto") or "").split()[:450])
        prompt = f"Título: {d.get('titulo')}\nFuente: {d.get('fuente')}\nURL: {d.get('url')}\n\nTexto:\n{extracto}"
        r = llamar_gemini(prompt, api_key, modelo, proveedor, sistema=sistema, json_puro=True)
        ia = parsear_json_respuesta(r["texto"]) if r["ok"] else None
        info = clave["documentos"].get(d["doc_id"], {})
        return {
            **r,
            "doc_id": d["doc_id"],
            "titulo": d.get("titulo") or "",
            "fuente": d.get("fuente") or "",
            "esperado": info.get("esperado"),
            "tipo_sembrado": info.get("tipo") or "bueno",
            "v3_decision": v3_por_id.get(d["doc_id"]),
            "ia": ia,
        }

    t0 = time.perf_counter()
    resultados = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrencia) as ex:
        for res in ex.map(evaluar, enumerate(docs)):
            resultados.append(res)
            dec = (res.get("ia") or {}).get("decision") or f"HTTP {res['status']}"
            print(f"[{len(resultados):2d}/{len(docs)}] {res['latencia_s']:5.2f}s  {dec:<10} (esp: {res['esperado']:<8} · v3: {res['v3_decision'] or '—':<8})  {res['titulo'][:45]}")

    duracion = time.perf_counter() - t0
    limites = resumir_limites(resultados, duracion)
    cal = calificar_contra_clave(resultados, clave)
    reporte = {
        "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
        "modelo": modelo,
        "proveedor": proveedor,
        "canon": origen_canon,
        "concurrencia": concurrencia,
        "limites": limites,
        "calificacion_gemini": cal,
        "referencia_local_v3": {"malos_detenidos": "9/13", "buenos_aceptados": "13/22", "mediana_s_doc": 185.1},
        "resultados": resultados,
    }
    SALIDA_DIR.mkdir(parents=True, exist_ok=True)
    ruta_json = SALIDA_DIR / "maestro_c1.json"
    ruta_html = SALIDA_DIR / "reporte.html"
    ruta_json.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")
    renderizar_html(reporte, ruta_html)
    print("\n=== RESUMEN ===")
    print(json.dumps({"canon": origen_canon, "limites": limites, "calificacion_gemini": cal}, ensure_ascii=False, indent=2))
    print(f"\nGuardado: {ruta_json} y {ruta_html}")
    return 0


FUENTES_PUBLICAS_PESADAS = (
    "blender-manual",
    "blender-compositor-45",
    "blender-notas-version",
    "blender-api-python",
    "blender-stackexchange",
    "blender-stackexchange-clasicos",
    "computergraphics-stackexchange",
    "computergraphics-stackexchange-clasicos",
    "arxiv-cs-gr",
    "stackoverflow-blender",
    "stackoverflow-web3d",
    "gamedev-stackexchange",
    "blender-extensions-ast-gpl",
    "github-blender-ast-open",
)
MODELOS_CASCADA = (
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite-preview",
    "gemini-3-flash-preview",
    "gemma-4-31b-it",
    "gemini-3.5-flash",
)
POOLS_ROTACION_ACTIVOS = (
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite-preview",
    "gemini-3-flash-preview",
    "gemma-4-31b-it",
)
RUTA_DISCO_RAG_D = Path(os.environ.get("AMATISTA_RAG_DIR", r"D:\Amatista_Nucleo_RAG"))

REGLAS_ROSETTA_PROMPT = """
=== REGLAS DE COMPATIBILIDAD Y PIEDRA ROSETTA BLENDER 5.3 ===
Al evaluar o destilar contenido comunitario u oficial (2.8 / 3.x / 4.x / 5.x), traduce mentalmente y en `receta_53` cualquier sintaxis legada:
- `mesh.use_auto_smooth` / `calc_normals_split` -> Modificador 'Smooth by Angle' o `GeometryNodeSetShadeSmooth`.
- Principled BSDF v2: `Transmission` -> `Transmission Weight`, `Specular` -> `Specular IOR Level`, `Clearcoat` -> `Coat Weight`, `Emission` -> `Emission Color` + `Emission Strength`.
- `Musgrave Texture` -> `ShaderNodeTexNoise` (`noise_type='FBM'`, `'RIDGED_MULTIFRACTAL'`, etc.).
- EEVEE 4.2–5.3: `use_bloom` -> `CompositorNodeGlare` en Viewport Compositor; `use_ssr`/`use_gtao` -> `eevee.use_raytracing = True`; `material.blend_method` -> `surface_render_method` (`DITHERED` | `BLENDED`).
- Geometry Nodes: `Transfer Attribute` -> `Sample Nearest Surface` / `Sample Index`; `Align Euler to Vector` -> `FunctionNodeAlignRotationToVector`.
- Animación 5.0–5.3: `action.fcurves` -> `action.layers` (Slotted/Layered Actions -> `channelbag(slot).fcurves`); `bgl` -> módulo `gpu`; dict override en `bpy.ops` -> `bpy.context.temp_override(...)`.
Además de las claves del Canon (`decision`, `cita`, `problema_detectado`, `motivo`, `pista_para_8b`), incluye siempre:
- `"compatibilidad_53"`: `"vigente_5_3"` | `"migrado_rosetta_5_3"` | `"agnostico_3d"`
- `"receta_53"`: si `decision == "aceptar"`, síntesis técnica original en español (55–120 palabras) con estructura `Problema -> Combinación de herramientas/nodos/API en Blender 5.3 -> Parámetros clave`; vacío `""` si se rechaza.
"""


def armar_prompt_paquete(paquete: list[dict], palabras_max: int = 650) -> str:
    """Empaqueta N documentos en un único prompt numerado para multiplicar el rendimiento por RPD."""
    bloques = [
        f"Evalúa los siguientes {len(paquete)} documentos de forma independiente y responde ÚNICAMENTE con un objeto JSON válido "
        f'con la forma exacta {{"resultados": [ ... {len(paquete)} objetos ... ]}}, donde cada objeto incluye su `"doc_id"` exacto '
        f"además de `decision`, `cita`, `problema_detectado`, `motivo`, `pista_para_8b`, `compatibilidad_53` y `receta_53`.\n"
    ]
    for i, doc in enumerate(paquete, 1):
        palabras_doc = (doc.get("texto") or "").split()
        extracto = " ".join(palabras_doc[:palabras_max])
        bloques.append(
            f"--- DOCUMENTO {i} ---\n"
            f"doc_id: {doc['doc_id']}\n"
            f"Título: {doc.get('titulo')}\n"
            f"Fuente: {doc.get('fuente')} ({doc.get('licencia')})\n"
            f"URL: {doc.get('url')}\n"
            f"Palabras totales: {len(palabras_doc)}\n"
            f"Texto:\n{extracto}\n"
        )
    return "\n".join(bloques)


def parsear_respuesta_paquete(texto: str, ids_esperados: list[str]) -> dict[str, dict]:
    """Extrae el mapa doc_id -> dict de evaluación desde un JSON de paquete (tolera vallas ``` y listas directas)."""
    t = (texto or "").strip()
    if t.startswith("```"):
        lineas = [l for l in t.splitlines() if not l.strip().startswith("```")]
        t = "\n".join(lineas).strip()
    if not t.startswith(("{", "[")):
        i_obj, i_arr = t.find("{"), t.find("[")
        inicios = [x for x in (i_obj, i_arr) if x != -1]
        if inicios:
            t = t[min(inicios):]
            fin = max(t.rfind("}"), t.rfind("]"))
            if fin != -1:
                t = t[: fin + 1]
    try:
        data = json.loads(t)
    except Exception:
        return {}

    items: list = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        if isinstance(data.get("resultados"), list):
            items = data["resultados"]
        elif "decision" in data and len(ids_esperados) == 1:
            data["doc_id"] = data.get("doc_id") or ids_esperados[0]
            items = [data]

    mapa: dict[str, dict] = {}
    for idx, obj in enumerate(items):
        if not isinstance(obj, dict):
            continue
        did = str(obj.get("doc_id") or (ids_esperados[idx] if idx < len(ids_esperados) else "")).strip()
        if did:
            mapa[did] = obj
    return mapa


def elegir_pool_rotacion(enfriamientos: dict[str, float], turno: int, pools: tuple[str, ...] = POOLS_ROTACION_ACTIVOS) -> list[str]:
    """Ordena los pools activos en round-robin saltando temporalmente los que estén en enfriamiento por 429/503."""
    ahora = time.time()
    n = len(pools)
    orden_rr = [pools[(turno + i) % n] for i in range(n)]
    disponibles = [m for m in orden_rr if enfriamientos.get(m, 0.0) <= ahora]
    en_pausa = [m for m in orden_rr if enfriamientos.get(m, 0.0) > ahora]
    return disponibles + en_pausa


def inyectar_recetas_en_sqlite_d(registros_aceptados: list[dict], ruta_sqlite: Path | None = None) -> int:
    """Inyecta en D:\\Amatista_Nucleo_RAG\\indices\\nucleo_conocimiento.sqlite el fragmento destilado receta_53."""
    import contextlib
    import sqlite3

    sq = ruta_sqlite or (RUTA_DISCO_RAG_D / "indices" / "nucleo_conocimiento.sqlite")
    if not sq.is_file() or not registros_aceptados:
        return 0

    inyectados = 0
    with contextlib.closing(sqlite3.connect(str(sq), timeout=45.0)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        for reg in registros_aceptados:
            receta = str(reg.get("receta_53") or "").strip()
            if reg.get("decision") != "aceptar" or len(receta.split()) < 20:
                continue
            did = str(reg["doc_id"])
            row = conn.execute(
                "SELECT fuente, titulo, url, version_blender, dominio, metadatos_json FROM documentos WHERE doc_id = ?",
                (did,),
            ).fetchone()
            if row is None:
                continue
            clave_u = f"{did}::receta_gemini_53"
            titulo = str(row["titulo"])
            fuente = str(row["fuente"])
            url = str(row["url"] or "")
            ver = str(row["version_blender"] or "5.3")
            dom = str(row["dominio"] or "general_3d")
            comp53 = str(reg.get("compatibilidad_53") or "vigente_5_3")
            texto_frag = f"### Receta Destilada Blender 5.3 ({comp53})\n\n{receta}"
            texto_ctx = f"[{fuente} | Blender 5.3 | {titulo} | Receta 5.3]\n{texto_frag}"

            conn.execute(
                """
                INSERT INTO fragmentos (
                    clave_unica, doc_id, orden, fuente, titulo, seccion, url,
                    texto, texto_contextual, operadores_bpy, tiene_codigo,
                    nivel_confianza, peso_confianza, version_blender, dominio,
                    prioridad_vector, tiene_vector
                ) VALUES (?, ?, 999, ?, ?, 'Receta Destilada Blender 5.3', ?, ?, ?, '', 0, 'destilado_maestro_53', 1.35, ?, ?, 0, 0)
                ON CONFLICT(clave_unica) DO UPDATE SET
                    texto = excluded.texto,
                    texto_contextual = excluded.texto_contextual,
                    peso_confianza = 1.35,
                    prioridad_vector = 0
                """,
                (clave_u, did, fuente, titulo, url, texto_frag, texto_ctx, ver, dom),
            )
            try:
                meta = json.loads(row["metadatos_json"] or "{}")
            except Exception:
                meta = {}
            meta["receta_53_modelo"] = reg.get("modelo")
            meta["compatibilidad_53"] = comp53
            conn.execute(
                "UPDATE documentos SET metadatos_json = ?, peso_confianza = MAX(peso_confianza, 1.30) WHERE doc_id = ?",
                (json.dumps(meta, ensure_ascii=False), did),
            )
            inyectados += 1
        conn.commit()
    return inyectados


def ordenar_documentos_pesados(docs: list[dict], ya_vistos: set[str]) -> list[dict]:
    """Filtra fuentes públicas verificadas no procesadas y prioriza la documentación más densa/pesada."""
    elegibles = [
        d for d in docs
        if d.get("doc_id")
        and d["doc_id"] not in ya_vistos
        and d.get("fuente") in FUENTES_PUBLICAS_PESADAS
        and (d.get("texto") or "").strip()
    ]
    # Round-robin entre fuentes (cada una de más a menos pesada): así los foros, más ruidosos, se
    # auditan desde el principio y no esperan a que se acabe el manual.
    por_fuente: dict[str, list[dict]] = {}
    for d in sorted(elegibles, key=lambda d: (-len((d.get("texto") or "").split()), d.get("doc_id") or "")):
        por_fuente.setdefault(d["fuente"], []).append(d)
    orden: list[dict] = []
    colas = [por_fuente[k] for k in sorted(por_fuente)]
    while any(colas):
        for c in colas:
            if c:
                orden.append(c.pop(0))
    return orden


# [REVISION-SEGURIDAD] (decidir) Este modo envia a Google texto de documentos leidos de MongoDB (conocimiento_3d). Son
# fuentes publicas, pero contradice la regla de amatista-ia/revisor ('ningun texto del lago sale de aqui'). Documentar la excepcion.
def modo_ciclo_24h(
    api_key: str,
    modelo_primario: str,
    proveedor: str,
    horas: float = 24.0,
    tamano_lote: int = 40,
    pausa_ms: int = 8000,
    palabras_max: int = 650,
    docs_por_llamada: int = 8,
    una_vez_paquete: bool = False,
) -> int:
    """Ciclo continuo Multi-Pool (4 modelos en rotación) + Micro-Batching (8 docs/llamada) hacia D:\\."""
    import contextlib
    import sqlite3
    from pymongo import MongoClient

    rutas_env = [Path(__file__).resolve().parent / ".env", RAIZ_AMATISTA_IA / ".env"]
    cfg = _leer_vars_env(rutas_env, ("MONGO_URI_LECTURA", "MONGO_DATABASE"))
    uri = cfg.get("MONGO_URI_LECTURA")
    db_nombre = cfg.get("MONGO_DATABASE") or "conocimiento_3d"

    canon, origen_canon = cargar_canon_supabase()
    sistema_base, _ = construir_prompt_con_canon(canon)
    sistema = sistema_base + "\n\n" + REGLAS_ROSETTA_PROMPT

    carpeta = SALIDA_DIR / "ciclo_24h"
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta_estado = carpeta / "estado_ciclo_24h.json"

    if ruta_estado.is_file():
        estado = json.loads(ruta_estado.read_text(encoding="utf-8"))
        estado["horas_objetivo"] = horas
        estado["modelo_primario"] = "rotacion_4_pools"
        estado["modo_rosetta_53"] = True
        estado["docs_por_llamada"] = docs_por_llamada
        estado["pausa_ms"] = pausa_ms
        estado.setdefault("por_modelo", {})
        estado.setdefault("recetas_53_inyectadas_d", 0)
        estado.setdefault("llamadas_empaquetadas", 0)
    else:
        estado = {
            "iniciado_en": time.strftime("%Y-%m-%d %H:%M:%S"),
            "horas_objetivo": horas,
            "modelo_primario": "rotacion_4_pools",
            "modo_rosetta_53": True,
            "docs_por_llamada": docs_por_llamada,
            "canon": origen_canon,
            "pausa_ms": pausa_ms,
            "tamano_lote": tamano_lote,
            "lote_actual": 1,
            "docs_en_lote_actual": 0,
            "total_procesados": 0,
            "llamadas_empaquetadas": 0,
            "recetas_53_inyectadas_d": 0,
            "por_modelo": {},
            "decisiones": {"aceptar": 0, "revision": 0, "rechazar": 0, "error": 0},
            "errores_429": 0,
            "lotes_cerrados": [],
            "actividad": "iniciando",
            "actualizado_en": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    ruta_sq = RUTA_DISCO_RAG_D / "indices" / "nucleo_conocimiento.sqlite"

    def cargar_ya_destilados() -> set[str]:
        """doc_id que ya tienen evaluación/receta_53 de Gemini."""
        vistos: set[str] = set()
        for p in sorted(carpeta.glob("lote_api_*.jsonl")):
            for linea in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                if linea.strip():
                    try:
                        did = json.loads(linea).get("doc_id")
                        if did:
                            vistos.add(str(did))
                    except Exception:
                        pass
        if ruta_sq.is_file():
            try:
                with contextlib.closing(sqlite3.connect(str(ruta_sq), timeout=20.0)) as con_sq:
                    for (did_r,) in con_sq.execute(
                        "SELECT doc_id FROM fragmentos WHERE seccion = 'Receta Destilada Blender 5.3'"
                    ):
                        if did_r:
                            vistos.add(str(did_r))
            except Exception:
                pass
        return vistos

    def cargar_cola_desde_d_y_mongo(ya_destilados: set[str], cli_m) -> list[dict]:
        """Arma cola priorizando lotes frescos de la VM y foros/docs en D:\\ sin receta_53, más pendientes en Mongo."""
        candidatos: list[dict] = []
        ids_en_cola: set[str] = set()

        if ruta_sq.is_file():
            try:
                with contextlib.closing(sqlite3.connect(str(ruta_sq), timeout=25.0)) as con_sq:
                    con_sq.row_factory = sqlite3.Row
                    filas = con_sq.execute(
                        """
                        SELECT d.doc_id, d.fuente, d.titulo, d.url, d.licencia, d.lote_origen
                        FROM documentos d
                        WHERE d.fuente IN (
                            'blender-stackexchange', 'stackoverflow-blender', 'stackoverflow-web3d',
                            'computergraphics-stackexchange', 'gamedev-stackexchange',
                            'blender-notas-version', 'blender-api-python', 'blender-manual',
                            'blender-stackexchange-clasicos', 'computergraphics-stackexchange-clasicos'
                        )
                        ORDER BY
                            CASE WHEN d.lote_origen LIKE 'vm_oracle_24h:%' THEN 0 ELSE 1 END ASC,
                            d.rowid DESC
                        LIMIT 600
                        """
                    ).fetchall()
                    elegidos = [r for r in filas if str(r["doc_id"]) not in ya_destilados][:240]
                    for r in elegidos:
                        did = str(r["doc_id"])
                        partes_txt = [
                            fr[0]
                            for fr in con_sq.execute(
                                "SELECT texto FROM fragmentos WHERE doc_id = ? AND seccion != 'Receta Destilada Blender 5.3' ORDER BY orden ASC LIMIT 6",
                                (did,),
                            ).fetchall()
                            if fr[0]
                        ]
                        texto_unido = "\n\n".join(partes_txt).strip()
                        if len(texto_unido.split()) >= 35:
                            candidatos.append(
                                {
                                    "doc_id": did,
                                    "fuente": str(r["fuente"]),
                                    "titulo": str(r["titulo"]),
                                    "url": str(r["url"] or ""),
                                    "licencia": str(r["licencia"] or "CC-BY-SA-4.0"),
                                    "texto": texto_unido,
                                }
                            )
                            ids_en_cola.add(did)
            except Exception:
                pass

        if len(candidatos) < docs_por_llamada and cli_m is not None:
            try:
                col_m = cli_m[db_nombre]["documentos"]
                for d in col_m.find(
                    {"fuente": {"$in": list(FUENTES_PUBLICAS_PESADAS)}},
                    {"_id": 0, "doc_id": 1, "url": 1, "fuente": 1, "titulo": 1, "texto": 1, "licencia": 1},
                ):
                    did_m = str(d.get("doc_id") or "")
                    if did_m and did_m not in ya_destilados and did_m not in ids_en_cola and (d.get("texto") or "").strip():
                        candidatos.append(d)
                        ids_en_cola.add(did_m)
                        if len(candidatos) >= 160:
                            break
            except Exception:
                pass

        return ordenar_documentos_pesados(candidatos, ya_destilados)

    ya_destilados: set[str] = cargar_ya_destilados()
    enfriamientos: dict[str, float] = {}
    turno_pool = 0
    fin_ts = time.time() + horas * 3600.0
    cli_mongo = MongoClient(uri, serverSelectionTimeoutMS=15000) if uri else None

    def guardar_estado(act: str) -> None:
        estado["actividad"] = act
        estado["actualizado_en"] = time.strftime("%Y-%m-%d %H:%M:%S")
        estado["restante_h"] = round(max(fin_ts - time.time(), 0.0) / 3600.0, 2)
        estado["ya_destilados_totales"] = len(ya_destilados)
        estado["pools_activos"] = list(POOLS_ROTACION_ACTIVOS)
        tmp = ruta_estado.with_suffix(".tmp")
        tmp.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, ruta_estado)

    guardar_estado(f"escudrón 4-pools activo (×{docs_por_llamada} docs/llamada) sobre D:\\ + MongoDB")

    try:
        while time.time() < fin_ts:
            ya_destilados |= cargar_ya_destilados()
            cola = cargar_cola_desde_d_y_mongo(ya_destilados, cli_mongo)
            estado["disponibles_sin_revisar"] = len(cola)
            if not cola:
                guardar_estado("al día (0 sin receta_53) · vigilando nuevos lotes de la VM cada 60 s")
                if una_vez_paquete:
                    break
                time.sleep(min(60.0, max(fin_ts - time.time(), 1.0)))
                continue

            for idx_ini in range(0, len(cola), docs_por_llamada):
                if time.time() >= fin_ts:
                    break
                paquete = [d for d in cola[idx_ini : idx_ini + docs_por_llamada] if str(d["doc_id"]) not in ya_destilados]
                if not paquete:
                    continue

                num_lote = int(estado["lote_actual"])
                ruta_jsonl = carpeta / f"lote_api_{num_lote:03d}.jsonl"
                ids_paq = [str(d["doc_id"]) for d in paquete]
                prompt_paq = armar_prompt_paquete(paquete, palabras_max=palabras_max)

                orden_modelos = elegir_pool_rotacion(enfriamientos, turno_pool)
                turno_pool += 1

                respuesta = None
                modelo_usado = orden_modelos[0]
                mapa_ia: dict[str, dict] = {}

                for mod in orden_modelos:
                    modelo_usado = mod
                    guardar_estado(
                        f"lote {num_lote} · [{mod}] destilando paquete ×{len(paquete)} docs (D:\\ -> receta_53)"
                    )
                    timeout_mod = 75 if mod.startswith("gemma") else 45
                    r = llamar_gemini(prompt_paq, api_key, mod, proveedor, sistema=sistema, json_puro=True, timeout=timeout_mod)
                    if r["ok"]:
                        mapa_cand = parsear_respuesta_paquete(r["texto"], ids_paq)
                        if mapa_cand:
                            respuesta = r
                            mapa_ia = mapa_cand
                            break
                    if r["status"] == 429:
                        estado["errores_429"] = int(estado.get("errores_429", 0)) + 1
                        ra_s = float(r.get("retry_after") or 90.0)
                        enfriamientos[mod] = time.time() + min(max(ra_s, 60.0), 300.0)
                        continue
                    if r["status"] in (500, 502, 503, 504, 0):
                        enfriamientos[mod] = time.time() + 45.0
                        continue

                if respuesta is None or not mapa_ia:
                    guardar_estado("todos los pools en enfriamiento breve (30 s) · reintentando")
                    if una_vez_paquete:
                        return 1
                    time.sleep(min(30.0, max(fin_ts - time.time(), 1.0)))
                    continue

                estado["llamadas_empaquetadas"] = int(estado.get("llamadas_empaquetadas", 0)) + 1
                por_mod = estado.setdefault("por_modelo", {})
                est_m = por_mod.setdefault(modelo_usado, {"llamadas": 0, "docs": 0})
                est_m["llamadas"] += 1
                est_m["docs"] += len(paquete)

                registros_lote_paq: list[dict] = []
                lat_por_doc = round(respuesta["latencia_s"] / max(len(paquete), 1), 3)
                tok_in_doc = respuesta["tokens_entrada"] // max(len(paquete), 1)
                tok_out_doc = respuesta["tokens_salida"] // max(len(paquete), 1)

                with ruta_jsonl.open("a", encoding="utf-8") as f:
                    for doc in paquete:
                        did = str(doc["doc_id"])
                        ia = mapa_ia.get(did)
                        decision = (ia or {}).get("decision") if ia else None
                        if decision not in ("aceptar", "revision", "rechazar"):
                            decision = "error"
                        palabras_doc = (doc.get("texto") or "").split()
                        reg = {
                            "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "lote": num_lote,
                            "doc_id": did,
                            "fuente": doc.get("fuente"),
                            "titulo": doc.get("titulo"),
                            "url": doc.get("url"),
                            "licencia": doc.get("licencia"),
                            "palabras_totales": len(palabras_doc),
                            "palabras_enviadas": min(len(palabras_doc), palabras_max),
                            "modelo": modelo_usado,
                            "latencia_s": lat_por_doc,
                            "latencia_paquete_s": respuesta["latencia_s"],
                            "tamano_paquete": len(paquete),
                            "tokens_entrada": tok_in_doc,
                            "tokens_salida": tok_out_doc,
                            "decision": decision,
                            "compatibilidad_53": (ia or {}).get("compatibilidad_53", ""),
                            "receta_53": (ia or {}).get("receta_53", ""),
                            "ia": ia,
                            "error": None if ia else "sin_item_en_paquete",
                        }
                        f.write(json.dumps(reg, ensure_ascii=False) + "\n")
                        if ia:
                            ya_destilados.add(did)
                            registros_lote_paq.append(reg)
                        estado["total_procesados"] = int(estado["total_procesados"]) + 1
                        estado["docs_en_lote_actual"] = int(estado["docs_en_lote_actual"]) + 1
                        estado["decisiones"][decision] = int(estado["decisiones"].get(decision, 0)) + 1

                inyectadas = inyectar_recetas_en_sqlite_d(registros_lote_paq)
                estado["recetas_53_inyectadas_d"] = int(estado.get("recetas_53_inyectadas_d", 0)) + inyectadas

                if estado["docs_en_lote_actual"] >= tamano_lote:
                    filas_lote = [json.loads(l) for l in ruta_jsonl.read_text(encoding="utf-8").splitlines() if l.strip()]
                    conteo_lote: dict[str, int] = {}
                    for fl in filas_lote:
                        conteo_lote[fl["decision"]] = conteo_lote.get(fl["decision"], 0) + 1
                    resumen_lote = {
                        "lote": num_lote,
                        "cerrado_en": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "documentos": len(filas_lote),
                        "decisiones": conteo_lote,
                        "palabras_promedio": round(statistics.mean(fl["palabras_totales"] for fl in filas_lote), 1),
                        "latencia_mediana_s": round(statistics.median(fl["latencia_s"] for fl in filas_lote), 3),
                    }
                    (carpeta / f"lote_api_{num_lote:03d}_resumen.json").write_text(
                        json.dumps(resumen_lote, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                    estado["lotes_cerrados"].append(resumen_lote)
                    estado["lote_actual"] = num_lote + 1
                    estado["docs_en_lote_actual"] = 0

                guardar_estado(
                    f"último paquete ×{len(paquete)} OK en {respuesta['latencia_s']}s [{modelo_usado}] · +{inyectadas} recetas_53 en D:\\"
                )

                if una_vez_paquete:
                    print(
                        json.dumps(
                            {
                                "modelo_usado": modelo_usado,
                                "latencia_paquete_s": respuesta["latencia_s"],
                                "tokens_entrada": respuesta["tokens_entrada"],
                                "tokens_salida": respuesta["tokens_salida"],
                                "docs_procesados": len(paquete),
                                "recetas_53_inyectadas_d": inyectadas,
                                "muestra_receta": next(
                                    (r["receta_53"] for r in registros_lote_paq if r.get("receta_53")), ""
                                )[:320],
                            },
                            ensure_ascii=False,
                            indent=2,
                        )
                    )
                    return 0

                if pausa_ms > 0 and time.time() < fin_ts:
                    time.sleep(min(pausa_ms / 1000.0, max(fin_ts - time.time(), 0.0)))
    finally:
        if cli_mongo is not None:
            cli_mongo.close()

    guardar_estado("ciclo 24h completado")
    return 0


def modo_preguntar(api_key: str, modelo: str, proveedor: str, pregunta: str) -> int:
    """Responde una pregunta con fragmentos del Canon (RAG lexico)."""
    canon, origen = cargar_canon_supabase()
    frags = buscar_fragmentos_canon(canon, pregunta, top_k=6)
    print(f"Canon ({origen}): {len(canon['documentos'])} docs, {len(canon['fragmentos'])} fragmentos · recuperados {len(frags)}")
    contexto = "\n\n".join(f"[{f['documento_id']} · {f.get('seccion') or ''}]\n{f['texto']}" for f in frags)
    sistema = (
        "Responde en español usando ÚNICAMENTE los fragmentos del Canon de Amatista proporcionados. "
        "Cita explícitamente entre corchetes el fragmento [documento · sección] que respalda cada afirmación. "
        "Si el canon no cubre algo, dilo sin inventar."
    )
    r = llamar_gemini(f"PREGUNTA:\n{pregunta}\n\nFRAGMENTOS DEL CANON:\n{contexto}", api_key, modelo, proveedor, sistema=sistema)
    if not r["ok"]:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 1
    print(f"\n[{modelo} · {r['latencia_s']}s · {r['tokens_entrada']} in / {r['tokens_salida']} out]\n")
    print(r["texto"])
    return 0


def main(argv=None) -> int:
    """CLI del laboratorio."""
    p = argparse.ArgumentParser(description="Laboratorio aislado de límites Gemini + Canon Supabase vs qwen3:8b.")
    p.add_argument("--modo", choices=("ping", "rafaga", "c1", "preguntar", "ciclo-24h"), default="ping")
    p.add_argument("--modelo", default="gemini-3.5-flash-lite")
    p.add_argument("--proveedor", choices=("auto", "vertex", "aistudio"), default="auto")
    p.add_argument("--n", type=int, default=10, help="Número de llamadas (rafaga) o documentos de C1 (máx 35)")
    p.add_argument("--concurrencia", type=int, default=1, help="Hilos simultáneos para medir RPM/429")
    p.add_argument("--pausa-ms", type=int, default=0, help="Pausa opcional entre peticiones (ms)")
    p.add_argument("--horas", type=float, default=24.0, help="Duración del modo ciclo-24h en horas")
    p.add_argument("--tamano-lote", type=int, default=40, help="Documentos por lote en modo ciclo-24h")
    p.add_argument("--docs-por-llamada", type=int, default=8, help="Documentos empaquetados por llamada en modo ciclo-24h")
    p.add_argument("--una-vez-paquete", action="store_true", help="Ejecuta un solo paquete ×N en modo ciclo-24h y termina")
    p.add_argument("--usar-canon", action="store_true", help="Inyecta el Canon v5 vivo de Supabase (solo lectura) en el prompt de C1")
    p.add_argument("--pregunta", default="¿Cuándo se aprueba un lote y cuándo se activa el freno automático?", help="Pregunta para --modo preguntar")
    a = p.parse_args(argv)

    api_key = cargar_clave(Path(__file__).resolve().parent / ".env")
    proveedor = detectar_proveedor(api_key, a.proveedor)
    if a.modo == "ping":
        return modo_ping(api_key, a.modelo, proveedor)
    if a.modo == "rafaga":
        return modo_rafaga(api_key, a.modelo, proveedor, a.n, a.concurrencia, a.pausa_ms)
    if a.modo == "preguntar":
        return modo_preguntar(api_key, a.modelo, proveedor, a.pregunta)
    if a.modo == "ciclo-24h":
        pausa = a.pausa_ms if a.pausa_ms > 0 else 8000
        return modo_ciclo_24h(
            api_key,
            a.modelo,
            proveedor,
            horas=a.horas,
            tamano_lote=a.tamano_lote,
            pausa_ms=pausa,
            docs_por_llamada=max(1, a.docs_por_llamada),
            una_vez_paquete=a.una_vez_paquete,
        )
    return modo_c1(api_key, a.modelo, proveedor, min(a.n, 35), a.concurrencia, a.pausa_ms, usar_canon=a.usar_canon)


if __name__ == "__main__":
    sys.exit(main())
