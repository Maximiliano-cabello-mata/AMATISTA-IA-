"""Prueba rápida del revisor: un modelo local (Ollama) revisa documentos del lago con los estándares del canon.

    python -m revisor.muestra --n 20                              # saca la muestra de MongoDB (solo lectura)
    python -m revisor.revisar salidas/muestra.jsonl --modelo qwen3:8b

Por cada documento, la IA propone:
  - una decisión (aceptar, revision o rechazar);
  - la etapa del embudo que aplica y el motivo;
  - la pregunta del plan (P1–P6 o «ninguna»);
  - una cita al canon;
  - los datos concretos que encontró (versiones, hardware, medidas).
NO cambia nada en el lago ni en MongoDB: solo escribe archivos en salidas/ para que una persona los revise.

Privacidad: el canon se descarga una vez de Supabase (108 fragmentos con sus vectores) y se busca EN ESTA
COMPUTADORA. Ningún texto del lago sale de aquí: ni a Supabase ni a ningún servicio de IA.

El código, no el modelo, comprueba:
  - que la salida cumpla el esquema;
  - que la pregunta exista en la taxonomía;
  - que la cita sea de un fragmento que de verdad se le mostró;
  - que los datos extraídos aparezcan en el texto (fidelidad).
"""
import argparse
import csv
import json
import math
import os
import re
import statistics
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

import yaml

from evaluacion.evaluar import BM25
from indexador.entorno import cargar_env
from indexador.indexar import Ollama, _json

ETAPAS = ['entrada', 'calidad', 'duplicados', 'relevancia', 'valor', 'ninguna']
DECISIONES = ['aceptar', 'revision', 'rechazar']
CANON_REGLAS = 'g7b/ingesta'          # el embudo: va completo en la hoja fija, no se recupera
TAXONOMIA = 'https://raw.githubusercontent.com/Maximiliano-cabello-mata/amatista-g7b-etl/{commit}/fuentes/taxonomia.yml'

ESQUEMA = {
    'type': 'object',
    'properties': {
        'decision': {'type': 'string', 'enum': DECISIONES},
        'etapa': {'type': 'string', 'enum': ETAPAS},
        'motivo': {'type': 'string'},
        'pregunta': {'type': 'string'},
        'cita': {'type': 'object', 'properties': {'documento_id': {'type': 'string'}, 'seccion': {'type': 'string'}},
                 'required': ['documento_id', 'seccion']},
        'datos': {'type': 'object', 'properties': {
            'version_blender': {'type': 'array', 'items': {'type': 'string'}},
            'hardware': {'type': 'array', 'items': {'type': 'string'}},
            'medidas': {'type': 'array', 'items': {'type': 'string'}}},
            'required': ['version_blender', 'hardware', 'medidas']},
        'confianza': {'type': 'string', 'enum': ['alta', 'media', 'baja']},
        'no_se': {'type': 'boolean'},
    },
    'required': ['decision', 'etapa', 'motivo', 'pregunta', 'cita', 'datos', 'confianza', 'no_se'],
}


# --- Canon local -----------------------------------------------------------------------------------------------------
def descargar_canon(url, clave, cache, refrescar=False):
    """Los fragmentos del canon con sus vectores. Se guardan en `cache` para no volver a pedirlos."""
    cache = Path(cache)
    if cache.is_file() and not refrescar:
        return json.loads(cache.read_text(encoding='utf-8'))
    base = url.rstrip('/').removesuffix('/rest/v1') + '/rest/v1'
    cab = {'apikey': clave}
    docs = {d['id']: d for d in _json(f'{base}/canon_documentos?select=id,titulo,commit_fijado,repositorio', cabeceras=cab)}
    frags = _json(f'{base}/canon_fragmentos?select=id,documento_id,orden,seccion,texto,modelo_embedding,embedding'
                  '&order=documento_id,orden', cabeceras=cab)
    for f in frags:
        f['embedding'] = json.loads(f['embedding']) if isinstance(f['embedding'], str) else f['embedding']
        f['titulo'] = docs[f['documento_id']]['titulo']
    canon = {'documentos': docs, 'fragmentos': frags}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(canon, ensure_ascii=False), encoding='utf-8')
    return canon


def _coseno(a, b):
    return sum(x * y for x, y in zip(a, b)) / ((math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))) or 1)


