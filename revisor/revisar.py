"""Prueba rápida del revisor: un modelo local (Ollama) revisa documentos del lago con los estándares del canon.

    python -m revisor.muestra --n 20                              # saca la muestra de MongoDB (solo lectura)
    python -m revisor.revisar salidas/muestra.jsonl --modelo qwen3:8b

Por cada documento, la IA propone:
  - una decisión (aceptar, revision o rechazar);
  - la etapa del embudo que aplica y el motivo;
  - la pregunta del plan (P1–P6 o «ninguna»);
  - una cita al canon, elegida de una lista cerrada.
Los datos concretos (versiones, hardware, medidas) los extrae el CÓDIGO, no el modelo.

Versión 2 (22 de noviembre), tras la prueba con codellama y qwen3:8b:
  - la cita es una lista cerrada armada para cada documento: no puede citar algo que no se le mostró;
  - el modelo ya no extrae datos (copiaba los ejemplos del embudo, como «UHD 620»); los extrae el código,
    con la tabla oficial hardware.yml;
  - la respuesta es más corta (generar es lo lento en la CPU del laboratorio);
  - el código revisa que la decisión sea coherente (aceptar ⇒ etapa «ninguna»; con pregunta asignada, la
    relevancia no puede ser la etapa que falla).

Versión 3 (22 de noviembre), tras la v2 (9 de 20 decisiones incoherentes, las 14 revisiones con «relevancia»):
  - el modelo escribe primero el motivo y al final la decisión: razona antes de comprometerse;
  - «etapa» es solo la que falla (antes decía «o la que más pesa», y la usaba como etiqueta por defecto);
  - una decisión incoherente no cuenta como decisión: el código la manda a una persona;
  - opciones de velocidad, cada una para una corrida aparte: --cuantos, --umbral, --palabras y el diagnóstico de
    la caché con variantes.
NO cambia nada en el lago ni en MongoDB: solo escribe archivos en salidas/ para que una persona los revise.

Privacidad: el canon se descarga una vez de Supabase (108 fragmentos con sus vectores) y se busca EN ESTA
COMPUTADORA. Ningún texto del lago sale de aquí: ni a Supabase ni a ningún servicio de IA.

El código, no el modelo, comprueba:
  - que la salida cumpla el esquema;
  - que la pregunta exista en la taxonomía;
  - que la cita sea de un fragmento que de verdad se le mostró;
  - que la decisión sea coherente.
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
CANON_CRITERIOS = 'ia/criterios'      # lo aprendido probando: con --criterios va en la hoja fija, nunca se recupera
G7B_CRUDO = 'https://raw.githubusercontent.com/Maximiliano-cabello-mata/amatista-g7b-etl/{commit}/fuentes/{archivo}'
TAXONOMIA = G7B_CRUDO.replace('{archivo}', 'taxonomia.yml')
VERSION_REVISOR = 3
CITA_EMBUDO = 'g7b/ingesta · 4. El embudo'

def esquema_para(citas):
    """El formato de respuesta de cada documento: la cita solo puede ser uno de los fragmentos que se le muestran."""
    return {
        'type': 'object',
        # El orden importa: el modelo escribe los campos en este orden. Primero razona (motivo), después clasifica
        # y al final decide. En la v2 decidía primero y luego escribía un motivo que contradecía su decisión.
        'properties': {
            'motivo': {'type': 'string'},
            'pregunta': {'type': 'string', 'enum': PREGUNTAS + ['ninguna']},
            'cita': {'type': 'string', 'enum': list(citas)},
            'etapa': {'type': 'string', 'enum': ETAPAS},
            'decision': {'type': 'string', 'enum': DECISIONES},
            'confianza': {'type': 'string', 'enum': ['alta', 'media', 'baja']},
            'no_se': {'type': 'boolean'},
        },
        'required': ['motivo', 'pregunta', 'cita', 'etapa', 'decision', 'confianza', 'no_se'],
    }


PREGUNTAS = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6']
ESQUEMA = esquema_para([CITA_EMBUDO])
REQUERIDOS = ESQUEMA['required']


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
        self.frags = [f for f in fragmentos if f['documento_id'] not in (CANON_REGLAS, CANON_CRITERIOS)]
        self.bm25 = BM25(self.frags)
        self.k = k_rrf

    def buscar(self, texto, vector, cuantos=3, umbral=None):
        """umbral: si se da, solo entran fragmentos cuya similitud coseno con el documento llegue a ese valor."""
        if cuantos <= 0:
            return []
        puntos = {}
        for rango, f in enumerate(self.bm25.buscar(texto, cuantos=cuantos * 4), 1):
            puntos[f['id']] = puntos.get(f['id'], 0) + 1 / (self.k + rango)
        por_vector = sorted(self.frags, key=lambda f: -_coseno(vector, f['embedding']))[:cuantos * 4]
        for rango, f in enumerate(por_vector, 1):
            puntos[f['id']] = puntos.get(f['id'], 0) + 1 / (self.k + rango)
        por_id = {f['id']: f for f in self.frags}
        orden = [por_id[i] for i, _ in sorted(puntos.items(), key=lambda x: -x[1])]
        if umbral is not None:
            orden = [f for f in orden if _coseno(vector, f['embedding']) >= umbral]
        return orden[:cuantos]


# --- Instrucciones ---------------------------------------------------------------------------------------------------
def hoja_fija(fragmentos, taxonomia, criterios=False):
    """Va primero y es idéntica en cada documento: Ollama puede reutilizar su caché y no volver a leerla."""
    embudo = '\n\n'.join(f['texto'] for f in fragmentos if f['documento_id'] == CANON_REGLAS
                         and '4. El embudo' in (f['seccion'] or ''))
    aprendidos = ''
    if criterios:
        partes = [f"{f['seccion'].split(' > ')[-1]}\n{f['texto']}" for f in sorted(fragmentos, key=lambda f: f.get('orden', 0))
                  if f['documento_id'] == CANON_CRITERIOS and re.search(r'> [CE]\d', f['seccion'] or '')]
        if not partes:
            raise RuntimeError('El canon no tiene ia/criterios: indexa el canon v3 y usa --refrescar-canon.')
        aprendidos = '\n\nCRITERIOS APRENDIDOS Y TUS ERRORES CONOCIDOS (canon, ia/criterios; si chocan con una regla de G7B, manda la regla):\n' + \
            '\n\n'.join(partes)
    preguntas = '\n'.join(f'- {k}: {v["nombre"]}' for k, v in taxonomia['preguntas'].items())
    return f"""Eres el revisor de documentos de G7B. Revisas documentos que el embudo automático ya aceptó y \
