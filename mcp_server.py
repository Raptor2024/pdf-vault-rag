"""MCP server — lets any MCP-capable AI agent use this vault as a capability.

Exposes three tools:
  convert_pdf(path)   — convert a PDF to markdown into the vault (auto-splits huge files)
  update_index()      — re-index the vault (incremental)
  search_vault(query) — semantic search; returns chunks with source file + heading

Setup (inside this folder, after the normal venv setup):
    venv\Scripts\pip install mcp

Register with your agent (example for Claude Code):
    claude mcp add pdf-vault -- <path-to>/venv/Scripts/python.exe <path-to>/mcp_server.py

Any other MCP client works the same way — it's a standard stdio server.
"""

import subprocess
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

RAG_DIR = Path(__file__).resolve().parent
PY = sys.executable
DB_PATH = RAG_DIR / "chroma_db"
COLLECTION = "book_notes"

mcp = FastMCP("pdf-vault-rag")


def _run(script: str, *args: str, timeout: int = 7200) -> str:
    proc = subprocess.run(
        [PY, str(RAG_DIR / script), *args],
        capture_output=True, text=True, timeout=timeout,
    )
    out = (proc.stdout or "") + (("\n" + proc.stderr) if proc.returncode else "")
    return out.strip()[-4000:]  # keep agent context small


@mcp.tool()
def convert_pdf(path: str) -> str:
    """Convert a PDF (or a folder of PDFs) to Markdown in the vault's
    _pdf_imports folder. Handles scanned books via OCR; PDFs over 300MB are
    split and converted resumably. Slow for big scans (minutes to hours) —
    prefer running it on one file at a time. Skips already-converted PDFs."""
    p = Path(path)
    if not p.exists():
        return f"Not found: {path}"
    return _run("pdf_to_md.py", str(p))


@mcp.tool()
def update_index() -> str:
    """Update the semantic search index over every .md file in the vault.
    Incremental: unchanged files are skipped, so this is fast after the
    first build. Run this after convert_pdf or after editing notes."""
    return _run("build_index.py", timeout=3600)


@mcp.tool()
def search_vault(query: str, n_results: int = 5) -> str:
    """Semantically search the whole vault (notes + converted PDFs).
    Returns the most relevant chunks with their source file and heading —
    cite these sources when answering from the results."""
    import chromadb
    from embeddings import embed

    if not DB_PATH.exists():
        return "No index yet — call update_index() first."
    col = chromadb.PersistentClient(path=str(DB_PATH)).get_collection(COLLECTION)
    res = col.query(query_embeddings=[embed([query])[0]], n_results=int(n_results))
    parts = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        parts.append(f"[{meta['source']} > {meta['heading']}] (distance {dist:.3f})\n{doc[:1200]}")
    return "\n\n---\n\n".join(parts) if parts else "No results."


if __name__ == "__main__":
    mcp.run()
