"""Línea de comandos: ``cpcmini --help``."""

from __future__ import annotations

import json
import os
import shutil
from collections import Counter
from pathlib import Path
from typing import Annotated

import typer

from cpcmini.config import Settings, load_settings

app = typer.Typer(help="CPC-mini: dataset, modelos, evaluación y API.", no_args_is_help=True)
db_app = typer.Typer(help="Base de datos (migraciones y catálogo).", no_args_is_help=True)
gold_app = typer.Typer(help="Conjunto de oro revisado a mano.", no_args_is_help=True)
app.add_typer(db_app, name="db")
app.add_typer(gold_app, name="gold")

ConfigOpt = Annotated[Path, typer.Option(help="Carpeta con data.yaml, models.yaml y eval.yaml")]
OverrideOpt = Annotated[
    Path | None, typer.Option(help="YAML que reemplaza secciones (p. ej. configs/sample.yaml)")
]
DbOpt = Annotated[
    str, typer.Option(envvar="CPCMINI_DATABASE_URL", help="URL SQLAlchemy de la base")
]


def _settings(config: Path, override: Path | None) -> Settings:
    return load_settings(config, override)


@app.command()
def download(
    config: ConfigOpt = Path("configs"),
    override: OverrideOpt = None,
    years: Annotated[str | None, typer.Option(help="Años separados por coma")] = None,
) -> None:
    """Descarga los JSONL.gz anuales del OCP Data Registry (publicación 110)."""
    from cpcmini.data.download import download_year, write_checksums

    s = _settings(config, override)
    todo = [int(y) for y in years.split(",")] if years else s.data.source.years
    dest = Path(s.data.source.raw_dir)
    for year in todo:
        typer.echo(f"Descargando {year}…")
        download_year(s.data.source, year, dest)
    typer.echo(f"Sumas SHA-256: {write_checksums(dest, todo)}")


@app.command()
def ingest(
    config: ConfigOpt = Path("configs"), override: OverrideOpt = None, workers: int = 4
) -> None:
    """OCDS → Parquet intermedio por año (normalización, banderas de exclusión)."""
    from cpcmini.data.ingest import ingest_years

    s = _settings(config, override)
    for year, n in sorted(ingest_years(s.data, workers=workers).items()):
        typer.echo(f"{year}: {n} ítems")


@app.command()
def build(config: ConfigOpt = Path("configs"), override: OverrideOpt = None) -> None:
    """Exclusiones, división por tiempo, deduplicación y control de fuga → data/processed."""
    from cpcmini.data.coverage import coverage_report, write_report
    from cpcmini.data.dataset import build_dataset, read_split

    s = _settings(config, override)
    manifest = build_dataset(s.data)
    typer.echo(f"Dataset {manifest.dataset_hash[:12]}")
    for split in manifest.splits:
        typer.echo(f"  {split.split}: {split.rows} filas, {split.codes9} códigos de 9 dígitos")
    report = coverage_report(
        s.data.paths.interim_dir,
        s.data.source.years,
        read_split(s.data.paths.processed_dir, "train"),
    )
    typer.echo(
        f"Cobertura: {write_report(report, Path(s.data.paths.processed_dir) / 'coverage.json')}"
    )


@app.command()
def train(
    model: Annotated[list[str], typer.Option(help="tfidf_logreg, tfidf_svm, tfidf_knn")],
    config: ConfigOpt = Path("configs"),
    override: OverrideOpt = None,
    reports: Path = Path("reports"),
) -> None:
    """Entrena, calibra en validación y evalúa en prueba con el protocolo común."""
    from cpcmini.pipeline import train_and_evaluate

    s = _settings(config, override)
    for name in model:
        m = train_and_evaluate(name, s, s.data.paths.processed_dir, s.models.artifacts_dir, reports)
        t9 = m["test"]["level_9"]
        typer.echo(
            f"{name}: top-1 {t9['top1']['value']:.3f} · top-3 {t9['top3']['value']:.3f} (9 dígitos)"
        )