propones si de verdad debieron entrar. Tu propuesta la confirma una persona: no decides tú.

REGLAS DEL EMBUDO (canon, g7b/ingesta, sección 4):
{embudo}

PREGUNTAS DEL PLAN (lista cerrada; si ninguna aplica, responde «ninguna»):
{preguntas}{aprendidos}

CÓMO RESPONDER (en este orden: primero piensas, al final decides):
- motivo: primero, en una o dos frases en español (40 palabras como máximo), qué ofrece el documento y si alguna \
etapa del embudo falla. Habla del contenido concreto del documento.
- pregunta: P1, P2, P3, P4, P5, P6 o «ninguna». Si asignas una pregunta, la relevancia se cumple.
- cita: elige de la lista CITAS PERMITIDAS el fragmento del canon que respalda tu decisión.
- etapa: SOLO la etapa que falla según tu motivo. Si ninguna falla, «ninguna».
- decision: tiene que seguirse de lo anterior. «aceptar» si la etapa es «ninguna»; «revision» si una etapa está en \
el límite; «rechazar» si una etapa falla con claridad.
- confianza: alta, media o baja.
- no_se: true si el canon no alcanza para decidir; en ese caso, decision «revision».
Responde solo con el JSON pedido."""


def palabras(texto, n):
    p = (texto or '').split()
    return ' '.join(p[:n]) + (' […]' if len(p) > n else '')


def cita_de(f):
    return f"{f['documento_id']} · {f['seccion']}"


def citas_permitidas(contexto):
    return [CITA_EMBUDO] + [c for c in dict.fromkeys(cita_de(f) for f in contexto) if c != CITA_EMBUDO]


def mensaje_documento(doc, contexto, max_palabras):
    canon = '\n\n'.join(f"[{cita_de(f)}]\n{f['texto']}" for f in contexto)
    lista = '\n'.join(f'- {c}' for c in citas_permitidas(contexto))
    return f"""FRAGMENTOS DEL CANON QUE PUEDEN APLICAR:
{canon}

