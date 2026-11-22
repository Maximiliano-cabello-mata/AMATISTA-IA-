"""Pruebas de la prueba de recuperación: métricas por documento y BM25 sin red."""
from pathlib import Path

import yaml

from evaluacion.evaluar import BM25, documentos_en_orden, medir

RAIZ = Path(__file__).resolve().parents[1]


def test_documentos_en_orden_quita_repetidos_y_conserva_el_primero():
    frags = [{'documento_id': d} for d in ['a', 'b', 'a', 'c', 'b']]
    assert documentos_en_orden(frags) == ['a', 'b', 'c']


def test_medir_calcula_recall_y_mrr_por_documento():
    respuestas = {'q1': ['a', 'b'], 'q2': ['b', 'x', 'y', 'a'], 'q3': []}
    preguntas = [{'id': k, 'pregunta': k, 'esperado': 'a'} for k in respuestas]
    resumen, detalle = medir(preguntas, lambda q: [{'documento_id': d} for d in respuestas[q]])
    assert [d['rango'] for d in detalle] == [1, 4, None]
    assert resumen['recall_1'] == resumen['recall_3'] == 1 / 3
    assert abs(resumen['mrr'] - (1 + 1 / 4) / 3) < 1e-9


def test_bm25_prefiere_el_fragmento_con_la_palabra_rara():
    frags = [{'documento_id': 'a', 'seccion': '', 'texto': 'el embudo tiene cinco etapas'},
             {'documento_id': 'b', 'seccion': '', 'texto': 'el cubo tiene tablas y el cubo tiene vistas'}]
    assert BM25(frags).buscar('etapas del embudo')[0]['documento_id'] == 'a'


def test_las_preguntas_apuntan_a_documentos_del_canon_y_no_se_repiten():
    canon = yaml.safe_load((RAIZ / 'canon/canon.yml').read_text(encoding='utf-8'))
    conjunto = yaml.safe_load((RAIZ / 'evaluacion/preguntas.yml').read_text(encoding='utf-8'))
    ids_canon = {d['id'] for d in canon['documentos']}
    preguntas = conjunto['preguntas']
    assert 30 <= len(preguntas) <= 60
    assert len({p['id'] for p in preguntas}) == len(preguntas)
    assert {p['esperado'] for p in preguntas} == ids_canon     # cada documento del canon tiene al menos una pregunta
