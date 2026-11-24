"""Consola de control de Amatista IA.

    python -m consola                       # el botón: arranca el trabajo 24/7 y muestra la consola en vivo
    python -m consola estado                # una foto del estado, sin trabajar
    python -m consola veredicto 1           # lee la planilla marcada del lote 1 y deja el veredicto
    python -m consola etiquetas 1           # guarda las marcas del lote 1 en revisor/etiquetas/lote_001.yml
    python -m consola cierre 1              # cierra un lote a mano (normalmente es automático al llegar a 100)
    python -m consola quitar-freno "motivo" # quita el freno después de corregir lo que falló
    python -m consola instalar-acceso       # crea el botón «Iniciar Amatista IA» en el escritorio

El trabajo: el revisor (revisor/revisar.py, versión 3) decide cada documento de MongoDB (usuario de solo lectura) y
la decisión queda en cuarentena en salidas/consola/. Al llegar al tamaño del lote, la consola hace el cierre: 20
muestras al azar en una carpeta del escritorio. Nada se escribe en MongoDB, el cubo, el lago ni Supabase.
"""
import argparse
import os
import statistics
import sys
import threading
import time
import traceback
import urllib.request
from pathlib import Path

import yaml

from consola.nucleo import ABIERTO, ESPERANDO, Consola, carpeta_escritorio, etiquetas_de_planilla, leer_planilla

RAIZ = Path(__file__).resolve().parents[1]
CARPETA = RAIZ / 'salidas' / 'consola'
CAMPOS = ['doc_id', 'url', 'fuente', 'titulo', 'texto', 'licencia', 'modo', 'preguntas', 'puntajes']


def cargar_config():
    return yaml.safe_load((RAIZ / 'consola' / 'config.yml').read_text(encoding='utf-8'))


def carpeta_cierres(config):
    return Path(config['carpeta_cierres']) if config.get('carpeta_cierres') else carpeta_escritorio()


# --- la vista ---------------------------------------------------------------------------------------------------------
def dibujar(estado, config, ancho=78):
    """La consola en texto: qué hace la IA, cómo va el lote, a qué velocidad y qué espera de la persona."""
    lineas = ['=' * ancho, f"AMATISTA IA · CONSOLA DEL AUDITOR{('actualizado ' + (estado.get('actualizado') or '—')).rjust(ancho - 33)}",
              '=' * ancho]
    n = str(estado['lote_actual'])
    lote = estado['lotes'].get(n, {'documentos': 0, 'decisiones': {}, 'segundos': []})
    lineas.append(f"Actividad: {estado.get('actividad') or '—'}")
    freno = f"SÍ · {estado.get('motivo_freno')}" if estado.get('freno') else 'no'
    esperando = [k for k, l in estado['lotes'].items() if l['estado'] == ESPERANDO]
    lineas.append(f"Freno: {freno} · Lotes esperando tu veredicto: {', '.join(esperando) or 'ninguno'}")
    seg = lote.get('segundos') or []
    if seg:
        mediana = statistics.median(seg[-20:])
        faltan = max(config['tamano_lote'] - lote['documentos'], 0)
        lineas.append(f"Velocidad: {mediana:.0f} s por documento · faltan {faltan} para el cierre (~{faltan * mediana / 3600:.1f} h)")
    d = lote.get('decisiones') or {}
    barra = int(30 * lote['documentos'] / max(config['tamano_lote'], 1))
    lineas += ['', f"Lote {n} · {lote['documentos']}/{config['tamano_lote']}  [{'#' * barra}{'.' * (30 - barra)}]",
               f"  aceptar {d.get('aceptar', 0)} · revisión {d.get('revision', 0)} · rechazar {d.get('rechazar', 0)}"
               f" · a una persona {d.get('persona', 0)}"]
    cerrados = [(k, l) for k, l in sorted(estado['lotes'].items(), key=lambda x: int(x[0])) if l['estado'] != ABIERTO]
    if cerrados:
        lineas += ['', 'Lotes cerrados:']
        for k, l in cerrados[-6:]:
            extra = f" · {l['bien']}/{l['marcadas']} bien" if 'bien' in l else ''
            lineas.append(f"  {k:>3}  {l['estado']:<20} {l.get('cerrado', '')}{extra}")
            if l['estado'] == ESPERANDO:
                lineas.append(f"       muestras en: {l.get('carpeta')}")
    if estado.get('ultimo_error'):
        lineas += ['', f"Último error: {estado['ultimo_error']}"]
    lineas += ['', 'Ctrl+C detiene la consola. Lo revisado se conserva y se retoma al volver a iniciar.', '=' * ancho]
    return '\n'.join(lineas)