@app.command()
def report(
    config: ConfigOpt = Path("configs"),
    override: OverrideOpt = None,
    reports: Path = Path("reports"),
) -> None:
    """Genera reports/resultados.md con la comparación y elige el ganador en validación."""
    from cpcmini.data.dataset import read_manifest
    from cpcmini.eval.report import load_metrics, select_winner, write_results

    s = _settings(config, override)
    out = write_results(reports, read_manifest(s.data.paths.processed_dir))
    winner = select_winner(load_metrics(reports))
    (reports / "ganador.json").write_text(json.dumps({"model": winner}), encoding="utf-8")
    typer.echo(f"{out} · ganador: {winner}")


@app.command()
def package(
    model: str,
    config: ConfigOpt = Path("configs"),
    override: OverrideOpt = None,
    quantized: bool = True,
) -> None:
    """Copia el modelo elegido a artifacts/serving (int8 si pierde menos de lo permitido, T-07)."""
    s = _settings(config, override)
    base = Path(s.models.artifacts_dir)
    chosen = model
    meta = json.loads((base / model / "meta.json").read_text(encoding="utf-8"))
    q = base / f"{model}_int8"
    if quantized and q.exists():
        drop = json.loads((q / "meta.json").read_text(encoding="utf-8"))["metrics"]["quantization"][
            "drop"
        ]
        if drop < s.eval.quantization_max_drop:
            chosen = f"{model}_int8"
    target = base / "serving"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(base / chosen, target)
    typer.echo(f"Sirviendo {chosen} (dataset {meta['dataset_hash'][:12]}) desde {target}")


@app.command("predecir")
def predict(
    description: str,
    model_dir: Path = Path("artifacts/serving"),
    config: ConfigOpt = Path("configs"),
    override: OverrideOpt = None,
) -> None:
    """Sugiere los 3 códigos más probables para una descripción (sin red, en CPU)."""
    from cpcmini.data.normalize import TextNormalizer
    from cpcmini.models.calibration import calibrate
    from cpcmini.models.registry import load_meta, load_model

    s = _settings(config, override)
    norm = TextNormalizer(s.data.text)
    text = norm.normalize(description)
    if not norm.is_informative(text):
        typer.echo(f"{s.eval.abstain_label}: la descripción no tiene información suficiente")
        raise typer.Exit(0)
    meta = load_meta(model_dir)
    cands = calibrate(
        load_model(model_dir).predict_candidates([text], s.models.top_k), meta.temperature
    )
    codes, probs = cands.codes[0], cands.probs[0]
    if not codes or probs[0] < meta.threshold:
        typer.echo(f"{s.eval.abstain_label} (confianza por debajo de {meta.threshold:.2f})")
    for code, p in zip(codes, probs.tolist(), strict=True):
        typer.echo(f"  {code}  {100 * p:5.1f} %")


@app.command()
def sample(
    config: ConfigOpt = Path("configs"),
    out: Path = Path("sample_data/ocds"),
    rate: int = 120,
    seed: int = 20261112,
) -> None:
    """Crea la muestra mínima de OCDS versionada (sin partes ni datos personales)."""
    from cpcmini.data.sample import build_sample

    s = _settings(config, None)
    for year, n in build_sample(s.data, out, rate, seed).items():
        typer.echo(f"{year}: {n} procesos")


