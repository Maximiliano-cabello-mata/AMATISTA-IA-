"""La puerta (consola/promocion.py), sin MongoDB: colecciones simuladas."""
import copy

import pytest

from consola.__main__ import lineas_registro
from consola.nucleo import APROBADO, NO_APROBADO, Consola
from consola.promocion import comprobar_destino, promover, texto_resumen
from test_consola import CONFIG, llenar


class Fuente:
    name = 'documentos'

    def __init__(self, docs):
        self.docs = docs

    def find(self, filtro, proyeccion=None):
        ids = set(filtro['doc_id']['$in'])
        return [dict(d, _id='x') for d in self.docs if d['doc_id'] in ids]


class Destino:
    def __init__(self, name='conocimiento_auditado'):
        self.name, self.docs, self.escrituras = name, {}, 0

    def find(self, filtro, proyeccion=None):
        return [copy.deepcopy(d) for d in self.docs.values()]

    def update_one(self, filtro, cambio, upsert=False):
        self.escrituras += 1
        doc = self.docs.get(filtro['doc_id'])
        if doc is None:
            if not upsert:
                return
            doc = self.docs[filtro['doc_id']] = {'doc_id': filtro['doc_id']}
        for clave, valor in cambio['$set'].items():
            destino = doc
            partes = clave.split('.')
            for p in partes[:-1]:
                destino = destino.setdefault(p, {})
            destino[partes[-1]] = valor


def preparar(tmp_path):
    c = Consola(tmp_path / 'estado', CONFIG)
    llenar(c, ['aceptar'] * 6 + ['revision', 'revision', 'rechazar', 'persona'])
    c.cerrar(1, tmp_path / 'cierres')
    c._aplicar_veredicto('1', APROBADO, 19, 20, '2026-11-24')
    fuente = Fuente([{'doc_id': f'd{i}', 'url': f'https://docs.blender.org/{i}', 'titulo': f'Doc {i}',
                      'texto': 'texto completo ' * 300, 'fuente': 'blender-manual', 'preguntas': ['P6']} for i in range(10)])
    return c, fuente


def test_simular_no_escribe_nada(tmp_path):
    c, fuente = preparar(tmp_path)
    destino = Destino()
    r = promover(c, fuente, destino, CONFIG, tmp_path, simular=True)
    assert r['nuevos'] == 6 and r['aprobados'] == 6 and destino.escrituras == 0 and 'promocion' not in c.estado
    assert 'simulación' in texto_resumen(r)


def test_copia_solo_lo_aprobado_con_su_rastro_y_es_idempotente(tmp_path):
    c, fuente = preparar(tmp_path)
    destino = Destino()
    r = promover(c, fuente, destino, CONFIG, tmp_path, fecha='2026-11-24 12:00:00')
    assert (r['nuevos'], r['actualizados'], r['retirados']) == (6, 0, 0) and set(destino.docs) == {f'd{i}' for i in range(6)}
    d = destino.docs['d0']
    assert d['texto'] == 'texto completo ' * 300 and '_id' not in d          # el documento original completo, no el extracto
    a = d['auditoria']
    assert a['vigente'] and a['lote'] == 1 and a['decision_ia'] == 'aceptar' and a['veredicto_lote']['resultado'] == APROBADO
    assert a['cita'] == 'g7b/ingesta · 4. El embudo' and a['promovido_en'] == '2026-11-24 12:00:00'
    assert a['veredicto_lote']['marcas_independientes'] is None             # sin archivo de etiquetas para ese lote
    r2 = promover(c, fuente, destino, CONFIG, tmp_path)
    assert (r2['nuevos'], r2['actualizados']) == (0, 6) and len(destino.docs) == 6     # no duplica
    assert 'en MongoDB («conocimiento_auditado»): 6 vigentes' in '\n'.join(lineas_registro(c.estado))


def test_si_un_lote_deja_de_estar_aprobado_sus_documentos_se_retiran_sin_borrarse(tmp_path):
    c, fuente = preparar(tmp_path)
    destino = Destino()
    promover(c, fuente, destino, CONFIG, tmp_path)
    c._aplicar_veredicto('1', NO_APROBADO, 10, 20, '2026-11-25')
    r = promover(c, fuente, destino, CONFIG, tmp_path, fecha='2026-11-25 09:00:00')
    assert r['retirados'] == 6 and len(destino.docs) == 6
    assert all(not d['auditoria']['vigente'] and d['auditoria']['retirado_en'] == '2026-11-25 09:00:00' for d in destino.docs.values())


def test_lo_que_ya_no_esta_en_la_fuente_no_se_inventa(tmp_path):
    c, fuente = preparar(tmp_path)
    fuente.docs = [d for d in fuente.docs if d['doc_id'] != 'd3']
    destino = Destino()
    r = promover(c, fuente, destino, CONFIG, tmp_path)
    assert r['faltan_en_fuente'] == 1 and 'd3' not in destino.docs and r['nuevos'] == 5


def test_nunca_escribe_en_documentos(tmp_path):
    c, fuente = preparar(tmp_path)
    with pytest.raises(ValueError, match='nunca escribe'):
        comprobar_destino('documentos')
    with pytest.raises(ValueError):
        promover(c, fuente, Destino(name='documentos'), CONFIG, tmp_path)


def test_marcas_no_independientes_quedan_en_el_rastro(tmp_path):
    c, fuente = preparar(tmp_path)
    (tmp_path / 'revisor' / 'etiquetas').mkdir(parents=True)
    (tmp_path / 'revisor' / 'etiquetas' / 'lote_001.yml').write_text('lote: 1\nindependiente: false\n', encoding='utf-8')
    destino = Destino()
    promover(c, fuente, destino, CONFIG, tmp_path)
    assert destino.docs['d0']['auditoria']['veredicto_lote']['marcas_independientes'] is False
