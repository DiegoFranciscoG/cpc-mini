# Guía de etiquetado del conjunto de oro

El código CPC de cada ítem lo elige la entidad contratante, así que a veces está mal. El conjunto de
oro son **300 descripciones de prueba (2025–2026) revisadas a mano**: es la medida honesta frente a
etiquetas ruidosas.

## Muestra

`gold/gold_candidates.csv` se generó con `cpcmini gold sample` (semilla fija):

- Sólo texto libre (se excluyen descripciones idénticas al nombre del catálogo).
- 60 ítems por estrato según cuántas descripciones tenía el código original en entrenamiento:
  `0 (no visto)`, `1-5`, `6-20`, `21-100` y `101+`. Así la cola larga pesa lo mismo que los códigos
  frecuentes.

## Cómo revisar

```bash
export CPCMINI_DATABASE_URL=sqlite:///data/cpcmini.db
uv run cpcmini gold review --reviewer DG
```

La herramienta muestra la descripción, el código original con su etiqueta y las tres sugerencias del
modelo en servicio. Respuestas:

| Tecla | Significado | Estado |
|---|---|---|
| `c` | El código original es correcto | `confirmed` |
| 9 dígitos | El código correcto es otro (debe existir en el catálogo) | `corrected` |
| `d` | La descripción no permite decidir (genérica, ambigua, varios productos) | `discarded` |
| `q` | Guardar y salir; se retoma donde quedó | — |

Al salir se exporta `gold/gold_set.csv`, que es el archivo versionado.

## Criterios

1. **Clasifica el producto o servicio descrito, no el proceso.** Si la línea es «breaker de 16 A»
   dentro de una obra, el código correcto es el del breaker, aunque la entidad usó el de la obra.
2. **Busca en el nivel 9 dentro de la subclase de 5 dígitos.** Usa el
   [Clasificador del SERCOP](https://www.compraspublicas.gob.ec/ProcesoContratacion/compras/CPC/index.cpe)
   y elige el código más específico que describa el ítem.
3. **Si hay dos códigos igual de válidos**, conserva el original (`c`) y anota la duda en `notes`.
4. **Descarta** sólo cuando ni una persona experta podría decidir con el texto disponible.
5. **No uses las sugerencias del modelo como verdad**: sirven para buscar, no para decidir. Revisa
   primero el original.
6. Revisor: usa un alias corto (iniciales), nunca tu nombre completo ni datos personales.

## Validación

Revisa una segunda vez una muestra aleatoria de 30 ítems después de una semana y anota el acuerdo
contigo mismo; si es menor al 80 %, ajusta estos criterios antes de publicar métricas sobre el oro.

## Estado

La herramienta y la muestra están listas. **La revisión manual está pendiente**: las métricas sobre
el conjunto de oro se publicarán cuando exista `gold/gold_set.csv` con ítems revisados.
