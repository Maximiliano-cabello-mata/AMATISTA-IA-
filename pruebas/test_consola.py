"""Pruebas de la consola de Amatista IA, sin Ollama ni MongoDB."""
import csv
import threading

import pytest

from consola.__main__ import Trabajo, dibujar
from consola.nucleo import APROBADO, AVISO, ESPERANDO, NO_APROBADO, Consola, leer_planilla

CONFIG = {'tamano_lote': 10, 'muestras': 4, 'muestras_descartadas': 1, 'max_lotes_esperando': 2, 'espera_s': 0,
          'refresco_s': 0, 'modelo': 'x', 'embeddings': 'x', 'criterios': True, 'palabras': 50, 'cuantos': 3}


def resultado(i, decision):
    """Resultado simulado del revisor para el documento i con la decision dada."""
    return {'doc_id': f'd{i}', 'url': f'https://docs.blender.org/{i}', 'titulo': f'Doc {i}', 'fuente': 'blender-manual',
            'texto': 'texto ' * 20, 'decision_efectiva': decision, 'tiempos': {'total_s': 100.0 + i},
            'ia': {'decision': decision if decision != 'persona' else 'revision', 'etapa': 'ninguna', 'pregunta': 'P6',
                   'motivo': 'Explica un nodo.', 'cita': 'g7b/ingesta · 4. El embudo', 'confianza': 'alta'}}


def llenar(c, decisiones):
    """Registra en la consola un resultado por decision de la lista."""
    lleno = False
    for i, d in enumerate(decisiones):
        lleno = c.registrar(resultado(i, d))
    return lleno


def test_el_lote_se_llena_y_cuenta_decisiones(tmp_path):
    """Prueba: el lote se llena y cuenta decisiones."""
    c = Consola(tmp_path, CONFIG)
    assert not llenar(c, ['aceptar'] * 9)
    assert c.registrar(resultado(9, 'rechazar'))
    lote = c.lote(1)
    assert lote['documentos'] == 10 and lote['decisiones']['aceptar'] == 9 and lote['decisiones']['rechazar'] == 1
    assert c.revisados() == {f'd{i}' for i in range(10)}
    assert Consola(tmp_path, CONFIG).lote(1)['documentos'] == 10            # se retoma desde el disco


def test_muestra_estratificada_y_reproducible(tmp_path):
    """Prueba: muestra estratificada y reproducible."""
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
    """Prueba: el cierre escribe la carpeta y espera veredicto."""
    c = Consola(tmp_path / 'estado', CONFIG)
    llenar(c, ['aceptar'] * 10)
    carpeta = c.cerrar(1, tmp_path / 'escritorio')
    assert {p.name for p in carpeta.iterdir()} == {'planilla.csv', 'muestras.html', 'para_segunda_opinion.md', 'LEEME.txt'}
    filas = leer_planilla(carpeta / 'planilla.csv')
    assert len(filas) == 4 and all(f['humano_decision'] == '' for f in filas) and filas[0]['ia_decision'] == 'aceptar'
    assert 'fuentes públicas' in (carpeta / 'para_segunda_opinion.md').read_text(encoding='utf-8')
    assert c.lote(1)['estado'] == ESPERANDO and c.estado['lote_actual'] == 2


def marcar(carpeta, bien):
    """Marca la planilla del cierre con 'bien' aciertos (el resto, en desacuerdo)."""
    filas = leer_planilla(carpeta / 'planilla.csv')
    for i, f in enumerate(filas):
        f['humano_decision'] = f['ia_decision'] if i < bien else ('revision' if f['ia_decision'] == 'aceptar' else 'aceptar')
    return filas


def test_reglas_del_veredicto_con_20_muestras():
    # Muestra estratificada real: 14 aceptados por la IA y 6 detenidos (revision/persona)
    """Prueba: reglas del veredicto con 20 muestras."""
    def estratificada(malos_admitidos=0, retenidos_buenos=0):
        """Planilla de 20 filas con malos admitidos y buenos retenidos dados."""
        acept = [{'ia_decision': 'aceptar', 'humano_decision': 'rechazar' if i < malos_admitidos else 'aceptar'} for i in range(14)]
        det = [{'ia_decision': 'revision', 'humano_decision': 'aceptar' if i < retenidos_buenos else 'revision'} for i in range(6)]
        return acept + det

    assert Consola.calificar(estratificada(0, 0)) == (APROBADO, 20, 20)
    assert Consola.calificar(estratificada(0, 1)) == (APROBADO, 19, 20)
    assert Consola.calificar(estratificada(0, 6)) == (AVISO, 14, 20)         # 14/14 aceptados buenos, 6 retenidos → entra con aviso
    assert Consola.calificar(estratificada(1, 0)) == (AVISO, 19, 20)         # 13/14 aceptados buenos → aviso
    assert Consola.calificar(estratificada(2, 0)) == (NO_APROBADO, 18, 20)   # 12/14 aceptados buenos → bloquea la puerta
    persona = [{'ia_decision': 'persona', 'humano_decision': 'aceptar'}] + [
        {'ia_decision': 'aceptar', 'humano_decision': 'aceptar'} for _ in range(19)
    ]
    assert Consola.calificar(persona) == (APROBADO, 19, 20)                  # «persona» no cuenta como acierto global, 19/19 aceptados buenos
    with pytest.raises(ValueError, match='faltan 1'):
        Consola.calificar(estratificada(0, 0)[:19] + [{'ia_decision': 'aceptar', 'humano_decision': ''}])


