# Resultados de la escalera de modelos

Dataset `f064fad0abae` · prueba = años 2025–2026 (descripciones nunca vistas en entrenamiento ni validación) · intervalos al 95 % por bootstrap.

## Comparación en prueba

| Escalón | Top-1 9 díg. | Top-3 9 díg. | Top-1 5 díg. | Top-3 5 díg. | F1 macro 9 | ECE 9 | Cobertura @90 % | Latencia p50 | Tamaño |
|---|---|---|---|---|---|---|---|---|---|
| 4. Recuperación: vecinos TF-IDF + voto ponderado | 13.2 (13.1–13.4) | 23.6 (23.4–23.8) | 18.6 (18.4–18.8) | 35.2 (35.0–35.5) | 6.1 (5.9–6.5) | 0.033 | 0.0 % | 6.4 ms | 60 MB |
| 1. Base: TF-IDF + regresión logística jerárquica | 12.5 (12.3–12.6) | 23.0 (22.8–23.2) | 20.0 (19.8–20.2) | 36.6 (36.3–36.8) | 6.2 (6.0–6.6) | 0.216 | 0.0 % | 89.5 ms | 409 MB |
| 1. Base: TF-IDF + SVM lineal jerárquico | 12.9 (12.7–13.0) | 23.0 (22.8–23.2) | 19.3 (19.1–19.5) | 32.8 (32.5–33.0) | 6.7 (6.5–7.0) | 0.079 | 0.0 % | 23.1 ms | 237 MB |
| 2. Codificador: mmBERT-small jerárquico (Kaggle, GPU) | pendiente | pendiente | pendiente | pendiente | pendiente | — | — | — | — |
| 3. Generativo: Qwen3-0.6B-Base + LoRA, salida restringida (Kaggle, GPU) | pendiente | pendiente | pendiente | pendiente | pendiente | — | — | — | — |

**Ganador (elegido en validación):** `tfidf_svm` — 1. Base: TF-IDF + SVM lineal jerárquico.

Los escalones 2 y 3 necesitan GPU: su código, las pruebas unitarias de sus partes puras (trie de decodificación restringida, combinación jerárquica) y los cuadernos de Kaggle están en el repositorio, pero sus métricas sólo se publican cuando se ejecutan (nada se inventa).

## Abstención (umbral calibrado en validación para 90 % de exactitud)

| Modelo | Umbral | Cobertura en prueba | Exactitud de lo respondido |
|---|---|---|---|
| `tfidf_knn` | 0.678 | 0.0 % | 57.1 % |
| `tfidf_logreg` | 1.000 | 0.0 % | 0.0 % |
| `tfidf_svm` | 0.955 | 0.0 % | 64.3 % |

## Rendimiento por frecuencia del código en entrenamiento (top-1, 9 dígitos)

| Modelo | 0 (no visto) | 1-5 | 101+ | 21-100 | 6-20 |
|---|---|---|---|---|---|
| `tfidf_knn` | 0.0 % (n=1308) | 2.3 % (n=7100) | 15.1 % (n=109898) | 12.4 % (n=28004) | 5.2 % (n=11322) |
| `tfidf_logreg` | 0.0 % (n=1308) | 2.0 % (n=7100) | 14.4 % (n=109898) | 11.4 % (n=28004) | 4.4 % (n=11322) |
| `tfidf_svm` | 0.0 % (n=1308) | 1.9 % (n=7100) | 14.8 % (n=109898) | 12.1 % (n=28004) | 4.8 % (n=11322) |

## Subconjuntos de prueba (top-1 / top-3, 9 dígitos)

