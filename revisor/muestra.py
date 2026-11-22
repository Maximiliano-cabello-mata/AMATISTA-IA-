"""Saca una muestra al azar de los documentos de conocimiento de MongoDB, con un usuario de SOLO LECTURA.

    python -m revisor.muestra --n 20

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


def main(argv=None):
    cargar_env()
    p = argparse.ArgumentParser(description='Muestra al azar de conocimiento_3d.documentos.')
    p.add_argument('--n', type=int, default=20)
    p.add_argument('--salida', type=Path, default=Path('salidas/muestra.jsonl'))
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
