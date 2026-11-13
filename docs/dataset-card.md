---
language:
  - es
license: cc-by-3.0
pretty_name: CPC-mini · descripciones de compras públicas de Ecuador con su código CPC
task_categories:
  - text-classification
size_categories:
  - 100K<n<1M
tags:
  - public-procurement
  - ocds
  - ecuador
  - cpc
---

# CPC-mini · dataset

Pares **descripción de ítem → código CPC de 9 dígitos** de las compras públicas de Ecuador, limpios,
deduplicados y divididos por tiempo para medir cómo generaliza un modelo a compras nuevas.

## Origen y atribución

Datos del **Servicio Nacional de Contratación Pública (SERCOP)**, publicados en formato OCDS por el
[OCP Data Registry](https://data.open-contracting.org/en/publication/110) de **Open Contracting
Partnership** (publicación 110, recuperada el 10 de noviembre de 2026), bajo licencia
[Creative Commons Reconocimiento 3.0 Ecuador (CC BY 3.0 EC)](https://creativecommons.org/licenses/by/3.0/ec/).
Este dataset es una obra derivada con la misma licencia; su uso no implica respaldo del SERCOP ni de
Open Contracting Partnership.

## Transformaciones

1. Ítems de adjudicación (`awards[].items[]`); si el proceso no tiene, los de la licitación.
2. Código: sólo dígitos, restauración del 0 inicial de la sección 0 del CPC (10 771 ítems) usando
   `additionalClassifications`, longitud 9–13 y truncado a 9 dígitos.
3. Texto: entidades HTML decodificadas, minúsculas, sin tildes, unidades y abreviaturas unificadas
   (reglas en `configs/data.yaml`).
4. Exclusiones de 3 268 507 ítems:

| Motivo | Ítems |
|---|---|
| Sin código CPC utilizable (concentrado en 2018–2020) | 365 999 |
| Descripción genérica («ver pliegos», «de acuerdo a lo solicitado») | 16 270 |
| Patrones de datos personales (18 teléfonos, 2 cédulas) | 20 |
| **Usables** | **2 886 218** |

5. Agregación por descripción normalizada dentro de cada división, con el código mayoritario
   (`code_agreement` guarda qué fracción lo usó; el 9,1 % de las descripciones de entrenamiento
   aparece con más de un código).
6. División por tiempo y control de fuga: se quita de validación y prueba toda descripción vista
   antes, exacta o con la misma firma de tokens.

| División | Años | Ítems | Descripciones únicas | Quitadas por fuga | Filas | Códigos 9 díg. |
|---|---|---|---|---|---|---|
| train | 2015–2023 | 1 952 322 | 195 840 | 0 | 195 840 | 8 930 |
| val | 2024 | 211 030 | 28 282 | 11 663 | 16 619 | 1 881 |
| test | 2025–2026 | 722 866 | 185 377 | 27 745 | 157 632 | 4 055 |

Versión: `dataset_hash = f064fad0abaeb22a6222d6a6e8cc454e83ac0447e1ceeea0b1be229c7b6bbda4`
(SHA-256 del contenido; se reconstruye con `uv run cpcmini download && uv run cpcmini rebuild`).

## Campos

`desc_norm`, `description`, `signature`, `code9`, `code5`, `code`, `n_items`, `code_agreement`,
`label_copy`, `category`, `method`, `process_kind`, `year_min`, `year_max`, `split`. Detalle en
[modelo-datos.md](modelo-datos.md).

## Limitaciones conocidas

- **Etiquetas ruidosas:** la entidad contratante elige el código. En obras, cada rubro suele heredar
  el código de la obra completa (`process_kind = multi_un_codigo`), que no se deduce del texto.
- **Cambio de distribución en 2026:** el triple de ítems que en 2025, sobre todo rubros de obra.
- **Cola larga:** 3 708 de los 8 930 códigos de entrenamiento tienen una sola descripción.
- **Copia de la etiqueta:** entre el 11 % y el 51 % de los ítems por año repite el nombre del
  catálogo; tras deduplicar quedan pocos y se marcan con `label_copy`.
- No hay etiqueta oficial de las subclases de 5 dígitos en los datos.

## Datos personales

Sólo se publican descripciones de productos y servicios. No se incluyen partes, compradores,
proveedores ni montos. Se excluyó cualquier descripción con patrones de cédula, RUC de persona
natural, teléfono o correo (prueba T-04). Si encuentras un dato personal, repórtalo según
[SECURITY.md](../SECURITY.md) y se retirará.
