# Política de seguridad

## Reportar una vulnerabilidad
No abras un issue público. Escríbeme por GitHub (perfil DiegoFranciscoG) con los pasos para
reproducir el problema. Respondo en un máximo de 7 días.

## Prácticas aplicadas en este proyecto
- Secretos sólo por variables de entorno (`.env` no se versiona; ver `.env.example`). La API no
  arranca si falta su configuración crítica y rechaza `CORS` con comodín.
- Escaneo de secretos con gitleaks en cada push y pull request; Dependabot para dependencias,
  acciones e imágenes.
- API de sólo lectura: no guarda ni registra las descripciones que recibe (minimización, LOPDP).
- Validación de entradas con Pydantic (longitudes, campos extra prohibidos), límite de solicitudes por
  cliente, límite de tamaño de cuerpo, cabeceras de seguridad (CSP, `nosniff`, `DENY`), errores sin
  trazas internas.
- SQL sólo parametrizado (SQLAlchemy); búsquedas `LIKE` con comodines escapados.
- Los artefactos `joblib` los genera este mismo flujo; nunca cargues un `model.joblib` de terceros
  (deserializar pickle ejecuta código).
- Contenedores multi-stage, imágenes con versión fija, usuario sin privilegios y healthcheck.