CITAS PERMITIDAS:
{lista}

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


def validar(salida, preguntas_validas, citas_validas):
    """Lo que el código comprueba de la respuesta del modelo. citas_validas: las citas que se le ofrecieron."""
    if not isinstance(salida, dict) or any(k not in salida for k in REQUERIDOS):
        return {'esquema': False}
    pregunta = salida['pregunta']
    incoherencias = []
    if salida['decision'] == 'aceptar' and salida['etapa'] != 'ninguna':
        incoherencias.append('acepta pero marca una etapa que falla')
    if salida['decision'] != 'aceptar' and salida['etapa'] == 'ninguna':
        incoherencias.append('no acepta pero no dice qué etapa falla')
    if pregunta != 'ninguna' and salida['etapa'] == 'relevancia':
        incoherencias.append('asigna una pregunta pero dice que falla la relevancia')
    return {
        'esquema': salida['decision'] in DECISIONES and salida['etapa'] in ETAPAS,
        'pregunta': pregunta in preguntas_validas or pregunta == 'ninguna',
        'cita': salida['cita'] in citas_validas,
        'coherente': not incoherencias,
        'incoherencias': incoherencias,
    }


# --- Datos concretos: los extrae el código, no el modelo ----------------------------------------------------------
VERSION_TEXTO = re.compile(r'\bblender\s+(\d\.\d{1,2}(?:\.\d+)?)\b', re.I)
VERSION_URL = re.compile(r'/manual/[a-z_-]+/(\d\.\d{1,2})/')
MEDIDA = re.compile(r'\b\d+(?:[.,]\d+)?\s?(?:fps|ms|gib|gb|mib|mb|%|samples|muestras)(?![\w])', re.I)


def extraer_datos(doc, patrones_hardware):
    """Versiones de Blender (del texto y de la URL del manual), hardware según hardware.yml y medidas con unidad."""
    texto = f"{doc.get('titulo') or ''} {doc.get('texto') or ''}"
    versiones = sorted(set(VERSION_TEXTO.findall(texto)) | set(VERSION_URL.findall(doc.get('url') or '')))
    hardware = sorted({m.group(0).strip() for p in patrones_hardware for m in [p.search(texto)] if m})
    medidas = sorted({m.group(0).strip() for m in MEDIDA.finditer(texto)})
    return {'version_blender': versiones, 'hardware': hardware, 'medidas': medidas}


def patrones_de(hardware_yml):
    return [re.compile(r['patron'], re.I) for clave in ('gpus', 'cpus') for r in (hardware_yml.get(clave) or [])
            if r.get('patron')]