# --- el trabajo -------------------------------------------------------------------------------------------------------
class Trabajo:
    """Prepara el revisor una vez y revisa documentos de MongoDB uno por uno, sin parar."""

    def __init__(self, consola, config):
        self.c, self.config = consola, config
        self.detener = threading.Event()

    def actividad(self, texto):
        self.c.estado['actividad'] = texto
        self.c.guardar()

    def preparar(self):
        from indexador.entorno import cargar_env
        from indexador.indexar import Ollama
        from revisor import revisar as R
        cargar_env()
        url, clave = os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_PUBLISHABLE_KEY')
        uri = os.environ.get('MONGO_URI_LECTURA')
        if not (url and clave and uri):
            raise RuntimeError('Faltan SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY o MONGO_URI_LECTURA en .env')
        self.actividad('preparando: canon, taxonomía y modelos')
        self.canon = R.descargar_canon(url, clave, str(RAIZ / 'salidas' / 'canon_local.json'),
                                       refrescar=self.config.get('refrescar_canon_al_iniciar', True))
        commit = next(d['commit_fijado'] for d in self.canon['documentos'].values() if d['repositorio'] == 'g7b')

        def g7b(archivo):
            req = urllib.request.Request(R.G7B_CRUDO.format(commit=commit, archivo=archivo), headers={'User-Agent': 'amatista-ia-consola'})
            with urllib.request.urlopen(req, timeout=60) as r:
                return yaml.safe_load(r.read().decode('utf-8'))
        self.taxonomia, hardware = g7b('taxonomia.yml'), g7b('hardware.yml')
        self.patrones = R.patrones_de(hardware)
        base = os.environ.get('OLLAMA_HOST', 'http://127.0.0.1:11434')
        self.embebedor = Ollama(base, self.config['embeddings'])
        modelos = {f['modelo_embedding'] for f in self.canon['fragmentos']}
        if modelos != {self.embebedor.id}:
            raise RuntimeError(f'El canon se indexó con {modelos} y aquí está {self.embebedor.id}')
        self.generador = R.Generador(base, self.config['modelo'])
        self.R = R
        from pymongo import MongoClient
        self.coleccion = MongoClient(uri, serverSelectionTimeoutMS=20000)[os.environ.get('MONGO_DATABASE', 'conocimiento_3d')]['documentos']

    def pendientes(self):
        vistos = self.c.revisados()
        for doc in self.coleccion.find({}, {'_id': 0, **{k: 1 for k in CAMPOS}}).sort('doc_id', 1):
            if doc.get('doc_id') not in vistos:
                yield doc

    def esperar(self, motivo):
        self.actividad(f"en pausa: {motivo}")
        self.detener.wait(self.config['espera_s'])

    def revisar(self, doc):
        r = self.R.revisar_todo([doc], self.canon, self.taxonomia, self.embebedor, self.generador,
                                self.config['palabras'], cuantos=self.config['cuantos'], registro=lambda *_: None,
                                patrones_hardware=self.patrones, criterios=self.config['criterios'])[0]
        r['texto'] = self.R.palabras(doc.get('texto'), 400)       # para las muestras; se queda en esta computadora
        r['fecha'] = time.strftime('%Y-%m-%d %H:%M:%S')
        return r

    def correr(self):
        try:
            self.preparar()
        except Exception as e:
            self.c.estado['ultimo_error'] = f'al preparar: {e}'
            self.actividad('detenida: no se pudo preparar (ver último error)')
            return
        while not self.detener.is_set():
            hubo = False
            for doc in self.pendientes():
                if self.detener.is_set():
                    break
                self.c.aplicar_buzon()
                puede, motivo = self.c.puede_trabajar()
                while not puede and not self.detener.is_set():
                    self.esperar(motivo)
                    self.c.aplicar_buzon()
                    puede, motivo = self.c.puede_trabajar()
                if self.detener.is_set():
                    break
                hubo = True
                n = self.c.estado['lote_actual']
                self.actividad(f"revisando «{(doc.get('titulo') or doc.get('url') or '')[:50].strip()}» (lote {n})")
                try:
                    resultado = self.revisar(doc)
                except Exception as e:
                    self.c.estado['ultimo_error'] = f"{time.strftime('%H:%M')} {type(e).__name__}: {e}"
                    self.c.guardar()
                    self.detener.wait(60)
                    continue
                if self.c.registrar(resultado):
                    carpeta = self.c.cerrar(n, carpeta_cierres(self.config))
                    self.actividad(f'lote {n} cerrado: 20 muestras en {carpeta}')
            if not hubo and not self.detener.is_set():
                self.c.aplicar_buzon()
                self.esperar('no hay documentos nuevos en MongoDB')
        self.actividad('detenida')


