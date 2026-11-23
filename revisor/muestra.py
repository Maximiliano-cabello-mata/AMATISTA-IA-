"""Saca una muestra al azar de los documentos de conocimiento de MongoDB, con un usuario de SOLO LECTURA.

    python -m revisor.muestra --n 20
    python -m revisor.muestra --de-lote 1 --salida salidas/lote001.jsonl   # los mismos documentos de un lote de la consola

Escribe salidas/muestra.jsonl, que se queda en esta computadora (salidas/ no se sube). No modifica nada en MongoDB.
Variables en .env: MONGO_URI_LECTURA (un usuario con rol `read` sobre la base) y MONGO_DATABASE (por omisión
conocimiento_3d). Requiere `python -m pip install pymongo`.
"""
import argparse
import json
import os
import sys
from pathlib import Path

from indexador.entorno import cargar_env

CAMPOS = ['doc_id', 'url', 'fuente', 'titulo', 'texto', 'licencia', 'modo', 'preguntas', 'puntajes']


def ids_de_lote(ruta):
    """Los doc_id de un lote de la consola (salidas/consola/lote_NNN.jsonl), en el orden en que se revisaron."""
    ids = [json.loads(l).get('doc_id') for l in Path(ruta).read_text(encoding='utf-8').splitlines() if l.strip()]
    return list(dict.fromkeys(i for i in ids if i))


def main(argv=None):
    cargar_env()
    p = argparse.ArgumentParser(description='Muestra al azar de conocimiento_3d.documentos.')
    p.add_argument('--n', type=int, default=20)
    p.add_argument('--salida', type=Path, default=Path('salidas/muestra.jsonl'))
    p.add_argument('--de-lote', type=int, default=None, help='en vez de al azar: los documentos del lote N de la consola')
    p.add_argument('--consola', type=Path, default=Path('salidas/consola'), help='carpeta de estado de la consola')
    a = p.parse_args(argv)
    uri = os.environ.get('MONGO_URI_LECTURA')
    if not uri:
        sys.exit('Falta MONGO_URI_LECTURA en .env: un usuario de MongoDB con rol de solo lectura (ver TAREA_PRUEBA_REVISOR.md).')
    try:
        from pymongo import MongoClient
    except ImportError:
        sys.exit('Falta pymongo: python -m pip install pymongo')

    cliente = MongoClient(uri, serverSelectionTimeoutMS=20000)
    coleccion = cliente[os.environ.get('MONGO_DATABASE', 'conocimiento_3d')]['documentos']
    total = coleccion.estimated_document_count()
    if a.de_lote is not None:
        ruta = a.consola / f'lote_{a.de_lote:03d}.jsonl'
        if not ruta.is_file():
            sys.exit(f'No existe {ruta}: ¿la consola ya revisó ese lote?')
        ids = ids_de_lote(ruta)
        por_id = {d['doc_id']: d for d in coleccion.find({'doc_id': {'$in': ids}}, {'_id': 0, **{c: 1 for c in CAMPOS}})}
        faltan = [i for i in ids if i not in por_id]
        if faltan:
            print(f'Aviso: {len(faltan)} documentos del lote ya no están en MongoDB')
        docs = [por_id[i] for i in ids if i in por_id]
    else:
        docs = list(coleccion.aggregate([{'$sample': {'size': a.n}}, {'$project': {'_id': 0, **{c: 1 for c in CAMPOS}}}]))
    a.salida.parent.mkdir(parents=True, exist_ok=True)
    with open(a.salida, 'w', encoding='utf-8') as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False, default=str) + '\n')
    fuentes = {}
    for d in docs:
        fuentes[d.get('fuente')] = fuentes.get(d.get('fuente'), 0) + 1
    print(f'{len(docs)} de {total} documentos → {a.salida}')
    for k, v in sorted(fuentes.items(), key=lambda x: -x[1]):
        print(f'  {v:3d}  {k}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
