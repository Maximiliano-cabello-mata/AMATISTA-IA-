# [REVISION 2026-11-27] Pruebas de revisor.comparar_versiones y revisor.muestra.ids_de_lote (sin red).
import json

from revisor.comparar_versiones import comparar
from revisor.muestra import ids_de_lote


def test_ids_de_lote_en_orden_y_sin_repetir(tmp_path):
    """Prueba: ids de lote en orden y sin repetir."""
    ruta = tmp_path / 'lote_001.jsonl'
    ruta.write_text('\n'.join(json.dumps({'doc_id': i}) for i in ['b', 'a', 'b', 'c']) + '\n', encoding='utf-8')
    assert ids_de_lote(ruta) == ['b', 'a', 'c']


def test_comparar_versiones_con_y_sin_planilla():
    """Prueba: comparar versiones con y sin planilla."""
    lote = [{'doc_id': 'a', 'decision_efectiva': 'revision'}, {'doc_id': 'b', 'decision_efectiva': 'aceptar'},
            {'doc_id': 'c', 'decision_efectiva': 'aceptar'}]
    nueva = [{'doc_id': 'a', 'decision_efectiva': 'aceptar'}, {'doc_id': 'b', 'decision_efectiva': 'aceptar'}]
    s = comparar(lote, nueva)
    assert s['documentos'] == 2 and s['solo_en_el_lote'] == 1 and s['iguales'] == 1 and s['cambios'] == {'revision → aceptar': 1}
    planilla = [{'n': '1', 'doc_id': 'a', 'titulo': 'A', 'humano_decision': 'aceptar'},
                {'n': '2', 'doc_id': 'b', 'titulo': 'B', 'humano_decision': 'rechazar'}]
    s = comparar(lote, nueva, planilla)
    assert s['coincide_con_la_persona'] == {'v3': 0, 'nueva': 1}
    assert s['aceptados_que_la_persona_no_acepta'] == {'v3': 1, 'nueva': 1}
    assert [m['persona'] for m in s['muestras']] == ['aceptar', 'rechazar']
