"""Pruebas de los pesos de confianza: Beta, actualización, combinación de votos y Brier."""
import json
import math

from revisor.confianza import (actualizar, beta_cdf, beta_cuantil, brier, capa_acierto, capa_comportamiento, combinar,
                               votos_de_corridas)

TEORICOS = {'problemas_entre_aceptados': [2, 8], 'revisores': {
    'bueno': {'sensibilidad': [8, 2], 'especificidad': [8, 2], 'json': [8, 2]},
    'moneda': {'sensibilidad': [5, 5], 'especificidad': [5, 5]}}}


def test_beta_cdf_y_cuantiles_conocidos():
    assert abs(beta_cdf(0.5, 2, 2) - 0.5) < 1e-9
    assert abs(beta_cdf(0.3, 1, 1) - 0.3) < 1e-9
    assert abs(beta_cdf(0.2, 2, 3) - (1 - 0.8 ** 4 - 4 * 0.2 * 0.8 ** 3)) < 1e-9   # Beta(2,3) = binomial acumulada
    assert abs(beta_cuantil(0.5, 3, 3) - 0.5) < 1e-6 and beta_cuantil(0.05, 2, 8) < 0.2 < beta_cuantil(0.95, 2, 8)


def test_actualizar_suma_exitos_y_fracasos():
    assert actualizar([8, 2], 3, 20) == (11, 19)


def test_comportamiento_parte_de_lo_teorico_y_lo_corrige_con_lo_observado():
    comp = capa_comportamiento(TEORICOS, {'corridas': [{'modelo': 'bueno', 'senales': {'json': [10, 10], 'cita': [1, 10]}}]})
    assert comp['bueno']['json']['actualizado']['media'] == 18 / 20
    assert comp['bueno']['cita']['teorico'] == [1, 1] and comp['bueno']['cita']['actualizado']['media'] == 2 / 12


def test_una_moneda_pesa_cero_y_las_etiquetas_mueven_los_pesos():
    docs = [{'titulo': 'a', 'votos': {'bueno': 'revision', 'moneda': 'aceptar'}, 'humano': None}]
    sin = capa_acierto(TEORICOS, docs)
    assert sin['revisores']['moneda']['peso_si_marca'] == 0 == sin['revisores']['moneda']['peso_si_deja']
    assert math.isclose(sin['revisores']['bueno']['peso_si_marca'], math.log(0.8 / 0.2))
    # La persona dice que «bueno» se equivocó 5 veces marcando cosas buenas: su especificidad baja.
    falsas = [{'titulo': str(i), 'votos': {'bueno': 'revision'}, 'humano': 'aceptar'} for i in range(5)]
    con = capa_acierto(TEORICOS, docs + falsas)
    assert con['etiquetados'] == 5
    assert con['revisores']['bueno']['especificidad']['media'] == 8 / 15
    assert con['revisores']['bueno']['peso_si_marca'] < sin['revisores']['bueno']['peso_si_marca']


def test_combinar_ordena_por_probabilidad_y_hace_triaje():
    docs = [{'titulo': 'acuerdo_problema', 'votos': {'bueno': 'revision'}, 'humano': None},
            {'titulo': 'deja', 'votos': {'bueno': 'aceptar'}, 'humano': None}]
    r = combinar(docs, capa_acierto(TEORICOS, docs))
    assert [d['titulo'] for d in r] == ['acuerdo_problema', 'deja']
    p = 1 / (1 + math.exp(-(math.log(0.2 / 0.8) + math.log(4))))      # 0.20 de base y peso ln(0.8/0.2)
    assert math.isclose(r[0]['p_problema'], p) and r[0]['triaje'] == 'persona' and r[1]['triaje'] == 'proponer dejar'


def test_brier_solo_cuenta_lo_resuelto():
    b = brier([{'p': 0.9, 'resultado': True}, {'p': 0.6, 'resultado': False}, {'p': 0.7, 'resultado': None}])
    assert b['resueltas'] == 2 and b['pendientes'] == 1 and math.isclose(b['brier'], (0.01 + 0.36) / 2)


def test_votos_de_corridas_une_por_url_y_distingue_versiones(tmp_path):
    def corrida(nombre, revisor, decisiones, criterios=False):
        datos = {'resumen': {'modelo': 'qwen3:8b', 'revisor': revisor, 'criterios': criterios},
                 'resultados': [{'url': u, 'titulo': u, 'ia': {'decision': d} if d else None} for u, d in decisiones]}
        (tmp_path / nombre).write_text(json.dumps(datos), encoding='utf-8')
        return tmp_path / nombre
    docs = votos_de_corridas([corrida('a.json', 1, [('u1', 'aceptar'), ('u2', 'revision')]),
                              corrida('b.json', 2, [('u1', 'revision'), ('u2', None)], criterios=True)])
    assert {d['url']: d['votos'] for d in docs} == {'u1': {'qwen3:8b@v1': 'aceptar', 'qwen3:8b@v2+criterios': 'revision'},
                                                    'u2': {'qwen3:8b@v1': 'revision'}}


def test_los_revisores_descartados_no_votan_ni_aparecen():
    from revisor.confianza import sin_descartados
    t = {**TEORICOS, 'descartados': ['moneda']}
    docs = sin_descartados(t, [{'titulo': 'a', 'votos': {'bueno': 'revision', 'moneda@v1': 'aceptar'}, 'humano': None}])
    assert docs[0]['votos'] == {'bueno': 'revision'}
    comp = capa_comportamiento(t, {'corridas': [{'modelo': 'moneda', 'senales': {'json': [1, 1]}},
                                                {'modelo': 'bueno', 'senales': {'json': [1, 1]}}]})
    assert list(comp) == ['bueno']


def test_una_decision_incoherente_es_abstencion(tmp_path):
    datos = {'resumen': {'modelo': 'qwen3:8b', 'revisor': 3},
             'resultados': [{'url': 'u1', 'titulo': 't', 'ia': {'decision': 'revision'}, 'decision_efectiva': 'persona'},
                            {'url': 'u2', 'titulo': 't', 'ia': {'decision': 'aceptar'}, 'decision_efectiva': 'aceptar'}]}
    (tmp_path / 'v3.json').write_text(json.dumps(datos), encoding='utf-8')
    assert {d['url']: d['votos'] for d in votos_de_corridas([tmp_path / 'v3.json'])} == {'u2': {'qwen3:8b@v3': 'aceptar'}}
