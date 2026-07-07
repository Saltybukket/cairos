"""Streaming helpers for CAIROS router training/evaluation datasets."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import json
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

REQUIRED_FIELDS = {"text", "label"}
OPTIONAL_FIELDS = {"template_category", "expected_intent", "shell_hint", "risk_hint", "notes"}
VALID_LABELS = {"template", "ai", "conversation", "safety_check", "no_match"}


@dataclass
class DatasetStats:
    rows: int = 0
    invalid_json_lines: int = 0
    missing_field_count: int = 0
    duplicate_text_count: int = 0
    average_text_length: float = 0.0
    label_distribution: Counter[str] = field(default_factory=Counter)
    template_category_distribution: Counter[str] = field(default_factory=Counter)
    shell_hint_distribution: Counter[str] = field(default_factory=Counter)
    risk_hint_distribution: Counter[str] = field(default_factory=Counter)
    longest_examples: list[dict[str, object]] = field(default_factory=list)


def iter_jsonl(path: Path) -> Iterable[tuple[int, dict[str, Any] | None, str | None]]:
    """Yield parsed JSONL rows as ``(line_number, row, error)``."""
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            text = line.strip()
            if not text:
                continue
            try:
                value = json.loads(text)
            except json.JSONDecodeError as exc:
                yield line_number, None, str(exc)
                continue
            if not isinstance(value, dict):
                yield line_number, None, "row is not a JSON object"
                continue
            yield line_number, value, None


def load_rows(path: Path, *, skip_invalid: bool = True) -> list[dict[str, Any]]:
    """Load valid rows from disk without printing row contents."""
    rows: list[dict[str, Any]] = []
    for _, row, error in iter_jsonl(path):
        if error:
            if skip_invalid:
                continue
            raise ValueError(error)
        assert row is not None
        if not REQUIRED_FIELDS.issubset(row):
            if skip_invalid:
                continue
            raise ValueError(f"missing required fields: {REQUIRED_FIELDS - set(row)}")
        if str(row.get("label")) not in VALID_LABELS:
            if skip_invalid:
                continue
            raise ValueError(f"invalid label: {row.get('label')}")
        rows.append(row)
    return rows


def dataset_stats(path: Path, *, longest_limit: int = 20) -> DatasetStats:
    """Compute summary stats for a router JSONL dataset."""
    stats = DatasetStats()
    text_counts: Counter[str] = Counter()
    lengths: list[int] = []
    longest: list[dict[str, object]] = []

    for line_number, row, error in iter_jsonl(path):
        if error:
            stats.invalid_json_lines += 1
            continue
        assert row is not None
        stats.rows += 1
        missing = REQUIRED_FIELDS - set(row)
        if missing:
            stats.missing_field_count += 1
        text = str(row.get("text", ""))
        label = str(row.get("label", "<missing>"))
        text_counts[text] += 1
        lengths.append(len(text))
        stats.label_distribution[label] += 1
        stats.template_category_distribution[str(row.get("template_category") or "<empty>")] += 1
        stats.shell_hint_distribution[str(row.get("shell_hint") or "<empty>")] += 1
        stats.risk_hint_distribution[str(row.get("risk_hint") or "<empty>")] += 1
        longest.append({"line": line_number, "length": len(text), "label": label, "preview": text[:140]})

    stats.duplicate_text_count = sum(count - 1 for count in text_counts.values() if count > 1)
    stats.average_text_length = mean(lengths) if lengths else 0.0
    stats.longest_examples = sorted(longest, key=lambda item: int(item["length"]), reverse=True)[:longest_limit]
    return stats


def print_stats(stats: DatasetStats) -> None:
    """Print compact dataset stats without dumping the dataset."""
    print(f"rows: {stats.rows}")
    print(f"invalid_json_lines: {stats.invalid_json_lines}")
    print(f"missing_field_count: {stats.missing_field_count}")
    print(f"duplicate_text_count: {stats.duplicate_text_count}")
    print(f"average_text_length: {stats.average_text_length:.1f}")
    print("label_distribution:")
    for key, value in stats.label_distribution.most_common():
        print(f"  {key}: {value}")
    print("template_category_distribution:")
    for key, value in stats.template_category_distribution.most_common(20):
        print(f"  {key}: {value}")
    print("shell_hint_distribution:")
    for key, value in stats.shell_hint_distribution.most_common(20):
        print(f"  {key}: {value}")
    print("risk_hint_distribution:")
    for key, value in stats.risk_hint_distribution.most_common(20):
        print(f"  {key}: {value}")
    print("top_longest_examples:")
    for item in stats.longest_examples:
        print(f"  line={item['line']} length={item['length']} label={item['label']} preview={item['preview']!r}")
