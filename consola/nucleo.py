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
import io
import html
import json
import os
import random
import tempfile
import time
import unicodedata
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
    'mediciones': None,     # resumen del criterio de mediciones (telemetría: todavía no se audita)
    'registro': None,       # cuántos documentos de conocimiento hay en cada estado (se deriva de los lotes)
    'documentos_en_fuente': None,
    'buzon_aplicado': [],   # mensajes del buzón ya aplicados (veredictos, freno quitado)
    'actualizado': None,
}
ESPERANDO, APROBADO, AVISO, NO_APROBADO, ABIERTO = 'esperando_veredicto', 'aprobado', 'aprobado_con_aviso', 'no_aprobado', 'abierto'
DECISIONES = ('aceptar', 'revision', 'rechazar', 'persona')

# El estado de cada documento de conocimiento, en un solo lugar. Se DERIVA de los lotes y sus veredictos: no hay una
# segunda copia que pueda contradecirlos.
#   pendiente      está en la fuente (MongoDB) y la IA todavía no lo revisa
#   en_cuarentena  la IA ya lo revisó, pero su lote no tiene veredicto
#   aprobado       la IA lo aceptó y el lote se aprobó: pasa la puerta (lo que se promoverá al cubo o a MongoDB)
#   descartado     la IA lo rechazó y el lote se aprobó
#   por_revisar    la IA dudó (revisión o persona) o el lote no se aprobó: espera a una persona o una segunda pasada
ESTADOS_DOCUMENTO = ('pendiente', 'en_cuarentena', 'aprobado', 'descartado', 'por_revisar')


def estado_documento(decision, estado_lote):
    if estado_lote in (ABIERTO, ESPERANDO):
        return 'en_cuarentena'
    if estado_lote == NO_APROBADO:
        return 'por_revisar'            # el juicio de un lote no aprobado no se usa: ni lo aceptado ni lo rechazado
    return {'aceptar': 'aprobado', 'rechazar': 'descartado'}.get(decision, 'por_revisar')


