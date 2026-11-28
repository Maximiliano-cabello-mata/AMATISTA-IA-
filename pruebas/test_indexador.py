"""Pruebas del indexador del canon, sin red: Ollama y Supabase se simulan."""
import pytest

from indexador.indexar import DIMENSIONES, filtrar_secciones, fragmentar, sha256, sincronizar

DOC = """# Título

Intro del documento.

## 1. Uno
Texto uno.

### 1.1 Detalle
Detalle del uno.

## 2. Dos
```python
# esto no es un título
print("hola")
```

## 3. Operación
Comandos que no son estándar.
"""


def test_filtrar_excluye_una_seccion_con_sus_subtitulos():
    """Prueba: filtrar excluye una seccion con sus subtitulos."""
    t = filtrar_secciones(DOC, excluir=['1. Uno'])
    assert 'Texto uno' not in t and 'Detalle del uno' not in t
    assert 'Intro del documento' in t and '## 2. Dos' in t


def test_filtrar_solo_deja_esa_seccion():
    """Prueba: filtrar solo deja esa seccion."""
    t = filtrar_secciones(DOC, solo=['2. Dos'])
    assert '## 2. Dos' in t and 'print("hola")' in t
    assert 'Intro' not in t and 'Operación' not in t


def test_filtrar_ignora_titulos_dentro_de_codigo_y_avisa_si_falta_una_seccion():
    """Prueba: filtrar ignora titulos dentro de codigo y avisa si falta una seccion."""
    t = filtrar_secciones(DOC, excluir=['3. Operación'])
    assert '# esto no es un título' in t          # dentro del bloque de código: no es título
    with pytest.raises(ValueError, match='no existen'):
        filtrar_secciones(DOC, excluir=['9. No existe'])


def test_fragmentar_conserva_la_ruta_de_titulos_y_no_parte_el_codigo():
    """Prueba: fragmentar conserva la ruta de titulos y no parte el codigo."""
    frags = fragmentar(DOC, max_palabras=50)
    rutas = [f['seccion'] for f in frags]
    assert 'Título > 1. Uno > 1.1 Detalle' in rutas
    codigo = next(f for f in frags if 'print' in f['texto'])
    assert codigo['texto'].count('```') == 2          # el bloque entero, en un solo fragmento


def test_fragmentar_parte_tablas_largas_repitiendo_el_encabezado():
    """Prueba: fragmentar parte tablas largas repitiendo el encabezado."""
    filas = '\n'.join(f'| opción {i} | ' + 'palabra ' * 20 + '|' for i in range(10))
    tabla = '# T\n\n| Opción | Detalle |\n|---|---|\n' + filas + '\n'
    frags = fragmentar(tabla, max_palabras=60)
    assert len(frags) > 1
    assert all(f['texto'].startswith('| Opción | Detalle |\n|---|---|') for f in frags)
    assert sum(f['texto'].count('| opción ') for f in frags) == 10   # ninguna fila se pierde ni se duplica


def test_fragmentar_respeta_el_maximo_de_palabras_en_prosa():
    """Prueba: fragmentar respeta el maximo de palabras en prosa."""
    texto = '# T\n\n' + '\n\n'.join('palabra ' * 30 for _ in range(10))
    frags = fragmentar(texto, max_palabras=70)
    assert all(len(f['texto'].split()) <= 70 for f in frags)


class FalsoOllama:
    """Embebedor simulado que cuenta cuantos textos vectoriza."""
    id = 'bge-m3@prueba'

    def __init__(self):
        """Inicia el contador de llamadas."""
        self.llamadas = 0

    def vectores(self, textos):
        """Devuelve vectores nulos de DIMENSIONES componentes."""
        self.llamadas += len(textos)
        return [[0.0] * DIMENSIONES for _ in textos]


class FalsaBase:
    """Supabase simulado en memoria (documentos y fragmentos)."""
    def __init__(self):
        """Crea las tablas vacias."""
        self.docs, self.frags = {}, []

    def get(self, ruta):
        """Simula las dos consultas GET del indexador."""
        if ruta.startswith('canon_documentos'):
            return [{'id': k, 'sha256': v['sha256']} for k, v in self.docs.items()]
        return [{'documento_id': f['documento_id']} for f in self.frags]

    def post(self, tabla, filas, conflicto=None):
        """Simula inserciones/upserts."""
        if tabla == 'canon_documentos':
            for f in filas:
                self.docs[f['id']] = f
        else:
            self.frags.extend(filas)

    def delete(self, ruta):
        """Simula los DELETE con cascada."""
        if ruta.startswith('canon_documentos'):
            doc = ruta.split('id=eq.')[1]
            self.docs.pop(doc, None)
            self.frags = [f for f in self.frags if f['documento_id'] != doc]
        else:
            doc = ruta.split('documento_id=eq.')[1].split('&')[0]
            self.frags = [f for f in self.frags if f['documento_id'] != doc]


def _preparado(texto='Texto A.'):
    """Canon preparado de un documento con un fragmento."""
    doc = {'id': 'g7b/prueba', 'titulo': 'Prueba', 'sha256': sha256(texto)}
    return [(doc, [{'documento_id': 'g7b/prueba', 'orden': 0, 'seccion': 'S', 'texto': texto, 'tokens': 3, 'sha256': sha256(texto)}])]


def test_sincronizar_es_incremental_y_poda_lo_que_salio_del_canon():
    """Prueba: sincronizar es incremental y poda lo que salio del canon."""
    base, oll = FalsaBase(), FalsoOllama()
    r1 = sincronizar(_preparado(), oll, base, registro=lambda *_: None)
    assert r1['actualizados'] == 1 and len(base.frags) == 1
    r2 = sincronizar(_preparado(), oll, base, registro=lambda *_: None)       # nada cambió: no recalcula
    assert r2['sin_cambios'] == 1 and oll.llamadas == 1
    r3 = sincronizar(_preparado('Texto B.'), oll, base, registro=lambda *_: None)   # cambió: reemplaza, no duplica
    assert r3['actualizados'] == 1 and len(base.frags) == 1 and base.frags[0]['texto'] == 'Texto B.'
    r4 = sincronizar([], oll, base, podar=True, registro=lambda *_: None)
    assert r4['podados'] == 1 and not base.docs and not base.frags
