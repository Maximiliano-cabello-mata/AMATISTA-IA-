"""Lógica de la consola de Amatista IA: estado, lotes, cierre con muestras, veredicto y freno.

Todo es lógica pura sobre archivos en `salidas/consola/` (nada sale de esta computadora): se prueba sin Ollama ni
MongoDB. Lo que habla con el exterior está en `consola/__main__.py`.

Ciclo de un lote (BASE.md, sección 3):
  1. trabajar: el revisor decide cada documento; la decisión queda EN CUARENTENA (lote abierto).
  2. cierre: al llegar al tamaño del lote, se sacan 20 muestras al azar (unas 14 de lo aceptado y 6 de lo demás)
     a una carpeta del escritorio. El lote queda «esperando veredicto».
  3. veredicto: la persona marca la planilla. 19–20 bien → aprobado · 17–18 → aprobado con aviso · ≤16 → no aprobado.
     Dos lotes no aprobados seguidos → freno: la consola deja de trabajar hasta que una persona lo quite.
  Mientras un lote espera veredicto, el siguiente sigue en cuarentena; con 2 lotes esperando, la consola se pausa.
"""
import csv
import html
import json
import os
import random
import time
from pathlib import Path

ESTADO_INICIAL = {
    'version': 1,
    'lote_actual': 1,
    'freno': False,
    'motivo_freno': None,
    'fallos_seguidos': 0,
    'actividad': 'detenida',
    'ultimo_error': None,
    'lotes': {},            # número → {estado, abierto, cerrado, documentos, decisiones, ...}
    'mediciones': None,     # resumen del criterio de mediciones
    'buzon_aplicado': [],   # mensajes del buzón ya aplicados (veredictos, freno quitado)
    'actualizado': None,
}
ESPERANDO, APROBADO, AVISO, NO_APROBADO, ABIERTO = 'esperando_veredicto', 'aprobado', 'aprobado_con_aviso', 'no_aprobado', 'abierto'
DECISIONES = ('aceptar', 'revision', 'rechazar', 'persona')


def ahora():
    return time.strftime('%Y-%m-%d %H:%M:%S')


