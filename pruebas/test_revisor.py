"""Pruebas del revisor sin red: el modelo, los vectores y el canon se simulan."""
import json

from revisor.revisar import (CANON_REGLAS, CITA_EMBUDO, BuscadorLocal, citas_permitidas, diagnosticar_cache,
                             escribir_planilla, esquema_para, extraer_datos, hoja_fija, mensaje_documento, resumir,
                             revisar_todo, validar)

TAX = {'preguntas': {'P1': {'nombre': 'Fluidez'}, 'P2': {'nombre': 'Versión'}}}


def frag(i, doc, seccion, texto, eje):
    v = [0.0] * 4
    v[eje] = 1.0
    return {'id': i, 'documento_id': doc, 'seccion': seccion, 'texto': texto, 'embedding': v, 'titulo': doc}


CANON = {'fragmentos': [
    frag(1, CANON_REGLAS, 'Ingesta > 4. El embudo (`g7b_ingesta/embudo.py`)', 'Cinco etapas: entrada, calidad...', 0),
    frag(2, 'g7b/cubo', 'Cubo > Calidad', 'v_resumen no suma FPS con muestras por minuto', 1),
    frag(3, 'g7b/estandar-telemetria', 'Hardware', 'hardware records g7b.hardware/1 gpu vram', 2),
]}


def salida(**cambios):
    base = {'decision': 'aceptar', 'etapa': 'ninguna', 'motivo': 'Tiene medidas.', 'pregunta': 'P1',
            'cita': CITA_EMBUDO, 'confianza': 'alta', 'no_se': False}
    return {**base, **cambios}


TEXTO = 'En Blender 4.2 con una RTX 3060 la vista da 45 fps.'


def test_validar_detecta_citas_ajenas_preguntas_fuera_de_lista_e_incoherencias():
    ok = validar(salida(), {'P1', 'P2'}, {CITA_EMBUDO})
    assert ok == {'esquema': True, 'pregunta': True, 'cita': True, 'coherente': True, 'incoherencias': []}
    mal = validar(salida(pregunta='P9', cita='g7b/vision · x'), {'P1', 'P2'}, {CITA_EMBUDO})
    assert not mal['pregunta'] and not mal['cita']
    # Lo que hizo qwen3:8b en «Group»: asigna P6 y a la vez dice que falla la relevancia.
    raro = validar(salida(decision='revision', etapa='relevancia', pregunta='P6'), {'P6'}, {CITA_EMBUDO})
    assert not raro['coherente'] and 'falla la relevancia' in raro['incoherencias'][0]
    assert not validar(salida(etapa='valor'), {'P1'}, {CITA_EMBUDO})['coherente']        # acepta con etapa que falla
    assert not validar(salida(decision='revision'), {'P1'}, {CITA_EMBUDO})['coherente']  # no acepta sin etapa
    assert validar(None, set(), set()) == {'esquema': False}


def test_la_cita_es_una_lista_cerrada_por_documento():
    contexto = [CANON['fragmentos'][1], CANON['fragmentos'][2], CANON['fragmentos'][1]]
    citas = citas_permitidas(contexto)
    assert citas == [CITA_EMBUDO, 'g7b/cubo · Cubo > Calidad', 'g7b/estandar-telemetria · Hardware']
    assert esquema_para(citas)['properties']['cita']['enum'] == citas
    assert 'CITAS PERMITIDAS:\n- ' + CITA_EMBUDO in mensaje_documento({'titulo': 't'}, contexto, 50)


def test_los_datos_los_extrae_el_codigo_con_la_tabla_de_hardware():
    import re
    patrones = [re.compile(r'rtx (4090|3090)', re.I), re.compile(r'rtx 3060', re.I), re.compile(r'intel.*(uhd|hd graphics)', re.I)]
    d = extraer_datos({'titulo': 'T', 'texto': TEXTO, 'url': 'https://docs.blender.org/manual/en/4.5/x.html'}, patrones)
    assert d == {'version_blender': ['4.2', '4.5'], 'hardware': ['RTX 3060'], 'medidas': ['45 fps']}
    # Los ejemplos del embudo («UHD 620») NO están en el documento: el código no los puede «copiar».
    assert extraer_datos({'titulo': 'x', 'texto': 'Sin datos.', 'url': ''}, patrones) == \
        {'version_blender': [], 'hardware': [], 'medidas': []}


def test_el_buscador_local_no_devuelve_el_embudo_y_fusiona_texto_y_vector():
    b = BuscadorLocal(CANON['fragmentos'])
    r = b.buscar('fps muestras por minuto', [0, 1, 0, 0], cuantos=2)
    assert r[0]['documento_id'] == 'g7b/cubo'
    assert all(f['documento_id'] != CANON_REGLAS for f in r)


def test_la_hoja_fija_lleva_el_embudo_y_la_lista_cerrada():
    h = hoja_fija(CANON['fragmentos'], TAX)
    assert 'Cinco etapas' in h and '- P1: Fluidez' in h and '- P2: Versión' in h


