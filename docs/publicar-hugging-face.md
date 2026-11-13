# Publicar dataset y modelo en Hugging Face (pasos para ejecutar tú)

Nada se publicó desde este repositorio. Cuando quieras hacerlo, con tu cuenta y un token de
escritura en la variable de entorno `HF_TOKEN` (nunca en un archivo versionado):

```bash
pip install -U "huggingface_hub"
hf auth login --token "$HF_TOKEN"
```

## Dataset

```bash
hf repos create DiegoFranciscoG/cpc-mini-dataset --repo-type dataset --private
cp docs/dataset-card.md data/processed/README.md
hf upload DiegoFranciscoG/cpc-mini-dataset data/processed . --repo-type dataset
```

Revisa la vista previa y cambia la visibilidad a pública desde la web cuando estés conforme.

## Modelo

```bash
hf repos create DiegoFranciscoG/cpc-mini-model --private
cp docs/model-card.md artifacts/serving/README.md
hf upload DiegoFranciscoG/cpc-mini-model artifacts/serving .
```

El artefacto es un archivo `joblib`: avisa en la ficha que sólo debe cargarse si confías en el origen
(deserializar pickle ejecuta código).

## Demo

Los Spaces Gradio o Docker requieren plan pago para cuentas personales (verificado el 12-nov-2026);
un Space estático es gratis pero necesitaría la API en otro servicio. Por decisión del proyecto la
demo corre en local con `docker compose up --build`.
