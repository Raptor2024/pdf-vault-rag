"""Build (or update) the RAG index for the book notes vault.

- Reads every .md file under the vault (default: the folder containing this tool),
  skipping .obsidian and the rag folder itself.
- Chunks by markdown headings, then splits oversized sections with overlap.
- Embeds via embeddings.py — Ollama by default, or any OpenAI-compatible server (see embeddings.py for configuration).
- Persists to ChromaDB at rag/chroma_db (collection: book_notes).

Re-running is safe: files whose content is unchanged are skipped;
changed files have their old chunks replaced.

Usage:
    venv\Scripts\python.exe build_index.py [vault_path]
"""

import hashlib
import sys
import time
from pathlib import Path

import chromadb

from embeddings import embed

RAG_DIR = Path(__file__).resolve().parent
NOTES_ROOT = RAG_DIR.parent
DEFAULT_VAULT = NOTES_ROOT
DB_PATH = RAG_DIR / "chroma_db"
COLLECTION = "book_notes"
MAX_CHARS = 2500      # target max chunk size
OVERLAP = 300         # overlap when splitting oversized sections
SKIP_DIRS = {".obsidian", "rag", "chroma_db"}


def split_long(text: str) -> list[str]:
    if len(text) <= MAX_CHARS:
        return [text]
    parts = []
    start = 0
    while start < len(text):
        end = min(start + MAX_CHARS, len(text))
        if end < len(text):
            # try to break on a paragraph or sentence boundary
            for sep in ("\n\n", "\n", ". "):
                cut = text.rfind(sep, start + MAX_CHARS // 2, end)
                if cut != -1:
                    end = cut + len(sep)
                    break
        parts.append(text[start:end])
        if end >= len(text):
            break
        start = max(end - OVERLAP, start + 1)
    return parts


def chunk_markdown(text: str) -> list[tuple[str, str]]:
    """Split on headings; returns list of (heading_path, chunk_text)."""
    lines = text.splitlines()
    sections: list[tuple[str, list[str]]] = [("(top)", [])]
    for line in lines:
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            if 1 <= level <= 4:
                sections.append((line.lstrip("#").strip() or "(untitled)", [line]))
                continue
        sections[-1][1].append(line)
    chunks = []
    for heading, body in sections:
        joined = "\n".join(body).strip()
        if len(joined) < 40:  # skip empty/trivial sections
            continue
        for piece in split_long(joined):
            chunks.append((heading, piece))
    return chunks


def main() -> None:
    vault = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_VAULT
    if not vault.is_dir():
        sys.exit(f"Vault folder not found: {vault}")

    client = chromadb.PersistentClient(path=str(DB_PATH))
    col = client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})

    md_files = [
        p for p in sorted(vault.rglob("*.md"))
        if not any(part in SKIP_DIRS for part in p.parts)
    ]
    print(f"Vault: {vault}")
    print(f"Index: {DB_PATH}  (collection '{COLLECTION}')")
    print(f"Found {len(md_files)} markdown files.\n")

    total_new = 0
    for path in md_files:
        rel = path.relative_to(vault).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        digest = hashlib.sha256(text.encode()).hexdigest()[:16]

        existing = col.get(where={"source": rel}, include=["metadatas"], limit=1)
        if existing["ids"] and existing["metadatas"][0].get("hash") == digest:
            print(f"  unchanged  {rel}")
            continue
        if existing["ids"]:
            col.delete(where={"source": rel})
            print(f"  updating   {rel}")
        else:
            print(f"  indexing   {rel}")

        chunks = chunk_markdown(text)
        if not chunks:
            continue
        for i in range(0, len(chunks), 16):  # embed in small batches
            batch = chunks[i : i + 16]
            vectors = embed([c[1] for c in batch])
            col.add(
                ids=[f"{digest}:{i + j}" for j in range(len(batch))],
                embeddings=vectors,
                documents=[c[1] for c in batch],
                metadatas=[
                    {"source": rel, "heading": c[0], "hash": digest, "chunk": i + j}
                    for j, c in enumerate(batch)
                ],
            )
        total_new += len(chunks)

    # Prune chunks whose source file no longer exists in the vault.
    current = {p.relative_to(vault).as_posix() for p in md_files}
    existing_meta = col.get(include=["metadatas"])
    stale = {m["source"] for m in existing_meta["metadatas"]} - current
    for gone in sorted(stale):
        col.delete(where={"source": gone})
        print(f"  pruned     {gone} (file removed from vault)")

    print(f"\nDone. {total_new} chunks embedded this run; collection now holds {col.count()} chunks.")


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"Elapsed: {time.time() - t0:.1f}s")