class FalsoEmbebedor:
    def vectores(self, textos):
        return [[0, 1, 0, 0] for _ in textos]


class FalsoGenerador:
    def __init__(self, respuestas):
        self.respuestas, self.sistemas = list(respuestas), []

    def responder(self, sistema, usuario, esquema=None, max_tokens=300, formato=True, apagar_pensar=True):
        self.sistemas.append(sistema)
        self.esquemas = getattr(self, 'esquemas', []) + [esquema]
        return self.respuestas.pop(0), {'lee_tokens': 900, 'lee_s': 30.0, 'genera_tokens': 120, 'genera_s': 24.0, 'carga_s': 0}


def test_corrida_completa_resume_y_escribe_la_planilla(tmp_path):
    docs = [{'doc_id': 'a', 'titulo': 'Rendimiento', 'texto': TEXTO, 'preguntas': ['P1']},
            {'doc_id': 'b', 'titulo': 'Receta', 'texto': 'Pan con harina.', 'preguntas': ['P2']},
            {'doc_id': 'c', 'titulo': 'Roto', 'texto': 'x', 'preguntas': []}]
    gen = FalsoGenerador([json.dumps(salida()),
                          json.dumps(salida(decision='rechazar', etapa='relevancia', pregunta='ninguna')),
                          'esto no es JSON'])
    r = revisar_todo(docs, CANON, TAX, FalsoEmbebedor(), gen, registro=lambda *_: None)
    assert len(set(gen.sistemas)) == 1                         # la hoja fija es idéntica: Ollama la reutiliza
    s = resumir(r)
    assert s['json_valido'] == 2 / 3 and s['decisiones'] == {'aceptar': 1, 'revision': 0, 'rechazar': 1}
    assert s['cita_valida'] == 1.0 and s['coherente'] == 1.0 and s['coincide_pregunta_embudo'] == 0.5
    assert all(e['properties']['cita']['enum'][0] == CITA_EMBUDO for e in gen.esquemas)   # cita cerrada en cada documento
    assert r[0]['datos_codigo']['medidas'] == ['45 fps'] and len(r[0]['similitudes']) == len(r[0]['contexto'])
    assert s['tokens_por_documento'] == {'lee': 900, 'genera': 120}
    assert s['tokens_por_segundo'] == {'genera': 5.0, 'lee': 30.0}
    escribir_planilla(r, tmp_path / 'p.csv')
    filas = (tmp_path / 'p.csv').read_text(encoding='utf-8-sig').splitlines()
    assert len(filas) == 4 and 'JSON inválido' in filas[3] and filas[0].endswith('humano_nota')


def test_comparar_mide_acuerdo_deteccion_y_falsas_alarmas():
    from revisor.comparar import comparar
    filas = [{'ia_decision': 'aceptar', 'humano_decision': 'aceptar', 'ia_pregunta': 'P1', 'humano_pregunta': 'P1'},
             {'ia_decision': 'rechazar', 'humano_decision': 'Rechazar', 'ia_pregunta': 'ninguna', 'humano_pregunta': ''},
             {'ia_decision': 'revision', 'humano_decision': 'aceptar', 'ia_pregunta': 'P2', 'humano_pregunta': 'P1'},
             {'ia_decision': 'aceptar', 'humano_decision': 'revision', 'ia_pregunta': 'P1', 'humano_pregunta': ''},
             {'ia_decision': 'aceptar', 'humano_decision': '', 'ia_pregunta': 'P1', 'humano_pregunta': ''}]
    r = comparar(filas)
    assert r['marcadas'] == 4 and r['acuerdo_decision'] == 0.5
    assert r['detecta_problemas'] == 0.5 and r['falsas_alarmas'] == 0.5 and r['acuerdo_pregunta'] == 0.5


def test_diagnostico_de_cache():
    class G:
        def __init__(self, leidos):
            self.leidos = list(leidos)

        def responder(self, sistema, usuario, esquema=None, max_tokens=300, formato=True, apagar_pensar=True):
            self.llamadas = getattr(self, 'llamadas', []) + [(usuario, formato, apagar_pensar)]
            return '{}', {'lee_tokens': self.leidos.pop(0), 'lee_s': 30.0}
    mensajes = []
    diagnosticar_cache(G([1200, 40]), 'hoja', registro=mensajes.append)
    diagnosticar_cache(G([1200, 1190]), 'hoja', registro=mensajes.append)
    assert 'SÍ se reutiliza' in mensajes[0] and 'NO se reutiliza' in mensajes[1]
    # Mismos tokens contados, pero la segunda lectura tarda mucho menos: también es caché.
    class GT(G):
        def responder(self, *a, **k):
            r = super().responder(*a, **k)
            return r[0], {**r[1], 'lee_s': 30.0 if len(self.leidos) % 2 else 2.0}
    assert diagnosticar_cache(GT([1200, 1200]), 'hoja', registro=lambda *_: None)[0]['reutiliza']
    from revisor.revisar import VARIANTES_CACHE
    g = G([1200, 1190, 1200, 30, 1200, 1195, 1200, 20])
    r = diagnosticar_cache(g, 'hoja', registro=lambda *_: None, variantes=VARIANTES_CACHE)
    assert [x['reutiliza'] for x in r] == [False, True, False, True]           # «sin formato» y «mismo mensaje» sí
    assert [(f, p) for _, f, p in g.llamadas[::2]] == [(True, True), (False, True), (True, False), (True, True)]
    assert g.llamadas[6][0] == g.llamadas[7][0]                                # la última variante repite el mensaje


