"""Pesos de confianza de la IA revisora: de lo teórico a lo observado.

    python -m revisor.confianza
    python -m revisor.confianza --etiquetas salidas/prueba_revisor.csv     # con las decisiones de una persona
    python -m revisor.confianza --corridas salidas/v1_qwen3.json salidas/v2_qwen3.json --etiquetas planilla.csv

Tres capas:

1. **Comportamiento** (sin persona): cada comprobación por código (JSON válido, cita válida, datos fieles) es un
   éxito o un fracaso. Se parte del peso teórico Beta(a, b) de revisor/pesos_teoricos.yml y se suma lo observado
   en revisor/comportamiento.yml: Beta(a + éxitos, b + fracasos).
2. **Acierto** (con persona): la sensibilidad (de lo que una persona sacaría, cuánto marca) y la especificidad
   (de lo que deja, cuánto deja) de cada revisor, actualizadas con las etiquetas humanas de la misma forma.
3. **Combinación**: las opiniones se suman en log-odds, como un clasificador bayesiano ingenuo:

       logit P(problema) = logit(tasa de problemas) + Σ_revisor peso(voto)
       peso(marca problema) = ln(sens / (1 − espec))
       peso(deja)           = ln((1 − sens) / espec)

   Un revisor que no sabe más que una moneda (sens = espec = 0.5) pesa 0. Con P se ordena el trabajo de la
   persona: P < 0.20 se propone dejar, P > 0.80 se propone revisar, y lo de en medio lo decide una persona.

Además calcula el puntaje de Brier de las predicciones ya resueltas (revisor/predicciones.yml).
El algoritmo no decide nada: ordena y dice cuánto se puede confiar en cada opinión.
"""
import argparse
import csv
import json
import math
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent
PROBLEMA = {'revision', 'rechazar'}
UMBRAL_DEJAR, UMBRAL_REVISAR = 0.20, 0.80


# --- Beta ------------------------------------------------------------------------------------------------------------
def _betacf(a, b, x):
    """Fracción continua de la beta incompleta (Numerical Recipes, 6.4)."""
    tiny = 1e-30
    c, d = 1.0, 1.0 - (a + b) * x / (a + 1)
    d = 1 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        for num in (m * (b - m) * x / ((a + m2 - 1) * (a + m2)), -(a + m) * (a + b + m) * x / ((a + m2) * (a + m2 + 1))):
            d = 1 + num * d
            d = 1 / (d if abs(d) > tiny else tiny)
            c = 1 + num / c
            c = c if abs(c) > tiny else tiny
            h *= d * c
        if abs(d * c - 1) < 1e-12:
            break
    return h


def beta_cdf(x, a, b):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    ln = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
    if x < (a + 1) / (a + b + 2):
        return math.exp(ln) * _betacf(a, b, x) / a
    return 1 - math.exp(ln) * _betacf(b, a, 1 - x) / b


def beta_cuantil(q, a, b):
    bajo, alto = 0.0, 1.0
    for _ in range(80):
        medio = (bajo + alto) / 2
        bajo, alto = (medio, alto) if beta_cdf(medio, a, b) < q else (bajo, medio)
    return (bajo + alto) / 2


def resumen_beta(a, b):
    return {'media': a / (a + b), 'intervalo_90': [beta_cuantil(0.05, a, b), beta_cuantil(0.95, a, b)], 'a': a, 'b': b}


def actualizar(prior, exitos, total):
    a, b = prior
    return a + exitos, b + (total - exitos)


# --- Capas -----------------------------------------------------------------------------------------------------------
def capa_comportamiento(teoricos, comportamiento):
    """Por revisor y señal: el peso teórico, lo observado y el peso actualizado."""
    salida = {}
    for corrida in comportamiento.get('corridas', []):
        modelo = corrida['modelo']
        for senal, (k, n) in corrida['senales'].items():
            prior = teoricos['revisores'].get(modelo, {}).get(senal, [1, 1])
            fila = salida.setdefault(modelo, {}).setdefault(senal, {'teorico': list(prior), 'k': 0, 'n': 0})
            fila['k'] += k
            fila['n'] += n
    for modelo, senales in salida.items():
        for senal, fila in senales.items():
            fila['teorico_media'] = fila['teorico'][0] / sum(fila['teorico'])
            fila['observado'] = fila['k'] / fila['n'] if fila['n'] else None
            fila['actualizado'] = resumen_beta(*actualizar(fila['teorico'], fila['k'], fila['n']))
    return salida


