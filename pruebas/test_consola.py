"""Pruebas de la consola de Amatista IA, sin Ollama ni MongoDB."""
import csv
import threading

import pytest

from consola.__main__ import Trabajo, dibujar
from consola.nucleo import APROBADO, AVISO, ESPERANDO, NO_APROBADO, Consola, leer_planilla

CONFIG = {'tamano_lote': 10, 'muestras': 4, 'muestras_descartadas': 1, 'max_lotes_esperando': 2, 'espera_s': 0,
          'refresco_s': 0, 'modelo': 'x', 'embeddings': 'x', 'criterios': True, 'palabras': 50, 'cuantos': 3}


def resultado(i, decision):
    return {'doc_id': f'd{i}', 'url': f'https://docs.blender.org/{i}', 'titulo': f'Doc {i}', 'fuente': 'blender-manual',
            'texto': 'texto ' * 20, 'decision_efectiva': decision, 'tiempos': {'total_s': 100.0 + i},
            'ia': {'decision': decision if decision != 'persona' else 'revision', 'etapa': 'ninguna', 'pregunta': 'P6',
                   'motivo': 'Explica un nodo.', 'cita': 'g7b/ingesta · 4. El embudo', 'confianza': 'alta'}}


def llenar(c, decisiones):
    lleno = False
    for i, d in enumerate(decisiones):
        lleno = c.registrar(resultado(i, d))
    return lleno


def test_el_lote_se_llena_y_cuenta_decisiones(tmp_path):
    c = Consola(tmp_path, CONFIG)
    assert not llenar(c, ['aceptar'] * 9)
    assert c.registrar(resultado(9, 'rechazar'))
    lote = c.lote(1)
    assert lote['documentos'] == 10 and lote['decisiones']['aceptar'] == 9 and lote['decisiones']['rechazar'] == 1
    assert c.revisados() == {f'd{i}' for i in range(10)}
    assert Consola(tmp_path, CONFIG).lote(1)['documentos'] == 10            # se retoma desde el disco


def test_muestra_estratificada_y_reproducible(tmp_path):
    c = Consola(tmp_path, CONFIG)
    llenar(c, ['aceptar'] * 7 + ['revision', 'rechazar', 'persona'])
    m = c.muestrear(1)
    assert len(m) == 4 and sum(r['decision_efectiva'] != 'aceptar' for r in m) == 1
    assert [r['doc_id'] for r in m] == [r['doc_id'] for r in c.muestrear(1)]
    c2 = Consola(tmp_path / 'b', CONFIG)
    llenar(c2, ['revision'] * 9 + ['aceptar'])                               # casi no hay aceptados: se completa
    m2 = c2.muestrear(1)
    assert len(m2) == 4 and sum(r['decision_efectiva'] == 'aceptar' for r in m2) == 1


def test_el_cierre_escribe_la_carpeta_y_espera_veredicto(tmp_path):
    c = Consola(tmp_path / 'estado', CONFIG)
    llenar(c, ['aceptar'] * 10)
    carpeta = c.cerrar(1, tmp_path / 'escritorio')
    assert {p.name for p in carpeta.iterdir()} == {'planilla.csv', 'muestras.html', 'para_segunda_opinion.md', 'LEEME.txt'}
    filas = leer_planilla(carpeta / 'planilla.csv')
    assert len(filas) == 4 and all(f['humano_decision'] == '' for f in filas) and filas[0]['ia_decision'] == 'aceptar'
    assert 'fuentes públicas' in (carpeta / 'para_segunda_opinion.md').read_text(encoding='utf-8')
    assert c.lote(1)['estado'] == ESPERANDO and c.estado['lote_actual'] == 2


def marcar(carpeta, bien):
    filas = leer_planilla(carpeta / 'planilla.csv')
    for i, f in enumerate(filas):
        f['humano_decision'] = f['ia_decision'] if i < bien else ('revision' if f['ia_decision'] == 'aceptar' else 'aceptar')
    return filas


def test_reglas_del_veredicto_con_20_muestras():
    filas = lambda bien: [{'ia_decision': 'aceptar', 'humano_decision': 'aceptar' if i < bien else 'rechazar'} for i in range(20)]
    assert Consola.calificar(filas(19))[0] == APROBADO
    assert Consola.calificar(filas(17))[0] == AVISO
    assert Consola.calificar(filas(16))[0] == NO_APROBADO
    persona = [{'ia_decision': 'persona', 'humano_decision': 'aceptar'}] + filas(19)[:19]
    assert Consola.calificar(persona)[1:] == (19, 20)                        # «persona» no cuenta como acierto
    with pytest.raises(ValueError, match='faltan 1'):
        Consola.calificar(filas(20)[:19] + [{'ia_decision': 'aceptar', 'humano_decision': ''}])


