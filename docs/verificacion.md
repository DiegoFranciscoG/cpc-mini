# Verificación (fase 1)

Fecha de verificación: **2026-11-12**. Fuentes numeradas en [investigacion.md](investigacion.md).

## a) Versiones y licencias

| Componente | Versión fijada | Licencia | Fuente |
|---|---|---|---|
| Python | 3.13 (imagen `python:3.13.18-slim`) | PSF | [13] |
| uv | 0.11.14 local · 0.13.8 en Docker | MIT/Apache-2.0 | [14] |
| Polars | 2.1.0 | MIT | [10] |
| scikit-learn | 1.9.1 | BSD-3-Clause | [10] |
| NumPy / SciPy | 2.5.4 / 1.18.1 | BSD | [10] |
| FastAPI / Uvicorn / Pydantic | 0.162.5 / 0.54.0 / 2.14.3 | MIT / BSD-3 / MIT | [10] |
| SQLAlchemy / Alembic | 2.1.8 / 1.20.1 | MIT | [10] |
| Transformers / PEFT / Datasets | 5.22.2 / 0.21.2 / 5.2.0 | Apache-2.0 | [10] |
| PyTorch | 2.15.0 | BSD-style | [10] |
| Unsloth | 2026.11.4 (sólo en Kaggle) | Apache-2.0 | [10] |
| MLflow (skinny) | 3.18.0 (opcional) | Apache-2.0 | [10] |
| mmBERT-small | `jhu-clsp/mmBERT-small` (sha `abc32620dd`) | MIT | [6] |
| Qwen3-0.6B-Base | `Qwen/Qwen3-0.6B-Base` (sha `da87bfb608`) | Apache-2.0 | [7] |
| React / Vite / TypeScript | 19.3.1 / 8.3.8 / 7.0.2 | MIT / MIT / Apache-2.0 | [11] |
| Astryx (`@astryxdesign/core`) | 0.7.15 (beta) | MIT | [11][12] |

Licencia del proyecto: MIT. Es compatible con las de los modelos base (MIT y Apache-2.0); los datos
conservan su licencia CC BY 3.0 EC con atribución (ver dataset card).

## b) GPU gratuita (Kaggle)

No verificable en la fuente oficial desde aquí (supuesto **S-2**). Referencia de tercero: T4/P100,
sesiones de hasta 12 h, cuota semanal visible en la cuenta. Los escalones 2 y 3 se dejan listos en
`notebooks/` y **no se ejecutaron**: necesitan tu cuenta de Kaggle y su cuota.

## c) Cobertura medida (12 años, 3 268 507 ítems)

Se recorrieron en flujo todos los archivos anuales. «Usable» = tiene descripción informativa, código
CPC limpio de ≥ 9 dígitos y ningún patrón de datos personales.

| Año | Ítems | % con descripción | % con CPC | Cero restaurado | Genéricas | Copia de la etiqueta | Con datos personales | Usables | % usable | Códigos 9 | Códigos 5 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2015 | 398 763 | 100,0 | 99,99 | 522 | 2 929 | 10,9 % | 1 | 395 417 | 99,2 | 5 167 | 1 297 |
| 2016 | 333 300 | 100,0 | 98,65 | 377 | 2 435 | 19,1 % | 0 | 326 160 | 97,9 | 5 112 | 1 284 |
| 2017 | 355 994 | 100,0 | 95,41 | 568 | 2 361 | 27,5 % | 0 | 337 023 | 94,7 | 4 942 | 1 228 |
| 2018 | 372 443 | 100,0 | **63,47** | 1 195 | 1 919 | 30,9 % | 0 | 234 145 | 62,9 | 5 025 | 1 256 |
| 2019 | 213 808 | 100,0 | **58,75** | 763 | 1 156 | 25,3 % | 2 | 124 119 | 58,1 | 4 279 | 1 147 |
| 2020 | 195 527 | 100,0 | **51,50** | 927 | 1 045 | 22,7 % | 0 | 99 389 | 50,8 | 4 033 | 1 073 |
| 2021 | 160 162 | 100,0 | 88,44 | 759 | 614 | 50,6 % | 0 | 140 831 | 87,9 | 3 579 | 963 |
| 2022 | 133 753 | 100,0 | 99,99 | 685 | 760 | 47,1 % | 0 | 132 755 | 99,3 | 4 088 | 1 034 |
| 2023 | 163 385 | 100,0 | 100,00 | 962 | 660 | 50,5 % | 0 | 162 483 | 99,5 | 3 682 | 996 |
| 2024 | 212 222 | 100,0 | 100,00 | 1 113 | 840 | 45,5 % | 1 | 211 030 | 99,4 | 4 220 | 1 081 |
| 2025 | 181 292 | 100,0 | 99,92 | 967 | 817 | 41,5 % | 5 | 179 912 | 99,2 | 4 536 | 1 114 |
| 2026 | 547 858 | 100,0 | 99,64 | 1 933 | 734 | 14,9 % | 11 | 542 954 | 99,1 | 5 426 | 1 239 |