def es_problema(decision):
    return (decision or '').strip().lower() in PROBLEMA


def prior_de(teoricos, revisor):
    """«qwen3:8b@v2» usa los pesos teóricos de «qwen3:8b»."""
    return teoricos['revisores'].get(revisor.split('@')[0], {})


def votos_de_corridas(rutas):
    """Documentos con el voto de cada corrida (prueba_revisor.json), unidos por URL."""
    por_url = {}
    for ruta in rutas:
        datos = json.loads(Path(ruta).read_text(encoding='utf-8'))
        r = datos['resumen']
        nombre = f"{r['modelo']}@v{r.get('revisor', 1)}" + ('+criterios' if r.get('criterios') else '')
        for x in datos['resultados']:
            if not x.get('ia'):
                continue
            d = por_url.setdefault(x['url'], {'titulo': (x.get('titulo') or '').strip(), 'url': x['url'], 'votos': {}, 'humano': None})
            d['votos'][nombre] = x['ia']['decision']
    return list(por_url.values())


def capa_acierto(teoricos, documentos):
    """Sensibilidad, especificidad y tasa de problemas, actualizadas con los documentos que tienen etiqueta humana."""
    etiquetados = [d for d in documentos if d.get('humano')]
    base = actualizar(teoricos['problemas_entre_aceptados'],
                      sum(es_problema(d['humano']) for d in etiquetados), len(etiquetados))
    revisores = {}
    nombres = sorted({r for d in documentos for r in d['votos']})
    for r in nombres:
        prior = prior_de(teoricos, r)
        pos = [d for d in etiquetados if r in d['votos'] and es_problema(d['humano'])]
        neg = [d for d in etiquetados if r in d['votos'] and not es_problema(d['humano'])]
        sens = actualizar(prior.get('sensibilidad', [1, 1]), sum(es_problema(d['votos'][r]) for d in pos), len(pos))
        espec = actualizar(prior.get('especificidad', [1, 1]), sum(not es_problema(d['votos'][r]) for d in neg), len(neg))
        revisores[r] = {'sensibilidad': resumen_beta(*sens), 'especificidad': resumen_beta(*espec),
                        'etiquetas_usadas': len(pos) + len(neg)}
        s, e = revisores[r]['sensibilidad']['media'], revisores[r]['especificidad']['media']
        revisores[r]['peso_si_marca'] = math.log(s / (1 - e))
        revisores[r]['peso_si_deja'] = math.log((1 - s) / e)
    return {'tasa_problemas': resumen_beta(*base), 'etiquetados': len(etiquetados), 'revisores': revisores}


def combinar(documentos, acierto):
    base = acierto['tasa_problemas']['media']
    salida = []
    for d in documentos:
        logit = math.log(base / (1 - base))
        aportes = {}
        for r, voto in d['votos'].items():
            w = acierto['revisores'][r]['peso_si_marca' if es_problema(voto) else 'peso_si_deja']
            aportes[r] = w
            logit += w
        p = 1 / (1 + math.exp(-logit))
        triaje = 'proponer dejar' if p < UMBRAL_DEJAR else 'proponer revisar' if p > UMBRAL_REVISAR else 'persona'
        salida.append({**d, 'p_problema': p, 'aportes': aportes, 'triaje': triaje})
    return sorted(salida, key=lambda x: -x['p_problema'])


def brier(predicciones):
    resueltas = [x for x in predicciones if x.get('resultado') is not None]
    if not resueltas:
        return {'resueltas': 0, 'pendientes': len(predicciones), 'brier': None}
    b = sum((x['p'] - (1.0 if x['resultado'] else 0.0)) ** 2 for x in resueltas) / len(resueltas)
    return {'resueltas': len(resueltas), 'pendientes': len(predicciones) - len(resueltas), 'brier': b,
            'aciertos': sum(bool(x['resultado']) for x in resueltas)}


# --- Entrada y salida ------------------------------------------------------------------------------------------------
def cargar_etiquetas(ruta):
    """humano_decision por url, de una planilla de revisor.revisar ya marcada por una persona."""
    with open(ruta, encoding='utf-8-sig', newline='') as f:
        return {fila['url']: fila['humano_decision'].strip().lower() for fila in csv.DictReader(f)
                if (fila.get('humano_decision') or '').strip()}


