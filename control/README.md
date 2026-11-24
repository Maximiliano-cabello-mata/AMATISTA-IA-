# Conjunto de control C1

35 documentos públicos con el mismo formato que los de `conocimiento_3d` (`doc_id`, `url`, `fuente`, `titulo`, `texto`, `licencia`, `modo`, `preguntas`, `puntajes`). Sirve para comparar versiones del revisor con documentos que **no vienen del lago**: por eso sus resultados sí se pueden subir, en `control/resultados/`.

- Cada documento pasó el embudo de G7B (`g7b_ingesta.embudo`, versión 2) y salió aceptado, igual que los del lago.
- Contiene texto del manual de Blender (© Blender Documentation Team, CC BY-SA 4.0, docs.blender.org).
- **La clave** ([`clave_c1.yml`](clave_c1.yml)) estuvo fuera del repositorio mientras corría la prueba. Se publicó el 24 de noviembre; su huella coincide con [`clave_c1.sha256`](clave_c1.sha256), subida antes de las corridas. Se califica con `python -m revisor.calificar_control`.
- No se edita: si el archivo cambia, la clave deja de servir. Para otra prueba se arma un conjunto C2.
