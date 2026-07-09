"""Convert HUGE PDFs to Markdown by splitting into parts first.

For PDFs too large for a single docling pass (500MB+, thousands of pages).
Splits into chunks of PAGES_PER_PART pages, converts each part separately,
and stitches the results into one markdown file in _pdf_imports.

CRASH-PROOF / RESUMABLE: each finished part is saved as its own .md in the
work folder. If the run dies (crash, reboot, out of memory), just run the
same command again — finished parts are skipped and it picks up where it
left off. Long-s normalization is applied automatically.

Usage:
    venv\Scripts\python.exe pdf_to_md_big.py "C:\path\to\huge.pdf"

Work files live in rag\big_work\<name>\ and can be deleted once the final
stitched file exists.
"""

import sys
import time
from pathlib import Path

RAG_DIR = Path(__file__).resolve().parent
OUT_DIR = RAG_DIR.parent / "_pdf_imports"
WORK_ROOT = RAG_DIR / "big_work"
PAGES_PER_PART = 200

from normalize_long_s import normalize_text


def split_pdf(pdf_path: Path, work: Path) -> list[Path]:
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(str(pdf_path))
    total = len(reader.pages)
    n_parts = (total + PAGES_PER_PART - 1) // PAGES_PER_PART
    print(f"{total} pages -> {n_parts} parts of up to {PAGES_PER_PART} pages")

    parts = []
    for i in range(n_parts):
        part_path = work / f"part_{i + 1:04d}.pdf"
        parts.append(part_path)
        if part_path.exists():
            continue
        writer = PdfWriter()
        for p in range(i * PAGES_PER_PART, min((i + 1) * PAGES_PER_PART, total)):
            writer.add_page(reader.pages[p])
        tmp = part_path.with_suffix(".tmp")
        with open(tmp, "wb") as f:
            writer.write(f)
        tmp.rename(part_path)
        print(f"  split part {i + 1}/{n_parts}")
    return parts


def convert_big(pdf_path: Path, out_dir: Path = OUT_DIR) -> Path:
    """Split-convert-stitch one huge PDF. Resumable. Returns the output path."""
    target = out_dir / (pdf_path.stem + ".md")
    if target.exists():
        print(f"Already converted: {target}")
        return target

    work = WORK_ROOT / pdf_path.stem
    work.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Splitting {pdf_path.name} ...")
    parts = split_pdf(pdf_path, work)

    print("Loading Docling ...")
    from docling.document_converter import DocumentConverter

    converter = DocumentConverter()
    t0 = time.time()
    for i, part in enumerate(parts, 1):
        part_md = part.with_suffix(".md")
        if part_md.exists():
            print(f"  part {i}/{len(parts)}: already done, skipping")
            continue
        print(f"  part {i}/{len(parts)}: converting ...")
        t = time.time()
        result = converter.convert(str(part))
        md, n_fixed = normalize_text(result.document.export_to_markdown())
        tmp = part_md.with_suffix(".md.tmp")
        tmp.write_text(md, encoding="utf-8")
        tmp.rename(part_md)
        print(f"  part {i}/{len(parts)}: done in {time.time() - t:.0f}s ({n_fixed} long-s fixes)")

    print("Stitching parts ...")
    header = f"---\nsource_pdf: {pdf_path.name}\nconverted_by: docling (split into {len(parts)} parts)\n---\n\n"
    with open(target, "w", encoding="utf-8") as out:
        out.write(header)
        for i, part in enumerate(parts, 1):
            out.write(f"\n\n<!-- part {i}: pages {(i - 1) * PAGES_PER_PART + 1}+ -->\n\n")
            out.write(part.with_suffix(".md").read_text(encoding="utf-8"))

    print(f"\nDONE: {target}")
    print(f"Work files in {work} can now be deleted to reclaim space.")
    print("Run build_index.py to add it to the RAG index.")
    return target


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    pdf_path = Path(sys.argv[1])
    if not pdf_path.is_file():
        sys.exit(f"Not found: {pdf_path}")
    convert_big(pdf_path)


if __name__ == "__main__":
    main()
