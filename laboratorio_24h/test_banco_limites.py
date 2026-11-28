# [REVISION 2026-11-27] Pruebas sin red del laboratorio Gemini.
"""Pruebas unitarias del sandbox lab-limites-gemini (sin red ni gasto de cuota)."""
import banco_limites as B


def test_deteccion_proveedor_y_endpoints():
    """Prueba: deteccion proveedor y endpoints."""
    assert B.detectar_proveedor("AQ.abc123") == "aistudio"
    assert B.detectar_proveedor("AQ.abc123", "vertex") == "vertex"
    assert B.detectar_proveedor("AIzaSy123") == "aistudio"
    assert "aiplatform.googleapis.com" in B.url_endpoint("gemini-3.5-flash", "vertex")
    assert "generativelanguage.googleapis.com" in B.url_endpoint("gemini-3.5-flash", "aistudio")


def test_construir_prompt_con_canon_y_busqueda():
    """Prueba: construir prompt con canon y busqueda."""
    canon = {
        "documentos": {"g7b/ingesta": {"titulo": "Ingesta"}},
        "fragmentos": [
            {"documento_id": "g7b/ingesta", "seccion": "4. El embudo", "texto": "Etapas del embudo."},
            {"documento_id": "g7b/seleccion-documental", "seccion": "Utilidad", "texto": "Parámetro y efecto."},
            {"documento_id": "ia/criterios", "seccion": "C1", "texto": "Solo datos del documento."},
        ],
    }
    prompt, citas = B.construir_prompt_con_canon(canon)
    assert "Etapas del embudo." in prompt and "g7b/ingesta · 4. El embudo" in citas
    assert len(B.buscar_fragmentos_canon(canon, "etapas del embudo")) == 1


def test_resumen_limites_y_429():
    """Prueba: resumen limites y 429."""
    llamadas = [
        {"ok": True, "status": 200, "latencia_s": 0.5, "tokens_entrada": 100, "tokens_salida": 20},
        {"ok": True, "status": 200, "latencia_s": 1.5, "tokens_entrada": 200, "tokens_salida": 40},
        {"ok": False, "status": 429, "latencia_s": 0.2, "tokens_entrada": 0, "tokens_salida": 0},
    ]
    r = B.resumir_limites(llamadas, 6.0)
    assert r["total_llamadas"] == 3 and r["exitosas"] == 2 and r["errores_429"] == 1
    assert r["rpm_efectivo"] == 30.0 and r["latencia_p50_s"] == 1.0


def test_calificar_y_renderizar_html(tmp_path):
    """Prueba: calificar y renderizar html."""
    clave = {"documentos": {"d1": {"esperado": "aceptar"}, "d2": {"esperado": "rechazar"}}}
    res = [
        {"doc_id": "d1", "titulo": "Bueno", "esperado": "aceptar", "tipo_sembrado": "bueno", "v3_decision": "aceptar",
         "status": 200, "latencia_s": 0.8, "ia": {"decision": "aceptar", "motivo": "ok", "pista_para_8b": "p1"}},
        {"doc_id": "d2", "titulo": "Malo", "esperado": "rechazar", "tipo_sembrado": "dato_invertido", "v3_decision": "aceptar",
         "status": 200, "latencia_s": 0.9, "ia": {"decision": "rechazar", "motivo": "dato al revés", "pista_para_8b": "p2"}},
    ]
    cal = B.calificar_contra_clave(res, clave)
    assert cal == {"buenos_aceptados": [1, 1], "malos_detenidos": [1, 1], "malos_que_pasan": 0}
    html_out = tmp_path / "reporte.html"
    B.renderizar_html({
        "fecha": "2026-11-24", "modelo": "gemini-2.5-flash", "proveedor": "vertex",
        "limites": B.resumir_limites([{"ok": True, "status": 200, "latencia_s": 0.8, "tokens_entrada": 50, "tokens_salida": 10}], 1.0),
        "calificacion_gemini": cal, "referencia_local_v3": {"malos_detenidos": "9/13", "buenos_aceptados": "13/22"},
        "resultados": res,
    }, html_out)
    texto = html_out.read_text(encoding="utf-8")
    assert "Bueno" in texto and "dato al revés" in texto and "gemini-2.5-flash" in texto


