"""Segunda revisión de la auditoría de Site 4.1: un modelo local juzga, a ciegas, los 70 bloques que etiquetó Codex.

    python -m revisor.segunda_revision reconstruir --g7b ../amatista-g7b-etl
    python -m revisor.segunda_revision revisar --modelo qwen3:8b
    python -m revisor.segunda_revision adjudicar salidas/segunda_revision.csv

1. reconstruir: vuelve a descargar las 46 páginas del manual público de Blender 4.5 y extrae los bloques con el
   MISMO código de G7B, en el commit fijado del canon. Solo se acepta un bloque si su id (hash del bloque completo)
   es idéntico al de la auditoría: así se garantiza que el texto es exactamente el que juzgó Codex.
   No necesita acceso a Azure.
2. revisar: el modelo local juzga cada bloque con la rúbrica del canon (g7b/seleccion-documental y g7b/site).
   NO ve la etiqueta ni el motivo de Codex: dos opiniones independientes.
3. adjudicar: una persona decide solo los desacuerdos. Con eso se recalcula el límite inferior de Wilson
   de las 24 muestras de páginas inéditas, que es lo que habilita o no la publicación automática.

La IA no habilita nada: la etiqueta final de un desacuerdo la pone una persona.
"""
import argparse
import csv
import json
import math
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import yaml

from indexador.entorno import cargar_env
from indexador.indexar import Ollama  # noqa: F401  (misma instalación que el revisor)
from revisor.revisar import Generador, descargar_canon

Z = 1.64485                  # el mismo z de G7B (unilateral al 95 %)
UMBRAL = 0.80
RUBRICA = ('g7b/seleccion-documental', 'g7b/site')
AUDITORIA = 'algoritmos/documentacion/'
BLOQUES = Path('salidas/site41_bloques.jsonl')
FALLAS = ['ninguna', 'descripcion_generica', 'reformula_el_nombre', 'sin_ajustes_reproducibles', 'indice_o_navegacion',
          'solo_coincidencia_de_palabras', 'efecto_incorrecto_o_mal_atribuido', 'otra']

ESQUEMA_UTIL = {
    'type': 'object',
    # Primero el motivo y al final la decisión: en la v2 del revisor, decidir antes de razonar produjo decisiones
    # que contradecían su propio motivo.
    'properties': {
        'motivo': {'type': 'string'},
        'falla': {'type': 'string', 'enum': FALLAS},
        'util': {'type': 'boolean'},
        'confianza': {'type': 'string', 'enum': ['alta', 'media', 'baja']},
    },
    'required': ['motivo', 'falla', 'util', 'confianza'],
}


# --- Estadística -----------------------------------------------------------------------------------------------------
def wilson_inferior(k, n, z=Z):
    """Límite inferior unilateral de Wilson, la misma fórmula de algoritmos/documentacion/README.md."""
    if n == 0:
        return 0.0
    p = k / n
    centro = p + z * z / (2 * n)
    radio = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centro - radio) / (1 + z * z / n)


def kappa(a, b):
    """Kappa de Cohen para dos listas de booleanos: acuerdo corregido por el que se daría por azar."""
    n = len(a)
    if not n:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