class BuscadorLocal:
    """La misma idea que buscar_canon() en Supabase (texto + vectores fusionados por RRF), pero en memoria."""

    def __init__(self, fragmentos, k_rrf=50):
        self.frags = [f for f in fragmentos if f['documento_id'] != CANON_REGLAS]
        self.bm25 = BM25(self.frags)
        self.k = k_rrf

    def buscar(self, texto, vector, cuantos=3):
        puntos = {}
        for rango, f in enumerate(self.bm25.buscar(texto, cuantos=cuantos * 4), 1):
            puntos[f['id']] = puntos.get(f['id'], 0) + 1 / (self.k + rango)
        por_vector = sorted(self.frags, key=lambda f: -_coseno(vector, f['embedding']))[:cuantos * 4]
        for rango, f in enumerate(por_vector, 1):
            puntos[f['id']] = puntos.get(f['id'], 0) + 1 / (self.k + rango)
        por_id = {f['id']: f for f in self.frags}
        return [por_id[i] for i, _ in sorted(puntos.items(), key=lambda x: -x[1])[:cuantos]]


# --- Instrucciones ---------------------------------------------------------------------------------------------------
def hoja_fija(fragmentos, taxonomia):
    """Va primero y es idéntica en cada documento: Ollama reutiliza su caché y no la vuelve a leer."""
    embudo = '\n\n'.join(f['texto'] for f in fragmentos if f['documento_id'] == CANON_REGLAS
                         and '4. El embudo' in (f['seccion'] or ''))
    preguntas = '\n'.join(f'- {k}: {v["nombre"]}' for k, v in taxonomia['preguntas'].items())
    return f"""Eres el revisor de documentos de G7B. Revisas documentos que el embudo automático ya aceptó y \
propones si de verdad debieron entrar. Tu propuesta la confirma una persona: no decides tú.

REGLAS DEL EMBUDO (canon, g7b/ingesta, sección 4):
{embudo}

PREGUNTAS DEL PLAN (lista cerrada; si ninguna aplica, responde «ninguna»):
{preguntas}

CÓMO RESPONDER:
- decision: «aceptar» si cumple las cinco etapas; «revision» si está en el límite o es dudoso; «rechazar» si falla una etapa.
- etapa: la etapa que falla, o la que más pesa en tu decisión. Si acepta, «ninguna».
- motivo: una o dos frases en español, concretas, que una persona pueda comprobar.
- pregunta: P1, P2, P3, P4, P5, P6 o «ninguna».
- cita: el documento_id y la sección del fragmento del canon que respalda tu decisión. Solo puedes citar un fragmento \
de los que se te muestran (o g7b/ingesta, sección «4. El embudo»).
- datos: copia EXACTAMENTE del texto las versiones de Blender, los modelos de hardware y las medidas con unidad. \
Si no aparecen, deja la lista vacía. No inventes ni completes.
- confianza: alta, media o baja.
- no_se: true si el canon no alcanza para decidir; en ese caso, decision «revision».
Responde solo con el JSON pedido."""


def palabras(texto, n):
    p = (texto or '').split()
    return ' '.join(p[:n]) + (' […]' if len(p) > n else '')


def mensaje_documento(doc, contexto, max_palabras):
    canon = '\n\n'.join(f"[{f['documento_id']} · {f['seccion']}]\n{f['texto']}" for f in contexto)
    return f"""FRAGMENTOS DEL CANON QUE PUEDEN APLICAR:
{canon}

DOCUMENTO A REVISAR:
- fuente: {doc.get('fuente')}
- modo: {doc.get('modo')}
- título: {doc.get('titulo')}
- url: {doc.get('url')}
- preguntas que le asignó el embudo por palabras clave: {', '.join(doc.get('preguntas') or []) or 'ninguna'}

TEXTO ({max_palabras} palabras como máximo):
{palabras(doc.get('texto'), max_palabras) or '(sin texto)'}"""