def test_los_criterios_van_en_la_hoja_fija_solo_con_la_opcion_y_nunca_se_recuperan():
    import pytest
    from revisor.revisar import CANON_CRITERIOS
    crit = [{'id': 9, 'documento_id': CANON_CRITERIOS, 'orden': 1, 'seccion': 'Criterios > Criterios verificados > C1. Datos',
             'texto': 'Los datos son solo los del documento.', 'embedding': [0, 1, 0, 0], 'titulo': 'Criterios'}]
    fr = CANON['fragmentos'] + crit
    assert 'CRITERIOS APRENDIDOS' not in hoja_fija(fr, TAX)
    h = hoja_fija(fr, TAX, criterios=True)
    assert 'C1. Datos\nLos datos son solo los del documento.' in h
    assert all(f['documento_id'] != CANON_CRITERIOS for f in BuscadorLocal(fr).buscar('datos documento', [0, 1, 0, 0], 5))
    with pytest.raises(RuntimeError, match='canon v3'):
        hoja_fija(CANON['fragmentos'], TAX, criterios=True)


def test_v3_el_motivo_va_primero_y_la_decision_al_final():
    props = list(esquema_para([CITA_EMBUDO])['properties'])
    assert props[0] == 'motivo' and props.index('decision') > props.index('etapa') > props.index('pregunta')
    h = hoja_fija(CANON['fragmentos'], TAX)
    assert 'primero piensas, al final decides' in h and 'o la que más pesa' not in h


def test_v3_una_decision_incoherente_va_a_una_persona():
    docs = [{'doc_id': 'a', 'titulo': 'A', 'texto': TEXTO, 'preguntas': ['P6'], 'url': 'u'},
            {'doc_id': 'b', 'titulo': 'B', 'texto': TEXTO, 'preguntas': ['P6'], 'url': 'v'}]
    gen = FalsoGenerador([json.dumps({'motivo': 'Responde P6.', **salida(decision='revision', etapa='relevancia', pregunta='P6')}),
                          json.dumps({'motivo': 'Explica un nodo.', **salida()})])
    r = revisar_todo(docs, CANON, {'preguntas': {'P6': {'nombre': 'x'}}}, FalsoEmbebedor(), gen, registro=lambda *_: None)
    assert [x['decision_efectiva'] for x in r] == ['persona', 'aceptar']
    s = resumir(r)
    assert s['decisiones'] == {'aceptar': 1, 'revision': 1, 'rechazar': 0}
    assert s['decisiones_efectivas'] == {'aceptar': 1, 'revision': 0, 'rechazar': 0, 'persona': 1}
    assert s['etapas'] == {'relevancia': 1, 'ninguna': 1} and s['motivo_primero'] == 1.0


def test_v3_buscar_con_cuantos_y_umbral():
    b = BuscadorLocal(CANON['fragmentos'])
    assert b.buscar('fps muestras', [0, 1, 0, 0], cuantos=0) == []
    assert [f['documento_id'] for f in b.buscar('fps muestras', [0, 1, 0, 0], cuantos=3, umbral=0.9)] == ['g7b/cubo']


def test_v3_los_errores_conocidos_entran_con_los_criterios():
    from revisor.revisar import CANON_CRITERIOS
    fr = CANON['fragmentos'] + [
        {'id': 9, 'documento_id': CANON_CRITERIOS, 'orden': 1, 'seccion': 'X > Criterios verificados > C1. Datos', 'texto': 'c', 'embedding': [0, 0, 0, 1]},
        {'id': 10, 'documento_id': CANON_CRITERIOS, 'orden': 2, 'seccion': 'X > Errores conocidos del revisor > E1. Decidías antes', 'texto': 'e', 'embedding': [0, 0, 0, 1]},
        {'id': 11, 'documento_id': CANON_CRITERIOS, 'orden': 3, 'seccion': 'X > Errores conocidos del revisor', 'texto': 'intro', 'embedding': [0, 0, 0, 1]}]
    h = hoja_fija(fr, TAX, criterios=True)
    assert 'C1. Datos\nc' in h and 'E1. Decidías antes\ne' in h and 'intro' not in h and 'TUS ERRORES CONOCIDOS' in h