def test_el_veredicto_pasa_por_el_buzon_y_dos_fallos_ponen_el_freno(tmp_path):
    """Prueba: el veredicto pasa por el buzon y dos fallos ponen el freno."""
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
    """Prueba: la vista muestra lo que importa."""
    c = Consola(tmp_path / 'estado', CONFIG)
    llenar(c, ['aceptar'] * 10)
    c.cerrar(1, tmp_path / 'escritorio')
    llenar(c, ['revision'] * 3)
    texto = dibujar(c.estado, CONFIG)
    assert 'Lote 2 · 3/10' in texto and 'revisión 3' in texto and 'esperando_veredicto' in texto
    assert 'muestras en:' in texto and 'faltan 7 para el cierre' in texto


class FalsaColeccion:
    """Coleccion de MongoDB simulada (find + sort)."""
    def __init__(self, docs):
        """Guarda los documentos simulados."""
        self.docs = docs

    def find(self, filtro, proyeccion):
        """Devuelve self para encadenar .sort()."""
        return self

    def sort(self, campo, orden):
        """Devuelve los documentos ordenados por el campo."""
        return sorted(self.docs, key=lambda d: d['doc_id'])


class FalsoR:
    """Sustituto del modulo revisor.revisar para las pruebas."""
    @staticmethod
    def revisar_todo(docs, *a, **k):
        """Decide 'aceptar' para cada documento sin llamar a ningun modelo."""
        d = docs[0]
        decision = 'aceptar' if int(d['doc_id'][1:]) % 3 else 'revision'
        return [{**resultado(int(d['doc_id'][1:]), decision), 'doc_id': d['doc_id']}]

    @staticmethod
    def palabras(texto, n):
        """Devuelve el texto sin recortar."""
        return ' '.join((texto or '').split()[:n])


def test_el_trabajo_revisa_cierra_solo_y_se_pausa_con_dos_lotes_esperando(tmp_path):
    """Prueba: el trabajo revisa cierra solo y se pausa con dos lotes esperando."""
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
    """Prueba: carpeta escritorio encuentra onedrive empresarial."""
    from consola.nucleo import carpeta_escritorio
    onedrive = tmp_path / 'OneDrive - Universidad'
    (onedrive / 'Escritorio').mkdir(parents=True)
    monkeypatch.setattr('consola.nucleo._escritorio_windows', lambda: None)
    monkeypatch.setenv('USERPROFILE', str(tmp_path))
    monkeypatch.setenv('OneDriveCommercial', str(onedrive))
    monkeypatch.delenv('OneDrive', raising=False)
    assert carpeta_escritorio() == onedrive / 'Escritorio' / 'Amatista IA · cierres'


def test_marcas_con_acento_mayusculas_y_planilla_de_excel_con_punto_y_coma(tmp_path):
    """Prueba: marcas con acento mayusculas y planilla de excel con punto y coma."""
    from consola.nucleo import Consola, decision_normal, etiquetas_de_planilla, leer_planilla
    assert decision_normal(' Revisión ') == 'revision' and decision_normal('ACEPTAR') == 'aceptar'
    ruta = tmp_path / 'planilla.csv'
    filas = ['n;doc_id;url;titulo;fuente;ia_decision;humano_decision;humano_nota']
    filas += [f'{i};d{i};https://docs.blender.org/x{i}.html;T{i};blender-manual;revision;Revisión;' for i in range(1, 20)]
    filas += ['20;d20;https://docs.blender.org/x20.html;T20;blender-manual;aceptar;rechazar;falta texto']
    ruta.write_text('﻿' + '\n'.join(filas) + '\n', encoding='utf-8')
    leidas = leer_planilla(ruta)
    assert len(leidas) == 20 and leidas[0]['humano_decision'] == 'Revisión'
    assert Consola.calificar(leidas) == ('aprobado_con_aviso', 19, 20)
    e = etiquetas_de_planilla(1, leidas)
    assert e['marcadas'] == 20 and e['documentos'][19] == {'n': 20, 'titulo': 'T20', 'url': 'https://docs.blender.org/x20.html',
                                                          'fuente': 'blender-manual', 'ia': 'aceptar', 'humano': 'rechazar', 'nota': 'falta texto'}


