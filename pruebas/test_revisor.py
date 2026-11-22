"""Pruebas del revisor sin red: el modelo, los vectores y el canon se simulan."""
import json

from revisor.revisar import (CANON_REGLAS, BuscadorLocal, escribir_planilla, hoja_fija, resumir, revisar_todo,
                             validar)

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
            'cita': {'documento_id': CANON_REGLAS, 'seccion': '4. El embudo'},
            'datos': {'version_blender': ['Blender 4.2'], 'hardware': ['RTX 3060'], 'medidas': ['45 fps']},
            'confianza': 'alta', 'no_se': False}
    return {**base, **cambios}


TEXTO = 'En Blender 4.2 con una RTX 3060 la vista da 45 fps.'


def test_validar_detecta_datos_inventados_citas_ajenas_y_preguntas_fuera_de_lista():
    ok = validar(salida(), {'P1', 'P2'}, {CANON_REGLAS}, TEXTO)
    assert ok == {'esquema': True, 'pregunta': True, 'cita': True, 'datos_extraidos': 3, 'datos_fieles': 3, 'inventados': []}
    mal = validar(salida(pregunta='P9', cita={'documento_id': 'g7b/vision', 'seccion': 'x'},
                         datos={'version_blender': ['Blender 3.6'], 'hardware': ['rtx3060'], 'medidas': []}),
                  {'P1', 'P2'}, {CANON_REGLAS}, TEXTO)
    assert not mal['pregunta'] and not mal['cita']
    assert mal['inventados'] == ['Blender 3.6']          # «rtx3060» sí está (sin espacios ni mayúsculas)
    assert validar(None, set(), set(), '') == {'esquema': False}


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

    def responder(self, sistema, usuario):
        self.sistemas.append(sistema)
        return self.respuestas.pop(0), {'lee_tokens': 900, 'lee_s': 30.0, 'genera_tokens': 120, 'genera_s': 24.0, 'carga_s': 0}


def test_corrida_completa_resume_y_escribe_la_planilla(tmp_path):
    docs = [{'doc_id': 'a', 'titulo': 'Rendimiento', 'texto': TEXTO, 'preguntas': ['P1']},
            {'doc_id': 'b', 'titulo': 'Receta', 'texto': 'Pan con harina.', 'preguntas': ['P2']},
            {'doc_id': 'c', 'titulo': 'Roto', 'texto': 'x', 'preguntas': []}]
    gen = FalsoGenerador([json.dumps(salida()),
                          json.dumps(salida(decision='rechazar', etapa='relevancia', pregunta='ninguna',
                                            datos={'version_blender': [], 'hardware': [], 'medidas': []})),
                          'esto no es JSON'])
    r = revisar_todo(docs, CANON, TAX, FalsoEmbebedor(), gen, registro=lambda *_: None)
    assert len(set(gen.sistemas)) == 1                         # la hoja fija es idéntica: Ollama la reutiliza
    s = resumir(r)
    assert s['json_valido'] == 2 / 3 and s['decisiones'] == {'aceptar': 1, 'revision': 0, 'rechazar': 1}
    assert s['datos_fieles'] == 1.0 and s['coincide_pregunta_embudo'] == 0.5
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
