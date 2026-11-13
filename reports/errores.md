
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
