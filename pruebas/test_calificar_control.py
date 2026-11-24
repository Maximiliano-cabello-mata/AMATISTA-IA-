"""La calificación del conjunto de control C1: la clave publicada coincide con la huella subida antes de la prueba,
y las corridas guardadas dan lo que dice el análisis de las corridas 10–12."""
import hashlib
import json
from pathlib import Path

import yaml

from revisor.calificar_control import calificar, wilson_inferior

RAIZ = Path(__file__).resolve().parents[1]
C = RAIZ / 'control'


def test_la_clave_es_la_misma_que_se_selló_antes_de_la_prueba():
    assert hashlib.sha256((C / 'clave_c1.yml').read_bytes()).hexdigest() == (C / 'clave_c1.sha256').read_text().strip()
    clave = yaml.safe_load((C / 'clave_c1.yml').read_text(encoding='utf-8'))
    assert hashlib.sha256((C / 'conjunto_c1.jsonl').read_bytes()).hexdigest() == clave['sha256_conjunto']
    esperados = [d['esperado'] for d in clave['documentos'].values()]
    assert esperados.count('aceptar') == 22 and len(esperados) == 35


def test_v3_y_v4_en_el_conjunto_de_control():
    clave = yaml.safe_load((C / 'clave_c1.yml').read_text(encoding='utf-8'))
    r = {v: calificar(clave, json.loads((C / 'resultados' / f'prueba_revisor_{v}_control.json').read_text(encoding='utf-8'))['resultados'])
         for v in ('v3', 'v4')}
    assert r['v3']['malos_detenidos'] == [9, 13] and r['v4']['malos_detenidos'] == [7, 13]
    assert r['v3']['buenos_aceptados'] == [13, 22] and r['v4']['buenos_aceptados'] == [15, 22]
    assert len(r['v3']['malos_que_pasan_la_puerta']) == 4 and len(r['v4']['malos_que_pasan_la_puerta']) == 6
    assert r['v3']['malos_rechazados'] == 2 and r['v4']['malos_rechazados'] == 0


def test_wilson_inferior():
    assert round(wilson_inferior(14, 14), 3) == 0.838 and wilson_inferior(0, 0) is None