| Modelo | anio_2025 | anio_2026 | proceso_multi_un_codigo | proceso_multi_varios_codigos | proceso_unico | texto_libre |
|---|---|---|---|---|---|---|
| `tfidf_knn` | 15.6 / 26.9 (n=28771) | 12.7 / 22.9 (n=128861) | 2.5 / 5.0 (n=39843) | 16.7 / 29.6 (n=114463) | 23.5 / 40.7 (n=3326) | 13.2 / 23.6 (n=156813) |
| `tfidf_logreg` | 14.6 / 25.9 (n=28771) | 12.0 / 22.4 (n=128861) | 2.7 / 5.5 (n=39843) | 15.6 / 28.8 (n=114463) | 23.1 / 33.8 (n=3326) | 12.4 / 23.0 (n=156813) |
| `tfidf_svm` | 15.3 / 26.5 (n=28771) | 12.3 / 22.2 (n=128861) | 2.7 / 5.5 (n=39843) | 16.0 / 28.6 (n=114463) | 25.9 / 40.4 (n=3326) | 12.8 / 22.9 (n=156813) |

## Cuantización int8 (T-07)

| Modelo | Top-1 float32 | Top-1 int8 | Pérdida | Pesos float32 | Pesos int8 | Latencia int8 p50 |
|---|---|---|---|---|---|---|
| `tfidf_logreg` | 12.5 % | 12.5 % | -0.01 pts | 474 MB | 133 MB | 114.4 ms |
| `tfidf_svm` | 12.9 % | 12.9 % | 0.01 pts | 474 MB | 133 MB | 8.8 ms |

## Análisis de errores

Muestra aleatoria fija de 20000 descripciones de prueba, modelo en servicio.

| Categoría | Descripciones | Top-1 9 díg. | Top-1 5 díg. |
|---|---|---|---|
| Sin categoría | 58 | 27.6 % | 75.9 % |
| Bienes | 595 | 9.8 % | 18.8 % |
| Servicios | 248 | 29.8 % | 46.8 % |
| Obras | 19099 | 12.6 % | 18.9 % |

Confusiones más frecuentes entre subclases de 5 dígitos (verdadera → predicha):

| Verdadera | Predicha | Casos | Ejemplo |
|---|---|---|---|
| 37510 (hormigon premezclado…) | 54540 (servicios que utilizan en general hormig…) | 105 | ARRIOSTRAMIENTO DE HORMIGON SIMPLE |
| 53290 (otras obras de ingenieria civil…) | 37510 (hormigon premezclado…) | 84 | Hormigón simple para columnas f 'c= 210 kg/cm2 (incl. enc. y des). |
| 36320 (tubos de pvc…) | 53251 (tuberias de agua potable…) | 73 | PUNTO DE INSTALACIONES DE AGUA POTABLE Ø 1/2" PVC |
| 54540 (servicios que utilizan en general hormig…) | 37510 (hormigon premezclado…) | 72 | HORMIGON SIMPLE DE 210 KG/ CM2 EN VIGAS |
| 54740 (servicios de construccion para la coloca…) | 37510 (hormigon premezclado…) | 66 | POZOS REV. f´c=210 kg/cm2 H=0-2m d=1m (cuerpo) |
| 54290 (construccion de redes de distribucion…) | 54611 (servicios de trabajos de construccion es…) | 64 | TENDIDO,CALIBRACION Y AMARRE CONDUCTOR CALIBRENo.2/0 TIPO ACSR |
| 51140 (excavaciones…) | 54330 (servicios de obras, excavaciones,…) | 58 | EXCAVACIÓN MECÁNICA DE SUELO CONGLOMERADO (0-3)m |
| 54730 (servicios de pintura (principalmente dec…) | 35110 (pintura…) | 57 | PINTURA DE CAUCHO H= 6.01 A 12 M |
| 53290 (otras obras de ingenieria civil…) | 54540 (servicios que utilizan en general hormig…) | 56 | Bordillo deHormigón Simple de 15x40cm - f´c= 210 kg/cm²; INCLUYE ENCOF |
| 53290 (otras obras de ingenieria civil…) | 36320 (tubos de pvc…) | 52 | Sum, Tuberia PVC para Alcant, U/E DNE=160 mm (dimin= 135 mm) serie 5,  |
