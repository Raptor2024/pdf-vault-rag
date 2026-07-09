---
name: pdf-vault-rag
description: Convert PDFs (including scanned books) to Markdown in the user's notes vault and semantically search the whole vault. Use when the user asks to convert/ingest a PDF, index their notes, or find something in their notes or sources ("search my notes for...", "what does my vault say about...", "ingest this PDF").
---

# PDF Vault RAG

This folder is a self-contained pipeline living inside the user's vault
(the parent directory holds their .md notes). Use the venv Python in this
folder for every command.

## Commands

Convert a PDF to Markdown (lands in ../_pdf_imports; scanned books get OCR;
files >300MB auto-split with resume support — safe to re-run after a crash):

    venv/Scripts/python.exe pdf_to_md.py "<path-to-pdf-or-folder>"

Update the search index (incremental — run after conversions or note edits):

    venv/Scripts/python.exe build_index.py

Search the vault semantically (returns chunks with source file + heading):

    venv/Scripts/python.exe query.py "<question>" [n_results]

## Rules

- Big scanned PDFs take a long time (30–60 min per 400 pages). Run them in
  the background and tell the user; never block on them silently.
- When answering from search results, cite the source file and heading.
- The index is tied to one embedding model (see embeddings.py). Never switch
  models without deleting chroma_db/ and re-indexing.
- Requires a local embedding server (Ollama with nomic-embed-text by default;
  any OpenAI-compatible server via EMBED_* env vars).
