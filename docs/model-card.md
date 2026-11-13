---
language:
  - es
license: mit
library_name: scikit-learn
pipeline_tag: text-classification
tags:
  - public-procurement
  - ecuador
  - cpc
  - tf-idf
datasets:
  - cpc-mini (derivado de SERCOP vía OCP Data Registry, CC BY 3.0 EC)
---

# CPC-mini · modelo en servicio

**TF-IDF (n-gramas de caracteres y palabras) + SVM lineal jerárquico** (grupo de 3 dígitos →
subclase de 5 → código de 9), con búsqueda en haz, calibración por temperatura y pesos cuantizados a
int8. Elegido en **validación** entre tres modelos entrenados en CPU; los escalones con mmBERT-small
y Qwen3-0.6B están implementados y pendientes de GPU.

## Uso previsto

Sugerir los tres códigos CPC más probables para la descripción de un ítem de compra pública de
Ecuador, y ayudar a revisar ítems posiblemente mal clasificados, **siempre con revisión humana**.

## Usos no previstos

Decisiones automáticas, sanciones, auditorías concluyentes o cualquier uso que trate la sugerencia
como la clasificación oficial del SERCOP. No está pensado para textos que no describan un producto o
servicio, ni para datos personales.

## Métricas (prueba: compras de 2025 y 2026 nunca vistas)

Intervalos del 95 % por bootstrap (1 000 remuestreos; 200 para el F1 macro).

| Medida | 9 dígitos | 5 dígitos |
|---|---|---|
| Exactitud top-1 | 12,9 % (12,7–13,0) | 19,3 % (19,1–19,5) |
| Exactitud top-3 | 23,0 % (22,8–23,2) | 32,8 % (32,5–33,0) |
| F1 macro | 6,7 % (6,5–7,0) | — |
| ECE (calibración) | 0,079 | 0,053 |
| Cobertura exigiendo 90 % de exactitud | 0,0 % | — |

| Subconjunto de prueba | Descripciones | Top-1 9 díg. | Top-3 9 díg. |
|---|---|---|---|
| Procesos de un solo ítem | 3 326 | 25,9 % | 40,4 % |
| Procesos con varios ítems y varios códigos | 114 463 | 16,0 % | 28,6 % |
| Rubros que heredan el código de la obra | 39 843 | 2,7 % | 5,5 % |
| Compras de 2025 | 28 771 | 15,3 % | 26,5 % |
| Compras de 2026 | 128 861 | 12,3 % | 22,2 % |

Por frecuencia del código en entrenamiento (top-1, 9 dígitos): nunca visto 0,0 %; 1–5 ejemplos
1,9 %; 6–20 4,8 %; 21–100 12,1 %; más de 100 14,8 %.

**Conjunto de oro:** 300 ítems muestreados y herramienta lista; la revisión manual está pendiente,
así que aún no hay métrica sobre el oro.

## Abstención

El umbral se calibra en validación para que lo respondido acierte el 90 %. Con estas etiquetas
ninguna confianza lo alcanza (incluso exigiendo 50 %, sólo el 2 % de los códigos exactos nuevos sería
respondible), así que el modelo **responde «no sé» casi siempre** y muestra sus candidatos como
referencia. Es el resultado honesto, no un error de la demo.

## Eficiencia (CPU de laptop, Intel i5-1135G7)

| Versión | Tamaño en disco | Latencia p50 / p95 por ítem | Top-1 9 díg. |
|---|---|---|---|
| float32 | 237 MB | 23,1 / 38,1 ms | 12,9 % |
| **int8 (en servicio)** | **42 MB** | **8,8 / 13,5 ms** | 12,9 % (−0,01 pts) |

## Sesgos y limitaciones

- Aprende la costumbre de clasificación de las entidades, incluidos sus errores; el error dominante
  es confundir el **bien** con el **servicio de obra que lo usa** (hormigón premezclado frente a
  servicios con hormigón, pintura frente a servicios de pintura).
- La prueba está dominada por rubros de obra de 2026; en compras de bienes y servicios de un solo
  ítem rinde el doble.
- No reconoce códigos que nunca vio y rinde mal en la cola larga.
- Fecha de corte de los datos: registro del 10 de noviembre de 2026.

## Entrenamiento y reproducibilidad

147 532 descripciones (tope de 400 por código), semilla `20261112`, 479 s en CPU.
Configuración en `configs/models.yaml`; dataset `f064fad0abae…`; dependencias fijadas en `uv.lock`.
Reconstrucción completa: `uv run cpcmini download && uv run cpcmini rebuild --models tfidf_svm`.

## Licencias y atribución

Código y modelo: MIT. Datos de entrenamiento: SERCOP, publicados por el OCP Data Registry de Open
Contracting Partnership, [CC BY 3.0 EC](https://creativecommons.org/licenses/by/3.0/ec/).
Autor: Diego Francisco Granda Zhingre.