def test_ordenar_documentos_pesados_prioriza_manual_y_longitud():
    """Prueba: ordenar documentos pesados prioriza manual y longitud."""
    docs = [
        {"doc_id": "corto", "fuente": "blender-stackexchange", "texto": "uno dos tres"},
        {"doc_id": "privado", "fuente": "interna", "texto": "palabra " * 500},
        {"doc_id": "manual_pesado", "fuente": "blender-manual", "texto": "render cycles samples " * 200},
        {"doc_id": "manual_corto", "fuente": "blender-manual", "texto": "render cycles"},
        {"doc_id": "visto", "fuente": "blender-manual", "texto": "render " * 900},
    ]
    cola = B.ordenar_documentos_pesados(docs, {"visto"})
    # Round-robin entre fuentes: manual y foro alternan; dentro de cada fuente, el más pesado primero.
    assert [d["doc_id"] for d in cola] == ["manual_pesado", "corto", "manual_corto"]


def test_empaquetado_y_rotacion_multipool_e_inyeccion_sqlite(tmp_path):
    """Prueba sin red: empaquetado ×N, parseo tolerante (JSON + vallas Gemma), rotación 4-pools e inyección SQLite."""
    import sqlite3

    paq = [
        {"doc_id": "d_uno", "fuente": "blender-manual", "licencia": "CC-BY-SA-4.0", "titulo": "Extrude", "url": "https://x/1", "texto": "extrude mesh node " * 30},
        {"doc_id": "d_dos", "fuente": "blender-stackexchange", "licencia": "CC-BY-SA-4.0", "titulo": "Cycles", "url": "https://x/2", "texto": "cycles samples noise " * 30},
    ]
    prompt = B.armar_prompt_paquete(paq, palabras_max=20)
    assert "--- DOCUMENTO 1 ---" in prompt and "doc_id: d_dos" in prompt

    salida_fenced = """```json
    {"resultados": [
      {"doc_id": "d_uno", "decision": "aceptar", "compatibilidad_53": "vigente_5_3", "receta_53": "Problema: extruir caras. Solución en Blender 5.3: usar GeometryNodeExtrudeMesh conectado a Group Output con Offset Scale en 0.05 y modo Faces activado para extrusión limpia."},
      {"doc_id": "d_dos", "decision": "rechazar", "compatibilidad_53": "vigente_5_3", "receta_53": ""}
    ]}
    ```"""
    mapa = B.parsear_respuesta_paquete(salida_fenced, ["d_uno", "d_dos"])
    assert mapa["d_uno"]["decision"] == "aceptar" and mapa["d_dos"]["decision"] == "rechazar"

    enfriamientos = {"gemini-3.5-flash-lite": 9999999999.0}
    orden = B.elegir_pool_rotacion(enfriamientos, turno=0, pools=("gemini-3.5-flash-lite", "gemini-3.1-flash-lite-preview", "gemma-4-31b-it"))
    assert orden[0] == "gemini-3.1-flash-lite-preview" and orden[-1] == "gemini-3.5-flash-lite"

    sq = tmp_path / "test_rag.sqlite"
    con = sqlite3.connect(str(sq))
    con.executescript(
        """
        CREATE TABLE documentos (doc_id TEXT PRIMARY KEY, fuente TEXT, titulo TEXT, url TEXT, version_blender TEXT, dominio TEXT, peso_confianza REAL, metadatos_json TEXT);
        CREATE TABLE fragmentos (frag_id INTEGER PRIMARY KEY AUTOINCREMENT, clave_unica TEXT UNIQUE, doc_id TEXT, orden INTEGER, fuente TEXT, titulo TEXT, seccion TEXT, url TEXT, texto TEXT, texto_contextual TEXT, operadores_bpy TEXT, tiene_codigo INTEGER, nivel_confianza TEXT, peso_confianza REAL, version_blender TEXT, dominio TEXT, prioridad_vector INTEGER, tiene_vector INTEGER);
        INSERT INTO documentos VALUES ('d_uno', 'blender-manual', 'Extrude', 'https://x/1', '5.3', 'geometry_nodes', 1.2, '{}');
        """
    )
    con.commit()
    con.close()

    n_iny = B.inyectar_recetas_en_sqlite_d(
        [{"doc_id": "d_uno", "decision": "aceptar", "modelo": "gemini-3.5-flash-lite", "compatibilidad_53": "vigente_5_3", "receta_53": mapa["d_uno"]["receta_53"]}],
        ruta_sqlite=sq,
    )
    assert n_iny == 1