def test_registro_un_estado_por_documento(tmp_path):
    """Prueba: registro un estado por documento."""
    import json
    from consola.nucleo import estado_documento
    assert estado_documento('aceptar', ESPERANDO) == 'en_cuarentena'
    assert estado_documento('aceptar', APROBADO) == 'aprobado' and estado_documento('aceptar', AVISO) == 'aprobado'
    assert estado_documento('rechazar', APROBADO) == 'descartado' and estado_documento('persona', APROBADO) == 'por_revisar'
    assert estado_documento('aceptar', NO_APROBADO) == 'por_revisar' and estado_documento('rechazar', NO_APROBADO) == 'por_revisar'

    c = Consola(tmp_path, CONFIG)
    c.estado['documentos_en_fuente'] = 25
    llenar(c, ['aceptar'] * 6 + ['revision', 'revision', 'rechazar', 'persona'])      # lote 1, lleno
    c.cerrar(1, tmp_path / 'cierres')
    c.registrar(resultado(10, 'aceptar'))                                             # lote 2, abierto
    assert c.estado['registro']['estados'] == {'pendiente': 14, 'en_cuarentena': 11, 'aprobado': 0, 'descartado': 0, 'por_revisar': 0}
    c._aplicar_veredicto('1', APROBADO, 19, 20, '2026-11-24')
    assert c.estado['registro']['estados'] == {'pendiente': 14, 'en_cuarentena': 1, 'aprobado': 6, 'descartado': 1, 'por_revisar': 3}
    carpeta, resumen = c.escribir_registro(tmp_path / 'registro')
    aprobados = [json.loads(l) for l in (carpeta / 'aprobado.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(aprobados) == 6 and aprobados[0]['lote'] == 1 and aprobados[0]['decision_ia'] == 'aceptar'
    assert 'texto' not in aprobados[0]                                                # el registro no copia los documentos
    assert json.loads((carpeta / 'resumen.json').read_text(encoding='utf-8'))['estados']['por_revisar'] == 3
    texto = dibujar(c.estado, CONFIG)
    assert 'aprobados 6 · descartados 1 · por revisar 3' in texto and 'Telemetría: todavía no se audita' in texto


def test_si_ollama_no_esta_listo_reintenta_en_vez_de_detenerse(tmp_path):
    """Prueba: si ollama no esta listo reintenta en vez de detenerse."""
    c = Consola(tmp_path / 'estado', CONFIG)
    config = {**CONFIG, 'reintento_preparar_s': 0}

    class TrabajoDePrueba(Trabajo):
        intentos = 0

        def preparar(self):
            TrabajoDePrueba.intentos += 1
            if TrabajoDePrueba.intentos < 3:                    # los dos primeros arranques: Ollama todavía no responde
                raise ConnectionRefusedError('[WinError 10061] el equipo de destino denegó la conexión')
            self.R, self.canon, self.taxonomia, self.embebedor, self.generador, self.patrones = FalsoR, {}, {}, None, None, []
            self.coleccion = FalsaColeccion([])

        def esperar(self, motivo):
            self.detener.set()

    t = TrabajoDePrueba(c, config)
    t.correr()
    assert TrabajoDePrueba.intentos == 3
    assert c.estado['ultimo_error'] is None
    assert c.estado['bitacora'][-1]['preparada_tras_intentos'] == 3


def test_el_reintento_respeta_la_orden_de_detener(tmp_path):
    """Prueba: el reintento respeta la orden de detener."""
    c = Consola(tmp_path / 'estado', CONFIG)

    class TrabajoDePrueba(Trabajo):
        def preparar(self):
            self.detener.set()                                   # la persona presiona Ctrl+C mientras espera
            raise ConnectionRefusedError('sin Ollama')

    t = TrabajoDePrueba(c, {**CONFIG, 'reintento_preparar_s': 0})
    t.correr()
    assert 'intento 1' in c.estado['ultimo_error'] and c.estado['actividad'] == 'detenida'


def test_pureza_perfecta_con_retenidos_aprueba_con_aviso_y_habilita_promocion(tmp_path):
    """Prueba: pureza perfecta con retenidos aprueba con aviso y habilita promocion."""
    c = Consola(tmp_path / 'estado', CONFIG)
    llenar(c, ['aceptar'] * 7 + ['revision', 'revision', 'persona'])
    carpeta = c.cerrar(1, tmp_path / 'escritorio')
    filas = leer_planilla(carpeta / 'planilla.csv')
    for f in filas:
        f['humano_decision'] = 'aceptar'                          # los 3 aceptados son buenos y el detenido también era bueno
    assert Consola(tmp_path / 'estado', CONFIG).veredicto(1, filas) == (AVISO, 3, 4)
    c.aplicar_buzon()
    lote = c.lote(1)
    assert lote['estado'] == AVISO and lote['aceptados_bien'] == 3 and lote['aceptados_total'] == 3 and lote['retenidos_buenos'] == 1
    assert c.estado['registro']['estados']['aprobado'] == 7       # los 7 aceptados pasan a aprobados; los 3 detenidos a por_revisar
    assert c.estado['registro']['estados']['por_revisar'] == 3
    assert '3/3 aceptados, 1 retenidos' in dibujar(c.estado, CONFIG)