@app.command()
def rebuild(
    config: ConfigOpt = Path("configs"),
    override: OverrideOpt = None,
    models: str = "tfidf_logreg,tfidf_knn",
    reports: Path = Path("reports"),
    workers: int = 1,
) -> None:
    """Reconstruye todo desde los JSONL.gz: ingesta → dataset → modelos → informe → paquete (T-12)."""
    s = _settings(config, override)
    ingest(config, override, workers)
    build(config, override)
    names = [m.strip() for m in models.split(",") if m.strip()]
    train(names, config, override, reports)
    report(config, override, reports)
    winner = json.loads((reports / "ganador.json").read_text(encoding="utf-8"))["model"]
    package(winner, config, override)
    db_url = os.environ.get("CPCMINI_DATABASE_URL")
    if db_url:
        db_upgrade(db_url)
        db_seed(db_url, config, override)
    typer.echo(f"Reconstrucción completa en {s.models.artifacts_dir}/serving")


@db_app.command("upgrade")
def db_upgrade(db_url: DbOpt) -> None:
    """Aplica las migraciones de Alembic hasta la última versión."""
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    if not Path(cfg.config_file_name or "").exists():
        cfg = Config("alembic.ini")
    cfg.attributes["database_url"] = db_url
    command.upgrade(cfg, "head")
    typer.echo("Migraciones aplicadas")


@db_app.command("seed")
def db_seed(
    db_url: DbOpt, config: ConfigOpt = Path("configs"), override: OverrideOpt = None
) -> None:
    """Carga el catálogo de códigos y registra la versión del dataset."""
    import polars as pl

    from cpcmini.data.dataset import read_manifest
    from cpcmini.db.repository import (
        CatalogRepository,
        DatasetVersionRepository,
        make_engine,
        make_session_factory,
    )

    s = _settings(config, override)
    processed = Path(s.data.paths.processed_dir)
    catalog = pl.read_parquet(processed / "catalog.parquet")
    manifest = read_manifest(processed)
    rows = {sp["split"]: sp["rows"] for sp in manifest["splits"]}
    sessions = make_session_factory(make_engine(db_url))
    with sessions() as session:
        n = CatalogRepository(session).replace_all(
            [
                {
                    "code9": r["code9"],
                    "code5": r["code5"],
                    "label": r["label"][:300],
                    "n_items": r["n_items"],
                    "first_year": r["first_year"],
                    "last_year": r["last_year"],
                }
                for r in catalog.iter_rows(named=True)
            ]
        )
        DatasetVersionRepository(session).get_or_create(
            manifest["dataset_hash"], manifest["config_hash"], rows, manifest["source_license"]
        )
    typer.echo(f"Catálogo cargado: {n} códigos")


@gold_app.command("sample")
def gold_sample(
    config: ConfigOpt = Path("configs"),
    override: OverrideOpt = None,
    n: int = 300,
    out: Path = Path("gold/gold_candidates.csv"),
) -> None:
    """Muestreo estratificado de prueba para revisión manual."""
    from cpcmini.data.dataset import read_split
    from cpcmini.gold.sample import stratified_sample, write_candidates

    s = _settings(config, override)
    train_counts = Counter(read_split(s.data.paths.processed_dir, "train")["code9"].to_list())
    test = read_split(s.data.paths.processed_dir, "test")
    frame = stratified_sample(test, train_counts, n, s.eval.frequency_buckets, s.models.seed)
    write_candidates(frame, out)
    typer.echo(
        f"{frame.height} ítems en {out}: "
        + ", ".join(f"{k}={v}" for k, v in sorted(Counter(frame["stratum"].to_list()).items()))
    )