def test_el_veredicto_pasa_por_el_buzon_y_dos_fallos_ponen_el_freno(tmp_path):
    c = Consola(tmp_path / 'estado', CONFIG)
    for n in (1, 2):
        llenar(c, ['aceptar'] * 10)
        carpeta = c.cerrar(n, tmp_path / 'escritorio')
        Consola(tmp_path / 'estado', CONFIG).veredicto(n, marcar(carpeta, 1))   # otro proceso deja el veredicto
    assert c.lote(1)['estado'] == ESPERANDO                                       # aún no se aplica
    assert not c.puede_trabajar()[0]                                              # 2 lotes esperando: pausa
    assert sorted(c.aplicar_buzon()) == ['veredicto', 'veredicto']
    assert c.lote(1)['estado'] == NO_APROBADO and c.estado['freno']
    assert c.aplicar_buzon() == []                                                # idempotente
    assert not c.puede_trabajar()[0] and 'freno' in c.puede_trabajar()[1]
    Consola(tmp_path / 'estado', CONFIG).quitar_freno('se corrigieron las instrucciones')
    c.aplicar_buzon()
    assert c.puede_trabajar() == (True, '') and c.estado['fallos_seguidos'] == 0


def test_la_vista_muestra_lo_que_importa(tmp_path):
    c = Consola(tmp_path / 'estado', CONFIG)
    llenar(c, ['aceptar'] * 10)
    c.cerrar(1, tmp_path / 'escritorio')
    llenar(c, ['revision'] * 3)
    texto = dibujar(c.estado, CONFIG)
    assert 'Lote 2 · 3/10' in texto and 'revisión 3' in texto and 'esperando_veredicto' in texto
    assert 'muestras en:' in texto and 'faltan 7 para el cierre' in texto


class FalsaColeccion:
    def __init__(self, docs):
        self.docs = docs

    def find(self, filtro, proyeccion):
        return self

    def sort(self, campo, orden):
        return sorted(self.docs, key=lambda d: d['doc_id'])


class FalsoR:
    @staticmethod
    def revisar_todo(docs, *a, **k):
        d = docs[0]
        decision = 'aceptar' if int(d['doc_id'][1:]) % 3 else 'revision'
        return [{**resultado(int(d['doc_id'][1:]), decision), 'doc_id': d['doc_id']}]

    @staticmethod
    def palabras(texto, n):
        return ' '.join((texto or '').split()[:n])


def test_el_trabajo_revisa_cierra_solo_y_se_pausa_con_dos_lotes_esperando(tmp_path):
    c = Consola(tmp_path / 'estado', CONFIG)
    config = {**CONFIG, 'carpeta_cierres': str(tmp_path / 'escritorio')}

    class TrabajoDePrueba(Trabajo):
        def preparar(self):
            self.R, self.canon, self.taxonomia, self.embebedor, self.generador, self.patrones = FalsoR, {}, {}, None, None, []
            self.coleccion = FalsaColeccion([{'doc_id': f'd{i:02d}', 'titulo': f'Doc {i}', 'texto': 'x'} for i in range(35)])

        def esperar(self, motivo):
            self.motivo = motivo
            self.detener.set()                                      # en la prueba, la primera pausa termina el trabajo

    t = TrabajoDePrueba(c, config)
    hilo = threading.Thread(target=t.correr)
    hilo.start()
    hilo.join(10)
    assert not hilo.is_alive()
    assert [c.lote(n)['estado'] for n in (1, 2)] == [ESPERANDO, ESPERANDO]
    assert c.lote(1)['documentos'] == 10 and c.lote(2)['documentos'] == 10
    assert '2 lotes esperan tu veredicto' in t.motivo                        # se pausó con 20 revisados de 35
    assert len(c.revisados()) == 20
    assert (tmp_path / 'escritorio' / 'lote_001' / 'planilla.csv').is_file()


def test_carpeta_escritorio_encuentra_onedrive_empresarial(tmp_path, monkeypatch):
    from consola.nucleo import carpeta_escritorio
    onedrive = tmp_path / 'OneDrive - Universidad'
    (onedrive / 'Escritorio').mkdir(parents=True)
    monkeypatch.setattr('consola.nucleo._escritorio_windows', lambda: None)
    monkeypatch.setenv('USERPROFILE', str(tmp_path))
    monkeypatch.setenv('OneDriveCommercial', str(onedrive))
    monkeypatch.delenv('OneDrive', raising=False)
    assert carpeta_escritorio() == onedrive / 'Escritorio' / 'Amatista IA · cierres'
