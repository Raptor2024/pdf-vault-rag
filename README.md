# PDF Vault RAG

Turn a folder of PDFs into a **local, semantically searchable knowledge base** for
your [Obsidian](https://obsidian.md) vault (or any folder of markdown notes).

- 📄 **PDF → Markdown** with [Docling](https://github.com/docling-project/docling)
  (real OCR — handles scanned books, not just born-digital PDFs)
- 🏺 **Long-s normalization** for 18th/19th-century scans
  (`confideration` → `consideration`, while real f-words are left alone)
- 🧠 **Semantic search** over all your notes via ChromaDB +
  [Ollama](https://ollama.com) embeddings **100% local, no API keys, no cloud**
- 🖱️ **Point-and-click UI** (Windows) or plain CLI (any OS)
- 💪 **Huge-PDF mode**: files over 300MB are split into 200-page parts,
  converted resumably (a crash loses minutes, not hours), and stitched back

Built by a researcher who needed 18,000 pages of 18th-century legal sources
searchable next to his notes. Shared in the hope it saves you the same work.

## Setup

1. **Install [Ollama](https://ollama.com)** and pull the embedding model:
   ```
   ollama pull nomic-embed-text
   ```
2. **Drop this folder into your vault** (the folder that holds your `.md` notes):
   ```
   My Vault/
   ├── my notes.md ...
   └── pdf-vault-rag/        ← this repo
   ```
3. **Create the Python environment** (Python 3.10–3.13; docling doesn't support 3.14 yet):
   ```
   python -m venv venv
   venv\Scripts\pip install -r requirements.txt      (Windows)
   venv/bin/pip install -r requirements.txt          (macOS/Linux)
   ```

## Use

### Windows point-and-click
Double-click **`PDF Converter.bat`** → Add PDFs → Convert now.
PDFs are staged in `../PDF Inbox`, converted markdown lands in `../_pdf_imports`,
and the search index updates automatically. Already-converted PDFs are skipped,
and the Convert button refuses to run two conversions at once.

### CLI (any OS)
```bash
# convert PDFs (files or folders; >300MB automatically uses resumable split mode)
venv/bin/python pdf_to_md.py "path/to/some.pdf" "path/to/folder-of-pdfs"

# build / update the search index (incremental — only changed files re-embed)
venv/bin/python build_index.py

# search your whole vault semantically
venv/bin/python query.py "what did the 1771 dictionary mean by 'arms'?"
```

### Fix long-s OCR in an existing file
```bash
venv/bin/python normalize_long_s.py "old-scan.md" --dry-run
```

## How it works

- `build_index.py` chunks every `.md` in the vault by heading (max ~2,500 chars,
  with overlap), embeds with `nomic-embed-text`, and persists to `chroma_db/`
  in this folder. File-hash tracking makes re-runs incremental.
- `query.py` embeds your question and returns the top chunks with source file
  + heading, so you can jump straight to the note.
- The ChromaDB collection (`book_notes`) is standard point any RAG agent or
  pipeline at it:
  ```python
  import chromadb
  col = chromadb.PersistentClient(path="pdf-vault-rag/chroma_db").get_collection("book_notes")
  ```

## Don't use Ollama? No problem

The tool needs an **embedding model**, not a chat LLM — and it speaks two APIs:

- **Ollama** (default): `ollama pull nomic-embed-text` and you're done.
- **Any OpenAI-compatible server** — LM Studio, Jan, llama.cpp server, GPT4All,
  LocalAI, or OpenAI itself. Set three environment variables:
  ```
  set EMBED_PROVIDER=openai
  set EMBED_URL=http://localhost:1234/v1        (LM Studio's default)
  set EMBED_MODEL=text-embedding-nomic-embed-text-v1.5
  ```
  (Hosted services also need `EMBED_API_KEY`. See `embeddings.py` for details.)

⚠️ An index is tied to the model that built it — if you switch embedding
models, delete `chroma_db/` and re-run `build_index.py`.

## Notes & limits

- First Docling run downloads its layout/OCR models (~500MB, one time).
- A 400-page scanned book ≈ 30–60 min of CPU OCR; born-digital PDFs are fast.
- Long-s normalization only fixes words where an f→s swap yields a more common
  English word (dictionary-frequency based) it never invents text. Verify
  quotes against the original scan before publishing them.
- Everything stays on your machine. Nothing is uploaded anywhere.

## License

MIT — see [LICENSE](LICENSE).