@gold_app.command("review")
def gold_review(
    db_url: DbOpt,
    reviewer: Annotated[str, typer.Option(help="Alias del revisor")],
    candidates: Path = Path("gold/gold_candidates.csv"),
    config: ConfigOpt = Path("configs"),
    override: OverrideOpt = None,
    model_dir: Path = Path("artifacts/serving"),
    out: Path = Path("gold/gold_set.csv"),
) -> None:
    """Herramienta de terminal para confirmar, corregir o descartar cada ítem del conjunto de oro."""
    import csv

    from cpcmini.data.dataset import read_manifest
    from cpcmini.db.repository import (
        CatalogRepository,
        DatasetVersionRepository,
        GoldRepository,
        make_engine,
        make_session_factory,
    )
    from cpcmini.gold.sample import REVIEWED_COLUMNS, decide
    from cpcmini.models.registry import load_model

    s = _settings(config, override)
    manifest = read_manifest(s.data.paths.processed_dir)
    rows = {sp["split"]: sp["rows"] for sp in manifest["splits"]}
    model = load_model(model_dir) if (model_dir / "model.joblib").exists() else None
    sessions = make_session_factory(make_engine(db_url))
    with sessions() as session:
        version = DatasetVersionRepository(session).get_or_create(
            manifest["dataset_hash"], manifest["config_hash"], rows, manifest["source_license"]
        )
        gold = GoldRepository(session)
        catalog_repo = CatalogRepository(session)
        with candidates.open(encoding="utf-8", newline="") as fh:
            gold.add_candidates(version.id, list(csv.DictReader(fh)))
        for item in gold.pending(version.id):
            entry = catalog_repo.get(item.original_code9)
            typer.echo(f"\n[{item.stratum}] {item.description}")
            typer.echo(f"  Código original: {item.original_code9} {entry.label if entry else ''}")
            if model is not None:
                sug = model.predict_candidates([item.desc_norm], 3)
                for code in sug.codes[0]:
                    label = catalog_repo.get(code)
                    typer.echo(f"  Sugerido: {code} {label.label if label else ''}")
            answer = typer.prompt(
                "c = confirmar · d = descartar · 9 dígitos = corregir · q = salir"
            )
            if answer.strip().lower() == "q":
                break
            typed = answer.strip()
            known = (
                frozenset({typed}) if typed.isdigit() and catalog_repo.get(typed) else frozenset()
            )
            decision = decide(answer, item.original_code9, known)
            if decision.error:
                typer.echo(f"  ⚠ {decision.error}")
                continue
            gold.review(item, decision.status, decision.gold_code9, reviewer)
        with out.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=REVIEWED_COLUMNS)
            writer.writeheader()
            for g in gold.all(version.id):
                writer.writerow(
                    {
                        "desc_norm": g.desc_norm,
                        "description": g.description,
                        "original_code9": g.original_code9,
                        "stratum": g.stratum,
                        "status": g.status,
                        "gold_code9": g.gold_code9 or "",
                        "notes": g.notes,
                    }
                )
    typer.echo(f"Conjunto de oro exportado a {out}")


@gold_app.command("evaluate")
def gold_evaluate(
    gold: Path = Path("gold/gold_set.csv"),
    model_dir: Path = Path("artifacts/serving"),
    config: ConfigOpt = Path("configs"),
    override: OverrideOpt = None,
    out: Path = Path("reports/metrics_gold.json"),
) -> None:
    """Mide el modelo contra el conjunto de oro revisado (sólo ítems confirmados o corregidos)."""
    from cpcmini.gold.sample import gold_metrics, read_reviewed
    from cpcmini.models.calibration import calibrate
    from cpcmini.models.registry import load_meta, load_model

    rows = read_reviewed(gold)
    if not rows:
        typer.echo("Aún no hay ítems revisados en el conjunto de oro (ver docs/etiquetado.md)")
        raise typer.Exit(0)
    meta = load_meta(model_dir)
    cands = calibrate(
        load_model(model_dir).predict_candidates([r["desc_norm"] for r in rows], 20),
        meta.temperature,
    )
    result = {"model": meta.name, **gold_metrics(cands, rows)}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(json.dumps(result, ensure_ascii=False))


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Levanta la API (requiere CPCMINI_DATABASE_URL, CPCMINI_MODEL_DIR y CPCMINI_CORS_ALLOWED_ORIGINS)."""
    import uvicorn

    uvicorn.run("cpcmini.serve.api:create_app", factory=True, host=host, port=port)


if __name__ == "__main__":
    app()
