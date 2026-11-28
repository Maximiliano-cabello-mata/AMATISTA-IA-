"""Relevo 24 h (Telemetría -> GitHub | Conocimiento Comunitario -> Núcleo RAG D:\\).

Extrae cada lote listo de ``/tmp/g7b-bandeja-salida`` en la VM de Oracle usando la llave asegurada
en ``~/.ssh/oracle_vm_amatista.key``, verifica su ``SHA-256`` y aplica separación estricta:
- Lotes de **telemetría** (``blender-open-data``, ``web3d_y_fallas_hw``) -> rama aislada
  ``telemetria-vm-24h`` en GitHub (``[skip ci]``). Jamás entran al RAG documental.
- Lotes de **conocimiento comunitario 5.3** (``comunidad_conocimiento_53``: Stack Exchange aceptadas,
  Release Notes ``CC-BY-SA-4.0`` y patrones AST ``GPLv3/MIT``) -> se validan con ``PiedraRosetta53``
  y ``agente_curador`` y entran directo a ``D:\\Amatista_Nucleo_RAG``.
Tras procesar y verificar, borra de inmediato el lote en la VM para mantener 0 bytes retenidos allá.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

RUTA_NUCLEO_PROYECTO = Path(r"C:\Users\KANEDA\.gemini\antigravity\scratch\amatista-nucleo-blender")
if str(RUTA_NUCLEO_PROYECTO) not in sys.path:
    sys.path.insert(0, str(RUTA_NUCLEO_PROYECTO))

SSH_KEY_DEFAULT = Path.home() / ".ssh" / "oracle_vm_amatista.key"
SSH_KEY_FALLBACK = Path(r"C:\Users\KANEDA\Downloads\Claves y Certificados\ssh-key-2026-09-27.key")
SSH_KEY = Path(os.environ.get("AMATISTA_SSH_KEY", str(SSH_KEY_DEFAULT if SSH_KEY_DEFAULT.exists() else SSH_KEY_FALLBACK)))
KNOWN_HOSTS = Path.home() / ".ssh" / "known_hosts"

VM_HOST = os.environ.get("AMATISTA_VM_HOST", "opc@158.101.118.222")
VM_BANDEJA = "/tmp/g7b-bandeja-salida"
REPO_URL = "https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl.git"
RAMA_DESTINO = "telemetria-vm-24h"
PUENTE_DIR = Path(r"C:\Users\KANEDA\.gemini\antigravity\scratch\puente-telemetria-vm")
BANDEJA_RAG_VM = Path(r"D:\Amatista_Nucleo_RAG\bandeja_comunidad_vm")
ESTADO_LOCAL = Path(__file__).resolve().parents[1] / "resultados" / "ciclo_24h" / "estado_relevo_vm_github.json"


def _opciones_ssh() -> list[str]:
    opts = ["-i", str(SSH_KEY), "-o", "BatchMode=yes", "-o", "ConnectTimeout=15"]
    if KNOWN_HOSTS.exists() and KNOWN_HOSTS.stat().st_size > 0:
        opts += ["-o", f"UserKnownHostsFile={KNOWN_HOSTS}", "-o", "StrictHostKeyChecking=accept-new"]
    else:
        opts += ["-o", "StrictHostKeyChecking=accept-new"]
    return opts


def _ssh(cmd: str, timeout: int = 45) -> subprocess.CompletedProcess:
    """Ejecuta un comando en la VM por SSH."""
    return subprocess.run(
        ["ssh.exe", *_opciones_ssh(), VM_HOST, cmd],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _scp(remoto: str, destino: Path, timeout: int = 120) -> subprocess.CompletedProcess:
    """Copia un archivo remoto de la VM."""
    return subprocess.run(
        ["scp.exe", *_opciones_ssh(), f"{VM_HOST}:{remoto}", str(destino)],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _git(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    """Ejecuta git en el repo puente."""
    return subprocess.run(["git", *args], cwd=str(PUENTE_DIR), capture_output=True, text=True, timeout=timeout)


def sha256_archivo(ruta: Path) -> str:
    """SHA-256 por bloques de un archivo."""
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        while b := f.read(1024 * 1024):
            h.update(b)
    return h.hexdigest()


def preparar_repo_puente() -> None:
    """Inicializa el repo puente y la rama aislada si no existen."""
    if (PUENTE_DIR / ".git").exists():
        return
    PUENTE_DIR.mkdir(parents=True, exist_ok=True)
    _git(["init"])
    _git(["config", "core.autocrlf", "false"])
    _git(["config", "user.name", "Amatista Telemetria VM"])
    _git(["config", "user.email", "telemetria-vm@amatista-3dt.tech"])
    _git(["remote", "add", "origin", REPO_URL])
    ls_rem = _git(["ls-remote", "--heads", "origin", RAMA_DESTINO])
    if ls_rem.returncode == 0 and RAMA_DESTINO in (ls_rem.stdout or ""):
        _git(["fetch", "--depth=1", "origin", RAMA_DESTINO])
        _git(["checkout", "-B", RAMA_DESTINO, f"origin/{RAMA_DESTINO}"])
    else:
        _git(["checkout", "--orphan", RAMA_DESTINO])
        readme = PUENTE_DIR / "README.md"
        readme.write_text(
            "# Lotes de telemetría 24h desde VM Oracle\n\n"
            "Rama aislada con lotes `.jsonl.gz` e `informe.json` normalizados con `g7b.hardware/1`.\n",
            encoding="utf-8",
        )
        _git(["add", "README.md"])
        _git(["commit", "-m", "chore(telemetria-vm): inicializar rama aislada de lotes [skip ci]"])
        push = _git(["push", "-u", "origin", RAMA_DESTINO])
        if push.returncode != 0:
            raise RuntimeError(f"Error al crear rama {RAMA_DESTINO}: {push.stderr}")


def guardar_estado(datos: dict) -> None:
    """Guarda el estado del relevo de forma atómica."""
    ESTADO_LOCAL.parent.mkdir(parents=True, exist_ok=True)
    datos["actualizado_en"] = time.strftime("%Y-%m-%d %H:%M:%S")
    tmp = ESTADO_LOCAL.with_suffix(".tmp")
    tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, ESTADO_LOCAL)


def _ingestar_lote_comunidad_en_rag_d(gz_local: Path, inf_local: Path, meta: dict) -> dict:
    """Valida con PiedraRosetta53 + agente_curador e ingiere conocimiento comunitario de la VM en D:\\."""
    from nucleo_rag.agente_curador import evaluar_documento_heuristica_canon
    from nucleo_rag.almacen_rag import AlmacenNucleoRAG
    from nucleo_rag.fragmentador import clasificar_dominio, fragmentar_documento
    from nucleo_rag.piedra_rosetta_53 import enriquecer_texto_con_rosetta

    BANDEJA_RAG_VM.mkdir(parents=True, exist_ok=True)
    destino_gz = BANDEJA_RAG_VM / gz_local.name
    destino_inf = BANDEJA_RAG_VM / inf_local.name
    if destino_gz.exists():
        destino_gz.unlink()
    if destino_inf.exists():
        destino_inf.unlink()
    shutil.move(str(gz_local), str(destino_gz))
    shutil.move(str(inf_local), str(destino_inf))

    almacen = AlmacenNucleoRAG()
    aceptados = 0
    rechazados = 0
    frags_tot = 0

    with gzip.open(destino_gz, "rt", encoding="utf-8", errors="replace") as fin, almacen.conectar() as conn:
        for linea in fin:
            if not linea.strip():
                continue
            raw = json.loads(linea)
            ev = evaluar_documento_heuristica_canon(raw, sim_prototipo_pos=0.66)
            if ev["decision"] == "rechazar":
                rechazados += 1
                continue
            ver = str(raw.get("version_blender") or ev.get("version_blender") or "")
            texto_enriq, _ = enriquecer_texto_con_rosetta(str(raw.get("texto") or ""), version_origen=ver)
            titulo = str(raw.get("titulo") or raw["doc_id"])
            fuente = str(raw.get("fuente") or "vm-comunidad-53")
            url = str(raw.get("url") or "")
            licencia = str(raw.get("licencia") or "CC-BY-SA-4.0")
            dominio = clasificar_dominio(fuente, titulo, texto_enriq, url)
            frags = fragmentar_documento(titulo=titulo, fuente=fuente, texto=texto_enriq, version_blender=ver or "5.3")
            if not frags:
                continue

            nivel = "lote_aprobado" if ev["decision"] == "aceptar" else "lote_revisado_util"
            peso = 1.22 if ev["decision"] == "aceptar" else 1.10
            conn.execute("DELETE FROM fragmentos WHERE doc_id = ?", (raw["doc_id"],))
            almacen.upsert_documento_y_fragmentos(
                conn,
                doc={
                    "doc_id": raw["doc_id"],
                    "fuente": fuente,
                    "titulo": titulo,
                    "url": url,
                    "licencia": licencia,
                    "nivel_confianza": nivel,
                    "peso_confianza": peso,
                    "version_blender": ver or "5.3",
                    "dominio": dominio,
                    "lote_origen": f"vm_oracle_24h:{meta.get('lote_vm', 0)}",
                    "palabras": len(texto_enriq.split()),
                    "metadatos": {
                        "score_curador": ev["score_calidad"],
                        "estado_compatibilidad_53": ev.get("estado_compatibilidad_53", ""),
                    },
                },
                fragmentos=[
                    {
                        "orden": f.orden,
                        "seccion": f.seccion,
                        "texto": f.texto,
                        "texto_contextual": f.texto_contextual,
                        "operadores_bpy": f.operadores_bpy,
                        "tiene_codigo": f.tiene_codigo,
                        "prioridad_vector": 0 if nivel == "lote_aprobado" else 1,
                    }
                    for f in frags
                ],
            )
            aceptados += 1
            frags_tot += len(frags)
        conn.commit()

    return {"aceptados_rag_d": aceptados, "rechazados_curador": rechazados, "fragmentos_sqlite": frags_tot}


def procesar_bandeja(estado: dict) -> int:
    """Procesa los lotes listos en la VM separando telemetría (GitHub) y conocimiento (RAG D:\\)."""
    ssh_key_actual = Path(os.environ.get("AMATISTA_SSH_KEY", str(SSH_KEY_DEFAULT if SSH_KEY_DEFAULT.exists() else SSH_KEY_FALLBACK)))
    globals()["SSH_KEY"] = ssh_key_actual

    r = _ssh(f"ls -1 {VM_BANDEJA}/*.informe.json 2>/dev/null || true")
    if r.returncode != 0:
        estado["ultimo_error"] = f"SSH ls fallo: {r.stderr.strip()[:160]}"
        return 0
    informes_remotos = [l.strip() for l in (r.stdout or "").splitlines() if l.strip().endswith(".informe.json")]
    enviados = 0
    carpeta_lotes = PUENTE_DIR / "lotes"
    carpeta_lotes.mkdir(parents=True, exist_ok=True)

    for ruta_inf_rem in informes_remotos:
        nombre_inf = Path(ruta_inf_rem).name
        inf_local = carpeta_lotes / nombre_inf
        if _scp(ruta_inf_rem, inf_local).returncode != 0:
            continue
        meta = json.loads(inf_local.read_text(encoding="utf-8"))
        nombre_gz = meta["archivo"]
        ruta_gz_rem = f"{VM_BANDEJA}/{nombre_gz}"
        gz_local = carpeta_lotes / nombre_gz
        if _scp(ruta_gz_rem, gz_local, timeout=180).returncode != 0:
            inf_local.unlink(missing_ok=True)
            continue

        sha_real = sha256_archivo(gz_local)
        if sha_real != meta.get("sha256_gz"):
            inf_local.unlink(missing_ok=True)
            gz_local.unlink(missing_ok=True)
            estado["ultimo_error"] = f"SHA-256 no coincide en {nombre_gz}"
            continue

        borrar_remotos = [f"'{ruta_gz_rem}'", f"'{ruta_inf_rem}'"]

        # CARRIL A: DOCUMENTACIÓN Y CONOCIMIENTO 5.3 -> Directo al Núcleo RAG en D:\
        if meta.get("tipo") in ("comunidad_conocimiento_53", "documentacion_53"):
            res_rag = _ingestar_lote_comunidad_en_rag_d(gz_local, inf_local, meta)
            borrado = _ssh(f"rm -f {' '.join(borrar_remotos)} && ls -1 {VM_BANDEJA} | wc -l")
            restantes = (borrado.stdout or "").strip()
            estado["lotes_comunidad_rag"] = int(estado.get("lotes_comunidad_rag", 0)) + 1
            estado["docs_comunidad_ingeridos_d"] = int(estado.get("docs_comunidad_ingeridos_d", 0)) + res_rag["aceptados_rag_d"]
            estado["ultimo_lote_comunidad"] = {
                "archivo": nombre_gz,
                "tipo": meta.get("tipo"),
                "por_fuente": meta.get("por_fuente", {}),
                "progreso_sphinx": meta.get("progreso_sphinx", {}),
                "sha256_gz": sha_real,
                **res_rag,
                "archivos_restantes_en_bandeja_vm": restantes,
                "procesado_en": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            estado["ultimo_error"] = None
            guardar_estado(estado)
            enviados += 1
            continue

        # CARRIL B: TELEMETRÍA DE HARDWARE -> Rama aislada telemetria-vm-24h en GitHub
        nombre_mat = meta.get("archivo_matriz")
        archivos_git = [f"lotes/{nombre_inf}", f"lotes/{nombre_gz}", "indice_lotes.jsonl"]
        if nombre_mat:
            ruta_mat_rem = f"{VM_BANDEJA}/{nombre_mat}"
            mat_local = carpeta_lotes / nombre_mat
            if _scp(ruta_mat_rem, mat_local, timeout=120).returncode != 0:
                inf_local.unlink(missing_ok=True)
                gz_local.unlink(missing_ok=True)
                continue
            if sha256_archivo(mat_local) != meta.get("sha256_matriz"):
                inf_local.unlink(missing_ok=True)
                gz_local.unlink(missing_ok=True)
                mat_local.unlink(missing_ok=True)
                estado["ultimo_error"] = f"SHA-256 no coincide en {nombre_mat}"
                continue
            archivos_git.append(f"lotes/{nombre_mat}")
            borrar_remotos.append(f"'{ruta_mat_rem}'")

        indice_path = PUENTE_DIR / "indice_lotes.jsonl"
        lineas_prev = indice_path.read_text(encoding="utf-8") if indice_path.exists() else ""
        if nombre_gz not in lineas_prev:
            with indice_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(meta, ensure_ascii=False) + "\n")

        _git(["add", *archivos_git])
        msg = f"data(telemetria-vm): {nombre_gz} ({meta.get('benchmarks_validos', meta.get('filas', 0))} items) [skip ci]"
        commit = _git(["commit", "-m", msg])
        if commit.returncode != 0 and "nothing to commit" not in (commit.stdout + commit.stderr):
            estado["ultimo_error"] = f"git commit fallo: {commit.stderr.strip()[:160]}"
            continue

        push = _git(["push", "origin", RAMA_DESTINO], timeout=180)
        if push.returncode != 0:
            estado["ultimo_error"] = f"git push fallo: {push.stderr.strip()[:160]}"
            continue

        sha_commit = (_git(["rev-parse", "--short", "HEAD"]).stdout or "").strip()
        borrado = _ssh(f"rm -f {' '.join(borrar_remotos)} && ls -1 {VM_BANDEJA} | wc -l")
        restantes = (borrado.stdout or "").strip()

        estado["lotes_enviados"] = int(estado.get("lotes_enviados", 0)) + 1
        estado["bytes_enviados"] = int(estado.get("bytes_enviados", 0)) + int(meta.get("bytes_gz", 0))
        estado["benchmarks_enviados"] = int(estado.get("benchmarks_enviados", 0)) + int(meta.get("benchmarks_validos", 0))
        estado["ultimo_lote_enviado"] = {
            "archivo": nombre_gz,
            "bytes_gz": meta.get("bytes_gz"),
            "sha256_gz": sha_real,
            "commit_github": sha_commit,
            "rama": RAMA_DESTINO,
            "archivos_restantes_en_bandeja_vm": restantes,
            "enviado_en": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        estado["ultimo_error"] = None
        guardar_estado(estado)
        enviados += 1
    return enviados


def main() -> int:
    """Bucle del relevo (o una sola vez)."""
    p = argparse.ArgumentParser()
    p.add_argument("--horas", type=float, default=24.0)
    p.add_argument("--intervalo-s", type=int, default=60)
    p.add_argument("--una-vez", action="store_true")
    a = p.parse_args()

    preparar_repo_puente()
    estado = json.loads(ESTADO_LOCAL.read_text(encoding="utf-8")) if ESTADO_LOCAL.is_file() else {
        "iniciado_en": time.strftime("%Y-%m-%d %H:%M:%S"),
        "destino_github": f"{REPO_URL}#{RAMA_DESTINO}",
        "lotes_enviados": 0,
        "lotes_comunidad_rag": 0,
        "docs_comunidad_ingeridos_d": 0,
        "bytes_enviados": 0,
        "benchmarks_enviados": 0,
        "actividad": "iniciando",
    }
    guardar_estado(estado)

    if a.una_vez:
        procesar_bandeja(estado)
        return 0

    fin_ts = time.time() + a.horas * 3600.0
    while time.time() < fin_ts:
        estado["actividad"] = "vigilando bandeja documental en VM Oracle (Modo 100 % Documentación 5.3 -> D:\\)"
        guardar_estado(estado)
        try:
            procesar_bandeja(estado)
        except Exception as exc:
            estado["ultimo_error"] = f"{type(exc).__name__}: {str(exc)[:180]}"
            guardar_estado(estado)
        time.sleep(min(float(a.intervalo_s), max(fin_ts - time.time(), 1.0)))

    estado["actividad"] = "ciclo 24h completado"
    guardar_estado(estado)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
