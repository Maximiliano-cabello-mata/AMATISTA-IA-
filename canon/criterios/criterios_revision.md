# Criterios de revisión aprendidos

Reglas que el proyecto aprendió **probando**: con la recuperación del canon, con la prueba del revisor (`codellama` y `qwen3:8b`, 20 documentos) y con la auditoría de la araña Site 4.1. Complementan los estándares de G7B; no los reemplazan. **Si un criterio choca con un estándar de G7B, manda el estándar.**

Cada criterio dice de dónde salió. La sección «Por decidir» no es regla: la IA no la usa para juzgar. Lo de este documento lo aprueba una persona; está en **borrador** mientras el PR que lo agrega no se fusione.

## Criterios verificados

### C1. Los datos de un documento son solo los que están en el documento

Una versión, un modelo de hardware o una medida cuentan solo si aparecen en el **título, el texto o la URL** del documento revisado.

Los ejemplos de las reglas del embudo («UHD 620», «RTX 3060», «Ryzen», «fps», «GB») son ejemplos, no datos del documento. Lo mismo vale para lo que aparece en los fragmentos del canon.

*Evidencia:* `codellama` copió 45 de esos ejemplos como si fueran datos de 11 documentos.

### C2. La versión de una página del manual está en su URL

En `docs.blender.org/manual/<idioma>/<versión>/…`, la versión (por ejemplo 4.5) es un dato real del documento, aunque el texto no la repita.

*Evidencia:* `qwen3:8b` tomó la versión de la URL en 17 de 19 datos. Eran correctos y la comprobación anterior los contaba mal.

### C3. Una cita es a un fragmento del canon, nunca al propio documento

Citar la URL, la fuente o la ruta del documento revisado no es una cita. La cita dice qué **regla** respalda la decisión.

*Evidencia:* `codellama` citó el propio documento o números inventados en 19 de 20 casos. `qwen3:8b` puso el documento en el campo de la cita en 14 de 20.

### C4. La decisión tiene que ser coherente

- **Aceptar** quiere decir que no falla ninguna etapa: la etapa es «ninguna».
- **Revisión** o **rechazo** quiere decir que alguna etapa falla o está en el límite, y hay que nombrarla.
- **Asignar una pregunta del plan (P1–P6)** quiere decir que la relevancia se cumple. Si el documento es pobre, la etapa que falla es **valor**, no relevancia.

*Evidencia:* `qwen3:8b` asignó P6 y a la vez dijo que fallaba la relevancia en 2 de los 11 documentos que mandó a revisión.

### C5. Un bloque útil tiene acción o parámetro, efecto y condición

Un bloque de documentación es útil si dice qué hacer o qué ajustar, qué efecto tiene y cuándo aplica.

No son útiles:
- las plantillas («Factor controls the amount of influence…»);
- las definiciones que solo repiten el nombre del parámetro («Maximum: clamps to this value»);
- los pies de figura sin los ajustes que producen el resultado;
- los textos genéricos repetidos en varias páginas.

*Evidencia:* las 6 fallas de la auditoría de Site 4.1, de 70 bloques. Es la rúbrica `g7b/site` del canon, resumida.

### C6. Con duda, a revisión y diciendo que no se sabe

Si el canon no alcanza para decidir, la decisión es **revisión** con `no_se`, no una decisión adivinada. Un documento ya aceptado por el embudo no se **rechaza** sin una regla concreta que lo respalde.

*Evidencia:* en 40 decisiones, ninguno de los dos modelos rechazó un documento aceptado.

### C7. La IA propone, una persona decide

Ninguna propuesta del revisor cambia el lago, MongoDB ni Supabase. Se publica sola una fuente de documentación solo si el límite inferior de Wilson al 95 % de sus muestras útiles llega a 0.80, con etiquetas confirmadas por una persona.

*Evidencia:* la regla de `g7b/seleccion-documental`. En Site 4.1, con 20 de 24 útiles, el límite fue 0.676.

## Por decidir

No son reglas. Se deciden cuando una persona marque los 20 documentos de la prueba.

- **P6 y las páginas del manual.** ¿Toda página del manual que explica cómo se hace algo en una versión concreta responde a P6? El embudo dice que sí. `qwen3:8b` dijo que no en 9 de 20, sobre todo en páginas introductorias.
- **Páginas introductorias o generales** («Introduction», «Structure», «Limitations»). ¿Se aceptan como referencia o se mandan a revisión por falta de valor? Los dos modelos mandaron a revisión 5 de ellas.
