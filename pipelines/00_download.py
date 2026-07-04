"""Download raw Han (.txt) / Viet (.pdf) source files from Google Drive.

Saves each book's files to dataset/raw/<slug>/{han,viet}.<ext>, skipping any
file that already exists so the script is safe to re-run.

Usage:
    python pipelines/00_download.py [--only slug1,slug2]
"""
import argparse
import logging
from pathlib import Path

import gdown

from config import BOOKS, RAW_DIR

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


def existing_file(folder: Path, stem: str) -> Path | None:
    matches = list(folder.glob(f"{stem}.*"))
    return matches[0] if matches else None


def sniff_extension(path: Path) -> str:
    with path.open("rb") as f:
        head = f.read(8)
    if head.startswith(b"%PDF"):
        return ".pdf"
    return ".txt"


def download_one(file_id: str, folder: Path, stem: str) -> None:
    existing = existing_file(folder, stem)
    if existing:
        log.info("  [skip] %s already exists", existing.name)
        return

    folder.mkdir(parents=True, exist_ok=True)
    # Use an explicit output filename (not a directory) so gdown doesn't try
    # to infer the name from the Content-Disposition header, which fails
    # for Drive's "large file" confirmation page.
    tmp_path = folder / f"_{stem}.download"
    print(f"Downloading {stem} from Google Drive id={file_id} to {tmp_path}...")
    downloaded_path = gdown.download(id=file_id, output=str(tmp_path), quiet=False)
    if not downloaded_path:
        log.error("  [fail] could not download id=%s", file_id)
        return

    ext = sniff_extension(Path(downloaded_path))
    target = folder / f"{stem}{ext}"
    Path(downloaded_path).rename(target)
    log.info("  [ok] saved to %s", target)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="comma-separated book slugs to download (default: all)")
    args = parser.parse_args()
    wanted = set(args.only.split(",")) if args.only else None

    for book in BOOKS:
        if wanted and book["slug"] not in wanted:
            continue
        log.info("== %s (%s) ==", book["name"], book["slug"])
        folder = RAW_DIR / book["slug"]
        download_one(book["han_id"], folder, "han")
        download_one(book["viet_id"], folder, "viet")


if __name__ == "__main__":
    main()
