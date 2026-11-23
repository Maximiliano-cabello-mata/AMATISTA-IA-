# Conjunto de control C1

35 documentos públicos con el mismo formato que los de `conocimiento_3d` (`doc_id`, `url`, `fuente`, `titulo`, `texto`, `licencia`, `modo`, `preguntas`, `puntajes`). Sirve para comparar versiones del revisor con documentos que **no vienen del lago**: por eso sus resultados sí se pueden subir, en `control/resultados/`.

- Cada documento pasó el embudo de G7B (`g7b_ingesta.embudo`, versión 2) y salió aceptado, igual que los del lago.
- Contiene texto del manual de Blender (© Blender Documentation Team, CC BY-SA 4.0, docs.blender.org).
- **La clave** (la decisión esperada de cada documento) está fuera del repositorio hasta que termine la prueba, para que nadie ajuste nada al verla. Su huella SHA-256 está en [`clave_c1.sha256`](clave_c1.sha256): al publicarla se puede comprobar que no cambió.
- No se edita: si el archivo cambia, la clave deja de servir. Para otra prueba se arma un conjunto C2.
