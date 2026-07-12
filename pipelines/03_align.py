"""Align Han and Vietnamese sentences per book with an embedding-based aligner.

Reads dataset/segmented/<slug>/{han,viet}.jsonl, aligns sentences, drops
pairs below --min-score, and writes:
  - dataset/aligned/<slug>.tsv   (book, han_ids, viet_ids, han, viet, score)
  - dataset/aligned/report.json (per-book quality summary)

The embedding model is swappable via --model (comma-separated for an
ensemble); the aligner algorithm itself is swapped by passing a different
SentenceAligner implementation in main() below.

Usage:
    python pipelines/03_align.py [--only slug1,slug2] [--min-score 0.5]
                                  [--model sentence-transformers/LaBSE]
                                  [--model sentence-transformers/LaBSE,intfloat/multilingual-e5-large]
"""
import argparse
import csv
import json
import logging
import statistics
from pathlib import Path

from tqdm import tqdm

from aligners.base import AlignedPair
from aligners.labse_dp import LabseDPAligner
from config import BOOKS, CLEANED_DIR

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

SEGMENTED_DIR = CLEANED_DIR.parent / "segmented"
ALIGNED_DIR = CLEANED_DIR.parent / "aligned"


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def value_stats(values: list[float]) -> dict:
    """min/max/mean/median/stdev/p10/p90 -- deciles only computed with enough data."""
    if not values:
        return {}
    values = sorted(values)
    stats = {
        "min": round(values[0], 4),
        "max": round(values[-1], 4),
        "mean": round(statistics.mean(values), 4),
    }
    if len(values) >= 2:
        stats["median"] = round(statistics.median(values), 4)
        stats["stdev"] = round(statistics.stdev(values), 4)
    if len(values) >= 10:
        deciles = statistics.quantiles(values, n=10)
        stats["p10"] = round(deciles[0], 4)
        stats["p90"] = round(deciles[8], 4)
    return stats


def merge_pattern_counts(pairs: list[AlignedPair]) -> dict:
    """Tally pairs by '{han_span_len}-{viet_span_len}', e.g. '1-1', '1-2', '1-0' (han
    sentence skipped), '0-1' (viet sentence skipped). A high skip/merge share
    signals upstream segmentation problems worth revisiting."""
    counts: dict[str, int] = {}
    for p in pairs:
        key = f"{len(p.han_ids)}-{len(p.viet_ids)}"
        counts[key] = counts.get(key, 0) + 1
    return counts


def length_ratio_stats(pairs: list[AlignedPair]) -> dict:
    """viet/han character-length ratio per pair. Genuine translations should sit in a
    fairly consistent band; pairs far from the mean are a cheap automatic proxy for
    likely-bad alignments, without reading any Han/Vietnamese."""
    ratios = [len(p.viet_text) / len(p.han_text) for p in pairs if p.han_text]
    stats = value_stats(ratios)
    if stats.get("stdev"):
        mean, stdev = stats["mean"], stats["stdev"]
        stats["outliers_beyond_2stdev"] = sum(1 for r in ratios if abs(r - mean) > 2 * stdev)
    return stats


def align_book(book: dict, min_score: float, aligner) -> tuple[dict, list[AlignedPair]]:
    han_path = SEGMENTED_DIR / book["slug"] / "han.jsonl"
    viet_path = SEGMENTED_DIR / book["slug"] / "viet.jsonl"
    if not han_path.exists() or not viet_path.exists():
        log.warning("  [skip] missing segmented data for %s", book["slug"])
        return {}, []

    han_sents = [r["text"] for r in read_jsonl(han_path)]
    viet_sents = [r["text"] for r in read_jsonl(viet_path)]

    pairs = aligner.align(han_sents, viet_sents)
    kept = [p for p in pairs if p.han_ids and p.viet_ids and p.score >= min_score]

    out_path = ALIGNED_DIR / f"{book['slug']}.tsv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["book", "han_ids", "viet_ids", "han", "viet", "score"])
        for p in kept:
            writer.writerow(
                [
                    book["slug"],
                    ",".join(map(str, p.han_ids)),
                    ",".join(map(str, p.viet_ids)),
                    p.han_text,
                    p.viet_text,
                    f"{p.score:.4f}",
                ]
            )

    score_summary = value_stats([p.score for p in kept])
    summary = {
        "book": book["slug"],
        "han_sentences": len(han_sents),
        "viet_sentences": len(viet_sents),
        "pairs_kept": len(kept),
        "pairs_dropped": len(pairs) - len(kept),
        "score_stats": score_summary,
        "merge_pattern_counts": merge_pattern_counts(pairs),
        "length_ratio_stats": length_ratio_stats(kept),
    }
    log.info(
        "  [ok] %s: %d pairs kept (avg score %.3f), %d dropped",
        book["slug"], len(kept), score_summary.get("mean", 0.0), summary["pairs_dropped"],
    )
    return summary, kept


def sum_dicts(dicts: list[dict]) -> dict:
    total: dict[str, int] = {}
    for d in dicts:
        for k, v in d.items():
            total[k] = total.get(k, 0) + v
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="comma-separated book slugs to align (default: all)")
    parser.add_argument("--min-score", type=float, default=0.5, help="drop pairs scoring below this")
    parser.add_argument(
        "--model",
        help="sentence-transformers model name(s) for the aligner, comma-separated for an "
        "ensemble (similarity = average across models). Default: paraphrase-multilingual-"
        "MiniLM-L12-v2. See aligners/labse_dp.py MODEL_SIZES for other options tried "
        "(e.g. sentence-transformers/LaBSE, intfloat/multilingual-e5-large, BAAI/bge-m3).",
    )
    args = parser.parse_args()
    wanted = set(args.only.split(",")) if args.only else None
    aligner = LabseDPAligner(model_names=args.model)

    books = [b for b in BOOKS if not wanted or b["slug"] in wanted]
    summaries = []
    all_kept: list[AlignedPair] = []
    for book in tqdm(books, desc="Aligning books"):
        log.info("== %s (%s) ==", book["name"], book["slug"])
        summary, kept = align_book(book, args.min_score, aligner)
        if summary:
            summaries.append(summary)
            all_kept.extend(kept)

    overall = {
        "score_stats": value_stats([p.score for p in all_kept]),
        "merge_pattern_counts": sum_dicts([s["merge_pattern_counts"] for s in summaries]),
        "length_ratio_stats": length_ratio_stats(all_kept),
    }

    report_path = ALIGNED_DIR / "report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as f:
        json.dump({"books": summaries, "overall": overall}, f, ensure_ascii=False, indent=2)
    log.info("Wrote report to %s", report_path)


if __name__ == "__main__":
    main()