class Consola:
    """Estado persistente en un JSON. Se guarda después de cada cambio: si la computadora se apaga, se retoma."""

    def __init__(self, carpeta, config):
        self.dir = Path(carpeta)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.config = config
        self.ruta_estado = self.dir / 'estado.json'
        self.estado = json.loads(self.ruta_estado.read_text(encoding='utf-8')) if self.ruta_estado.is_file() \
            else json.loads(json.dumps(ESTADO_INICIAL))

    # --- persistencia ------------------------------------------------------------------------------------------------
    def guardar(self):
        self.estado['actualizado'] = ahora()
        tmp = self.ruta_estado.with_suffix('.tmp')
        tmp.write_text(json.dumps(self.estado, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(tmp, self.ruta_estado)

    def ruta_lote(self, n):
        return self.dir / f'lote_{int(n):03d}.jsonl'

    def lote(self, n=None):
        n = str(n or self.estado['lote_actual'])
        return self.estado['lotes'].setdefault(n, {'estado': ABIERTO, 'abierto': ahora(), 'documentos': 0,
                                                  'decisiones': {d: 0 for d in DECISIONES}, 'segundos': []})

    def resultados(self, n):
        ruta = self.ruta_lote(n)
        if not ruta.is_file():
            return []
        return [json.loads(l) for l in ruta.read_text(encoding='utf-8').splitlines() if l.strip()]

    def revisados(self):
        """doc_id de todo lo que ya pasó por el revisor, en cualquier lote."""
        vistos = set()
        for n in self.estado['lotes']:
            vistos.update(r.get('doc_id') for r in self.resultados(n))
        return vistos

    # --- trabajo -----------------------------------------------------------------------------------------------------
    def esperando(self):
        return [n for n, l in self.estado['lotes'].items() if l['estado'] == ESPERANDO]

    def puede_trabajar(self):
        """(sí/no, por qué). Se detiene con freno o con demasiados lotes esperando veredicto."""
        if self.estado['freno']:
            return False, f"freno puesto: {self.estado['motivo_freno']}"
        if len(self.esperando()) >= self.config['max_lotes_esperando']:
            return False, f"{len(self.esperando())} lotes esperan tu veredicto"
        return True, ''

    def registrar(self, resultado):
        """Guarda la decisión de un documento en el lote abierto (cuarentena). Devuelve True si el lote se llenó."""
        lote = self.lote()
        with open(self.ruta_lote(self.estado['lote_actual']), 'a', encoding='utf-8') as f:
            f.write(json.dumps(resultado, ensure_ascii=False) + '\n')
        lote['documentos'] += 1
        decision = resultado.get('decision_efectiva') or 'persona'
        lote['decisiones'][decision] = lote['decisiones'].get(decision, 0) + 1
        segundos = (resultado.get('tiempos') or {}).get('total_s')
        if segundos is not None:
            lote['segundos'] = (lote['segundos'] + [round(segundos, 1)])[-500:]
        self.guardar()
        return lote['documentos'] >= self.config['tamano_lote']

    # --- cierre ------------------------------------------------------------------------------------------------------
    def muestrear(self, n):
        """Muestra estratificada y reproducible: la semilla es el número de lote."""
        res = self.resultados(n)
        rng = random.Random(1000 + int(n))
        aceptados = [r for r in res if r.get('decision_efectiva') == 'aceptar']
        otros = [r for r in res if r.get('decision_efectiva') != 'aceptar']
        total = min(self.config['muestras'], len(res))
        quiero_otros = min(len(otros), self.config['muestras_descartadas'])
        quiero_acept = min(len(aceptados), total - quiero_otros)
        quiero_otros = min(len(otros), total - quiero_acept)          # si faltan aceptados, se completa con los demás
        muestra = rng.sample(aceptados, quiero_acept) + rng.sample(otros, quiero_otros)
        rng.shuffle(muestra)
        return muestra

    def cerrar(self, n, carpeta_base):
        """Cierra el lote: escribe la carpeta de muestras y lo deja esperando veredicto."""
        n = str(n)
        lote = self.lote(n)
        muestra = self.muestrear(n)
        carpeta = Path(carpeta_base) / f'lote_{int(n):03d}'
        escribir_carpeta(carpeta, n, muestra, lote)
        lote.update(estado=ESPERANDO, cerrado=ahora(), carpeta=str(carpeta), muestras=len(muestra))
        if n == str(self.estado['lote_actual']):
            self.estado['lote_actual'] = int(n) + 1
        self.guardar()
        return carpeta

    # --- buzón: lo que escriben otros procesos (veredicto, quitar freno) sin pisar estado.json ------------------------
    # Solo el proceso que trabaja escribe estado.json. Los comandos de la persona dejan un mensaje en el buzón, y el
    # estado lo aplica al cargarse o en la siguiente vuelta del trabajo. Aplicar es idempotente.
    def escribir_buzon(self, tipo, datos):
        buzon = self.dir / 'buzon'
        buzon.mkdir(exist_ok=True)
        nombre = f"{time.strftime('%Y%m%d-%H%M%S')}-{tipo}-{random.randrange(1 << 30):08x}.json"
        (buzon / nombre).write_text(json.dumps({'tipo': tipo, **datos}, ensure_ascii=False), encoding='utf-8')
        return nombre

    def aplicar_buzon(self):
        buzon = self.dir / 'buzon'
        aplicados = set(self.estado.setdefault('buzon_aplicado', []))
        cambios = []
        for ruta in sorted(buzon.glob('*.json')) if buzon.is_dir() else []:
            if ruta.name in aplicados:
                continue
            m = json.loads(ruta.read_text(encoding='utf-8'))
            if m['tipo'] == 'veredicto':
                self._aplicar_veredicto(m['lote'], m['resultado'], m['bien'], m['marcadas'], m['fecha'])
            elif m['tipo'] == 'quitar_freno':
                self.estado.update(freno=False, motivo_freno=None, fallos_seguidos=0)
                self.estado.setdefault('bitacora', []).append({'fecha': m['fecha'], 'freno_quitado': m['motivo']})
            self.estado['buzon_aplicado'].append(ruta.name)
            cambios.append(m['tipo'])
        if cambios:
            self.guardar()
        return cambios

    def _aplicar_veredicto(self, n, resultado, bien, marcadas, fecha):
        lote = self.lote(n)
        self.estado['fallos_seguidos'] = self.estado['fallos_seguidos'] + 1 if resultado == NO_APROBADO else 0
        if self.estado['fallos_seguidos'] >= 2:
            self.estado.update(freno=True, motivo_freno=f'dos lotes seguidos no aprobados (el último, el {n})')
        lote.update(estado=resultado, veredicto=fecha, bien=bien, marcadas=marcadas)

    # --- veredicto ---------------------------------------------------------------------------------------------------
    @staticmethod
    def calificar(filas):
        """filas: la planilla marcada. Bien = la persona coincide con la decisión de la IA («persona» no cuenta como bien)."""
        marcadas = [f for f in filas if (f.get('humano_decision') or '').strip().lower() in DECISIONES[:3]]
        if len(marcadas) < len(filas):
            raise ValueError(f'faltan {len(filas) - len(marcadas)} muestras por marcar (humano_decision: aceptar, revision o rechazar)')
        bien = sum(f['humano_decision'].strip().lower() == (f.get('ia_decision') or '').strip().lower() for f in marcadas)
        n_m = len(marcadas)
        # Las reglas de BASE.md están escritas para 20 muestras; con menos se escalan en proporción.
        if bien >= round(19 / 20 * n_m):
            resultado = APROBADO
        elif bien >= round(17 / 20 * n_m):
            resultado = AVISO
        else:
            resultado = NO_APROBADO
        return resultado, bien, n_m

    def veredicto(self, n, filas):
        """Califica la planilla y deja el veredicto en el buzón. Devuelve (resultado, bien, marcadas)."""
        resultado, bien, n_m = self.calificar(filas)
        self.escribir_buzon('veredicto', {'lote': str(n), 'resultado': resultado, 'bien': bien, 'marcadas': n_m, 'fecha': ahora()})
        return resultado, bien, n_m

    def quitar_freno(self, motivo):
        self.escribir_buzon('quitar_freno', {'motivo': motivo, 'fecha': ahora()})


# --- carpeta del cierre ----------------------------------------------------------------------------------------------
COLUMNAS = ['n', 'doc_id', 'url', 'titulo', 'fuente', 'ia_decision', 'ia_etapa', 'ia_pregunta', 'ia_motivo', 'ia_cita',
            'ia_confianza', 'humano_decision', 'humano_nota']


def _fila(i, r):
    ia = r.get('ia') or {}
    return {'n': i, 'doc_id': r.get('doc_id'), 'url': r.get('url'), 'titulo': (r.get('titulo') or '').strip(),
            'fuente': r.get('fuente'), 'ia_decision': r.get('decision_efectiva') or 'persona', 'ia_etapa': ia.get('etapa', ''),
            'ia_pregunta': ia.get('pregunta', ''), 'ia_motivo': ia.get('motivo', ''), 'ia_cita': ia.get('cita', ''),
            'ia_confianza': ia.get('confianza', ''), 'humano_decision': '', 'humano_nota': ''}


def escribir_carpeta(carpeta, n, muestra, lote):
    carpeta.mkdir(parents=True, exist_ok=True)
    filas = [_fila(i, r) for i, r in enumerate(muestra, 1)]
    with open(carpeta / 'planilla.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS)
        w.writeheader()
        w.writerows(filas)

    tarjetas = []
    for f, r in zip(filas, muestra):
        extracto = ' '.join((r.get('texto') or '').split()[:300])
        tarjetas.append(f"""<article><h2>{f['n']}. {html.escape(f['titulo'] or '(sin título)')}</h2>
<p class="meta">{html.escape(str(f['fuente']))} · <a href="{html.escape(str(f['url']))}">{html.escape(str(f['url']))}</a></p>
<p class="ia"><b>IA: {html.escape(f['ia_decision'])}</b> · etapa {html.escape(f['ia_etapa'] or '—')} · pregunta {html.escape(f['ia_pregunta'] or '—')} · confianza {html.escape(f['ia_confianza'] or '—')}</p>
<p class="motivo">{html.escape(f['ia_motivo'] or '')}</p><p class="cita">Cita: {html.escape(f['ia_cita'] or '—')}</p>
<details><summary>Extracto del documento (300 palabras)</summary><p>{html.escape(extracto) or '(sin texto)'}</p></details></article>""")
    (carpeta / 'muestras.html').write_text(f"""<!doctype html><meta charset="utf-8"><title>Lote {n} · muestras</title>
<style>body{{font:15px/1.5 system-ui,sans-serif;max-width:860px;margin:2rem auto;padding:0 16px;color:#1e1a26}}
article{{border:1px solid #d6d0e0;border-radius:8px;padding:12px 16px;margin:12px 0}} h2{{font-size:17px;margin:0 0 4px}}
.meta,.cita{{color:#625c70;font-size:13px}} .ia{{margin:6px 0}} .motivo{{background:#f4f1f8;padding:8px;border-radius:6px}}</style>
<h1>Lote {n}: {len(filas)} muestras para revisar</h1>
<p>El lote tiene {lote['documentos']} documentos. Para cada muestra, decide si la IA acertó y escribe tu decisión en
<code>planilla.csv</code> (columna <code>humano_decision</code>: aceptar, revision o rechazar). Después:
<code>python -m consola veredicto {n}</code></p>
{''.join(tarjetas)}""", encoding='utf-8')

    bloques = []
    for f, r in zip(filas, muestra):
        extracto = ' '.join((r.get('texto') or '').split()[:300])
        bloques.append(f"## {f['n']}. {f['titulo']}\n\n- Fuente: {f['fuente']} · {f['url']}\n- Decisión de la IA: **{f['ia_decision']}** "
                       f"(etapa {f['ia_etapa'] or '—'}, pregunta {f['ia_pregunta'] or '—'}, confianza {f['ia_confianza'] or '—'})\n"
                       f"- Motivo de la IA: {f['ia_motivo']}\n- Cita: {f['ia_cita'] or '—'}\n\n> {extracto or '(sin texto)'}\n")
    (carpeta / 'para_segunda_opinion.md').write_text(
        f"# Lote {n}: {len(filas)} muestras para una segunda opinión\n\n"
        "Solo documentos de fuentes públicas (manual de Blender y foros con licencia confirmada). "
        "Nunca datos de estudiantes. Para cada muestra: ¿la decisión de la IA es correcta? ¿por qué?\n\n"
        + '\n'.join(bloques), encoding='utf-8')
    (carpeta / 'LEEME.txt').write_text(
        f"Lote {n}: cierre de Amatista IA\n\n"
        "1. Abre muestras.html y revisa cada muestra.\n"
        "2. En planilla.csv escribe tu decisión en humano_decision (aceptar, revision o rechazar) y, si quieres, una nota.\n"
        "3. Si quieres una segunda opinión, pasa para_segunda_opinion.md al asistente.\n"
        f"4. En la consola: python -m consola veredicto {n}\n\n"
        "19-20 bien: el lote se aprueba. 17-18: aprobado con aviso. 16 o menos: no se aprueba.\n"
        "Dos lotes no aprobados seguidos ponen el freno: la IA deja de trabajar hasta que lo quites.\n", encoding='utf-8')
    return filas


def carpeta_escritorio(nombre='Amatista IA · cierres'):
    """La carpeta del escritorio de esta computadora (Windows con o sin OneDrive, o Linux)."""
    perfil = Path(os.environ.get('USERPROFILE') or Path.home())
    for candidato in (perfil / 'OneDrive' / 'Desktop', perfil / 'OneDrive' / 'Escritorio', perfil / 'Desktop', perfil / 'Escritorio'):
        if candidato.is_dir():
            return candidato / nombre
    return perfil / nombre


def leer_planilla(ruta):
    with open(ruta, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))
