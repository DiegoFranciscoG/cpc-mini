# Muestra mínima de datos OCDS del SERCOP

Archivos `ocds/<año>.jsonl.gz`: unos 22 400 procesos de contratación (≈ 1 de cada 100 por año,
elegidos de forma determinista por un hash del `ocid`), 2015–2026.

- **Fuente:** Servicio Nacional de Contratación Pública (SERCOP), publicados en formato OCDS por el
  [OCP Data Registry](https://data.open-contracting.org/en/publication/110) de Open Contracting
  Partnership, recuperados el 10 de noviembre de 2026.
- **Licencia:** [Creative Commons Reconocimiento 3.0 Ecuador (CC BY 3.0 EC)](https://creativecommons.org/licenses/by/3.0/ec/).
- **Cambios:** se conservan sólo `ocid`, `date`, el método y la categoría del proceso, y por cada ítem
  su `id`, descripción y clasificación CPC; se eliminaron partes, compradores, proveedores, montos y
  documentos (minimización). Se descartaron los procesos con descripciones que contienen patrones de
  cédula, RUC de persona natural, teléfono o correo. Máximo 40 ítems por proceso.
- **Uso:** CI, la imagen Docker de demostración y la prueba de reconstrucción desde cero (T-12).
  Regenerar: `uv run cpcmini sample --rate 100` (requiere los datos completos en `data/raw`).

El uso de estos datos no implica respaldo del SERCOP ni de Open Contracting Partnership.