def cmd_iniciar(config):
    consola = Consola(CARPETA, config)
    consola.aplicar_buzon()
    trabajo = Trabajo(consola, config)
    hilo = threading.Thread(target=trabajo.correr, daemon=True)
    hilo.start()
    try:
        while hilo.is_alive():
            os.system('cls' if os.name == 'nt' else 'clear')
            print(dibujar(consola.estado, config))
            hilo.join(config['refresco_s'])
    except KeyboardInterrupt:
        trabajo.detener.set()
        print('\nDeteniendo… (termina el documento en curso)')
        hilo.join(600)
    print(dibujar(consola.estado, config))
    return 0


def cmd_instalar_acceso():
    """El botón: un acceso en el escritorio que abre la consola y arranca el trabajo."""
    escritorio = carpeta_escritorio('x').parent
    if os.name == 'nt':
        ruta = escritorio / 'Iniciar Amatista IA.bat'
        activar = RAIZ / '.venv' / 'Scripts' / 'activate.bat'
        ruta.write_text('@echo off\r\nchcp 65001 >nul\r\ntitle Amatista IA - consola\r\n' f'cd /d "{RAIZ}"\r\n'
                        + (f'call "{activar}"\r\n' if activar.is_file() else '') + 'python -m consola\r\npause\r\n', encoding='utf-8')
    else:
        ruta = escritorio / 'iniciar-amatista-ia.sh'
        activar = RAIZ / '.venv' / 'bin' / 'activate'
        ruta.write_text('#!/usr/bin/env bash\n' f'cd "{RAIZ}"\n' + (f'source "{activar}"\n' if activar.is_file() else '')
                        + 'python3 -m consola\n', encoding='utf-8')
        ruta.chmod(0o755)
    print(f'Botón creado: {ruta}')
    return 0


def main(argv=None):
    config = cargar_config()
    p = argparse.ArgumentParser(description='Consola de control de Amatista IA.')
    sub = p.add_subparsers(dest='cmd')
    sub.add_parser('estado')
    v = sub.add_parser('veredicto')
    v.add_argument('lote', type=int)
    c = sub.add_parser('cierre')
    c.add_argument('lote', type=int)
    f = sub.add_parser('quitar-freno')
    f.add_argument('motivo')
    sub.add_parser('instalar-acceso')
    e = sub.add_parser('etiquetas')
    e.add_argument('lote', type=int)
    a = p.parse_args(argv)

    if a.cmd is None:
        return cmd_iniciar(config)
    if a.cmd == 'instalar-acceso':
        return cmd_instalar_acceso()
    consola = Consola(CARPETA, config)
    if a.cmd == 'estado':
        print(dibujar(consola.estado, config))
    elif a.cmd == 'veredicto':
        lote = consola.estado['lotes'].get(str(a.lote))
        if not lote or not lote.get('carpeta'):
            sys.exit(f'El lote {a.lote} no tiene cierre todavía.')
        try:
            resultado, bien, n = consola.veredicto(a.lote, leer_planilla(Path(lote['carpeta']) / 'planilla.csv'))
        except ValueError as e:
            sys.exit(str(e))
        print(f'Lote {a.lote}: {bien} de {n} bien → {resultado}. La consola lo aplica en su siguiente vuelta.')
    elif a.cmd == 'etiquetas':
        # Las marcas de la persona del cierre N → revisor/etiquetas/lote_NNN.yml (se sube; la planilla no).
        lote = consola.estado['lotes'].get(str(a.lote))
        if not lote or not lote.get('carpeta'):
            sys.exit(f'El lote {a.lote} no tiene cierre todavía.')
        datos = etiquetas_de_planilla(a.lote, leer_planilla(Path(lote['carpeta']) / 'planilla.csv'))
        destino = RAIZ / 'revisor' / 'etiquetas' / f'lote_{a.lote:03d}.yml'
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text('# Marcas de la persona en el cierre (consola etiquetas). Solo títulos y URL públicas.\n'
                           + yaml.safe_dump(datos, allow_unicode=True, sort_keys=False), encoding='utf-8')
        print(f'{datos["marcadas"]} de {len(datos["documentos"])} marcadas → {destino}')
    elif a.cmd == 'cierre':
        # Solo con la consola detenida: el cierre escribe el estado directamente.
        print(f'Cierre: {consola.cerrar(a.lote, carpeta_cierres(config))}')
    elif a.cmd == 'quitar-freno':
        consola.quitar_freno(a.motivo)
        print('Freno quitado. La consola lo aplica en su siguiente vuelta.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(1)
