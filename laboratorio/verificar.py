"""Comprueba que la computadora del laboratorio está lista: Ollama, el modelo de embeddings y la conexión a Supabase.

    python -m laboratorio.verificar                       # lo necesario para indexar
    python -m laboratorio.verificar --revisor qwen3:8b    # además, mide la velocidad de un modelo revisor

Nunca imprime ni guarda el valor de una clave ni del token de GitHub: solo si está, de qué tipo es y si Supabase la acepta. Escribe el
resultado en salidas/verificacion_laboratorio.json (sin secretos) para entregarlo a una persona. Termina con código 1
si alguna comprobación necesaria falla.
"""
import argparse
import json
import os
import platform
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from indexador.entorno import cargar_env
import yaml

from indexador.indexar import DIMENSIONES, cabeceras_github, url_cruda

OK, AVISO, FALLA = 'ok', 'aviso', 'falla'


def pedir(url, datos=None, cabeceras=None, metodo=None, timeout=120):
    """Devuelve (código, cuerpo como texto). No lanza por errores HTTP; sí por errores de red."""
    cuerpo = None if datos is None else json.dumps(datos).encode('utf-8')
    req = urllib.request.Request(url, data=cuerpo, method=metodo,
                                 headers={'Content-Type': 'application/json', 'User-Agent': 'amatista-ia-laboratorio',
                                          **(cabeceras or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')


def tipo_de_clave(valor):
    if not valor:
        return None
    if valor.startswith('sb_secret_'):
        return 'secreta'
    if valor.startswith('sb_publishable_'):
        return 'publicable'
    if valor.startswith('eyJ'):
        return 'jwt_antigua'
    return 'desconocida'


# --- Ollama ----------------------------------------------------------------------------------------------------------
def revisar_ollama(base, modelo, pedir=pedir):
    r = []
    try:
        c, cuerpo = pedir(f'{base}/api/version', timeout=10)
    except OSError as e:
        return [('ollama', FALLA, f'no responde en {base} ({e.__class__.__name__}). ¿Está instalado y corriendo?')]
    r.append(('ollama', OK if c == 200 else FALLA, f"versión {json.loads(cuerpo).get('version')}" if c == 200 else f'HTTP {c}'))
    if c != 200:
        return r
    _, cuerpo = pedir(f'{base}/api/tags', timeout=10)
    nombres = [m['name'] for m in json.loads(cuerpo).get('models', [])]
    if not any(n in (modelo, f'{modelo}:latest') for n in nombres):
        r.append(('modelo_embeddings', FALLA, f'falta {modelo}: corre «ollama pull {modelo}». Instalados: {nombres or "ninguno"}'))
        return r
    t = time.perf_counter()
    c, cuerpo = pedir(f'{base}/api/embed', {'model': modelo, 'input': ['¿Cuáles son las cinco etapas del embudo?']}, timeout=300)
    seg = time.perf_counter() - t
    if c != 200:
        r.append(('modelo_embeddings', FALLA, f'/api/embed respondió HTTP {c}: {cuerpo[:200]}'))
        return r
    dim = len(json.loads(cuerpo)['embeddings'][0])
    r.append(('modelo_embeddings', OK if dim == DIMENSIONES else FALLA,
              f'{modelo}: {dim} dimensiones (se esperan {DIMENSIONES}), primera llamada {seg:.1f} s'))
    return r


def medir_revisor(base, modelo, pedir=pedir):
    """Velocidad de un modelo generativo con una instrucción corta. Es un aviso, no una falla: elegir modelo es otra decisión."""
    try:
        c, cuerpo = pedir(f'{base}/api/generate', {
            'model': modelo, 'stream': False, 'options': {'num_predict': 80, 'temperature': 0},
            'prompt': 'Resume en dos frases qué es un embudo de calidad de datos con cinco etapas.'}, timeout=900)
    except OSError as e:
        return [('revisor', AVISO, f'no se pudo medir ({e.__class__.__name__})')]
    if c != 200:
        return [('revisor', AVISO, f'{modelo}: HTTP {c}. ¿Corriste «ollama pull {modelo}»? {cuerpo[:150]}')]
    d = json.loads(cuerpo)
    gen = d.get('eval_count', 0) / max(d.get('eval_duration', 1), 1) * 1e9
    lect = d.get('prompt_eval_count', 0) / max(d.get('prompt_eval_duration', 1), 1) * 1e9
    carga = d.get('load_duration', 0) / 1e9
    return [('revisor', OK, f'{modelo}: genera {gen:.1f} tok/s, lee {lect:.1f} tok/s, carga {carga:.1f} s')]


# --- Supabase --------------------------------------------------------------------------------------------------------
def _explicar(codigo, cuerpo):
    if codigo == 401:
        return 'Supabase rechazó la clave (401): revisa que esté completa y vigente'
    if codigo == 404 and ('PGRST205' in cuerpo or 'PGRST202' in cuerpo or 'Could not find' in cuerpo):
        return 'la migración no está aplicada: faltan las tablas o la función (ver LABORATORIO.md, paso 0)'
    return f'HTTP {codigo}: {cuerpo[:200]}'


def revisar_supabase(url, publicable, secreta, pedir=pedir):
    r = []
    if not url:
        return [('supabase_url', FALLA, 'falta SUPABASE_URL')]
    base = url.rstrip('/').removesuffix('/rest/v1') + '/rest/v1'
    r.append(('supabase_url', OK if base.startswith('https://') and '.supabase.co/' in base else AVISO, base))

    for nombre, valor, esperado in (('SUPABASE_PUBLISHABLE_KEY', publicable, 'publicable'),
                                    ('SUPABASE_SECRET_KEY', secreta, 'secreta')):
        tipo = tipo_de_clave(valor)
        if tipo is None:
            r.append((nombre, FALLA, 'no está definida'))
            continue
        if tipo != esperado and tipo != 'jwt_antigua':
            r.append((nombre, FALLA, f'parece una clave {tipo}, no {esperado}: ¿están intercambiadas?'))
            continue
        try:
            c, cuerpo = pedir(f'{base}/canon_documentos?select=id', cabeceras={'apikey': valor}, timeout=30)
        except OSError as e:
            r.append((nombre, FALLA, f'sin conexión con Supabase ({e.__class__.__name__}): ¿red o proxy?'))
            continue
        if c == 200:
            r.append((nombre, OK, f'acepta la clave {esperado}; documentos del canon en la base: {len(json.loads(cuerpo))}'))
        else:
            r.append((nombre, FALLA, _explicar(c, cuerpo)))

    if publicable and tipo_de_clave(publicable) in ('publicable', 'jwt_antigua'):
        cero = '[' + ','.join(['0'] * DIMENSIONES) + ']'
        try:
            c, cuerpo = pedir(f'{base}/rpc/buscar_canon', {'consulta': 'embudo', 'consulta_embedding': cero, 'cuantos': 1},
                              cabeceras={'apikey': publicable}, metodo='POST', timeout=30)
            r.append(('buscar_canon', OK if c == 200 else FALLA, 'la función responde' if c == 200 else _explicar(c, cuerpo)))
        except OSError as e:
            r.append(('buscar_canon', FALLA, f'sin conexión ({e.__class__.__name__})'))
    return r


def revisar_github(canon, pedir=pedir):
    """Lee el primer documento de cada repositorio del canon en su commit fijado, como lo hará el indexador."""
    r = []
    for nombre, repo in canon['repositorios'].items():
        doc = next((d for d in canon['documentos'] if d['repo'] == nombre), None)
        if not doc:
            continue
        try:
            c, _ = pedir(url_cruda(repo, doc['ruta']), cabeceras=cabeceras_github(), timeout=30)
        except OSError as e:
            r.append((f'github_{nombre}', FALLA, f'sin conexión con GitHub ({e.__class__.__name__})'))
            continue
        if c == 200:
            r.append((f'github_{nombre}', OK, f"lee {doc['ruta']} en {repo['commit'][:7]}"))
        elif c == 404 and not os.environ.get('GITHUB_TOKEN'):
            r.append((f'github_{nombre}', FALLA, '404: el repositorio es privado; falta GITHUB_TOKEN de solo lectura en .env'))
        else:
            r.append((f'github_{nombre}', FALLA, f'HTTP {c}: el token no tiene acceso de lectura a ese repositorio, o venció'))
    return r


def revisar_equipo(carpeta_modelos):
    r = [('python', OK if sys.version_info >= (3, 10) else FALLA, platform.python_version())]
    try:
        import yaml  # noqa: F401
        r.append(('pyyaml', OK, 'instalado'))
    except ImportError:
        r.append(('pyyaml', FALLA, 'falta: python -m pip install pyyaml'))
    libre = shutil.disk_usage(carpeta_modelos).free / 1e9
    r.append(('disco_modelos', OK if libre >= 15 else AVISO, f'{libre:.0f} GB libres en {carpeta_modelos} (bge-m3 ≈ 1.2 GB, un 8B ≈ 5 GB)'))
    r.append(('sistema', OK, f'{platform.system()} {platform.release()} · {platform.processor() or platform.machine()} · {os.cpu_count()} hilos'))
    return r


def main(argv=None):
    cargar_env()
    p = argparse.ArgumentParser(description='Comprueba la computadora del laboratorio para Amatista IA.')
    p.add_argument('--ollama', default=os.environ.get('OLLAMA_HOST', 'http://127.0.0.1:11434'))
    p.add_argument('--modelo', default='bge-m3')
    p.add_argument('--revisor', help='modelo generativo cuya velocidad medir (opcional)')
    p.add_argument('--salida', type=Path, default=Path('salidas/verificacion_laboratorio.json'))
    a = p.parse_args(argv)
    base = a.ollama if a.ollama.startswith('http') else f'http://{a.ollama}'
    carpeta = os.environ.get('OLLAMA_MODELS') or str(Path.home())

    canon = yaml.safe_load(Path('canon/canon.yml').read_text(encoding='utf-8'))
    resultados = revisar_equipo(carpeta) + revisar_github(canon) + revisar_ollama(base.rstrip('/'), a.modelo)
    if a.revisor:
        resultados += medir_revisor(base.rstrip('/'), a.revisor)
    resultados += revisar_supabase(os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_PUBLISHABLE_KEY'),
                                   os.environ.get('SUPABASE_SECRET_KEY'))

    marca = {OK: '✔', AVISO: '!', FALLA: '✘'}
    for nombre, estado, detalle in resultados:
        print(f'{marca[estado]} {nombre:26s} {detalle}')
    fallas = [n for n, e, _ in resultados if e == FALLA]
    a.salida.parent.mkdir(parents=True, exist_ok=True)
    a.salida.write_text(json.dumps({
        'fecha': time.strftime('%Y-%m-%d %H:%M'), 'listo': not fallas,
        'comprobaciones': [{'nombre': n, 'estado': e, 'detalle': d} for n, e, d in resultados],
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    print('\nLISTO para indexar.' if not fallas else f'\nFALTA: {", ".join(fallas)}')
    return 0 if not fallas else 1


if __name__ == '__main__':
    sys.exit(main())
