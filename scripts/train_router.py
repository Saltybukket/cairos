#!/usr/bin/env python3
"""Train an optional CAIROS router model from JSONL data."""

from __future__ import annotations

import argparse
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cairos.router_dataset import dataset_stats, load_rows, print_stats
from scripts.eval_router import metrics, print_metrics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/router_training.jsonl")
    parser.add_argument("--output", default="data/router_model.joblib")
    parser.add_argument("--test-ratio", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=20260707)
    args = parser.parse_args()

    try:
        import joblib  # type: ignore[import-not-found]
        from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore[import-not-found]
        from sklearn.linear_model import LogisticRegression  # type: ignore[import-not-found]
        from sklearn.pipeline import Pipeline  # type: ignore[import-not-found]
    except Exception:
        print("scikit-learn/joblib are not installed. Install optional extra: python -m pip install -e '.[ml-router]'")
        return 0

    path = Path(args.data)
    stats = dataset_stats(path)
    print_stats(stats)
    rows = load_rows(path)
    if not rows:
        print("No valid rows to train.", file=sys.stderr)
        return 1

    rng = random.Random(args.seed)
    rows = list(rows)
    rng.shuffle(rows)
    split = max(1, int(len(rows) * (1 - args.test_ratio)))
    train_rows = rows[:split]
    test_rows = rows[split:] or rows[:1]
    x_train = [str(row["text"]) for row in train_rows]
    y_train = [str(row["label"]) for row in train_rows]
    x_test = [str(row["text"]) for row in test_rows]
    y_test = [str(row["label"]) for row in test_rows]

    model = Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )
    model.fit(x_train, y_train)
    y_pred = list(model.predict(x_test))
    print(f"train_size: {len(train_rows)}")
    print(f"test_size: {len(test_rows)}")
    print_metrics("trained_ml_router", metrics(y_test, y_pred), y_test, y_pred, x_test)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output)
    print(f"model_output_path: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
