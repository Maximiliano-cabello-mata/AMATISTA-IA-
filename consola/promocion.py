"""La puerta: lo aprobado entra a MongoDB (BASE.md: «una sola puerta»).

    python -m consola promover --simular      # qué se escribiría, sin escribir nada
    python -m consola promover                # copia lo aprobado a conocimiento_auditado

Es la ÚNICA parte de Amatista IA que escribe. Reglas, comprobadas por código:
  - copia solo los documentos en estado «aprobado» del registro (la IA los aceptó y una persona aprobó su lote);
  - escribe solo en la colección de destino (por omisión `conocimiento_auditado`), nunca en `documentos`, que es de G7B;
  - usa su propio usuario de MongoDB (MONGO_URI_PROMOCION, con readWrite solo en esa colección); el revisor sigue leyendo
    con el usuario de solo lectura (MONGO_URI_LECTURA);
  - es idempotente: volver a correrla no duplica nada (se escribe por `doc_id`);
  - no borra: si un documento deja de estar aprobado, se marca `auditoria.vigente = false` y queda el rastro.

Cada documento promovido es el documento original de G7B, completo, más un bloque `auditoria` con el rastro: lote,
veredicto, decisión y motivo de la IA, regla citada, versión del revisor y fecha. La telemetría no pasa por aquí:
cuando se audite, su puerta será el cubo.
"""
import json
import time
from pathlib import Path

import yaml

FUENTE = 'documentos'
DESTINO_POR_OMISION = 'conocimiento_auditado'
PUERTA = 'amatista-ia/consola promover'


def ahora():
    return time.strftime('%Y-%m-%d %H:%M:%S')


def comprobar_destino(nombre):
    if not nombre or nombre == FUENTE:
        raise ValueError(f'la promoción nunca escribe en «{FUENTE}» (es de G7B): elige otra colección de destino')


def _etiquetas(raiz, n):
    """¿Las marcas de la persona de ese lote fueron independientes? (revisor/etiquetas/lote_NNN.yml)"""
    ruta = Path(raiz) / 'revisor' / 'etiquetas' / f'lote_{int(n):03d}.yml'
    if not ruta.is_file():
        return None
    datos = yaml.safe_load(ruta.read_text(encoding='utf-8')) or {}
    return datos.get('independiente', True)


def documento_auditado(original, entrada, resultado, lote, independiente, config, fecha):
    """El documento original (sin _id) más su rastro de auditoría."""
    ia = (resultado or {}).get('ia') or {}
    doc = {k: v for k, v in original.items() if k != '_id'}
    doc['auditoria'] = {
        'vigente': True,
        'puerta': PUERTA,
        'promovido_en': fecha,
        'lote': entrada['lote'],
        'veredicto_lote': {'resultado': lote.get('estado'), 'fecha': lote.get('veredicto'), 'bien': lote.get('bien'),
                           'marcadas': lote.get('marcadas'), 'marcas_independientes': independiente},
        'decision_ia': entrada['decision_ia'],
        'etapa': ia.get('etapa'), 'pregunta': ia.get('pregunta'), 'cita': ia.get('cita'),
        'motivo': ia.get('motivo'), 'confianza': ia.get('confianza'),
        'revisor': (resultado or {}).get('version', 3), 'modelo': config.get('modelo'),
        'revisado_en': (resultado or {}).get('fecha'),
    }
    return doc


def promover(consola, fuente, destino, config, raiz, simular=False, fecha=None):
    """fuente: la colección `documentos` (solo lectura). destino: la colección auditada. Devuelve el resumen."""
    comprobar_destino(getattr(destino, 'name', config.get('coleccion_promocion', DESTINO_POR_OMISION)))
    fecha = fecha or ahora()
    aprobados = [d for d in consola.registro() if d['estado'] == 'aprobado']
    ids = [d['doc_id'] for d in aprobados]
    originales = {d['doc_id']: d for d in fuente.find({'doc_id': {'$in': ids}}, {'_id': 0})}
    resultados = {}
    for n in {d['lote'] for d in aprobados}:
        for r in consola.resultados(n):
            resultados[r.get('doc_id')] = r
    existentes = {d['doc_id']: d for d in destino.find({}, {'_id': 0, 'doc_id': 1, 'auditoria.vigente': 1})}
    nuevos = actualizados = 0
    faltan = []
    for d in aprobados:
        original = originales.get(d['doc_id'])
        if original is None:                   # ya no está en la fuente: no se inventa nada
            faltan.append(d['doc_id'])
            continue
        lote = consola.estado['lotes'][str(d['lote'])]
        doc = documento_auditado(original, d, resultados.get(d['doc_id']), lote, _etiquetas(raiz, d['lote']), config, fecha)
        if d['doc_id'] in existentes:
            actualizados += 1
        else:
            nuevos += 1
        if not simular:
            destino.update_one({'doc_id': d['doc_id']}, {'$set': doc}, upsert=True)
    vigentes = set(ids) - set(faltan)
    retirar = [i for i, e in existentes.items() if (e.get('auditoria') or {}).get('vigente', True) and i not in vigentes]
    if not simular:
        for i in retirar:
            destino.update_one({'doc_id': i}, {'$set': {'auditoria.vigente': False, 'auditoria.retirado_en': fecha}})
    resumen = {'fecha': fecha, 'simulado': simular, 'aprobados': len(aprobados), 'nuevos': nuevos,
               'actualizados': actualizados, 'retirados': len(retirar), 'faltan_en_fuente': len(faltan),
               'destino': getattr(destino, 'name', None)}
    if not simular:
        consola.estado['promocion'] = resumen
        consola.estado.setdefault('bitacora', []).append({'fecha': fecha, 'promocion': {k: resumen[k] for k in
                                                          ('nuevos', 'actualizados', 'retirados', 'faltan_en_fuente')}})
        consola.guardar()
    return resumen


def texto_resumen(r):
    verbo = 'Se escribirían' if r['simulado'] else 'Escritos'
    return (f"{verbo} en «{r['destino']}»: {r['nuevos']} nuevos y {r['actualizados']} actualizados de {r['aprobados']} aprobados; "
            f"{r['retirados']} dejan de estar vigentes; {r['faltan_en_fuente']} ya no están en la fuente."
            + (' (simulación: no se escribió nada)' if r['simulado'] else ''))


if __name__ == '__main__':      # pragma: no cover
    print(json.dumps({'uso': 'python -m consola promover [--simular]'}, ensure_ascii=False))
