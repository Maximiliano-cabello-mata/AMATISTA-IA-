"""Pruebas de la segunda revisión de Site 4.1, sin red ni modelo."""
import csv

from revisor.segunda_revision import adjudicar, cargar_auditoria, escribir_csv, kappa, reconstruir, resumir, wilson_inferior


def test_wilson_reproduce_los_numeros_publicados_de_g7b():
    assert round(wilson_inferior(20, 24), 4) == 0.6762          # resultados-site-4.1.json
    assert wilson_inferior(8, 10) < 0.80 <= wilson_inferior(19, 20)   # los ejemplos del README de G7B
    assert wilson_inferior(0, 0) == 0.0


def test_kappa():
    assert kappa([True, False, True, False], [True, False, True, False]) == 1.0
    assert abs(kappa([True, True, False, False], [True, False, True, False])) < 1e-9


def test_cargar_auditoria_marca_las_24_ineditas():
    import json
    resultados = {'calibracion_paginas_ineditas': {'n': 2, 'k': 1}, 'evidencia': [
        {'id': 'a', 'url': 'u1#x', 'trabajo': 't/3', 'util': True, 'muestra': True, 'motivo': ''},
        {'id': 'b', 'url': 'u2', 'trabajo': 't/3', 'util': True, 'muestra': True, 'motivo': ''},
        {'id': 'c', 'url': 'u3', 'trabajo': 't/4', 'util': False, 'muestra': True, 'motivo': ''},
        {'id': 'd', 'url': 'u3', 'trabajo': 't/4', 'util': True, 'muestra': False, 'motivo': ''}]}
    piloto = [{'id': 'a', 'inedita_40': True}, {'id': 'b', 'inedita_40': False}]
    archivos = {'algoritmos/documentacion/resultados-site-4.1.json': json.dumps(resultados),
                'algoritmos/documentacion/revision-piloto-4.1.json': json.dumps(piloto)}
    ev, pub = cargar_auditoria(archivos.__getitem__)
    assert [e['inedita'] for e in ev] == [True, False, True, False] and pub == {'n': 2, 'k': 1}


def test_reconstruir_solo_acepta_ids_identicos():
    ev = [{'id': 'a', 'url': 'p1#s', 'util': True, 'motivo': 'm', 'muestra': True, 'inedita': True},
          {'id': 'b', 'url': 'p1#t', 'util': False, 'motivo': 'm', 'muestra': False, 'inedita': False}]
    visitadas = []

    def anotar(url):
        visitadas.append(url)
        return [{'id': 'a', 'texto': 'Texto A', 'seccion': 'S'}, {'id': 'zz', 'texto': 'otro', 'seccion': 'S'}]
    b = reconstruir(ev, anotar, pausa=0)
    assert visitadas == ['p1']                                 # una descarga por página, sin el ancla
    assert [x['reconstruido'] for x in b] == [True, False] and b[0]['texto'] == 'Texto A' and b[1]['texto'] is None


def _revisado(i, codex, ia, inedita=True):
    return {'id': str(i), 'url': 'u', 'seccion': 's', 'texto': 't', 'codex_util': codex, 'codex_motivo': 'm',
            'inedita': inedita, 'ia': None if ia is None else {'util': ia, 'falla': 'ninguna' if ia else 'otra',
                                                              'motivo': 'x', 'confianza': 'alta'}, 'segundos': 10.0}


def test_resumen_y_adjudicacion_de_punta_a_punta(tmp_path):
    rev = [_revisado(0, True, True), _revisado(1, True, False), _revisado(2, False, False), _revisado(3, True, None),
           _revisado(4, True, True, inedita=False)]
    s = resumir(rev)
    assert s['json_valido'] == 4 and s['desacuerdos'] == 1 and s['acuerdo'] == 0.75
    assert s['ineditas']['n'] == 3 and s['ineditas']['codex'] == 2 and s['ineditas']['ia'] == 1
    escribir_csv(rev, tmp_path / 'r.csv')
    with open(tmp_path / 'r.csv', encoding='utf-8-sig', newline='') as f:
        filas = list(csv.DictReader(f))
    assert [f['desacuerdo'] for f in filas] == ['', 'SÍ', '', 'SÍ', '']     # JSON inválido también va a la persona
    sin_persona = adjudicar(filas)
    assert sin_persona['pendientes_de_persona'] == 2 and sin_persona['habilitada'] is False and sin_persona['nota']
    filas[1]['humano_util'], filas[3]['humano_util'] = 'no', 'sí'
    final = adjudicar(filas)
    assert final['pendientes_de_persona'] == 0 and final['origen_de_la_etiqueta'] == {'persona': 2, 'acuerdo': 3}
    assert final['ineditas'] == {'util': 2, 'n': 4, 'de': 4, 'wilson_inferior': wilson_inferior(2, 4)}
    assert final['nota'] is None


def test_la_segunda_revision_tambien_razona_antes_de_decidir():
    from revisor.segunda_revision import ESQUEMA_UTIL
    assert list(ESQUEMA_UTIL['properties']) == ['motivo', 'falla', 'util', 'confianza']
