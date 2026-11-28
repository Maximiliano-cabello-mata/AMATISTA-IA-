# [REVISION 2026-11-27] Indexador del canon: lee los documentos de canon/canon.yml en su commit fijado, los filtra y fragmenta,
# calcula embeddings con Ollama (bge-m3, 1024 dim.) y sincroniza con Supabase (REST, clave secreta).
# Entradas: canon.yml, GitHub raw o clones locales, Ollama, SUPABASE_URL/SUPABASE_SECRET_KEY.
# Salidas: tablas canon_documentos/canon_fragmentos o salidas/fragmentos.jsonl (--simulacro).
"""Indexador del canon de Amatista IA (canon/canon.yml → Supabase).

    python -m indexador.indexar canon/canon.yml --simulacro
    python -m indexador.indexar canon/canon.yml                      # Ollama local + Supabase
    python -m indexador.indexar canon/canon.yml --local g7b=../amatista-g7b-etl,amatista=../amatista-recuperada-20261106

Pasos, por documento del canon:
  1. Lo lee del repositorio de origen EN EL COMMIT FIJADO (GitHub raw, o un clon local con --local).
  2. Quita las secciones de `excluir_secciones` (o deja solo las de `solo_secciones`).
  3. Lo parte por títulos en fragmentos de hasta --max-palabras, sin cortar bloques de código ni tablas. Cada
     fragmento conserva la ruta de títulos donde vive («4. El embudo > Suma valor»).
  4. Calcula el vector de cada fragmento con Ollama (por omisión bge-m3: multilingüe, 1024 dimensiones). El vector
     se calcula sobre «título del documento · sección · texto», para que un fragmento suelto no pierda su contexto.
  5. Lo sube a Supabase con la clave secreta. Si el hash del documento y el modelo no cambiaron, no hace nada:
     volver a correrlo es barato.

Variables de entorno (solo para subir): SUPABASE_URL y SUPABASE_SECRET_KEY, del entorno o de un archivo .env. La clave secreta nunca va en el
repositorio ni en la línea de comandos.

Solo usa la biblioteca estándar y PyYAML.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

from indexador.entorno import cargar_env

DIMENSIONES = 1024
TITULO = re.compile(r'^(#{1,6})\s+(.+?)\s*#*\s*$')
VALLA = re.compile(r'^\s*(```|~~~)')


def sha256(texto):
    """Hash SHA-256 hexadecimal de un texto UTF-8."""
    return hashlib.sha256(texto.encode('utf-8')).hexdigest()


def _titulo_limpio(t):
    """Quita anclas y marcas para comparar títulos: '## 2. Hardware records (`g7b.hardware/1`)' → igual sin espacios extra."""
    t = re.sub(r'<a id="[^"]*"></a>', '', t)
    return re.sub(r'\s+', ' ', t).strip()


def lineas_con_titulos(texto):
    """[(línea, nivel_o_None, título_o_None)], ignorando lo que parece título dentro de bloques de código."""
    en_codigo = False
    for linea in texto.splitlines():
        if VALLA.match(linea):
            en_codigo = not en_codigo
            yield linea, None, None
            continue
        m = None if en_codigo else TITULO.match(linea)
        yield (linea, len(m.group(1)), _titulo_limpio(m.group(2))) if m else (linea, None, None)


def filtrar_secciones(texto, excluir=(), solo=()):
    """Quita las secciones cuyo título está en `excluir` (con todo lo que cuelga de ellas) o, si `solo` no está vacío,
    deja únicamente esas secciones (con su contenido y subtítulos). El texto antes del primer título se conserva salvo
    con `solo`."""
    excluir = {_titulo_limpio(e) for e in excluir}
    solo = {_titulo_limpio(s) for s in solo}
    salida, cortando, nivel_corte, dentro_solo, nivel_solo = [], False, 0, False, 0
    for linea, nivel, titulo in lineas_con_titulos(texto):
        if nivel is not None:
            if cortando and nivel <= nivel_corte:
                cortando = False
            if dentro_solo and nivel <= nivel_solo:
                dentro_solo = False
            if titulo in excluir:
                cortando, nivel_corte = True, nivel
            if solo and titulo in solo:
                dentro_solo, nivel_solo = True, nivel
        if cortando or (solo and not dentro_solo):
            continue
        salida.append(linea)
    faltan = (excluir | solo) - {t for _, n, t in lineas_con_titulos(texto) if n is not None}
    if faltan:
        raise ValueError(f'secciones que no existen en el documento: {sorted(faltan)}')
    return '\n'.join(salida).strip() + '\n'


def _palabras(texto):
    """Numero de palabras (separadas por espacios) de un texto."""
    return len(texto.split())


def fragmentar(texto, max_palabras=260):
    """Parte un Markdown en fragmentos [{seccion, texto}] por títulos y párrafos. Un bloque de código no se parte (si
    pasa del máximo, va solo en su fragmento); una tabla larga se parte por filas, repitiendo su encabezado."""
    fragmentos, pila, bloque, buffer, en_codigo = [], [], [], [], False

    def ruta():
        """Ruta de titulos actual ('A > B > C') o None."""
        return ' > '.join(t for _, t in pila) or None

    def cerrar_bloque():
        """Pasa el bloque de lineas acumulado al buffer de parrafos."""
        if bloque:
            buffer.append('\n'.join(bloque).strip())
            bloque.clear()

    def partir_tabla(tabla):
        """Una tabla más larga que el máximo se parte en grupos de filas, repitiendo el encabezado en cada uno."""
        filas = tabla.splitlines()
        if _palabras(tabla) <= max_palabras or len(filas) < 4:
            return [tabla]
        cabeza, grupos, grupo = filas[:2], [], []
        for fila in filas[2:]:
            if grupo and _palabras('\n'.join(cabeza + grupo + [fila])) > max_palabras:
                grupos.append('\n'.join(cabeza + grupo))
                grupo = []
            grupo.append(fila)
        if grupo:
            grupos.append('\n'.join(cabeza + grupo))
        return grupos

    def volcar():
        """Convierte el buffer en fragmentos respetando max_palabras (las tablas se parten por filas)."""
        cerrar_bloque()
        actual = []
        piezas = []
        for p in buffer:
            if p and all(l.lstrip().startswith('|') for l in p.splitlines()):
                piezas.extend(partir_tabla(p))
            elif p:
                piezas.append(p)
        for parrafo in piezas:
            if actual and _palabras('\n\n'.join(actual + [parrafo])) > max_palabras:
                fragmentos.append({'seccion': ruta(), 'texto': '\n\n'.join(actual)})
                actual = []
            actual.append(parrafo)
        if actual:
            fragmentos.append({'seccion': ruta(), 'texto': '\n\n'.join(actual)})
        buffer.clear()

    for linea, nivel, titulo in lineas_con_titulos(texto):
        if VALLA.match(linea):
            en_codigo = not en_codigo
            bloque.append(linea)
            continue
        if en_codigo:
            bloque.append(linea)
            continue
        if nivel is not None:
            volcar()
            while pila and pila[-1][0] >= nivel:
                pila.pop()
            pila.append((nivel, titulo))
            continue
        es_tabla = linea.lstrip().startswith('|')
        if not linea.strip():
            cerrar_bloque()
        elif bloque and es_tabla != bloque[-1].lstrip().startswith('|'):
            cerrar_bloque()
            bloque.append(linea)
        else:
            bloque.append(linea)
    volcar()
    return fragmentos


# --- Lectura de documentos -----------------------------------------------------------------------------------------
def leer_documento(repo, ruta, locales):
    """Lee un documento del canon desde un clon local (git show) o desde GitHub raw. Devuelve el texto."""
    nombre, commit = repo['nombre'], repo['commit']
    if nombre in locales:
        # [REVISION-BUG] subprocess.run(text=True) decodifica con la codificacion local (cp1252 en Windows): los .md en UTF-8
        # con acentos pueden salir corruptos y cambiar el sha256. Sugerencia: anadir encoding='utf-8'.
        r = subprocess.run(['git', '-C', locales[nombre], 'show', f'{commit}:{ruta}'], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f'{nombre}:{ruta}@{commit[:7]}: {r.stderr.strip()}')
        return r.stdout
    url = url_cruda(repo, ruta)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=cabeceras_github()), timeout=60) as resp:
            return resp.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise RuntimeError(f'{nombre}:{ruta}@{commit[:7]}: GitHub respondió 404. Si el repositorio es privado, define '
                               'GITHUB_TOKEN (solo lectura) en .env o usa --local con un clon') from None
        raise


def url_cruda(repo, ruta):
    """URL de raw.githubusercontent.com para la ruta en el commit fijado del repositorio."""
    dueno_repo = urllib.parse.urlparse(repo['url']).path.strip('/')
    return f"https://raw.githubusercontent.com/{dueno_repo}/{repo['commit']}/{urllib.parse.quote(ruta)}"


def cabeceras_github():
    """Con GITHUB_TOKEN (de solo lectura) se pueden leer repositorios privados, como el de Amatista."""
    cab = {'User-Agent': 'amatista-ia-indexador'}
    if os.environ.get('GITHUB_TOKEN'):
        cab['Authorization'] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    return cab


def titulo_de(texto, ruta):
    """Primer titulo de nivel 1 del Markdown, o el nombre del archivo si no hay."""
    for _, nivel, titulo in lineas_con_titulos(texto):
        if nivel == 1:
            return titulo
    return Path(ruta).stem


def preparar(canon, locales, max_palabras):
    """Lee y fragmenta todo el canon. Devuelve [(documento, [fragmentos])] sin vectores."""
    repos = {k: {**v, 'nombre': k} for k, v in canon['repositorios'].items()}
    salida = []
    for d in canon['documentos']:
        crudo = leer_documento(repos[d['repo']], d['ruta'], locales)
        texto = filtrar_secciones(crudo, d.get('excluir_secciones', ()), d.get('solo_secciones', ()))
        doc = {
            'id': d['id'], 'repositorio': d['repo'], 'ruta': d['ruta'], 'commit_fijado': repos[d['repo']]['commit'],
            'tipo': d['tipo'], 'titulo': titulo_de(crudo, d['ruta']), 'idioma': d.get('idioma', 'es'),
            'sha256': sha256(texto), 'version_canon': canon['version'],
        }
        frags = []
        for i, f in enumerate(fragmentar(texto, max_palabras)):
            frags.append({'documento_id': doc['id'], 'orden': i, 'seccion': f['seccion'], 'texto': f['texto'],
                          'tokens': round(_palabras(f['texto']) * 1.4) or 1, 'sha256': sha256(f['texto'])})
        salida.append((doc, frags))
    return salida


def entrada_embedding(doc, frag):
    """Texto que se vectoriza: 'titulo · seccion' + texto del fragmento."""
    return f"{doc['titulo']} · {frag['seccion'] or ''}\n\n{frag['texto']}"


# --- Ollama ---------------------------------------------------------------------------------------------------------
def _json(url, datos=None, cabeceras=None, metodo=None, timeout=300):
    """Peticion HTTP con cuerpo/respuesta JSON (urllib). Devuelve el JSON o None si la respuesta esta vacia."""
    cuerpo = None if datos is None else json.dumps(datos).encode('utf-8')
    req = urllib.request.Request(url, data=cuerpo, method=metodo, headers={'Content-Type': 'application/json', **(cabeceras or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        texto = resp.read().decode('utf-8')
        return json.loads(texto) if texto.strip() else None


class Ollama:
    """Cliente minimo de embeddings de Ollama; fija la version exacta del modelo por su digest."""
    def __init__(self, base, modelo):
        """Comprueba que el modelo existe en Ollama y arma el id 'modelo@digest'."""
        self.base, self.modelo = base.rstrip('/'), modelo
        etiquetas = _json(f'{self.base}/api/tags')['models']
        m = next((x for x in etiquetas if x['name'] in (modelo, f'{modelo}:latest')), None)
        if not m:
            raise RuntimeError(f'Ollama no tiene el modelo {modelo}: corre «ollama pull {modelo}»')
        self.id = f"{modelo}@{m['digest'][:12]}"   # el digest fija la versión exacta del modelo

    def vectores(self, textos, lote=16):
        """Calcula vectores en lotes y valida que tengan DIMENSIONES componentes."""
        salida = []
        for i in range(0, len(textos), lote):
            r = _json(f'{self.base}/api/embed', {'model': self.modelo, 'input': textos[i:i + lote]})
            salida.extend(r['embeddings'])
        for v in salida:
            if len(v) != DIMENSIONES:
                raise ValueError(f'el modelo devolvió {len(v)} dimensiones; la base espera {DIMENSIONES}')
        return salida


# --- Supabase (REST, con la clave secreta) ------------------------------------------------------------------------
class Supabase:
    """Cliente REST minimo (PostgREST) de Supabase con la clave en la cabecera apikey."""
    def __init__(self, url, clave):
        """Normaliza la URL base (/rest/v1) y guarda la cabecera de la clave."""
        self.base = url.rstrip('/').removesuffix('/rest/v1') + '/rest/v1'
        self.cab = {'apikey': clave}

    def get(self, ruta):
        """GET a una ruta de PostgREST; devuelve el JSON."""
        return _json(f'{self.base}/{ruta}', cabeceras=self.cab)

    def post(self, tabla, filas, conflicto=None):
        """POST de filas; con 'conflicto' hace upsert (merge-duplicates)."""
        q = f'?on_conflict={conflicto}' if conflicto else ''
        cab = {**self.cab, 'Prefer': 'resolution=merge-duplicates,return=minimal' if conflicto else 'return=minimal'}
        return _json(f'{self.base}/{tabla}{q}', filas, cabeceras=cab, metodo='POST')

    def delete(self, ruta):
        """DELETE con filtro PostgREST en la ruta."""
        return _json(f'{self.base}/{ruta}', cabeceras={**self.cab, 'Prefer': 'return=minimal'}, metodo='DELETE')


def sincronizar(preparado, embebedor, base, podar=False, registro=print):
    """Sube lo que cambió. Devuelve el resumen {sin_cambios, actualizados, fragmentos, podados}."""
    # [REVISION-BUG] PostgREST limita a max_rows=1000 filas (supabase/config.toml): con mas de 1000 fragmentos estas
    # consultas se truncan y se recalculan vectores sin necesidad. Paginar con Range/limit-offset.
    existentes = {d['id']: d['sha256'] for d in base.get('canon_documentos?select=id,sha256')}
    con_modelo = {f['documento_id'] for f in base.get(
        f"canon_fragmentos?select=documento_id&modelo_embedding=eq.{urllib.parse.quote(embebedor.id)}")}
    resumen = {'sin_cambios': 0, 'actualizados': 0, 'fragmentos': 0, 'podados': 0}
    for doc, frags in preparado:
        if existentes.get(doc['id']) == doc['sha256'] and doc['id'] in con_modelo:
            resumen['sin_cambios'] += 1
            continue
        vectores = embebedor.vectores([entrada_embedding(doc, f) for f in frags])
        # [REVISION-BUG] Escritura no atomica: el documento se sube con su nuevo sha256 ANTES de reemplazar los fragmentos.
        # Si falla a mitad de los POST de fragmentos, la siguiente corrida lo ve 'sin cambios' (sha igual y ya tiene algun
        # fragmento del modelo) y el indice queda incompleto para siempre. Subir el documento al final o usar una RPC transaccional.
        base.post('canon_documentos', [doc], conflicto='id')
        base.delete(f"canon_fragmentos?documento_id=eq.{urllib.parse.quote(doc['id'])}"
                    f"&modelo_embedding=eq.{urllib.parse.quote(embebedor.id)}")
        filas = [{**f, 'modelo_embedding': embebedor.id, 'embedding': '[' + ','.join(f'{x:.7g}' for x in v) + ']'}
                 for f, v in zip(frags, vectores)]
        for i in range(0, len(filas), 100):
            base.post('canon_fragmentos', filas[i:i + 100])
        resumen['actualizados'] += 1
        resumen['fragmentos'] += len(filas)
        registro(f"  ↑ {doc['id']}: {len(filas)} fragmentos")
    if podar:
        vigentes = {d['id'] for d, _ in preparado}
        for viejo in set(existentes) - vigentes:
            base.delete(f'canon_documentos?id=eq.{urllib.parse.quote(viejo)}')   # sus fragmentos caen en cascada
            resumen['podados'] += 1
            registro(f'  ✕ {viejo}: ya no está en el canon')
    return resumen


def main(argv=None):
    """CLI del indexador. Devuelve 0 si termina bien."""
    cargar_env()   # .env primero: los valores por omisión de los argumentos leen el entorno
    p = argparse.ArgumentParser(description='Indexa el canon de Amatista IA en Supabase.')
    p.add_argument('canon', type=Path)
    p.add_argument('--local', default='', help='repositorios desde clones locales: g7b=RUTA,amatista=RUTA')
    p.add_argument('--simulacro', action='store_true', help='solo leer y fragmentar; escribe salidas/fragmentos.jsonl')
    p.add_argument('--max-palabras', type=int, default=260)
    p.add_argument('--ollama', default=os.environ.get('OLLAMA_HOST', 'http://127.0.0.1:11434'))
    p.add_argument('--modelo', default='bge-m3')
    p.add_argument('--podar', action='store_true', help='borrar de Supabase los documentos que ya no están en el canon')
    a = p.parse_args(argv)

    canon = yaml.safe_load(a.canon.read_text(encoding='utf-8'))
    if canon.get('contrato') != 'amatista.ia.canon/1':
        sys.exit(f"{a.canon}: contrato desconocido {canon.get('contrato')}")
    locales = dict(x.split('=', 1) for x in a.local.split(',') if x)
    preparado = preparar(canon, locales, a.max_palabras)
    total = sum(len(f) for _, f in preparado)
    palabras = [_palabras(x['texto']) for _, fs in preparado for x in fs]
    print(f"Canon v{canon['version']}: {len(preparado)} documentos, {total} fragmentos "
          # [REVISION-BUG] Si el canon no produce fragmentos, sorted(palabras)[...] y max() lanzan error (lista vacia).
          f"(palabras por fragmento: mediana {sorted(palabras)[len(palabras) // 2]}, máximo {max(palabras)})")
    if a.simulacro:
        Path('salidas').mkdir(exist_ok=True)
        with open('salidas/fragmentos.jsonl', 'w', encoding='utf-8') as f:
            for doc, frags in preparado:
                for x in frags:
                    f.write(json.dumps({**x, 'titulo': doc['titulo'], 'tipo': doc['tipo']}, ensure_ascii=False) + '\n')
        for doc, frags in preparado:
            print(f"  {doc['id']:30s} {len(frags):3d} fragmentos  sha {doc['sha256'][:12]}")
        return 0
    url, clave = os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_SECRET_KEY')
    if not url or not clave:
        sys.exit('Faltan SUPABASE_URL y SUPABASE_SECRET_KEY en el entorno (la clave secreta nunca va en el repositorio).')
    embebedor = Ollama(a.ollama, a.modelo)
    print(f'Modelo de embeddings: {embebedor.id}')
    try:
        r = sincronizar(preparado, embebedor, Supabase(url, clave), podar=a.podar)
    except urllib.error.HTTPError as e:
        sys.exit(f'Supabase respondió {e.code}: {e.read().decode("utf-8", "replace")[:300]}')
    print(f"Listo: {r['actualizados']} documentos actualizados ({r['fragmentos']} fragmentos), "
          f"{r['sin_cambios']} sin cambios, {r['podados']} podados.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
