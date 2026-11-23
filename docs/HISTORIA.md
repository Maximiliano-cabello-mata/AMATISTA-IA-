# Historia de Amatista IA

Cómo se construyó el auditor, del 20 al 22 de noviembre de 2026: cada versión, qué cambió, por qué y qué se midió. Los resultados completos de cada corrida están en [`revisor/RESULTADOS_PRUEBA.md`](../revisor/RESULTADOS_PRUEBA.md); el canon, en [`canon/INVENTARIO.md`](../canon/INVENTARIO.md). El contexto del proyecto, en la [base oficial](https://github.com/Maximiliano-cabello-mata/amatista-recuperada-20261106/blob/recuperacion/BASE.md) y en el [registro de decisiones](https://github.com/Maximiliano-cabello-mata/amatista-recuperada-20261106/blob/recuperacion/docs/organizacion/05_registro_de_decisiones.md) del repositorio web.

## 1. Por qué existe

El 20 de noviembre se propuso integrar la IA al proyecto para revisar los datos del lago de G7B. Se decidió que fuera **local** (Ollama en una computadora del laboratorio: i3-10100, 40 GB de RAM, sin GPU), según la decisión de IA de G7B del 17 de noviembre. Antes de revisar, tenía que **conocer el proyecto**: de ahí el canon. El 22 de noviembre, la base oficial le dio su papel: **el auditor**, la única puerta al cubo y a MongoDB.

## 2. El canon (lo que sabe)

| Versión | Fecha | Qué agregó | Documentos / fragmentos | Por qué |
|---|---|---|---|---|
| v1 | 21 nov | 13 documentos de estándares de G7B y Amatista, fijados a un commit | 13 / 108 | La IA juzga con reglas, no con los datos que revisa |
| v2 | 22 nov | Rúbrica de utilidad de las arañas (`g7b/seleccion-documental`, `g7b/site`) | 15 / 111 | Juzgar bloques de documentación con el mismo criterio que la auditoría de Site 4.1 |
| v3 | 22 nov | Criterios aprendidos C1–C7 (`ia/criterios`, de este repositorio) | 16 / 119 | Lo que se aprendió probando: datos solo del documento, versión en la URL, citas al canon, coherencia… |
| v4 | 22 nov | Errores conocidos del revisor E1–E6 | 16 / 126 | Que la IA sepa lo que hacía mal y qué hacer en su lugar |
| v5 | 22 nov | La base oficial (`amatista/base`) | 17 / 135 | Que el auditor conozca las piezas, la puerta única y las prioridades |

**La búsqueda** (`supabase/migrations/`) combina texto y vectores (`bge-m3`) por RRF:

| | Recall@3 |
|---|---:|
| Texto con AND (diseño inicial, descartado) | 0.17 |
| Texto con OR | 0.89 |
| Híbrida con vectores, v1 (46 preguntas) | **0.96** |
| Híbrida con vectores, v3 (51 preguntas) | **0.96** |
| Texto, v5 (53 preguntas) | 0.868 |

## 3. El revisor (cómo decide)

Todas las corridas usan la misma muestra: 20 páginas del manual de Blender de `conocimiento_3d`.

| Versión | Qué cambió | Resultado | Lección |
|---|---|---|---|
| v1 con `codellama` | Primera prueba | Citas 1/20; 45 datos copiados de los ejemplos del canon | Modelo de código: descartado |
| v1 con `qwen3:8b` | Mismo revisor, otro modelo | Motivos sobre el contenido real; citas 3/20 (17 en otro campo); datos 17/19 contando la URL | Es el candidato |
| v2 | Cita de lista cerrada; datos extraídos por código; coherencia revisada | Citas 20/20; coherencia 0.55 | Las fallas mecánicas se eliminan por construcción |
| v2 con criterios C1–C7 | Criterios en las instrucciones fijas | Coherencia 0.70; «valor» reemplaza a «relevancia»; +29 s por documento | Los criterios ayudan, pero no bastan |
| v3 | Primero el motivo, al final la decisión; lo incoherente va a una persona | Coherencia 0.90; pero 1 aceptado, 11 a revisión y 8 rechazados | La coherencia subió quitando la pregunta del plan (16 → 5), no aceptando |
| v3 con criterios y errores conocidos (canon v4) | C1–C7 y E1–E6 en las instrucciones fijas | Coherencia 0.90; 9 aceptados, 11 a revisión, 0 rechazos; pregunta asignada en 16 de 20; 155 s por documento | Es la versión que usa la consola. Los criterios quitan los rechazos y devuelven la pregunta del plan, a costa de 41 s más |
| Lote 1 de la consola (23 nov) | La misma, sobre 100 documentos reales | En la muestra, los 14 aceptados están bien según la segunda opinión; 4 de las 6 revisiones debían aceptarse | Falla del lado seguro. Repite E3 y E4 aunque ya se le dijeron. Ver [`revisor/SEGUNDA_OPINION_LOTE_001.md`](../revisor/SEGUNDA_OPINION_LOTE_001.md) |

**Lo que sigue abierto:**
- el lote 1 espera las etiquetas de la persona: son las primeras;
- la muestra no puede decir si la IA detecta documentos malos, porque el lote solo trae páginas del manual ya aceptadas;
- en las páginas limítrofes, la decisión cambia mucho entre versiones;
- hay 0 etiquetas humanas, así que no se sabe si acierta.

## 4. Herramientas alrededor del revisor

| Herramienta | Para qué | Estado |
|---|---|---|
| `evaluacion/` | Prueba de recuperación del canon (53 preguntas con su documento esperado) | En uso |
| `laboratorio/verificar.py` | Comprueba Ollama, GitHub y Supabase sin mostrar claves | En uso |
| `revisor/confianza.py` | Pesos de confianza: Beta teórica actualizada con lo observado; combina votos; Brier de las predicciones | En uso: 25 predicciones resueltas, 18 acertadas, Brier 0.197 |
| `revisor/segunda_revision.py` | Segunda opinión a ciegas sobre los 70 bloques de Site 4.1, reconstruidos con `id` idéntico | Listo, sin correr |
| `consola/` | El auditor 24/7: lotes de 100, cuarentena, cierre con 20 muestras al escritorio, veredicto y freno | En marcha: lote 1 cerrado el 23 de noviembre, esperando veredicto |

## 5. Decisiones propias de este repositorio

- El canon tiene **solo estándares**, fijados a un commit y sin copias. Los datos del lago no entran.
- Las consultas exactas (hardware, taxonomía, catálogo) se resuelven por código, no por RAG.
- **Los datos los extrae el código; las citas son de lista cerrada.** El modelo no puede citar lo que no se le mostró.
- **Primero razonar, luego decidir.** Una decisión incoherente no cuenta.
- **Los pesos teóricos no se tocan después de ver resultados:** lo observado va en `revisor/comportamiento.yml`.
- **Para mediciones, el criterio es un algoritmo:** está documentado en G7B, `docs/investigacion/2026-11-22_teoria_rendimiento_y_criterio.md`.
- **Excepción aprobada el 22 de noviembre:** la persona puede pasarle al asistente las 20 muestras de un cierre. Solo fuentes públicas.

## 6. Cifras de velocidad en el laboratorio

| | |
|---|---|
| Generación | unos 2.4 tokens por segundo |
| Lectura | unos 40 tokens por segundo |
| Por documento | lee unos 2,700 tokens y genera unos 115–150 |
| Tiempo | 106–154 s por documento, según la versión. Sirve para lo que entra cada día; para los 1,033 acumulados serían unas 30–40 horas |
| Caché de Ollama | Reutiliza un mensaje idéntico (1.5 s → 0.3 s), pero en las corridas reales agregar 950 tokens fijos costó unos 20 s más por documento |
