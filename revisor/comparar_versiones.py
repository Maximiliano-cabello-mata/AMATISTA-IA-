"""Compara la v3 de la consola con otra corrida del revisor sobre los mismos documentos de un lote.

    python -m revisor.comparar_versiones 1 salidas/prueba_revisor_v4_lote001.json
    python -m revisor.comparar_versiones 1 salidas/prueba_revisor_v4_lote001.json --planilla "RUTA/lote_001/planilla.csv"

Lee el lote de la consola (salidas/consola/lote_NNN.jsonl) y la corrida nueva. Con la planilla marcada por una persona,
dice también cuántas veces coincide cada versión con ella en las muestras. Solo lee: no cambia nada.
"""
import argparse
from consola.nucleo import leer_planilla
import json
import sys
from collections import Counter
from pathlib import Path

DECISIONES = ('aceptar', 'revision', 'rechazar', 'persona')


def comparar(lote, nueva, planilla=None):
    """lote y nueva: listas de resultados ({doc_id, decision_efectiva, ...}). planilla: filas con humano_decision."""
    v3 = {r['doc_id']: r.get('decision_efectiva') or 'persona' for r in lote}
    v4 = {r['doc_id']: r.get('decision_efectiva') or 'persona' for r in nueva}
    comunes = [i for i in v3 if i in v4]
    salida = {
        'documentos': len(comunes),
        'solo_en_el_lote': len(set(v3) - set(v4)),
        'decisiones_v3': {k: sum(v3[i] == k for i in comunes) for k in DECISIONES},
        'decisiones_nueva': {k: sum(v4[i] == k for i in comunes) for k in DECISIONES},
        'iguales': sum(v3[i] == v4[i] for i in comunes),
        'cambios': {f'{a} → {b}': c for (a, b), c in sorted(Counter((v3[i], v4[i]) for i in comunes if v3[i] != v4[i]).items())},
    }
    if planilla:
        marcadas = [f for f in planilla if (f.get('humano_decision') or '').strip().lower() in DECISIONES[:3] and f['doc_id'] in v4]
        h = lambda f: f['humano_decision'].strip().lower()
        salida['muestras_marcadas'] = len(marcadas)
        if marcadas:
            salida['coincide_con_la_persona'] = {'v3': sum(v3.get(f['doc_id']) == h(f) for f in marcadas),
                                                 'nueva': sum(v4[f['doc_id']] == h(f) for f in marcadas)}
            # Lo que protege al cubo: aceptados que la persona no aceptaría.
            salida['aceptados_que_la_persona_no_acepta'] = {
                'v3': sum(v3.get(f['doc_id']) == 'aceptar' and h(f) != 'aceptar' for f in marcadas),
                'nueva': sum(v4[f['doc_id']] == 'aceptar' and h(f) != 'aceptar' for f in marcadas)}
        salida['muestras'] = [{'n': f.get('n'), 'titulo': f.get('titulo'), 'v3': v3.get(f['doc_id']), 'nueva': v4.get(f['doc_id']),
                               'persona': (f.get('humano_decision') or '').strip().lower() or None}
                              for f in planilla if f['doc_id'] in v4]
    return salida


def main(argv=None):
    p = argparse.ArgumentParser(description='Compara la v3 de la consola con otra corrida sobre el mismo lote.')
    p.add_argument('lote', type=int)
    p.add_argument('corrida', type=Path, help='salidas/prueba_revisor_<nombre>.json')
    p.add_argument('--consola', type=Path, default=Path('salidas/consola'))
    p.add_argument('--planilla', type=Path, default=None, help='planilla.csv del cierre, marcada por una persona')
    a = p.parse_args(argv)
    ruta = a.consola / f'lote_{a.lote:03d}.jsonl'
    lote = [json.loads(l) for l in ruta.read_text(encoding='utf-8').splitlines() if l.strip()]
    nueva = json.loads(a.corrida.read_text(encoding='utf-8'))['resultados']
    planilla = None
    if a.planilla:
        planilla = leer_planilla(a.planilla)
    print(json.dumps(comparar(lote, nueva, planilla), ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