Total usable: **2 886 218 ítems (88,3 %)**. Esquema de clasificación: `CPC` en el 100 % de los ítems
clasificados. Longitud de los códigos usables: 9 dígitos 1 837 570 · 10 dígitos 786 833 · 11 dígitos
272 657 · 12 dígitos 5 375 · 13 dígitos 73.

### Hallazgos que cambian el diseño

1. **Cero inicial perdido.** `classification.id` pierde el 0 de la sección 0 del CPC (alimentos y
   agro) a cualquier longitud: `134929123` frente a `01349.29.1` en `additionalClassifications`. Sin
   corregirlo, esos productos caen en ramas equivocadas. Se restauró en 10 771 ítems.
2. **2018–2020 con CPC incompleto** (51–63 %). Se usan igual; la falta de código se reporta como
   exclusión, no se imputa.
3. **Copia de la etiqueta.** Entre el 11 % y el 51 % de las descripciones son idénticas al nombre del
   código del catálogo (compras por catálogo electrónico). Son triviales; se marcan y se reporta
   aparte el subconjunto de **texto libre**.
4. **Código del proceso, no del ítem.** En obras con muchos rubros, cada línea («Breaker 16 A»,
   «Excavación a mano») hereda el CPC de la obra completa. 300 227 ítems están en procesos multi-ítem
   con un único código. Un experimento con vecinos sobre 150 000 descripciones dio exactitud top-1 de
   31 % en procesos de un solo ítem y 36 % en rubros de obra: el ruido es transversal, así que **no
   se recorta el alcance**; se agrega `process_kind` y se reportan métricas por tipo de proceso.
5. **2026 cambia de distribución.** 547 858 ítems (el triple de 2025), dominados por rubros de obra
   con entidades HTML (`&Oacute;`). La normalización decodifica HTML y la prueba se reporta por año.
6. **Cola larga.** De 8 930 códigos de 9 dígitos en entrenamiento, 3 708 tienen 1 sola descripción
   única, 6 350 tienen ≤ 5 y sólo 333 tienen > 100.
7. **Ruido de etiqueta medible.** El 9,1 % de las descripciones de entrenamiento aparece con más de
   un código; se usa el mayoritario y se guarda `code_agreement`.

## d) Demo pública

Hugging Face Spaces con Gradio ya no es gratis para cuentas personales (fuente [9]). Por decisión
tuya **no se despliega**: la demo corre en local con `docker compose up --build` (API FastAPI +
frontend React/Astryx). Si más adelante quieres publicarla, lo gratuito verificado es un Space
estático para el frontend; la API necesitaría otro servicio.

## e) Alcance propuesto (y aplicado)

- Datos: los 12 años, ítems de adjudicación (con respaldo en ítems de licitación si el proceso no
  tiene adjudicaciones), código truncado a 9 dígitos; evaluación a 5 y 9 dígitos.
- Exclusiones documentadas: sin código, descripciones genéricas (patrones versionados en
  `configs/data.yaml`) y cualquier patrón de datos personales.
- División por tiempo: entrenamiento ≤ 2023, validación 2024, prueba 2025–2026, con deduplicación
  exacta y casi-idéntica entre divisiones.
- Escalones 1 y 4 entrenados y medidos en esta laptop (CPU). Escalones 2 y 3 con código probado y
  cuadernos listos para Kaggle; sus métricas quedan **pendientes** hasta ejecutarlos.
- Conjunto de oro: 300 ítems estratificados y herramienta de revisión; **la revisión es manual y
  te corresponde a ti** (no se etiqueta en tu nombre).