# --- Modelo generativo -----------------------------------------------------------------------------------------------
class Generador:
    def __init__(self, base, modelo, contexto=8192, esquema=None):
        self.base, self.modelo, self.contexto = base.rstrip('/'), modelo, contexto
        self.esquema = esquema or ESQUEMA
        self.pensar = False

    def responder(self, sistema, usuario, esquema=None, max_tokens=300, formato=True, apagar_pensar=True):
        cuerpo = {'model': self.modelo, 'stream': False, 'keep_alive': '30m',
                  'messages': [{'role': 'system', 'content': sistema}, {'role': 'user', 'content': usuario}],
                  'options': {'temperature': 0, 'num_ctx': self.contexto, 'num_predict': max_tokens}}
        if formato:
            cuerpo['format'] = esquema or self.esquema
        if self.pensar is False and apagar_pensar:
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
def revisar_todo(docs, canon, taxonomia, embebedor, generador, max_palabras=450, cuantos=3, registro=print,
                 patrones_hardware=(), criterios=False, umbral=None):
    buscador = BuscadorLocal(canon['fragmentos'])
    sistema = hoja_fija(canon['fragmentos'], taxonomia, criterios)
    validas = set(taxonomia['preguntas'])
    resultados = []
    for i, doc in enumerate(docs, 1):
        consulta = f"{doc.get('titulo') or ''}\n{palabras(doc.get('texto'), 200)}"
        vector = embebedor.vectores([consulta])[0]
        contexto = buscador.buscar(consulta, vector, cuantos=cuantos, umbral=umbral)
        citas = citas_permitidas(contexto)
        t = time.perf_counter()
        crudo, stats = generador.responder(sistema, mensaje_documento(doc, contexto, max_palabras), esquema_para(citas))
        stats['total_s'] = time.perf_counter() - t
        try:
            salida = json.loads(crudo)
        except json.JSONDecodeError:
            salida = None
        chequeo = validar(salida, validas, set(citas))
        chequeo['motivo_primero'] = bool(salida) and list(salida)[:1] == ['motivo']   # ¿Ollama respetó el orden?
        efectiva = (salida or {}).get('decision', 'persona') if chequeo.get('esquema') and chequeo.get('coherente') else 'persona'
        resultados.append({'doc_id': doc.get('doc_id'), 'url': doc.get('url'), 'fuente': doc.get('fuente'),
                           'titulo': doc.get('titulo'), 'preguntas_embudo': doc.get('preguntas') or [],
                           'contexto': [cita_de(f) for f in contexto],
                           # similitudes: sirven para elegir --umbral después de ver una corrida
                           'similitudes': [round(_coseno(vector, f['embedding']), 4) for f in contexto],
                           'datos_codigo': extraer_datos(doc, patrones_hardware),
                           'ia': salida, 'decision_efectiva': efectiva, 'crudo': None if salida else crudo[:500],
                           'chequeo': chequeo, 'tiempos': stats})
        d = salida or {}
        registro(f"[{i}/{len(docs)}] {stats['total_s']:5.1f} s  {d.get('decision', 'JSON inválido'):9s} "
                 f"{d.get('etapa', ''):10s} {d.get('pregunta', ''):8s}{'  ⚠ incoherente → persona' if efectiva == 'persona' and salida else ''}"
                 f"  {(doc.get('titulo') or '')[:50]}")
    return resultados


def resumir(resultados):
    n = len(resultados)
    validos = [r for r in resultados if r['chequeo'].get('esquema')]
    t = [r['tiempos']['total_s'] for r in resultados]
    gen = [r['tiempos']['genera_tokens'] / r['tiempos']['genera_s'] for r in resultados if r['tiempos']['genera_s']]
    lee = [r['tiempos']['lee_tokens'] / r['tiempos']['lee_s'] for r in resultados if r['tiempos']['lee_s']]
    lee_tokens = [r['tiempos']['lee_tokens'] for r in resultados]
    gen_tokens = [r['tiempos']['genera_tokens'] for r in resultados]
    con_pregunta = [r for r in validos if r['preguntas_embudo']]
    decisiones = {k: sum(1 for r in validos if r['ia']['decision'] == k) for k in DECISIONES}
    return {
        'documentos': n,
        'json_valido': len(validos) / n if n else 0,
        'pregunta_valida': sum(r['chequeo']['pregunta'] for r in validos) / max(len(validos), 1),
        'cita_valida': sum(r['chequeo']['cita'] for r in validos) / max(len(validos), 1),
        'cita_embudo': sum(r['ia']['cita'] == CITA_EMBUDO for r in validos) / max(len(validos), 1),
        'coherente': sum(r['chequeo']['coherente'] for r in validos) / max(len(validos), 1),
        'motivo_primero': sum(bool(r['chequeo'].get('motivo_primero')) for r in validos) / max(len(validos), 1),
        'coincide_pregunta_embudo': (sum(r['ia']['pregunta'] in r['preguntas_embudo'] for r in con_pregunta)
                                     / len(con_pregunta)) if con_pregunta else None,
        'decisiones': decisiones,
        'decisiones_efectivas': {k: sum(1 for r in resultados if r.get('decision_efectiva') == k) for k in DECISIONES + ['persona']},
        'etapas': {k: sum(1 for r in validos if r['ia']['etapa'] == k) for k in ETAPAS if any(r['ia']['etapa'] == k for r in validos)},
        'no_se': sum(1 for r in validos if r['ia']['no_se']),
        'segundos_por_documento': {'mediana': statistics.median(t) if t else None, 'maximo': max(t) if t else None},
        'tokens_por_segundo': {'genera': statistics.median(gen) if gen else None, 'lee': statistics.median(lee) if lee else None},
        'tokens_por_documento': {'lee': statistics.median(lee_tokens) if lee_tokens else None,
                                 'genera': statistics.median(gen_tokens) if gen_tokens else None},
        'horas_estimadas_para_1033': statistics.median(t) * 1033 / 3600 if t else None,
    }


