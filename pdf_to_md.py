"""Convert PDFs to Markdown with Docling for ingestion into the Obsidian vault.

Converted files land in "_pdf_imports/<name>.md" (inside your vault) by default,
so you can review them in Obsidian before/after indexing. Re-run
build_index.py afterwards to add them to the RAG index.

Usage:
    venv\Scripts\python.exe pdf_to_md.py <file-or-folder> [more files...] [--out <folder>]

Examples:
    python pdf_to_md.py "C:\\Downloads\\Heller_Opinion.pdf"
    python pdf_to_md.py "C:\\Downloads\\pdfs"          (converts every PDF in the folder)
"""

import sys
from pathlib import Path

from normalize_long_s import normalize_text

RAG_DIR = Path(__file__).resolve().parent
DEFAULT_OUT = RAG_DIR.parent / "_pdf_imports"
BIG_PDF_MB = 300  # PDFs larger than this go through the split converter


def collect_pdfs(args: list[str]) -> list[Path]:
    pdfs: list[Path] = []
    for a in args:
        p = Path(a)
        if p.is_dir():
            pdfs.extend(sorted(p.glob("*.pdf")))
        elif p.suffix.lower() == ".pdf" and p.is_file():
            pdfs.append(p)
        else:
            print(f"  skipping (not a PDF or not found): {a}")
    return pdfs


def main() -> None:
    args = sys.argv[1:]
    out_dir = DEFAULT_OUT
    if "--out" in args:
        i = args.index("--out")
        out_dir = Path(args[i + 1])
        args = args[:i] + args[i + 2 :]
    if not args:
        sys.exit(__doc__)

    pdfs = collect_pdfs(args)
    if not pdfs:
        sys.exit("No PDFs found.")

    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output folder: {out_dir}")
    print("Loading Docling (first run downloads layout models — be patient)...")
    from docling.document_converter import DocumentConverter

    converter = DocumentConverter()
    for pdf in pdfs:
        target = out_dir / (pdf.stem + ".md")
        if target.exists():
            print(f"  already converted, skipping: {pdf.name}")
            continue
        size_mb = pdf.stat().st_size / 1024 / 1024
        if size_mb > BIG_PDF_MB:
            print(f"  {pdf.name} is {size_mb:.0f}MB -> using split converter (resumable)")
            from pdf_to_md_big import convert_big
            convert_big(pdf, out_dir)
            continue
        print(f"  converting {pdf.name} -> {target.name}")
        result = converter.convert(str(pdf))
        md = result.document.export_to_markdown()
        md, n_fixed = normalize_text(md)
        if n_fixed:
            print(f"    normalized {n_fixed} long-s OCR words")
        header = f"---\nsource_pdf: {pdf.name}\nconverted_by: docling\n---\n\n"
        target.write_text(header + md, encoding="utf-8")

    print(f"\nDone: {len(pdfs)} PDF(s) converted into {out_dir}")
    print("Run build_index.py to add them to the RAG index.")


if __name__ == "__main__":
    main()