def decision_normal(texto):
    """«Revisión», «REVISION » y «revision» son la misma marca: sin acentos, sin espacios y en minúsculas."""
    t = unicodedata.normalize('NFKD', (texto or '').strip().lower())
    return ''.join(c for c in t if not unicodedata.combining(c))


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

    # --- registro: un estado por documento ----------------------------------------------------------------------------
    def registro(self):
        """Cada documento revisado con su estado. Si un documento aparece en dos lotes, manda el más reciente."""
        docs = {}
        for n, lote in sorted(self.estado['lotes'].items(), key=lambda x: int(x[0])):
            for r in self.resultados(n):
                decision = r.get('decision_efectiva') or 'persona'
                docs[r.get('doc_id')] = {'doc_id': r.get('doc_id'), 'url': r.get('url'), 'titulo': r.get('titulo'),
                                         'fuente': r.get('fuente'), 'lote': int(n), 'decision_ia': decision,
                                         'estado': estado_documento(decision, lote['estado'])}
        return list(docs.values())

    def resumen_registro(self, docs=None):
        docs = self.registro() if docs is None else docs
        cuenta = {e: 0 for e in ESTADOS_DOCUMENTO}
        for d in docs:
            cuenta[d['estado']] += 1
        fuente = self.estado.get('documentos_en_fuente')
        cuenta['pendiente'] = max(fuente - len(docs), 0) if fuente is not None else None
        return {'tipo': 'conocimiento', 'en_fuente': fuente, 'revisados': len(docs), 'estados': cuenta, 'actualizado': ahora()}

    def actualizar_registro(self):
        self.estado['registro'] = self.resumen_registro()

    def escribir_registro(self, carpeta=None):
        """Una lista por estado en salidas/consola/registro/conocimiento/<estado>.jsonl, y el resumen. Se queda en esta
        computadora (salidas/ no se sube). La lista de aprobados es la que consumirá la promoción al cubo o a MongoDB."""
        carpeta = Path(carpeta or self.dir / 'registro') / 'conocimiento'
        carpeta.mkdir(parents=True, exist_ok=True)
        docs = self.registro()
        for e in ESTADOS_DOCUMENTO[1:]:
            with open(carpeta / f'{e}.jsonl', 'w', encoding='utf-8') as f:
                for d in docs:
                    if d['estado'] == e:
                        f.write(json.dumps(d, ensure_ascii=False) + '\n')
        resumen = self.resumen_registro(docs)
        (carpeta / 'resumen.json').write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding='utf-8')
        self.estado['registro'] = resumen
        self.guardar()
        return carpeta, resumen

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
        self.actualizar_registro()
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
            if m['tipo'] == 'veredicto' and self.estado['lotes'].get(str(m['lote']), {}).get('estado') == ESPERANDO:
                self._aplicar_veredicto(
                    m['lote'], m['resultado'], m['bien'], m['marcadas'], m['fecha'],
                    aceptados_bien=m.get('aceptados_bien'),
                    aceptados_total=m.get('aceptados_total'),
                    retenidos_buenos=m.get('retenidos_buenos'),
                )
            elif m['tipo'] == 'quitar_freno':
                self.estado.update(freno=False, motivo_freno=None, fallos_seguidos=0)
                self.estado.setdefault('bitacora', []).append({'fecha': m['fecha'], 'freno_quitado': m['motivo']})
            self.estado['buzon_aplicado'].append(ruta.name)
            cambios.append(m['tipo'])
        if cambios:
            self.guardar()
        return cambios

    def _aplicar_veredicto(self, n, resultado, bien, marcadas, fecha,
                           aceptados_bien=None, aceptados_total=None, retenidos_buenos=None):
        lote = self.lote(n)
        self.estado['fallos_seguidos'] = self.estado['fallos_seguidos'] + 1 if resultado == NO_APROBADO else 0
        if self.estado['fallos_seguidos'] >= 2:
            self.estado.update(freno=True, motivo_freno=f'dos lotes seguidos no aprobados (el último, el {n})')
        datos = {'estado': resultado, 'veredicto': fecha, 'bien': bien, 'marcadas': marcadas}
        if aceptados_total is not None:
            datos['aceptados_bien'] = aceptados_bien
            datos['aceptados_total'] = aceptados_total
            datos['retenidos_buenos'] = retenidos_buenos
        lote.update(datos)
        self.actualizar_registro()

    # --- veredicto ---------------------------------------------------------------------------------------------------
    @staticmethod
    def resumen_calificacion(filas):
        """Aplica los umbrales de BASE.md y cuenta por separado admisiones y retenciones."""
        if not filas:
            raise ValueError('la planilla no contiene muestras')
        marcadas = [f for f in filas if decision_normal(f.get('humano_decision')) in DECISIONES[:3]]
        if len(marcadas) < len(filas):
            raise ValueError(f'faltan {len(filas) - len(marcadas)} muestras por marcar (humano_decision: aceptar, revision o rechazar)')
        n_m = len(marcadas)
        bien = sum(decision_normal(f['humano_decision']) == decision_normal(f.get('ia_decision')) for f in marcadas)
        aceptados = [f for f in marcadas if decision_normal(f.get('ia_decision')) == 'aceptar']
        n_a = len(aceptados)
        aceptados_bien = sum(decision_normal(f['humano_decision']) == 'aceptar' for f in aceptados)
        retenidos_buenos = sum(
            decision_normal(f.get('ia_decision')) != 'aceptar' and decision_normal(f['humano_decision']) == 'aceptar'
            for f in marcadas
        )
        if bien * 20 >= 19 * n_m:
            resultado = APROBADO
        elif bien * 20 >= 17 * n_m:
            resultado = AVISO
        else:
            resultado = NO_APROBADO
        return {
            'resultado': resultado,
            'bien': bien,
            'marcadas': n_m,
            'aceptados_bien': aceptados_bien,
            'aceptados_total': n_a,
            'retenidos_buenos': retenidos_buenos,
        }

    @staticmethod
    def calificar(filas):
        """filas: la planilla marcada. Devuelve (resultado, bien, marcadas)."""
        r = Consola.resumen_calificacion(filas)
        return r['resultado'], r['bien'], r['marcadas']

    def veredicto(self, n, filas):
        """Califica la planilla y deja el veredicto en el buzón. Devuelve (resultado, bien, marcadas)."""
        lote = self.estado['lotes'].get(str(n), {})
        if lote.get('estado') != ESPERANDO or len(filas) != lote.get('muestras'):
            raise ValueError('el lote debe estar esperando su muestra completa')
        r = self.resumen_calificacion(filas)
        self.escribir_buzon('veredicto', {'lote': str(n), **r, 'fecha': ahora()})
        return r['resultado'], r['bien'], r['marcadas']

    def preparar_revision_ciega(self, n):
        """Prepara las mismas muestras de un cierre anterior sin modificar sus planillas."""
        lote = self.estado['lotes'].get(str(n), {})
        if lote.get('estado') != ESPERANDO:
            raise ValueError('el lote debe estar esperando veredicto')
        carpeta = Path(lote['carpeta'])
        if ruta_planilla(lote).parent != carpeta or (carpeta / 'referencia_ia.json').exists():
            return ruta_planilla(lote).parent
        filas = leer_planilla(carpeta / 'planilla.csv')
        if any((f.get('humano_decision') or f.get('humano_nota') or '').strip() for f in filas):
            raise ValueError('la planilla anterior ya tiene marcas; termina ese cierre antes de cambiar el formato')
        originales = {r['doc_id']: r for r in self.resultados(n)}
        ids = [f['doc_id'] for f in filas]
        if len(set(ids)) != len(ids) or len(ids) != lote['muestras'] or not set(ids) <= originales.keys():
            raise ValueError('la planilla anterior no corresponde a una muestra completa del lote')
        destino = carpeta / 'revision_ciega'
        with tempfile.TemporaryDirectory(dir=carpeta) as temporal:
            borrador = Path(temporal) / 'revision_ciega'
            escribir_carpeta(borrador, n, [originales[i] for i in ids], lote)
            borrador.rename(destino)
        return destino

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
        columnas_ciegas = [c for c in COLUMNAS if not c.startswith('ia_')]
        w = csv.DictWriter(f, fieldnames=columnas_ciegas, extrasaction='ignore')
        w.writeheader()
        w.writerows(filas)

    referencia = {f['doc_id']: {k: v for k, v in f.items() if k.startswith('ia_')} for f in filas}
    (carpeta / 'referencia_ia.json').write_text(json.dumps(referencia, ensure_ascii=False), encoding='utf-8')

    tarjetas = []
    for f, r in zip(filas, muestra):
        extracto = ' '.join((r.get('texto') or '').split()[:300])
        tarjetas.append(f"""<article><h2>{f['n']}. {html.escape(f['titulo'] or '(sin título)')}</h2>
<p class="meta">{html.escape(str(f['fuente']))} · <a href="{html.escape(str(f['url']))}">{html.escape(str(f['url']))}</a></p>
<details><summary>Extracto del documento (300 palabras)</summary><p>{html.escape(extracto) or '(sin texto)'}</p></details></article>""")
    (carpeta / 'muestras.html').write_text(f"""<!doctype html><meta charset="utf-8"><title>Lote {n} · muestras</title>
<style>body{{font:15px/1.5 system-ui,sans-serif;max-width:860px;margin:2rem auto;padding:0 16px;color:#1e1a26}}
article{{border:1px solid #d6d0e0;border-radius:8px;padding:12px 16px;margin:12px 0}} h2{{font-size:17px;margin:0 0 4px}}
.meta{{color:#625c70;font-size:13px}}</style>
<h1>Lote {n}: {len(filas)} muestras para revisar</h1>
<p>El lote tiene {lote['documentos']} documentos. Para cada muestra, lee el extracto o abre la fuente y escribe tu decisión en
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
        "3. Guarda tus marcas antes de consultar para_segunda_opinion.md.\n"
        f"4. En la consola: python -m consola veredicto {n}\n\n"
        "19-20 bien: el lote se aprueba. 17-18: aprobado con aviso. 16 o menos: no se aprueba.\n"
        "Dos lotes no aprobados seguidos ponen el freno: la IA deja de trabajar hasta que lo quites.\n", encoding='utf-8')
    return filas


def _escritorio_windows():
    if os.name != 'nt':
        return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders') as k:
            ruta_reg = Path(os.path.expandvars(winreg.QueryValueEx(k, 'Desktop')[0]))
            return ruta_reg if ruta_reg.is_dir() else None
    except OSError:
        return None


def carpeta_escritorio(nombre='Amatista IA · cierres'):
    """La carpeta del escritorio de esta computadora (Windows con o sin OneDrive empresarial, o Linux)."""
    ruta_reg = _escritorio_windows()
    if ruta_reg is not None:
        return ruta_reg / nombre
    perfil = Path(os.environ.get('USERPROFILE') or Path.home())
    candidatos = []
    for var in ('OneDriveCommercial', 'OneDrive'):
        if os.environ.get(var):
            base = Path(os.environ[var])
            candidatos += [base / 'Desktop', base / 'Escritorio']
    candidatos += [perfil / 'OneDrive' / 'Desktop', perfil / 'OneDrive' / 'Escritorio',
                   perfil / 'Desktop', perfil / 'Escritorio']
    for candidato in candidatos:
        if candidato.is_dir():
            return candidato / nombre
    return perfil / nombre


def ruta_planilla(lote):
    carpeta = Path(lote['carpeta'])
    ciega = carpeta / 'revision_ciega' / 'planilla.csv'
    return ciega if ciega.is_file() else carpeta / 'planilla.csv'


def leer_planilla(ruta):
    """La planilla marcada. Excel en español puede guardarla con «;» en vez de «,»: se detecta."""
    with open(ruta, encoding='utf-8-sig', newline='') as f:
        texto = f.read()
    primera = texto.splitlines()[0] if texto else ''
    separador = ';' if primera.count(';') > primera.count(',') else ','
    lector = csv.DictReader(io.StringIO(texto, newline=''), delimiter=separador)
    filas = list(lector)
    referencia = Path(ruta).parent / 'referencia_ia.json'
    if not referencia.exists() and 'ia_decision' in (lector.fieldnames or []):
        return filas  # planillas anteriores al cierre ciego
    if not referencia.is_file():
        raise ValueError('falta la referencia del cierre ciego')
    clave = json.loads(referencia.read_text(encoding='utf-8'))
    ids = [f.get('doc_id') for f in filas]
    if len(ids) != len(clave) or set(ids) != set(clave):
        raise ValueError('las filas no corresponden a la muestra completa de este cierre')
    return [{**f, **clave[f['doc_id']]} for f in filas]


def etiquetas_de_planilla(n, filas):
    """Las marcas de la persona en un cierre, para guardarlas en el repositorio: solo título, URL pública, fuente y las
    dos decisiones (la de la IA y la de la persona). Ni el texto del documento ni el motivo de la IA."""
    docs = []
    for f in filas:
        docs.append({'n': int(f.get('n') or 0), 'titulo': (f.get('titulo') or '').strip(), 'url': f.get('url'),
                     'fuente': f.get('fuente'), 'ia': decision_normal(f.get('ia_decision')),
                     'humano': decision_normal(f.get('humano_decision')) or None,
                     'nota': (f.get('humano_nota') or '').strip() or None})
    return {'version': 1, 'lote': int(n), 'marcadas': sum(1 for d in docs if d['humano'] in DECISIONES[:3]), 'documentos': docs}
