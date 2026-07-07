#!/usr/bin/env python3
"""Evaluate CAIROS request routers against a JSONL dataset."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cairos.router import route_request
from cairos.router_dataset import VALID_LABELS, dataset_stats, load_rows, print_stats


def metrics(y_true: list[str], y_pred: list[str]) -> dict[str, object]:
    labels = sorted(VALID_LABELS)
    total = len(y_true)
    accuracy = sum(1 for a, b in zip(y_true, y_pred) if a == b) / total if total else 0.0
    per_label: dict[str, dict[str, float]] = {}
    f1s: list[float] = []
    for label in labels:
        tp = sum(1 for a, b in zip(y_true, y_pred) if a == label and b == label)
        fp = sum(1 for a, b in zip(y_true, y_pred) if a != label and b == label)
        fn = sum(1 for a, b in zip(y_true, y_pred) if a == label and b != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        f1s.append(f1)
        per_label[label] = {"precision": precision, "recall": recall, "f1": f1}
    confusion: dict[str, Counter[str]] = defaultdict(Counter)
    for actual, predicted in zip(y_true, y_pred):
        confusion[actual][predicted] += 1
    return {"accuracy": accuracy, "macro_f1": sum(f1s) / len(f1s), "per_label": per_label, "confusion": confusion}


def print_metrics(title: str, data: dict[str, object], y_true: list[str], y_pred: list[str], texts: list[str]) -> None:
    print(title)
    print(f"accuracy: {data['accuracy']:.3f}")
    print(f"macro_f1: {data['macro_f1']:.3f}")
    print("per_label:")
    for label, values in (data["per_label"]).items():  # type: ignore[union-attr]
        print(f"  {label}: precision={values['precision']:.3f} recall={values['recall']:.3f} f1={values['f1']:.3f}")
    print("confusion_matrix:")
    confusion = data["confusion"]  # type: ignore[assignment]
    for actual in sorted(VALID_LABELS):
        row = " ".join(f"{predicted}={confusion[actual][predicted]}" for predicted in sorted(VALID_LABELS))  # type: ignore[index]
        print(f"  {actual}: {row}")
    print("top_misclassifications:")
    shown = 0
    for actual, predicted, text in zip(y_true, y_pred, texts):
        if actual != predicted:
            print(f"  expected={actual} predicted={predicted} text={text[:140]!r}")
            shown += 1
            if shown >= 10:
                break
    if shown == 0:
        print("  <none>")


def evaluate_router(rows: list[dict[str, object]], *, use_ml: bool, router: str) -> tuple[list[str], list[str], list[str]]:
    texts = [str(row["text"]) for row in rows]
    y_true = [str(row["label"]) for row in rows]
    y_pred = [route_request(text, allow_ml=use_ml, router=router).route for text in texts]
    return y_true, y_pred, texts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/router_training.jsonl")
    parser.add_argument("--use-ml", action="store_true")
    args = parser.parse_args()
    path = Path(args.data)
    stats = dataset_stats(path)
    print_stats(stats)
    rows = load_rows(path)
    if not rows:
        print("No valid rows to evaluate.", file=sys.stderr)
        return 1

    y_true, y_pred, texts = evaluate_router(rows, use_ml=False, router="heuristic")
    print_metrics("heuristic_router", metrics(y_true, y_pred), y_true, y_pred, texts)

    if args.use_ml:
        y_true, y_pred, texts = evaluate_router(rows, use_ml=True, router="ml")
        print_metrics("ml_or_fallback_router", metrics(y_true, y_pred), y_true, y_pred, texts)
    else:
        print("ML evaluation skipped. Pass --use-ml after installing cairos-shell[ml-router] or scikit-learn/joblib.")

    y_true, y_pred, texts = evaluate_router(rows, use_ml=True, router="auto")
    print_metrics("auto_router", metrics(y_true, y_pred), y_true, y_pred, texts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
