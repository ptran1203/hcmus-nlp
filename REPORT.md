# Pipeline Report

Goal: build a Han–Việt parallel corpus from four Vietnamese-history books
(Chiến Quốc Sách, Liệt Nữ Truyện, Sử Ký Tư Mã Thiên, Tam Quốc Chí) — for each
book, a set of Han sentences matched to their Vietnamese translation.

## Pipeline

```
 Download  →   Clean   →   Segment   →   Align
 (get raw     (turn raw    (split into    (match Han sentences
  files from   files into   sentences)     to Vietnamese sentences)
  Drive)       plain text)
```

**Download** — fetch each book's Han and Vietnamese source files from Google
Drive.

**Clean** — turn the raw sources (Han is text, Vietnamese is a scanned/typed
PDF) into plain, readable text, removing noise like page numbers and
duplicated content.

**Segment** — split the cleaned text into individual sentences, separately
for Han and for Vietnamese, since they need different rules. Han is split on
its own sentence-ending punctuation (`。！？`) — the source texts are already
densely and consistently punctuated this way, and Classical Chinese doesn't
use those marks for anything else, so a simple split is reliable. Vietnamese
is *not* split on `.` the same way, because in Vietnamese a `.` is often
*not* a sentence boundary — it shows up in abbreviations, numbers (`.` as a
thousands separator), and URLs/domain names, so a naive split would
constantly cut sentences in the wrong place. Instead Vietnamese is split with
[Underthesea](https://github.com/undertheseanlp/underthesea), an
off-the-shelf Vietnamese NLP toolkit trained to tell a real sentence boundary
apart from these other uses of `.`.

**Align** — for each book, match up Han sentences with the Vietnamese
sentences that translate them. Both sides are turned into vector embeddings
with a multilingual sentence-embedding model (`paraphrase-multilingual-MiniLM`,
a smaller/faster relative of Google's LaBSE, which is also supported) — this
captures *meaning* rather than exact words, so it can match a Han sentence to
its Vietnamese translation even though the wording is completely different.
The actual matching is done with a **dynamic programming algorithm** (in the
style of aligners like Vecalign/Bertalign): it finds the best overall path of
matches through the book that (a) always moves forward in order on both
sides (translations don't reorder sentences) and (b) is allowed to group a
couple of sentences together on either side when needed. Each match gets a
confidence score (embedding similarity) so low-quality matches can be
filtered out.

## Challenges hit along the way

- **Some books' Vietnamese source is a scanned image, not text.** Those
  still need OCR before they can go through the pipeline — not done yet.
- **One book's Han source had a chunk of its content duplicated** by
  whatever tool produced the file originally. Caught this by comparing the
  data before and after cleaning, and now duplicates get automatically
  dropped.
- **Han and Vietnamese don't break into sentences the same way** — Chinese
  punctuation marks clause boundaries much more often than a Vietnamese
  sentence boundary, so one Vietnamese sentence often corresponds to several
  Han sentences. The matching step allows grouping a few sentences together
  on either side to handle this, though very dialogue-heavy passages (lots
  of short back-and-forth lines) can still be a stretch.
- **Matching every sentence against every sentence doesn't scale** — a full
  book has tens of thousands of sentences, and comparing all of them against
  each other is too slow and memory-heavy. Since a Han sentence should land
  near the *proportionally* corresponding spot in the Vietnamese text, the
  matching only searches nearby candidates instead of the whole book.

## Quality check

After matching, each book gets an automatic quality summary: how confident
the matches are on average, how many sentences had to be grouped together to
find a match, and whether Han/Vietnamese pair lengths look proportional
(a very lopsided pair length is a good automatic sign of a likely bad match).
This is self-consistency checking, not a true accuracy number — no manually
verified sample exists yet to calibrate against.

## Status

- Working end-to-end for Liệt Nữ Truyện.
- Chiến Quốc Sách blocked on OCR (scanned PDF).
- Sử Ký Tư Mã Thiên and Tam Quốc Chí not yet downloaded/run.
- Possible future improvement: some books have clear internal structure
  (e.g. numbered biographical entries) that could be used to break the book
  into smaller pieces before matching, making the matching both easier and
  more accurate.
