# Investigación y fuentes

Todas las consultas se hicieron el **2026-11-12**. Cuando dos fuentes se contradicen gana la oficial y
más reciente. Lo que no se pudo verificar en una fuente oficial está en la sección **Supuestos**.

| # | Fuente (oficial / confiable) | URL | Consultada | Qué se tomó de aquí |
|---|---|---|---|---|
| 1 | OCP Data Registry — Ecuador: SERCOP (publicación 110) | https://data.open-contracting.org/en/publication/110 | 2026-11-12 | Archivos JSONL.gz por año 2015–2026 (1 109 MB en total), actualización diaria, recuperado el 10-nov-2026; 3 182 365 ítems de adjudicación y 1 261 106 de licitación; avisos de calidad (ids repetidos en `awards/items`). |
| 2 | Creative Commons — Reconocimiento 3.0 Ecuador (código legal) | https://creativecommons.org/licenses/by/3.0/ec/ | 2026-11-12 | Licencia de los datos (CC BY 3.0 EC): se puede compartir y adaptar, incluso comercialmente, con atribución, enlace a la licencia e indicación de cambios. |
| 3 | SERCOP — ¿Qué es el Clasificador Central de Productos (CPC)? | https://portal.compraspublicas.gob.ec/sercop/que-es-el-clasificador-central-de-productos-cpc/ | 2026-11-12 | El proveedor se registra con un CPC de **5 dígitos** y queda habilitado en todos los CPC de **nivel 9** contenidos en él → niveles de evaluación 5 y 9, jerarquía por prefijos. |
| 4 | Datos OCDS del SERCOP (observación directa, años 2015–2026) | archivos de la fuente 1 | 2026-11-12 | `classification.id` pierde el cero inicial de la sección 0 del CPC (`134929123` ↔ `01349.29.1`); descripciones con entidades HTML en 2026; códigos de 9 a 13 dígitos (ver docs/verificacion.md). |
| 5 | Corte Constitucional del Ecuador — Política de Protección de Datos Personales V1.0 (29-06-2026) | https://www.corteconstitucional.gob.ec/wp-content/uploads/2026/07/Pol_Proteccion_Datos_V1.0_29-06-26.pdf | 2026-11-12 | Aplicación de la LOPDP por una institución pública: principios de minimización y proporcionalidad, derechos ARCO, cookies sólo con fines técnicos/estadísticos y aviso de configuración con consentimiento informado. Base para la política de privacidad y de cookies de la demo. |
| 6 | Hugging Face — jhu-clsp/mmBERT-small (model card y config) | https://huggingface.co/jhu-clsp/mmBERT-small | 2026-11-12 | Licencia MIT; 140 M parámetros (42 M sin embeddings); 22 capas, ancho 384; contexto 8 192; tokenizador Gemma 2; artículo arXiv 2509.06888. |
| 7 | Hugging Face — Qwen/Qwen3-0.6B-Base | https://huggingface.co/Qwen/Qwen3-0.6B-Base | 2026-11-12 | Licencia Apache-2.0; 596 049 920 parámetros (safetensors). |
| 8 | Hugging Face — intfloat/multilingual-e5-small | https://huggingface.co/intfloat/multilingual-e5-small | 2026-11-12 | Licencia MIT; 117,7 M parámetros; embeddings de oraciones para la variante densa del escalón 4 (opcional). |
| 9 | Hugging Face Hub docs — Spaces overview | https://huggingface.co/docs/hub/spaces-overview | 2026-11-12 | Los Spaces **estáticos** son gratis; los Spaces Gradio/Docker **requieren plan pago** para crearse (cuentas gratis: hasta 2 Spaces Gradio en ZeroGPU). CPU Basic: 2 vCPU, 16 GB. → La demo se hace con React + API propia, no con Gradio. |
| 10 | PyPI (API JSON oficial de cada paquete) | https://pypi.org/pypi/&lt;paquete&gt;/json | 2026-11-12 | Versiones estables fijadas en `pyproject.toml` (ver tabla de versiones en docs/verificacion.md). |
| 11 | npm registry (`npm view`) | https://registry.npmjs.org | 2026-11-12 | Versiones fijadas en `frontend/package.json`. |
| 12 | Astryx Design System — Getting Started | https://astryx.atmeta.com/docs/getting-started | 2026-11-12 | `@astryxdesign/core` 0.7.15 (MIT, beta), requiere React ≥ 19 y `@stylexjs/stylex`; CSS `reset.css` + `astryx.css`; temas como paquetes; importación por componente (`@astryxdesign/core/Button`). |
| 13 | Docker Hub (API de tags) | https://hub.docker.com | 2026-11-12 | Imágenes fijadas: `python:3.13.18-slim`, `node:24.22.3-alpine`, `nginxinc/nginx-unprivileged:1.31.7-alpine`; `ghcr.io/astral-sh/uv:0.13.8`. |
| 14 | GitHub Releases (API) | https://api.github.com | 2026-11-12 | `actions/checkout` v7.0.1, `actions/setup-node` v7.1.0, `astral-sh/setup-uv` v10.3.3, `actions/upload-artifact` v7.0.2, gitleaks 8.30.1. |
| 15 | GPUPerHour — Free cloud GPUs and credits (21-sep-2026) — **tercero** | https://gpuperhour.com/blog/free-cloud-gpus-and-credits | 2026-11-12 | Kaggle: GPU T4/P100, sesiones de hasta 12 h, cuota semanal visible en la cuenta (≈ 30 h reportadas por usuarios, no declaradas por Kaggle). Ver supuesto S-2. |
| 16 | Reel de @go.expoose «Una web no es solo diseño» (inspiración, no norma) | https://www.facebook.com/reel/1604653857522838 | 2026-11-12 | Lista de la «infraestructura oculta» de una web: aviso legal y cookies, SEO, velocidad de carga y arquitectura de conversión → checklist del frontend. |

## Supuestos (no verificados en fuente oficial)

- **S-1 · Algoritmo de la cédula.** El filtro de datos personales valida cédulas con el dígito
  verificador módulo 10 (provincia 01–24 o 30, tercer dígito < 6). No se encontró un documento técnico
  oficial del Registro Civil que lo publique. Impacto: el filtro es conservador (excluye de más,
  nunca publica de menos); los teléfonos y correos se detectan con patrones independientes.
- **S-2 · Cuota de GPU de Kaggle.** La página oficial de Kaggle se renderiza con JavaScript y no se
  pudo leer de forma automática; la única fuente es un tercero (fuente 15). **Debes confirmar la cuota
  semanal en tu cuenta de Kaggle** antes de lanzar los escalones 2 y 3.
- **S-3 · Registro Oficial de la LOPDP.** La política de la Corte Constitucional (fuente 5) cita la
  LOPDP; el número de Registro Oficial (Quinto Suplemento 459, 26-may-2021) viene de conocimiento
  previo y no se re-verificó en el Registro Oficial durante esta sesión.
- **S-4 · Etiqueta de 5 dígitos.** Los datos OCDS no traen el nombre oficial de cada subclase CPC de
  5 dígitos; la demo muestra la subclase sólo como número y la etiqueta oficial del código de 9 dígitos.