def escribir_planilla(resultados, ruta):
    """Una fila por documento para que una persona marque si la IA acertó. Abre en Excel o LibreOffice."""
    with open(ruta, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['doc_id', 'url', 'titulo', 'fuente', 'preguntas_embudo', 'ia_decision', 'ia_etapa', 'ia_pregunta',
                    'ia_motivo', 'ia_cita', 'ia_confianza', 'incoherencias', 'decision_efectiva', 'datos_codigo', 'humano_decision',
                    'humano_pregunta', 'humano_nota'])
        for r in resultados:
            d = r['ia'] or {}
            datos = r.get('datos_codigo') or {}
            w.writerow([r['doc_id'], r['url'], r['titulo'], r['fuente'], ' '.join(r['preguntas_embudo']),
                        d.get('decision', 'JSON inválido'), d.get('etapa', ''), d.get('pregunta', ''), d.get('motivo', ''),
                        d.get('cita', ''), d.get('confianza', ''), '; '.join(r['chequeo'].get('incoherencias', [])),
                        r.get('decision_efectiva', ''),
                        '; '.join(f"{k}: {', '.join(v)}" for k, v in datos.items() if v), '', '', ''])


VARIANTES_CACHE = [
    # (nombre, mensajes, formato obligatorio, apagar «pensar»)
    ('como hoy: formato + sin pensar', ('DOCUMENTO A REVISAR: prueba uno.', 'DOCUMENTO A REVISAR: prueba dos, distinta.'), True, True),
    ('sin formato obligatorio', ('DOCUMENTO A REVISAR: prueba uno.', 'DOCUMENTO A REVISAR: prueba dos, distinta.'), False, True),
    ('sin el parámetro think', ('DOCUMENTO A REVISAR: prueba uno.', 'DOCUMENTO A REVISAR: prueba dos, distinta.'), True, False),
    ('el mismo mensaje dos veces', ('DOCUMENTO A REVISAR: prueba uno.', 'DOCUMENTO A REVISAR: prueba uno.'), True, True),
]


def diagnosticar_cache(generador, sistema, registro=print, variantes=None):
    """Para cada variante, dos llamadas con las mismas instrucciones fijas. Si la segunda lee casi lo mismo que la
    primera, Ollama no reutilizó la caché. Con varias variantes se ve qué la impide."""
    resultados = []
    for nombre, mensajes, formato, apagar in (variantes or VARIANTES_CACHE[:1]):
        leidos, segundos = [], []
        for mensaje in mensajes:
            _, stats = generador.responder(sistema, mensaje, max_tokens=1, formato=formato, apagar_pensar=apagar)
            leidos.append(stats['lee_tokens'])
            segundos.append(stats.get('lee_s', 0.0))
        # Por tokens o por tiempo: algunas versiones de Ollama cuentan todos los tokens aunque los tome de la caché.
        reutiliza = leidos[1] < leidos[0] * 0.5 or (segundos[0] > 0 and segundos[1] < segundos[0] * 0.5)
        resultados.append({'variante': nombre, 'leidos': leidos, 'segundos': segundos, 'reutiliza': reutiliza})
        registro(f'[{nombre}] tokens leídos: primera {leidos[0]} ({segundos[0]:.1f} s), segunda {leidos[1]} ({segundos[1]:.1f} s). '
                 + ('La caché SÍ se reutiliza.' if reutiliza else 'La caché NO se reutiliza.'))
    return resultados