# --- 1. Reconstruir --------------------------------------------------------------------------------------------------
def _git(ruta, *args):
    r = subprocess.run(['git', '-C', str(ruta), *args], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def cargar_auditoria(leer):
    """leer(ruta_en_g7b) -> texto. Devuelve la evidencia de Site 4.1 con la marca de muestra inédita (las 24)."""
    resultados = json.loads(leer(AUDITORIA + 'resultados-site-4.1.json'))
    piloto = json.loads(leer(AUDITORIA + 'revision-piloto-4.1.json'))
    ineditas = {x['id'] for x in piloto if x.get('inedita_40')}
    evidencia = []
    for e in resultados['evidencia']:
        inedita = bool(e['muestra'] and (e['id'] in ineditas or e['trabajo'].endswith('/4')))
        evidencia.append({**e, 'inedita': inedita})
    publicado = resultados['calibracion_paginas_ineditas']
    return evidencia, {'n': publicado['n'], 'k': publicado['k']}


def reconstruir(evidencia, anotar_pagina, pausa=0.5):
    """anotar_pagina(url) -> [{id, texto, seccion}] con el código de G7B. Une por id exacto."""
    por_id = {e['id']: e for e in evidencia}
    hallados = {}
    for url in sorted({e['url'].split('#')[0] for e in evidencia}):
        for b in anotar_pagina(url):
            if b['id'] in por_id:
                hallados[b['id']] = b
        time.sleep(pausa)
    bloques = []
    for e in evidencia:
        b = hallados.get(e['id'])
        bloques.append({'id': e['id'], 'url': e['url'], 'seccion': b['seccion'] if b else None,
                        'texto': b['texto'] if b else None, 'reconstruido': bool(b), 'codex_util': e['util'],
                        'codex_motivo': e['motivo'], 'muestra': e['muestra'], 'inedita': e['inedita']})
    return bloques


def anotador_g7b(ruta_codigo):
    """Usa el extractor y el modelo Site de G7B tal como están en ese commit."""
    sys.path.insert(0, str(ruta_codigo))
    from scrapy.http import HtmlResponse
    from motor_extraccion.site import ModeloSite
    from motor_extraccion.spiders.fragmentos_sphinx import extraer_fragmentos
    modelo = ModeloSite()

    def anotar(url):
        req = urllib.request.Request(url, headers={'User-Agent': 'amatista-ia-segunda-revision'})
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = HtmlResponse(url=url, body=r.read(), encoding='utf-8')
        titulo = (resp.css('title::text').get() or '').strip()
        contenedor = resp.css('main, [role=main]') or resp.css('body')
        item = {'fuente': 'blender-compositor-45', 'url': url, 'programa': 'blender', 'version': '4.5', 'titulo': titulo,
                'fragmentos': extraer_fragmentos(contenedor[0], resp, 'blender-compositor-45', 'blender', '4.5', titulo)}
        modelo.anotar(item)
        bloques = {(f['fragmento_id'], i): (f, b) for f in item['fragmentos'] for i, b in enumerate(f['bloques'])}
        salida = []
        for ev in item['documental']['eventos']:
            f, b = bloques[(ev['fragmento'], ev['bloque'])]
            jer = f.get('jerarquia')
            salida.append({'id': ev['id'], 'texto': b.get('texto'), 'seccion': ' > '.join(jer) if isinstance(jer, list) else jer})
        return salida
    return anotar


def cmd_reconstruir(a):
    canon = yaml.safe_load(Path('canon/canon.yml').read_text(encoding='utf-8'))
    commit = canon['repositorios']['g7b']['commit']
    g7b = Path(a.g7b).resolve()
    _git(g7b, 'cat-file', '-e', f'{commit}^{{commit}}')    # el clon tiene el commit fijado
    # Una copia de trabajo aparte en el commit fijado: no se toca la rama del clon de la persona.
    fijado = Path('salidas') / f'g7b-{commit[:7]}'
    if not fijado.exists():
        _git(g7b, 'worktree', 'add', '--detach', str(fijado.resolve()), commit)
    evidencia, publicado = cargar_auditoria(lambda ruta: _git(g7b, 'show', f'{commit}:{ruta}'))
    bloques = reconstruir(evidencia, anotador_g7b(fijado.resolve()))
    BLOQUES.parent.mkdir(parents=True, exist_ok=True)
    with open(BLOQUES, 'w', encoding='utf-8') as f:
        for b in bloques:
            f.write(json.dumps(b, ensure_ascii=False) + '\n')
    ok = sum(b['reconstruido'] for b in bloques)
    ined = [b for b in bloques if b['inedita']]
    print(f'Reconstruidos con id idéntico: {ok} de {len(bloques)} → {BLOQUES}')
    print(f"Muestras inéditas: {len(ined)} (útiles según Codex: {sum(b['codex_util'] for b in ined)}; "
          f"publicado: {publicado['k']} de {publicado['n']})")
    if ok < len(bloques):
        print('AVISO: los bloques sin reconstruir no se revisan. El manual pudo cambiar desde la auditoría: repórtalo.')
    return 0 if ok == len(bloques) else 1


# --- 2. Revisar ------------------------------------------------------------------------------------------------------
def hoja_rubrica(fragmentos):
    rubrica = '\n\n'.join(f"[{f['documento_id']} · {f['seccion']}]\n{f['texto']}" for f in fragmentos
                          if f['documento_id'] in RUBRICA)
    if not rubrica:
        raise RuntimeError('El canon no tiene la rúbrica: vuelve a indexar el canon v2 (LABORATORIO.md, paso 8).')
    return f"""Eres un auditor de documentación técnica de G7B. Juzgas si un bloque extraído del manual de Blender \
es útil según la rúbrica del proyecto. Tu juicio es una segunda opinión que revisa una persona.

RÚBRICA (canon):
{rubrica}

CÓMO RESPONDER (en este orden: primero piensas, al final decides):
- motivo: primero, una frase en español, concreta y comprobable con el texto: qué dice el bloque y si tiene \
acción o parámetro, efecto y condición.
- falla: si el bloque no es útil, la razón principal: {', '.join(FALLAS[1:])}. Si es útil, «ninguna».
- util: tiene que seguirse del motivo. true solo si el bloque describe una acción o un parámetro con un efecto útil, \
correcto y bien atribuido, o una comprobación, con detalle suficiente para aplicarlo. Un índice, una coincidencia de \
palabras, una descripción genérica o un pasaje sin detalle suficiente NO es útil. Si falla no es «ninguna», util es false.
- confianza: alta, media o baja.
Juzga solo el texto que se te muestra. Responde solo con el JSON pedido."""


def mensaje_bloque(b):
    return f"BLOQUE DEL MANUAL DE BLENDER 4.5\n- sección: {b['seccion']}\n- url: {b['url']}\n\nTEXTO:\n{b['texto']}"


def resumir(revisados):
    validos = [r for r in revisados if r['ia'] is not None]
    codex, ia = [r['codex_util'] for r in validos], [r['ia']['util'] for r in validos]
    ined = [r for r in validos if r['inedita']]
    t = [r['segundos'] for r in revisados]
    return {
        'bloques': len(revisados), 'json_valido': len(validos),
        'acuerdo': sum(x == y for x, y in zip(codex, ia)) / len(validos) if validos else None,
        'kappa': kappa(codex, ia),
        'matriz_codex_vs_ia': {f'codex {"útil" if c else "no"} → ia {"útil" if i else "no"}':
                               sum(1 for x, y in zip(codex, ia) if x == c and y == i)
                               for c in (True, False) for i in (True, False)},
        'censo_util': {'codex': sum(codex), 'ia': sum(ia), 'n': len(validos)},
        'ineditas': {'n': len(ined), 'codex': sum(r['codex_util'] for r in ined), 'ia': sum(r['ia']['util'] for r in ined),
                     'wilson_codex': wilson_inferior(sum(r['codex_util'] for r in ined), len(ined)),
                     'wilson_ia': wilson_inferior(sum(r['ia']['util'] for r in ined), len(ined))},
        'desacuerdos': sum(x != y for x, y in zip(codex, ia)),
        'segundos_por_bloque': sorted(t)[len(t) // 2] if t else None,
    }


def escribir_csv(revisados, ruta):
    with open(ruta, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['id', 'url', 'seccion', 'texto', 'inedita', 'codex_util', 'codex_motivo', 'ia_util', 'ia_falla',
                    'ia_motivo', 'ia_confianza', 'desacuerdo', 'humano_util', 'humano_nota'])
        for r in revisados:
            ia = r['ia'] or {}
            util = ia.get('util')
            w.writerow([r['id'], r['url'], r['seccion'], (r['texto'] or '')[:600], 'sí' if r['inedita'] else '',
                        'sí' if r['codex_util'] else 'no', r['codex_motivo'],
                        '' if util is None else ('sí' if util else 'no'), ia.get('falla', ''), ia.get('motivo', ''),
                        ia.get('confianza', ''), 'SÍ' if util is None or util != r['codex_util'] else '', '', ''])


def cmd_revisar(a):
    url, clave = os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_PUBLISHABLE_KEY')
    if not url or not clave:
        sys.exit('Faltan SUPABASE_URL y SUPABASE_PUBLISHABLE_KEY en .env (solo para descargar la rúbrica del canon).')
    if not BLOQUES.is_file():
        sys.exit(f'Falta {BLOQUES}: corre primero «python -m revisor.segunda_revision reconstruir --g7b RUTA».')
    canon = descargar_canon(url, clave, 'salidas/canon_rubrica.json', refrescar=True)   # su propio archivo: no altera el canon del revisor
    sistema = hoja_rubrica(canon['fragmentos'])
    bloques = [json.loads(l) for l in BLOQUES.read_text(encoding='utf-8').splitlines() if l.strip()]
    bloques = [b for b in bloques if b['reconstruido']][:a.n]
    gen = Generador(a.ollama, a.modelo, contexto=4096, esquema=ESQUEMA_UTIL)
    revisados = []
    for i, b in enumerate(bloques, 1):
        t = time.perf_counter()
        crudo, stats = gen.responder(sistema, mensaje_bloque(b))
        try:
            ia = json.loads(crudo)
            ia = ia if isinstance(ia.get('util'), bool) and ia.get('falla') in FALLAS else None
        except (json.JSONDecodeError, AttributeError):
            ia = None
        revisados.append({**b, 'ia': ia, 'segundos': time.perf_counter() - t, 'tiempos': stats})
        marca = '—' if ia is None else ('útil' if ia['util'] else 'no')
        print(f"[{i}/{len(bloques)}] {revisados[-1]['segundos']:5.1f} s  ia {marca:4s} codex {'útil' if b['codex_util'] else 'no':4s}"
              f"{'  ≠' if ia and ia['util'] != b['codex_util'] else ''}  {(b['seccion'] or '')[:55]}")
    resumen = {'modelo': a.modelo, 'fecha': time.strftime('%Y-%m-%d %H:%M'), **resumir(revisados)}
    Path('salidas/segunda_revision.json').write_text(json.dumps({'resumen': resumen, 'revisados': revisados},
                                                                ensure_ascii=False, indent=2), encoding='utf-8')
    escribir_csv(revisados, 'salidas/segunda_revision.csv')
    print('\n' + json.dumps(resumen, ensure_ascii=False, indent=2))
    print('\nUna persona decide los desacuerdos en salidas/segunda_revision.csv (columna humano_util: sí o no).')
    return 0


# --- 3. Adjudicar ----------------------------------------------------------------------------------------------------
def _si_no(v):
    v = (v or '').strip().lower()
    return True if v in ('sí', 'si', 'true', '1') else False if v in ('no', 'false', '0') else None


def adjudicar(filas):
    """Etiqueta final: la de la persona si la puso; si no, la compartida cuando Codex y la IA coinciden."""
    finales, pendientes, origen = [], [], {'persona': 0, 'acuerdo': 0}
    for f in filas:
        humano, codex, ia = _si_no(f.get('humano_util')), _si_no(f['codex_util']), _si_no(f['ia_util'])
        if humano is not None:
            finales.append((f, humano))
            origen['persona'] += 1
        elif ia is not None and ia == codex:
            finales.append((f, codex))
            origen['acuerdo'] += 1
        else:
            pendientes.append(f['id'])
    ined = [u for f, u in finales if f['inedita'] == 'sí']
    n_ined = sum(1 for f in filas if f['inedita'] == 'sí')
    k = sum(ined)
    completo = len(ined) == n_ined
    return {
        'pendientes_de_persona': len(pendientes), 'origen_de_la_etiqueta': origen,
        'censo': {'util': sum(u for _, u in finales), 'n': len(finales)},
        'ineditas': {'util': k, 'n': len(ined), 'de': n_ined, 'wilson_inferior': wilson_inferior(k, len(ined))},
        'habilitada': bool(completo and wilson_inferior(k, len(ined)) >= UMBRAL),
        'nota': None if completo else 'Faltan etiquetas de la persona en muestras inéditas: el resultado no es final.',
    }


def cmd_adjudicar(a):
    with open(a.planilla, encoding='utf-8-sig', newline='') as f:
        r = adjudicar(list(csv.DictReader(f)))
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


def main(argv=None):
    cargar_env()
    p = argparse.ArgumentParser(description='Segunda revisión de la auditoría de Site 4.1.')
    sub = p.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('reconstruir')
    r.add_argument('--g7b', required=True, help='clon local de amatista-g7b-etl (debe tener el commit fijado del canon)')
    v = sub.add_parser('revisar')
    v.add_argument('--modelo', default='qwen3:8b')
    v.add_argument('--ollama', default=os.environ.get('OLLAMA_HOST', 'http://127.0.0.1:11434'))
    v.add_argument('--n', type=int, default=None)
    j = sub.add_parser('adjudicar')
    j.add_argument('planilla', type=Path)
    a = p.parse_args(argv)
    return {'reconstruir': cmd_reconstruir, 'revisar': cmd_revisar, 'adjudicar': cmd_adjudicar}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
