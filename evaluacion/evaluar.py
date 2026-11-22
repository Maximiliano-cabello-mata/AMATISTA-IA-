"""Prueba de recuperación del canon: ¿el documento correcto sale entre los primeros resultados?

Dos modos:

  # Contra Supabase (en la computadora del laboratorio, con Ollama y bge-m3). Usa la clave PUBLICABLE: solo lee.
  SUPABASE_URL=https://<proyecto>.supabase.co SUPABASE_PUBLISHABLE_KEY=... \\
    python -m evaluacion.evaluar evaluacion/preguntas.yml

  # Sin red, solo texto (BM25 sobre los fragmentos del simulacro): una base mínima para comparar.
  python -m indexador.indexar canon/canon.yml --simulacro
  python -m evaluacion.evaluar evaluacion/preguntas.yml --lexico salidas/fragmentos.jsonl

Mide recall@1, recall@3 y MRR (rango recíproco medio) por documento, no por fragmento: basta que algún fragmento del
documento esperado esté arriba. Termina con código 1 si recall@3 queda bajo el umbral de preguntas.yml.
"""
import argparse
import json
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

from indexador.entorno import cargar_env
from indexador.indexar import Ollama, _json

PROFUNDIDAD = 10   # cuántos fragmentos se piden por pregunta


def documentos_en_orden(fragmentos):
    """Ids de documento sin repetir, en el orden en que aparece su primer fragmento."""
    vistos = []
    for f in fragmentos:
        if f['documento_id'] not in vistos:
            vistos.append(f['documento_id'])
    return vistos


def medir(preguntas, buscar):
    """buscar(pregunta) -> lista de fragmentos ordenados. Devuelve el resumen y el detalle por pregunta."""
    detalle = []
    for p in preguntas:
        docs = documentos_en_orden(buscar(p['pregunta']))
        rango = docs.index(p['esperado']) + 1 if p['esperado'] in docs else None
        detalle.append({'id': p['id'], 'esperado': p['esperado'], 'rango': rango, 'obtenidos': docs[:3]})
    n = len(detalle)
    resumen = {
        'preguntas': n,
        'recall_1': sum(1 for d in detalle if d['rango'] == 1) / n,
        'recall_3': sum(1 for d in detalle if d['rango'] and d['rango'] <= 3) / n,
        'mrr': sum(1 / d['rango'] for d in detalle if d['rango']) / n,
    }
    return resumen, detalle


# --- Modo léxico: BM25 sin red ---------------------------------------------------------------------------------------
def _tokens(texto):
    return re.findall(r'\w+', texto.lower())   # sin raíces ni acentos quitados: igual que la configuración «simple»


class BM25:
    def __init__(self, fragmentos, k1=1.2, b=0.75):
        self.frags = fragmentos
        self.docs = [Counter(_tokens(f"{f.get('seccion') or ''} {f['texto']}")) for f in fragmentos]
        self.largos = [sum(d.values()) for d in self.docs]
        self.promedio = sum(self.largos) / len(self.largos)
        df = Counter(t for d in self.docs for t in d)
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
        self.k1, self.b = k1, b

    def buscar(self, consulta, cuantos=PROFUNDIDAD):
        q = _tokens(consulta)
        puntos = []
        for i, d in enumerate(self.docs):
            s = 0.0
            for t in q:
                if t in d:
                    tf = d[t]
                    s += self.idf[t] * tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * self.largos[i] / self.promedio))
            puntos.append((s, i))
        puntos.sort(reverse=True)
        return [self.frags[i] for s, i in puntos[:cuantos] if s > 0]


# --- Modo Supabase: la función buscar_canon con la clave publicable --------------------------------------------------
def buscador_supabase(url, clave, embebedor, peso_texto, peso_vector):
    base = url.rstrip('/').removesuffix('/rest/v1') + '/rest/v1'

    def buscar(pregunta):
        vector = embebedor.vectores([pregunta])[0]
        return _json(f'{base}/rpc/buscar_canon', {
            'consulta': pregunta,
            'consulta_embedding': '[' + ','.join(f'{x:.7g}' for x in vector) + ']',
            'cuantos': PROFUNDIDAD,
            'modelo': embebedor.id,
            'peso_texto': peso_texto,
            'peso_vector': peso_vector,
        }, cabeceras={'apikey': clave}, metodo='POST')
    return buscar


def main(argv=None):
    cargar_env()   # .env primero: los valores por omisión de los argumentos leen el entorno
    p = argparse.ArgumentParser(description='Prueba de recuperación del canon.')
    p.add_argument('preguntas', type=Path)
    p.add_argument('--lexico', type=Path, help='fragmentos.jsonl del simulacro: BM25 sin red')
    p.add_argument('--ollama', default=os.environ.get('OLLAMA_HOST', 'http://127.0.0.1:11434'))
    p.add_argument('--modelo', default='bge-m3')
    p.add_argument('--peso-texto', type=float, default=1.0)
    p.add_argument('--peso-vector', type=float, default=1.0)
    p.add_argument('--salida', type=Path, default=Path('salidas/evaluacion.json'))
    a = p.parse_args(argv)

    conjunto = yaml.safe_load(a.preguntas.read_text(encoding='utf-8'))
    preguntas, umbral = conjunto['preguntas'], conjunto['umbral_recall_3']

    if a.lexico:
        fragmentos = [json.loads(l) for l in a.lexico.read_text(encoding='utf-8').splitlines() if l.strip()]
        modo, buscar = 'lexico_bm25', BM25(fragmentos).buscar
    else:
        url, clave = os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_PUBLISHABLE_KEY')
        if not url or not clave:
            sys.exit('Faltan SUPABASE_URL y SUPABASE_PUBLISHABLE_KEY (la publicable basta: esta prueba solo lee).')
        embebedor = Ollama(a.ollama, a.modelo)
        modo = f'supabase {embebedor.id} texto={a.peso_texto} vector={a.peso_vector}'
        buscar = buscador_supabase(url, clave, embebedor, a.peso_texto, a.peso_vector)

    resumen, detalle = medir(preguntas, buscar)
    resumen.update(modo=modo, umbral_recall_3=umbral, aprobada=resumen['recall_3'] >= umbral)
    a.salida.parent.mkdir(parents=True, exist_ok=True)
    a.salida.write_text(json.dumps({'resumen': resumen, 'detalle': detalle}, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f"{modo}: recall@1 {resumen['recall_1']:.2f} · recall@3 {resumen['recall_3']:.2f} · MRR {resumen['mrr']:.2f} "
          f"(umbral recall@3 {umbral})")
    for d in detalle:
        if not d['rango'] or d['rango'] > 3:
            print(f"  falla {d['id']}: esperaba {d['esperado']}, salió {d['obtenidos']} (rango {d['rango']})")
    return 0 if resumen['aprobada'] else 1


if __name__ == '__main__':
    sys.exit(main())