def main(argv=None):
    cargar_env()
    p = argparse.ArgumentParser(description='Prueba rápida del revisor local.')
    p.add_argument('muestra', type=Path, help='salidas/muestra.jsonl (de python -m revisor.muestra)')
    p.add_argument('--modelo', default='qwen3:8b', help='modelo generativo de Ollama')
    p.add_argument('--embeddings', default='bge-m3')
    p.add_argument('--ollama', default=os.environ.get('OLLAMA_HOST', 'http://127.0.0.1:11434'))
    p.add_argument('--n', type=int, default=None, help='revisar solo los primeros N documentos de la muestra')
    p.add_argument('--palabras', type=int, default=450, help='palabras del documento que se le muestran al modelo')
    p.add_argument('--refrescar-canon', action='store_true',
                   help='volver a bajar el canon de Supabase. NO lo uses si comparas con una corrida anterior')
    p.add_argument('--nombre', default='', help='sufijo de los archivos de salida, para no sobrescribir otra corrida')
    p.add_argument('--criterios', action='store_true',
                   help='agregar los criterios aprendidos (ia/criterios, canon v3) a las instrucciones fijas')
    p.add_argument('--diagnostico-cache', action='store_true',
                   help='solo comprobar si Ollama reutiliza las instrucciones fijas entre documentos')
    p.add_argument('--variantes', action='store_true', help='con --diagnostico-cache: probar las 4 variantes')
    p.add_argument('--cuantos', type=int, default=3, help='fragmentos del canon que se muestran por documento')
    p.add_argument('--umbral', type=float, default=None,
                   help='solo mostrar fragmentos con similitud coseno al documento de al menos este valor')
    a = p.parse_args(argv)

    url, clave = os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_PUBLISHABLE_KEY')
    if not url or not clave:
        sys.exit('Faltan SUPABASE_URL y SUPABASE_PUBLISHABLE_KEY en .env (solo se usan para descargar el canon).')
    canon = descargar_canon(url, clave, 'salidas/canon_local.json', a.refrescar_canon)
    commit = next(d['commit_fijado'] for d in canon['documentos'].values() if d['repositorio'] == 'g7b')
    def g7b(archivo):
        req = urllib.request.Request(G7B_CRUDO.format(commit=commit, archivo=archivo), headers={'User-Agent': 'amatista-ia-revisor'})
        with urllib.request.urlopen(req, timeout=60) as r:
            return yaml.safe_load(r.read().decode('utf-8'))
    taxonomia, hardware = g7b('taxonomia.yml'), g7b('hardware.yml')
    if a.diagnostico_cache:
        diagnosticar_cache(Generador(a.ollama, a.modelo), hoja_fija(canon['fragmentos'], taxonomia),
                           variantes=VARIANTES_CACHE if a.variantes else None)
        return 0

    docs = [json.loads(l) for l in a.muestra.read_text(encoding='utf-8').splitlines() if l.strip()][:a.n]
    embebedor = Ollama(a.ollama, a.embeddings)
    modelos = {f['modelo_embedding'] for f in canon['fragmentos']}
    if modelos != {embebedor.id}:
        sys.exit(f'El canon se indexó con {modelos} y aquí está {embebedor.id}: los vectores no serían comparables.')
    print(f'Canon: {len(canon["fragmentos"])} fragmentos · modelo {a.modelo} · {len(docs)} documentos\n')

    resultados = revisar_todo(docs, canon, taxonomia, embebedor, Generador(a.ollama, a.modelo), a.palabras,
                              cuantos=a.cuantos, patrones_hardware=patrones_de(hardware), criterios=a.criterios,
                              umbral=a.umbral)
    resumen = {'revisor': VERSION_REVISOR, 'criterios': a.criterios, 'modelo': a.modelo, 'palabras_por_documento': a.palabras,
               'cuantos': a.cuantos, 'umbral': a.umbral,
               'canon_fragmentos': len(canon['fragmentos']), 'fecha': time.strftime('%Y-%m-%d %H:%M'),
               **resumir(resultados)}
    Path('salidas').mkdir(exist_ok=True)
    base = 'salidas/prueba_revisor' + (f'_{a.nombre}' if a.nombre else '')
    Path(f'{base}.json').write_text(json.dumps({'resumen': resumen, 'resultados': resultados},
                                               ensure_ascii=False, indent=2), encoding='utf-8')
    escribir_planilla(resultados, f'{base}.csv')
    print('\n' + json.dumps(resumen, ensure_ascii=False, indent=2))
    print(f'\nArchivos: {base}.json (todo) y {base}.csv (para marcar a mano).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