# --- Comprobaciones por código ---------------------------------------------------------------------------------------
def _normal(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', '', s)


def validar(salida, preguntas_validas, citas_validas, texto):
    """Lo que el código comprueba de la respuesta del modelo. citas_validas: ids de documento que se le mostraron."""
    if not isinstance(salida, dict) or any(k not in salida for k in ESQUEMA['required']):
        return {'esquema': False}
    datos = [x for k in ('version_blender', 'hardware', 'medidas') for x in (salida['datos'].get(k) or [])]
    cuerpo = _normal(texto)
    fieles = [x for x in datos if _normal(x) and _normal(x) in cuerpo]
    return {
        'esquema': salida['decision'] in DECISIONES and salida['etapa'] in ETAPAS,
        'pregunta': salida['pregunta'] in preguntas_validas or salida['pregunta'] == 'ninguna',
        'cita': salida['cita'].get('documento_id') in citas_validas,
        'datos_extraidos': len(datos),
        'datos_fieles': len(fieles),
        'inventados': [x for x in datos if x not in fieles],
    }


# --- Modelo generativo -----------------------------------------------------------------------------------------------
class Generador:
    def __init__(self, base, modelo, contexto=8192, esquema=None):
        self.base, self.modelo, self.contexto = base.rstrip('/'), modelo, contexto
        self.esquema = esquema or ESQUEMA
        self.pensar = False

    def responder(self, sistema, usuario):
        cuerpo = {'model': self.modelo, 'stream': False, 'format': self.esquema, 'keep_alive': '30m',
                  'messages': [{'role': 'system', 'content': sistema}, {'role': 'user', 'content': usuario}],
                  'options': {'temperature': 0, 'num_ctx': self.contexto, 'num_predict': 500}}
        if self.pensar is False:
            cuerpo['think'] = False      # en modelos que «piensan», apagarlo ahorra minutos en CPU
        try:
            r = _json(f'{self.base}/api/chat', cuerpo, timeout=1800)
        except urllib.error.HTTPError as e:
            if e.code == 400 and 'think' in cuerpo:     # el modelo no acepta «think»: se repite sin él
                self.pensar = None
                cuerpo.pop('think')
                r = _json(f'{self.base}/api/chat', cuerpo, timeout=1800)
            else:
                raise
        s = lambda k: r.get(k, 0) or 0
        stats = {'lee_tokens': s('prompt_eval_count'), 'lee_s': s('prompt_eval_duration') / 1e9,
                 'genera_tokens': s('eval_count'), 'genera_s': s('eval_duration') / 1e9, 'carga_s': s('load_duration') / 1e9}
        return r['message']['content'], stats


# --- Corrida ---------------------------------------------------------------------------------------------------------
def revisar_todo(docs, canon, taxonomia, embebedor, generador, max_palabras=450, cuantos=3, registro=print):
    buscador = BuscadorLocal(canon['fragmentos'])
    sistema = hoja_fija(canon['fragmentos'], taxonomia)
    validas = set(taxonomia['preguntas'])
    resultados = []
    for i, doc in enumerate(docs, 1):
        consulta = f"{doc.get('titulo') or ''}\n{palabras(doc.get('texto'), 200)}"
        contexto = buscador.buscar(consulta, embebedor.vectores([consulta])[0], cuantos=cuantos)
        t = time.perf_counter()
        crudo, stats = generador.responder(sistema, mensaje_documento(doc, contexto, max_palabras))
        stats['total_s'] = time.perf_counter() - t
        try:
            salida = json.loads(crudo)
        except json.JSONDecodeError:
            salida = None
        citas = {f['documento_id'] for f in contexto} | {CANON_REGLAS}
        chequeo = validar(salida, validas, citas, f"{doc.get('titulo') or ''} {doc.get('texto') or ''}")
        resultados.append({'doc_id': doc.get('doc_id'), 'url': doc.get('url'), 'fuente': doc.get('fuente'),
                           'titulo': doc.get('titulo'), 'preguntas_embudo': doc.get('preguntas') or [],
                           'contexto': [f"{f['documento_id']} · {f['seccion']}" for f in contexto],
                           'ia': salida, 'crudo': None if salida else crudo[:500], 'chequeo': chequeo, 'tiempos': stats})
        d = salida or {}
        registro(f"[{i}/{len(docs)}] {stats['total_s']:5.1f} s  {d.get('decision', 'JSON inválido'):9s} "
                 f"{d.get('pregunta', ''):8s} {(doc.get('titulo') or '')[:60]}")
    return resultados


def resumir(resultados):
    n = len(resultados)
    validos = [r for r in resultados if r['chequeo'].get('esquema')]
    t = [r['tiempos']['total_s'] for r in resultados]
    gen = [r['tiempos']['genera_tokens'] / r['tiempos']['genera_s'] for r in resultados if r['tiempos']['genera_s']]
    lee = [r['tiempos']['lee_tokens'] / r['tiempos']['lee_s'] for r in resultados if r['tiempos']['lee_s']]
    extraidos = sum(r['chequeo'].get('datos_extraidos', 0) for r in validos)
    fieles = sum(r['chequeo'].get('datos_fieles', 0) for r in validos)
    con_pregunta = [r for r in validos if r['preguntas_embudo']]
    decisiones = {k: sum(1 for r in validos if r['ia']['decision'] == k) for k in DECISIONES}
    return {
        'documentos': n,
        'json_valido': len(validos) / n if n else 0,
        'pregunta_valida': sum(r['chequeo']['pregunta'] for r in validos) / max(len(validos), 1),
        'cita_valida': sum(r['chequeo']['cita'] for r in validos) / max(len(validos), 1),
        'datos_fieles': fieles / extraidos if extraidos else None,
        'datos_extraidos': extraidos,
        'coincide_pregunta_embudo': (sum(r['ia']['pregunta'] in r['preguntas_embudo'] for r in con_pregunta)
                                     / len(con_pregunta)) if con_pregunta else None,
        'decisiones': decisiones,
        'no_se': sum(1 for r in validos if r['ia']['no_se']),
        'segundos_por_documento': {'mediana': statistics.median(t) if t else None, 'maximo': max(t) if t else None},
        'tokens_por_segundo': {'genera': statistics.median(gen) if gen else None, 'lee': statistics.median(lee) if lee else None},
        'horas_estimadas_para_1033': statistics.median(t) * 1033 / 3600 if t else None,
    }


def escribir_planilla(resultados, ruta):
    """Una fila por documento para que una persona marque si la IA acertó. Abre en Excel o LibreOffice."""
    with open(ruta, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['doc_id', 'url', 'titulo', 'fuente', 'preguntas_embudo', 'ia_decision', 'ia_etapa', 'ia_pregunta',
                    'ia_motivo', 'ia_cita', 'ia_confianza', 'datos_inventados', 'humano_decision', 'humano_pregunta', 'humano_nota'])
        for r in resultados:
            d = r['ia'] or {}
            cita = d.get('cita') or {}
            w.writerow([r['doc_id'], r['url'], r['titulo'], r['fuente'], ' '.join(r['preguntas_embudo']),
                        d.get('decision', 'JSON inválido'), d.get('etapa', ''), d.get('pregunta', ''), d.get('motivo', ''),
                        f"{cita.get('documento_id', '')} · {cita.get('seccion', '')}", d.get('confianza', ''),
                        '; '.join(r['chequeo'].get('inventados', [])), '', '', ''])


def main(argv=None):
    cargar_env()
    p = argparse.ArgumentParser(description='Prueba rápida del revisor local.')
    p.add_argument('muestra', type=Path, help='salidas/muestra.jsonl (de python -m revisor.muestra)')
    p.add_argument('--modelo', default='qwen3:8b', help='modelo generativo de Ollama')
    p.add_argument('--embeddings', default='bge-m3')
    p.add_argument('--ollama', default=os.environ.get('OLLAMA_HOST', 'http://127.0.0.1:11434'))
    p.add_argument('--n', type=int, default=None, help='revisar solo los primeros N documentos de la muestra')
    p.add_argument('--palabras', type=int, default=450, help='palabras del documento que se le muestran al modelo')
    p.add_argument('--refrescar-canon', action='store_true')
    a = p.parse_args(argv)

    url, clave = os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_PUBLISHABLE_KEY')
    if not url or not clave:
        sys.exit('Faltan SUPABASE_URL y SUPABASE_PUBLISHABLE_KEY en .env (solo se usan para descargar el canon).')
    canon = descargar_canon(url, clave, 'salidas/canon_local.json', a.refrescar_canon)
    commit = next(d['commit_fijado'] for d in canon['documentos'].values() if d['repositorio'] == 'g7b')
    with urllib.request.urlopen(urllib.request.Request(TAXONOMIA.format(commit=commit), headers={'User-Agent': 'amatista-ia-revisor'}), timeout=60) as r:
        taxonomia = yaml.safe_load(r.read().decode('utf-8'))

    docs = [json.loads(l) for l in a.muestra.read_text(encoding='utf-8').splitlines() if l.strip()][:a.n]
    embebedor = Ollama(a.ollama, a.embeddings)
    modelos = {f['modelo_embedding'] for f in canon['fragmentos']}
    if modelos != {embebedor.id}:
        sys.exit(f'El canon se indexó con {modelos} y aquí está {embebedor.id}: los vectores no serían comparables.')
    print(f'Canon: {len(canon["fragmentos"])} fragmentos · modelo {a.modelo} · {len(docs)} documentos\n')

    resultados = revisar_todo(docs, canon, taxonomia, embebedor, Generador(a.ollama, a.modelo), a.palabras)
    resumen = {'modelo': a.modelo, 'palabras_por_documento': a.palabras, 'fecha': time.strftime('%Y-%m-%d %H:%M'),
               **resumir(resultados)}
    Path('salidas').mkdir(exist_ok=True)
    Path('salidas/prueba_revisor.json').write_text(json.dumps({'resumen': resumen, 'resultados': resultados},
                                                              ensure_ascii=False, indent=2), encoding='utf-8')
    escribir_planilla(resultados, 'salidas/prueba_revisor.csv')
    print('\n' + json.dumps(resumen, ensure_ascii=False, indent=2))
    print('\nArchivos: salidas/prueba_revisor.json (todo) y salidas/prueba_revisor.csv (para marcar a mano).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
