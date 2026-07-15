"""Multilingual-embedding + banded monotonic DP sentence aligner (Vecalign/Bertalign-style).

Embeds every contiguous span of up to MAX_MERGE consecutive sentences on
each side, then finds the lowest-cost monotonic (non-crossing) path through
the han x viet grid via dynamic programming, allowing 1-1, 1-2, 2-1 and 2-2
merges plus single-sentence skips (for content that has no counterpart on
the other side, e.g. footnotes/publisher notes).

The DP is restricted to a band around the expected diagonal (han sentence i
should land near viet position i*(m/n) if the two sides are roughly
proportional) instead of the full n x m grid. For a real book, n and m are
easily in the tens of thousands, and a full grid needs O(n*m) cost/back
cells -- infeasible RAM (tens of GB) regardless of how fast each cell is
computed. Banding cuts this to roughly O(n*BAND_MARGIN), using sparse dicts
so only band cells are ever allocated. Tradeoff: alignments that genuinely
need to jump far from the proportional diagonal (e.g. a large block present
on only one side) can fall outside the band and get missed.

Supports ensembling multiple embedding models: pass a comma-separated string
(or list) of model names and each span's embedding becomes the concatenation
of every model's (normalized) embedding, re-normalized to unit length -- a
cheap way to reduce the risk of any single model's blind spots dominating
the alignment (see MODEL_SIZES for the models this has been tried with).
Defaults to a single lightweight model instead of LaBSE for a much lighter
RAM/CPU footprint at some accuracy cost.
"""
import numpy as np
from tqdm import tqdm

from .base import AlignedPair, SentenceAligner

SKIP_PENALTY = 0.6
MAX_MERGE = 2
BATCH_SIZE = 8
MAX_SPAN_CHARS = 500  # defensive cap: guards against a runaway-long merged span
BAND_MARGIN = 150  # viet-index cells on each side of the expected diagonal position

DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Approximate download sizes, for reference when picking models to ensemble.
MODEL_SIZES = {
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": "~470MB",
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2": "~1.1GB",
    "sentence-transformers/LaBSE": "~1.8GB",
    "intfloat/multilingual-e5-small": "~470MB",
    "intfloat/multilingual-e5-large": "~2.2GB",
    "BAAI/bge-m3": "~2.3GB",
}

# Some models expect a task-instruction prefix on the input text for best
# results on symmetric similarity (not asymmetric query/passage retrieval).
MODEL_PREFIXES = {
    "intfloat/multilingual-e5-small": "query: ",
    "intfloat/multilingual-e5-base": "query: ",
    "intfloat/multilingual-e5-large": "query: ",
}


class LabseDPAligner(SentenceAligner):
    def __init__(self, model_names=None):
        if not model_names:
            model_names = [DEFAULT_MODEL]
        elif isinstance(model_names, str):
            model_names = [m.strip() for m in model_names.split(",") if m.strip()]
        self._model_names = model_names
        self._models = None

    @property
    def models(self):
        if self._models is None:
            from sentence_transformers import SentenceTransformer

            self._models = [SentenceTransformer(name) for name in self._model_names]
        return self._models

    def _span_embeddings(self, sents: list[str], lang_label: str) -> dict:
        """Concatenate each model's (unit-normalized) embedding for a span into
        one combined vector, then re-normalize to unit length. Cosine similarity
        of these combined vectors works out to the average of the per-model
        cosine similarities (since each sub-vector contributes equally), but
        expressed as a single embedding per span rather than a list of scores."""
        spans = [
            (start, start + length)
            for length in range(1, MAX_MERGE + 1)
            for start in range(len(sents) - length + 1)
        ]
        raw_texts = [" ".join(sents[s:e])[:MAX_SPAN_CHARS] for s, e in spans]

        per_model_embs = []
        for model_idx, (name, model) in enumerate(zip(self._model_names, self.models), start=1):
            prefix = MODEL_PREFIXES.get(name, "")
            texts = [prefix + t for t in raw_texts] if prefix else raw_texts
            tqdm.write(
                f"[{lang_label}] encoding {len(texts)} spans with model "
                f"{model_idx}/{len(self._model_names)}: {name}"
            )
            embs = model.encode(
                texts, normalize_embeddings=True, show_progress_bar=True, batch_size=BATCH_SIZE
            )
            per_model_embs.append(np.asarray(embs))

        combined = np.concatenate(per_model_embs, axis=1)
        combined /= np.linalg.norm(combined, axis=1, keepdims=True)
        return dict(zip(spans, combined))

    @staticmethod
    def _band(i: int, n: int, m: int) -> tuple[int, int]:
        center = round(i * m / n) if n else 0
        return max(0, center - BAND_MARGIN), min(m, center + BAND_MARGIN)

    def align(self, han_sents: list[str], viet_sents: list[str]) -> list[AlignedPair]:
        n, m = len(han_sents), len(viet_sents)
        if n == 0 or m == 0:
            return []

        han_embs = self._span_embeddings(han_sents, "han")
        viet_embs = self._span_embeddings(viet_sents, "viet")

        def sim(h_span, v_span) -> float:
            return float(np.dot(han_embs[h_span], viet_embs[v_span]))

        bands = [self._band(i, n, m) for i in range(n + 1)]

        INF = float("inf")
        cost = {(0, 0): 0.0}
        back = {}

        for i in tqdm(range(n + 1), desc="DP alignment"):
            lo, hi = bands[i]
            for j in range(lo, hi + 1):
                base = cost.get((i, j), INF)
                if base == INF:
                    continue

                if i < n:
                    nlo, nhi = bands[i + 1]
                    if nlo <= j <= nhi:
                        cand, key = base + SKIP_PENALTY, (i + 1, j)
                        if cand < cost.get(key, INF):
                            cost[key] = cand
                            back[key] = (i, j, [i], [])

                if j < hi:
                    cand, key = base + SKIP_PENALTY, (i, j + 1)
                    if cand < cost.get(key, INF):
                        cost[key] = cand
                        back[key] = (i, j, [], [j])

                for hl in range(1, MAX_MERGE + 1):
                    if i + hl > n:
                        break
                    nlo, nhi = bands[i + hl]
                    for vl in range(1, MAX_MERGE + 1):
                        nj = j + vl
                        if nj > m or not (nlo <= nj <= nhi):
                            continue
                        h_span, v_span = (i, i + hl), (j, nj)
                        c = base + (1 - sim(h_span, v_span))
                        key = (i + hl, nj)
                        if c < cost.get(key, INF):
                            cost[key] = c
                            back[key] = (i, j, list(range(i, i + hl)), list(range(j, nj)))

        pairs = []
        i, j = n, m
        while (i, j) != (0, 0):
            pi, pj, h_ids, v_ids = back[(i, j)]
            score = sim((pi, i), (pj, j)) if h_ids and v_ids else 0.0
            pairs.append(
                AlignedPair(
                    han_ids=h_ids,
                    viet_ids=v_ids,
                    han_text=" ".join(han_sents[k] for k in h_ids),
                    viet_text=" ".join(viet_sents[k] for k in v_ids),
                    score=score,
                )
            )
            i, j = pi, pj

        pairs.reverse()
        return pairs