def informe(comp, acierto, combinados, puntaje):
    lineas = ['## Comportamiento comprobable por código (teórico → observado → actualizado)', '',
              '| Revisor | Señal | Teórico | Observado | Actualizado (intervalo 90 %) |', '|---|---|---:|---:|---|']
    for modelo, senales in comp.items():
        for senal, f in senales.items():
            act = f['actualizado']
            lineas.append(f"| {modelo} | {senal} | {f['teorico_media']:.2f} | {f['k']}/{f['n']} = {f['observado']:.2f} | "
                          f"{act['media']:.2f} ({act['intervalo_90'][0]:.2f}–{act['intervalo_90'][1]:.2f}) |")
    lineas += ['', f"## Acierto frente a una persona ({acierto['etiquetados']} documentos con etiqueta humana)", '',
               '| Revisor | Sensibilidad | Especificidad | Peso si marca | Peso si deja |', '|---|---|---|---:|---:|']
    for r, v in acierto['revisores'].items():
        s, e = v['sensibilidad'], v['especificidad']
        lineas.append(f"| {r} | {s['media']:.2f} ({s['intervalo_90'][0]:.2f}–{s['intervalo_90'][1]:.2f}) | "
                      f"{e['media']:.2f} ({e['intervalo_90'][0]:.2f}–{e['intervalo_90'][1]:.2f}) | "
                      f"{v['peso_si_marca']:+.2f} | {v['peso_si_deja']:+.2f} |")
    t = acierto['tasa_problemas']
    lineas += ['', f"Tasa de problemas entre lo aceptado: {t['media']:.2f} ({t['intervalo_90'][0]:.2f}–{t['intervalo_90'][1]:.2f}).",
               '', '## Orden de trabajo para la persona', '', '| # | Documento | Votos | P(problema) | Triaje | Persona |',
               '|---:|---|---|---:|---|---|']
    for d in combinados:
        votos = ', '.join(f"{r.split(':')[0]}: {v}" for r, v in d['votos'].items())
        lineas.append(f"| {d.get('n', '')} | {d['titulo']} | {votos} | {d['p_problema']:.2f} | {d['triaje']} | {d.get('humano') or '—'} |")
    b = puntaje
    lineas += ['', f"## Predicciones: {b['resueltas']} resueltas, {b['pendientes']} pendientes" +
               (f"; Brier {b['brier']:.3f} ({b['aciertos']} aciertos)" if b['brier'] is not None else '')]
    return '\n'.join(lineas)


def main(argv=None):
    p = argparse.ArgumentParser(description='Pesos de confianza de la IA revisora.')
    p.add_argument('--votos', type=Path, default=RAIZ / 'votos_prueba_20.yml')
    p.add_argument('--corridas', type=Path, nargs='+', help='prueba_revisor.json de varias corridas (en vez de --votos)')
    p.add_argument('--etiquetas', type=Path, help='planilla de revisor.revisar con humano_decision llena')
    p.add_argument('--salida', type=Path, default=Path('salidas/confianza.json'))
    a = p.parse_args(argv)
    teoricos = yaml.safe_load((RAIZ / 'pesos_teoricos.yml').read_text(encoding='utf-8'))
    comportamiento = yaml.safe_load((RAIZ / 'comportamiento.yml').read_text(encoding='utf-8'))
    predicciones = yaml.safe_load((RAIZ / 'predicciones.yml').read_text(encoding='utf-8'))['predicciones']
    documentos = votos_de_corridas(a.corridas) if a.corridas else yaml.safe_load(a.votos.read_text(encoding='utf-8'))['documentos']
    if a.etiquetas:
        etiquetas = cargar_etiquetas(a.etiquetas)
        for d in documentos:
            d['humano'] = etiquetas.get(d.get('url'), d.get('humano'))
    comp = capa_comportamiento(teoricos, comportamiento)
    acierto = capa_acierto(teoricos, documentos)
    combinados = combinar(documentos, acierto)
    puntaje = brier(predicciones)
    a.salida.parent.mkdir(parents=True, exist_ok=True)
    a.salida.write_text(json.dumps({'comportamiento': comp, 'acierto': acierto, 'documentos': combinados,
                                    'predicciones': puntaje}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(informe(comp, acierto, combinados, puntaje))
    return 0


if __name__ == '__main__':
    sys.exit(main())
