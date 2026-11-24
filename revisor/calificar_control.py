"""Califica corridas del revisor sobre el conjunto de control C1 con su clave (control/clave_c1.yml).

La clave y este script se guardaron fuera del repositorio mientras corría la prueba, para que nadie ajustara nada al
ver qué documentos se sembraron como malos. Se publicaron al terminar; la huella SHA-256 de la clave se subió antes
de las corridas (control/clave_c1.sha256) y el script la comprueba.

    python -m revisor.calificar_control control/clave_c1.yml control/conjunto_c1.jsonl control/resultados/prueba_revisor_v3_control.json \
        control/resultados/prueba_revisor_v4_control.json
"""
import hashlib, json, math, sys
from collections import Counter, defaultdict
import yaml


def wilson_inferior(k, n, z=1.64485):
    if not n:
        return None
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def calificar(clave, resultados):
    docs = clave['documentos']
    por_id = {r['doc_id']: r for r in resultados}
    faltan = [i for i in docs if i not in por_id]
    buenos = [i for i, d in docs.items() if d['esperado'] == 'aceptar' and i in por_id]
    malos = [i for i, d in docs.items() if d['esperado'] != 'aceptar' and i in por_id]
    ef = lambda i: por_id[i].get('decision_efectiva') or 'persona'
    pasan = [i for i in malos if ef(i) == 'aceptar']
    por_tipo = defaultdict(lambda: [0, 0])
    for i in malos:
        por_tipo[docs[i]['tipo']][1] += 1
        por_tipo[docs[i]['tipo']][0] += ef(i) != 'aceptar'
    return {
        'documentos': len(por_id), 'faltan': len(faltan),
        'buenos_aceptados': [sum(ef(i) == 'aceptar' for i in buenos), len(buenos)],
        'malos_detenidos': [len(malos) - len(pasan), len(malos)],
        'malos_detenidos_wilson_inferior': wilson_inferior(len(malos) - len(pasan), len(malos)),
        'malos_que_pasan_la_puerta': [f"{docs[i]['titulo']} ({docs[i]['tipo']})" for i in pasan],
        'malos_rechazados': sum(ef(i) == 'rechazar' for i in malos),
        'detenidos_por_tipo': {t: v for t, v in sorted(por_tipo.items())},
        'buenos_retenidos': [f"{docs[i]['titulo']}: {ef(i)}" for i in buenos if ef(i) != 'aceptar'],
        'decisiones_efectivas': dict(Counter(ef(i) for i in por_id)),
    }


def main(argv):
    import os
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sello = os.path.join(raiz, 'control', 'clave_c1.sha256')
    if os.path.basename(argv[0]) == 'clave_c1.yml' and os.path.isfile(sello):
        if hashlib.sha256(open(argv[0], 'rb').read()).hexdigest() != open(sello).read().strip():
            sys.exit('La clave no coincide con la huella subida antes de la prueba.')
    clave = yaml.safe_load(open(argv[0], encoding='utf-8'))
    huella = hashlib.sha256(open(argv[1], 'rb').read()).hexdigest()
    if huella != clave['sha256_conjunto']:
        sys.exit(f'El conjunto cambió: {huella} no es {clave["sha256_conjunto"]}')
    for ruta in argv[2:]:
        datos = json.load(open(ruta, encoding='utf-8'))
        print(f"\n## {ruta} (revisor v{datos['resumen'].get('revisor')})")
        print(json.dumps(calificar(clave, datos['resultados']), ensure_ascii=False, indent=2))
    print('\nPredicciones (escritas antes de la corrida):')
    for p in clave.get('predicciones', []):
        print(f"- {p['id']} (p={p['p']}): {p['texto']}")


if __name__ == '__main__':
    main(sys.argv[1:])
