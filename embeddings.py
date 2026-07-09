"""One place to get embeddings, whatever the user runs.

Supports two API styles, configured by environment variables:

  EMBED_PROVIDER   "ollama" (default) or "openai"
  EMBED_URL        base URL of the server
                     ollama default: http://localhost:11434
                     openai-style default: http://localhost:1234/v1  (LM Studio)
  EMBED_MODEL      embedding model name (default: nomic-embed-text)
  EMBED_API_KEY    only needed for hosted services like OpenAI

"openai" here means the OpenAI-COMPATIBLE API, which nearly every local LLM
app speaks: LM Studio, Jan, llama.cpp server, GPT4All, LocalAI — and OpenAI
itself. Examples:

  # LM Studio with a local embedding model loaded:
  set EMBED_PROVIDER=openai
  set EMBED_URL=http://localhost:1234/v1
  set EMBED_MODEL=text-embedding-nomic-embed-text-v1.5

  # OpenAI (hosted — costs money, texts leave your machine):
  set EMBED_PROVIDER=openai
  set EMBED_URL=https://api.openai.com/v1
  set EMBED_MODEL=text-embedding-3-small
  set EMBED_API_KEY=sk-...

IMPORTANT: an index is tied to the model that built it. If you switch
embedding models, delete chroma_db and re-run build_index.py — vectors from
different models are not comparable.
"""

import os
import requests

PROVIDER = os.environ.get("EMBED_PROVIDER", "ollama").lower()
MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")
API_KEY = os.environ.get("EMBED_API_KEY", "")
URL = os.environ.get(
    "EMBED_URL",
    "http://localhost:11434" if PROVIDER == "ollama" else "http://localhost:1234/v1",
).rstrip("/")


def embed(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts. Returns one vector per text."""
    if PROVIDER == "ollama":
        r = requests.post(f"{URL}/api/embed", json={"model": MODEL, "input": texts}, timeout=120)
        r.raise_for_status()
        return r.json()["embeddings"]

    headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
    r = requests.post(
        f"{URL}/embeddings",
        json={"model": MODEL, "input": texts},
        headers=headers,
        timeout=120,
    )
    r.raise_for_status()
    data = sorted(r.json()["data"], key=lambda d: d["index"])
    return [d["embedding"] for d in data]
