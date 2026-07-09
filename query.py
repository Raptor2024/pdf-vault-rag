"""Query the book-notes RAG index.

Usage:
    venv\Scripts\python.exe query.py "your question here" [n_results]

Prints the top matching chunks with their source file and heading.
"""

import sys
from pathlib import Path

import requests
import chromadb

RAG_DIR = Path(__file__).resolve().parent
DB_PATH = RAG_DIR / "chroma_db"
COLLECTION = "book_notes"
OLLAMA_URL = "http://localhost:11434/api/embed"
EMBED_MODEL = "nomic-embed-text"


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit('Usage: python query.py "your question" [n_results]')
    question = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    r = requests.post(OLLAMA_URL, json={"model": EMBED_MODEL, "input": [question]}, timeout=60)
    r.raise_for_status()
    qvec = r.json()["embeddings"][0]

    col = chromadb.PersistentClient(path=str(DB_PATH)).get_collection(COLLECTION)
    res = col.query(query_embeddings=[qvec], n_results=n)

    for rank, (doc, meta, dist) in enumerate(
        zip(res["documents"][0], res["metadatas"][0], res["distances"][0]), 1
    ):
        print(f"\n{'=' * 70}")
        print(f"#{rank}  {meta['source']}  >  {meta['heading']}   (distance {dist:.3f})")
        print("-" * 70)
        print(doc[:1200])


if __name__ == "__main__":
    main()
