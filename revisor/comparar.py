# [REVISION 2026-11-27] Compara las decisiones de la IA con las de una persona en la planilla del revisor. Entrada: CSV. Salida: JSON.
"""Compara lo que propuso la IA con lo que marcó una persona en la planilla.

    python -m revisor.comparar salidas/prueba_revisor.csv

La persona llena humano_decision (aceptar, revision o rechazar) y, si quiere, humano_pregunta. Las filas sin
humano_decision no cuentan.
"""
import csv
import json
import sys
from collections import Counter

DECISIONES = ('aceptar', 'revision', 'rechazar')


def comparar(filas):
    """Acuerdo, deteccion de problemas, falsas alarmas y matriz IA vs humano de las filas marcadas."""
    marcadas = [f for f in filas if (f.get('humano_decision') or '').strip().lower() in DECISIONES]
    n = len(marcadas)
    if not n:
        return {'marcadas': 0}
    h = lambda f: f['humano_decision'].strip().lower()
    matriz = Counter((f['ia_decision'], h(f)) for f in marcadas)
    # Lo que más importa para depurar: de lo que la persona quiere sacar o revisar, ¿cuánto marcó la IA?
    problemas = [f for f in marcadas if h(f) != 'aceptar']
    alarmas = [f for f in marcadas if f['ia_decision'] in ('revision', 'rechazar')]
    con_pregunta = [f for f in marcadas if (f.get('humano_pregunta') or '').strip()]
    return {
        'marcadas': n,
        'acuerdo_decision': sum(f['ia_decision'] == h(f) for f in marcadas) / n,
        'detecta_problemas': (sum(f['ia_decision'] != 'aceptar' for f in problemas) / len(problemas)) if problemas else None,
        'falsas_alarmas': (sum(h(f) == 'aceptar' for f in alarmas) / len(alarmas)) if alarmas else None,
        'acuerdo_pregunta': (sum(f['ia_pregunta'] == f['humano_pregunta'].strip() for f in con_pregunta)
                             / len(con_pregunta)) if con_pregunta else None,
        'matriz_ia_vs_humano': {f'{a} → {b}': c for (a, b), c in sorted(matriz.items())},
    }


def main(argv=None):
    """CLI: lee la planilla (por omision salidas/prueba_revisor.csv) e imprime el resumen."""
    ruta = (argv or sys.argv[1:] or ['salidas/prueba_revisor.csv'])[0]
    with open(ruta, encoding='utf-8-sig', newline='') as f:
        print(json.dumps(comparar(list(csv.DictReader(f))), ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
