"""Pruebas de la verificación del laboratorio y de la carga de .env, sin red."""
import json
import os

from indexador.entorno import cargar_env
from laboratorio.verificar import FALLA, OK, revisar_github, revisar_ollama, revisar_supabase, tipo_de_clave

URL = 'https://abc.supabase.co'
PUB, SEC = 'sb_publishable_x', 'sb_secret_y'


def falso(respuestas):
    """respuestas: {(fragmento de ruta, apikey o None): (código, cuerpo)}."""
    llamadas = []

    def pedir(url, datos=None, cabeceras=None, metodo=None, timeout=0):
        llamadas.append((url, cabeceras))
        clave = (cabeceras or {}).get('apikey')
        for (ruta, k), r in respuestas.items():
            if ruta in url and k in (None, clave):
                return r
        raise OSError('sin respuesta simulada')
    pedir.llamadas = llamadas
    return pedir


def estados(r):
    return {n: e for n, e, _ in r}


def test_tipo_de_clave():
    assert tipo_de_clave(PUB) == 'publicable' and tipo_de_clave(SEC) == 'secreta'
    assert tipo_de_clave('eyJhbGc') == 'jwt_antigua' and tipo_de_clave('') is None


def test_supabase_listo():
    p = falso({('canon_documentos', None): (200, '[{"id":"g7b/vision"}]'), ('rpc/buscar_canon', None): (200, '[]')})
    e = estados(revisar_supabase(URL, PUB, SEC, pedir=p))
    assert e == {'supabase_url': OK, 'SUPABASE_PUBLISHABLE_KEY': OK, 'SUPABASE_SECRET_KEY': OK, 'buscar_canon': OK}


def test_supabase_sin_migracion_lo_explica():
    falta = (404, '{"code":"PGRST205","message":"Could not find the table"}')
    p = falso({('canon_documentos', None): falta, ('rpc/buscar_canon', None): (404, '{"code":"PGRST202"}')})
    r = revisar_supabase(URL, PUB, SEC, pedir=p)
    assert all(e == FALLA for n, e, _ in r if n != 'supabase_url')
    assert all('migración no está aplicada' in d for n, _, d in r if n != 'supabase_url')


def test_claves_intercambiadas_no_se_envian():
    p = falso({})
    r = revisar_supabase(URL, SEC, PUB, pedir=p)           # al revés
    assert estados(r)['SUPABASE_PUBLISHABLE_KEY'] == FALLA and 'intercambiadas' in dict((n, d) for n, _, d in r)['SUPABASE_PUBLISHABLE_KEY']
    assert p.llamadas == []                                 # la secreta no viaja como si fuera la publicable


def test_ningun_detalle_contiene_el_valor_de_una_clave():
    p = falso({('canon_documentos', None): (401, '{"message":"Invalid API key"}'), ('rpc/buscar_canon', None): (401, '{}')})
    r = revisar_supabase(URL, PUB, SEC, pedir=p)
    assert not any(PUB in d or SEC in d for _, _, d in r)


def test_ollama_sin_modelo_y_con_modelo():
    sin = falso({('/api/version', None): (200, '{"version":"0.12.0"}'), ('/api/tags', None): (200, '{"models":[]}')})
    assert estados(revisar_ollama('http://x', 'bge-m3', pedir=sin))['modelo_embeddings'] == FALLA
    con = falso({('/api/version', None): (200, '{"version":"0.12.0"}'),
                 ('/api/tags', None): (200, '{"models":[{"name":"bge-m3:latest"}]}'),
                 ('/api/embed', None): (200, json.dumps({'embeddings': [[0.1] * 1024]}))})
    assert estados(revisar_ollama('http://x', 'bge-m3', pedir=con))['modelo_embeddings'] == OK


def test_cargar_env_no_pisa_lo_que_ya_existe(tmp_path, monkeypatch):
    env = tmp_path / '.env'
    env.write_text('# comentario\nA_PRUEBA="uno"\nexport B_PRUEBA=dos\nC_PRUEBA=tres\n', encoding='utf-8')
    monkeypatch.setenv('C_PRUEBA', 'ya')
    for n in ('A_PRUEBA', 'B_PRUEBA'):
        monkeypatch.delenv(n, raising=False)
    assert cargar_env(env) == ['A_PRUEBA', 'B_PRUEBA']
    assert (os.environ['A_PRUEBA'], os.environ['B_PRUEBA'], os.environ['C_PRUEBA']) == ('uno', 'dos', 'ya')
    for n in ('A_PRUEBA', 'B_PRUEBA'):
        monkeypatch.delenv(n)


CANON = {'repositorios': {'g7b': {'url': 'https://github.com/o/g7b', 'commit': 'a' * 40},
                          'amatista': {'url': 'https://github.com/o/privado', 'commit': 'b' * 40}},
         'documentos': [{'repo': 'g7b', 'ruta': 'docs/VISION.md'}, {'repo': 'amatista', 'ruta': 'PROYECTO.md'}]}


def test_github_privado_sin_token_pide_el_token_y_con_token_lo_envia(monkeypatch):
    monkeypatch.delenv('GITHUB_TOKEN', raising=False)
    p = falso({('o/g7b/', None): (200, '# Visión'), ('o/privado/', None): (404, '404: Not Found')})
    r = dict((n, (e, d)) for n, e, d in revisar_github(CANON, pedir=p))
    assert r['github_g7b'][0] == OK and r['github_amatista'][0] == FALLA and 'GITHUB_TOKEN' in r['github_amatista'][1]

    monkeypatch.setenv('GITHUB_TOKEN', 'ghp_prueba')
    vistos = []

    def con_token(url, datos=None, cabeceras=None, metodo=None, timeout=0):
        vistos.append(cabeceras.get('Authorization'))
        return 200, 'ok'
    r = revisar_github(CANON, pedir=con_token)
    assert all(e == OK for _, e, _ in r) and vistos == ['Bearer ghp_prueba'] * 2
    assert not any('ghp_prueba' in d for _, _, d in r)
