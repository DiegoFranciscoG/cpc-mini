# Plan por días

| Día | Entregable | Pruebas | Estado |
|---|---|---|---|
| D1 | Investigación, verificación con cobertura medida, modelo de datos, plan | — | Hecho |
| D2 | Esqueleto `uv`, configuración tipada, ingesta en flujo, normalización, datos personales, dataset con división por tiempo, migraciones | T-01, T-02, T-03, T-04, T-11 | Hecho |
| D3 | Escalón 1 (TF-IDF + logística / SVM jerárquico), escalón 4 (vecinos), calibración, abstención, cuantización, protocolo de evaluación, informe | T-06, T-07, T-08, T-10 | Hecho |
| D3 | Escalones 2 y 3: código, pruebas de humo, cuadernos de Kaggle | T-05 | Código hecho · ejecución pendiente de GPU |
| D3 | Conjunto de oro: muestreo estratificado, guía, herramienta de terminal | — | Herramienta hecha · revisión manual pendiente |
| D4 | Frontend React + Astryx: clasificador, ficha del modelo, aviso legal, privacidad, cookies, licencias, SEO | Vitest + Playwright | Hecho |
| D5 | Seguridad de la API, Docker multi-stage, CI con gitleaks | API + seguridad | Hecho |
| D6 | Datos de demostración, capturas (sin despliegue, por decisión del autor) | — | Hecho |
| D7 | README, dataset card, model card, pulido | T-09, T-12 | Hecho |

Las doce pruebas del proyecto están en `tests/` y se listan en el README con su archivo.
