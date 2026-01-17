from __future__ import annotations

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple

import numpy as np
import pandas as pd

from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_auc_score, log_loss
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression

ART_DIR = Path("models")
ART_DIR.mkdir(parents=True, exist_ok=True)

DATA_PATH = "data/ml/driver_event_table_v1_4_quali_pos.parquet"


def _ensure_targets(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create targets if they don't exist:
    - pole: quali_pos == 1
    - quali_top3: quali_pos <= 3
    - win: finish_pos == 1
    - top3: finish_pos <= 3
    """
    out = df.copy()

    if "quali_pos" in out.columns:
        out["label_pole"] = (out["quali_pos"] == 1).astype(int)
        out["label_quali_top3"] = (out["quali_pos"] <= 3).astype(int)
    else:
        # if quali_pos isn't present, we can't train quali models yet
        out["label_pole"] = np.nan
        out["label_quali_top3"] = np.nan

    if "finish_pos" in out.columns:
        out["label_win"] = (out["finish_pos"] == 1).astype(int)
        out["label_top3"] = (out["finish_pos"] <= 3).astype(int)
    else:
        out["label_win"] = np.nan
        out["label_top3"] = np.nan

    return out


def _pick_features(df: pd.DataFrame, kind: str) -> Tuple[List[str], List[str]]:
    """
    kind: "quali" or "race"
    Returns (numeric_cols, cat_cols)
    """
    # Core numeric signals (pre-event)
    numeric = [
        "grid_pos",                 # for race model it helps; for quali may be NaN (we handle)
        "quali_best_s",
        "drv_roll_points",
        "drv_roll_finish",
        "drv_roll_grid",
        "drv_roll_quali",
        "drv_roll_pos_delta",
        "team_roll_points",
        "team_roll_finish",
        # Strategy/incident proxies (pre-race): keep minimal for v1
        "incident", "sc", "vsc", "red_flag",
    ]

    # Some of these may not exist depending on your dataset; keep only those available
    numeric = [c for c in numeric if c in df.columns]

    cat = []
    for c in ["driver", "team", "event_name", "circuit_key"]:
        if c in df.columns:
            cat.append(c)

    # season can be numeric (year effect)
    if "season" in df.columns:
        numeric.append("season")

    if kind == "quali":
        # grid_pos may not exist pre-quali; still okay if NaN
        pass

    return numeric, cat


def _build_model(numeric_cols: List[str], cat_cols: List[str]) -> Pipeline:
    pre = ColumnTransformer(
        transformers=[
            ("num", Pipeline(steps=[
                ("imputer", SimpleImputer(strategy="median")),
            ]), numeric_cols),
            ("cat", Pipeline(steps=[
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("ohe", OneHotEncoder(handle_unknown="ignore")),
            ]), cat_cols),
        ],
        remainder="drop",
    )

    # Strong baseline; stable and fast
    clf = LogisticRegression(max_iter=2000, n_jobs=1)

    return Pipeline(steps=[("pre", pre), ("clf", clf)])


def _train_cv(df: pd.DataFrame, target: str, kind: str) -> Dict[str, Any]:
    """
    GroupKFold by race (season-round) to avoid leakage across drivers in same race.
    """
    # remove rows missing target
    d = df.dropna(subset=[target]).copy()
    d[target] = d[target].astype(int)

    # define groups by event
    d["group"] = d["season"].astype(int) * 100 + d["round"].astype(int)

    numeric_cols, cat_cols = _pick_features(d, kind)
    model = _build_model(numeric_cols, cat_cols)

    X = d[numeric_cols + cat_cols]
    y = d[target].values
    groups = d["group"].values

    gkf = GroupKFold(n_splits=min(5, len(np.unique(groups))))
    oof = np.zeros(len(d), dtype=float)

    aucs = []
    lls = []

    for tr, te in gkf.split(X, y, groups):
        model.fit(X.iloc[tr], y[tr])
        p = model.predict_proba(X.iloc[te])[:, 1]
        oof[te] = p

        # metrics
        try:
            aucs.append(roc_auc_score(y[te], p))
        except Exception:
            pass
        try:
            lls.append(log_loss(y[te], p, labels=[0, 1]))
        except Exception:
            pass

    # fit final model on all
    model.fit(X, y)

    report = {
        "target": target,
        "kind": kind,
        "rows": int(len(d)),
        "n_groups": int(len(np.unique(groups))),
        "numeric_cols": numeric_cols,
        "cat_cols": cat_cols,
        "cv_auc_mean": float(np.mean(aucs)) if aucs else None,
        "cv_logloss_mean": float(np.mean(lls)) if lls else None,
    }

    return {"model": model, "report": report}


def main():
    df = pd.read_parquet(DATA_PATH)
    df = df.dropna(subset=["season", "round", "driver"])
    df["season"] = df["season"].astype(int)
    df["round"] = df["round"].astype(int)

    df = _ensure_targets(df)

    outputs = {}

    # Qualifying models (if quali_pos exists)
    if df["label_pole"].notna().any():
        outputs["pole"] = _train_cv(df, "label_pole", "quali")
        outputs["quali_top3"] = _train_cv(df, "label_quali_top3", "quali")
    else:
        print("⚠️ quali_pos not found; skipping quali models for now.")

    # Race models
    outputs["win"] = _train_cv(df, "label_win", "race")
    outputs["race_top3"] = _train_cv(df, "label_top3", "race")

    # Save artifacts
    for k, v in outputs.items():
        model = v["model"]
        report = v["report"]

        model_path = ART_DIR / f"model_{k}_v1.joblib"
        report_path = ART_DIR / f"model_{k}_v1_report.json"

        # lazy import to avoid dependency issues until needed
        import joblib
        joblib.dump(model, model_path)

        report_path.write_text(json.dumps(report, indent=2))
        print(f"✅ Saved: {model_path}")
        print(f"✅ Saved: {report_path}")
        print("   ", report)

    print("\nDone.")


if __name__ == "__main__":
    main()
