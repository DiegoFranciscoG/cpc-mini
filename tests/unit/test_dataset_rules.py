"""T-01, T-02, T-03 y T-04 sobre un dataset ficticio construido de punta a punta."""

import polars as pl

from cpcmini.data.dataset import SPLITS, read_manifest, read_split
from cpcmini.data.pii import PiiDetector


def _splits(ws):
    return {s: read_split(ws["data_cfg"].paths.processed_dir, s) for s in SPLITS}


def test_t01_counts_reconcile_with_source(synthetic_workspace):
    ws = synthetic_workspace
    manifest = read_manifest(ws["data_cfg"].paths.processed_dir)
    for year in manifest["years"]:
        excluded = year["excluded_no_code"] + year["excluded_generic"] + year["excluded_pii"]
        assert year["raw_items"] - excluded == year["kept"]
        assert year["raw_items"] == ws["ingested"][year["year"]]
    kept_total = sum(y["kept"] for y in manifest["years"])
    split_items = sum(s["items"] for s in manifest["splits"])
    assert kept_total == split_items


def test_t02_no_description_in_two_splits(synthetic_workspace):
    splits = _splits(synthetic_workspace)
    seen_desc: set[str] = set()
    seen_sig: set[str] = set()
    for name in SPLITS:
        frame = splits[name]
        desc = set(frame["desc_norm"].to_list())
        sig = set(frame["signature"].to_list())
        assert not desc & seen_desc, f"fuga exacta en {name}"
        assert not sig & seen_sig, f"fuga casi-idéntica en {name}"
        assert frame["desc_norm"].n_unique() == frame.height
        seen_desc |= desc
        seen_sig |= sig


def test_t03_time_split(synthetic_workspace, settings):
    splits = _splits(synthetic_workspace)
    assert splits["train"]["year_max"].max() <= settings.data.split.train_max_year
    assert set(splits["val"]["year_min"].unique().to_list()) <= set(settings.data.split.val_years)
    assert splits["test"]["year_min"].min() >= min(settings.data.split.test_years)


def test_t04_no_personal_data_in_published_splits(synthetic_workspace, settings):
    detector = PiiDetector(settings.data.pii)
    for frame in _splits(synthetic_workspace).values():
        assert not any(detector.has_pii(d) for d in frame["description"].to_list())
    manifest = read_manifest(synthetic_workspace["data_cfg"].paths.processed_dir)
    assert manifest["pii_types_excluded"].get("phone", 0) > 0


def test_generic_and_codeless_items_excluded(synthetic_workspace):
    manifest = read_manifest(synthetic_workspace["data_cfg"].paths.processed_dir)
    assert sum(y["excluded_generic"] for y in manifest["years"]) > 0
    assert sum(y["excluded_no_code"] for y in manifest["years"]) > 0


def test_codes_have_nine_digits_and_zero_restored(synthetic_workspace):
    splits = _splits(synthetic_workspace)
    all_codes = pl.concat([f.select("code9") for f in splits.values()])["code9"]
    assert all(len(c) == 9 and c.isdigit() for c in all_codes.to_list())
    assert "013492912" in set(all_codes.to_list())


def test_catalog_and_manifest(synthetic_workspace):
    processed = synthetic_workspace["data_cfg"].paths.processed_dir
    catalog = pl.read_parquet(f"{processed}/catalog.parquet")
    assert catalog["code9"].n_unique() == catalog.height
    assert (catalog["code5"] == catalog["code9"].str.slice(0, 5)).all()
    manifest = read_manifest(processed)
    assert len(manifest["dataset_hash"]) == 64
    assert "CC BY 3.0" in manifest["source_license"]
    assert "SERCOP" in manifest["attribution"]


def test_dataset_hash_is_deterministic(synthetic_workspace, tmp_path):
    from cpcmini.data.dataset import build_dataset

    cfg = synthetic_workspace["data_cfg"]
    again = build_dataset(cfg, out_dir=tmp_path)
    assert again.dataset_hash == synthetic_workspace["manifest"].dataset_hash


def test_majority_label_and_agreement(settings):
    from cpcmini.data.dataset import aggregate_split

    items = pl.DataFrame(
        {
            "desc_norm": ["a", "a", "a", "b"],
            "description": ["A", "A", "A", "B"],
            "signature": ["a", "a", "a", "b"],
            "code": ["111111111", "111111111", "222222222", "333333333"],
            "label_copy": [False, False, False, True],
            "category": ["goods"] * 4,
            "method": ["m"] * 4,
            "process_kind": ["unico"] * 4,
            "year": [2020, 2021, 2021, 2022],
        }
    )
    out = aggregate_split(items).sort("desc_norm")
    assert out["code9"].to_list() == ["111111111", "333333333"]
    assert out["code_agreement"].to_list() == [round(2 / 3, 4), 1.0]
    assert out["n_items"].to_list() == [3, 1]
