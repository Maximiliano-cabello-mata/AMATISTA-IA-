# [REVISION 2026-11-27] Carga minima de .env sin dependencias (usada por todos los comandos). Entrada: ruta del .env (por omision
# relativa al directorio actual). Salida: variables en os.environ; devuelve los nombres cargados.
"""Carga un archivo .env sin dependencias. No pisa variables que ya estén en el entorno y nunca imprime valores."""
import os
from pathlib import Path


# [REVISION-BUG] ruta='.env' es relativa al directorio de trabajo: si se ejecuta fuera de la raiz del repo no carga
# nada y el error aparece despues como 'faltan variables'. Sugerencia: resolver respecto a Path(__file__).parents[1].
def cargar_env(ruta='.env'):
    """Lee líneas NOMBRE=valor (con o sin comillas; ignora vacías y comentarios). Devuelve los nombres cargados."""
    p = Path(ruta)
    if not p.is_file():
        return []
    cargados = []
    for linea in p.read_text(encoding='utf-8-sig').splitlines():
        linea = linea.strip()
        if not linea or linea.startswith('#') or '=' not in linea:
            continue
        nombre, valor = linea.removeprefix('export ').split('=', 1)
        nombre, valor = nombre.strip(), valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in '"\'':
            valor = valor[1:-1]
        if nombre and nombre not in os.environ:
            os.environ[nombre] = valor
            cargados.append(nombre)
    return cargados
