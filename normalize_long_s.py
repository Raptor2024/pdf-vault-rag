"""Normalize long-s OCR artifacts in 18th-century texts.

Scanned period documents render the long s (ſ) as "f", producing
"confideration", "legiflature", "Prefident". For every word containing
an f, this tries the f→s substitutions and keeps whichever variant is a
more common English word (per wordfreq). Real f-words ("of", "for",
"federal") score higher as-is and are left alone. Words where no variant
is recognized are left untouched — better to preserve the OCR than guess.

Used automatically by pdf_to_md.py; also runnable standalone to fix an
existing file:

    venv\Scripts\python.exe normalize_long_s.py "path\to\file.md" [--dry-run]

Standalone mode prints a change summary and edits the file in place
(a .bak copy of the original is written next to it).
"""

import itertools
import re
import sys
from functools import lru_cache

from wordfreq import zipf_frequency

WORD_RE = re.compile(r"[A-Za-z]+")
MAX_F = 6  # cap combinatorial substitutions (2^6 variants max per word)


@lru_cache(maxsize=200_000)
def best_variant(word: str) -> str:
    lower = word.lower()
    positions = [i for i, ch in enumerate(lower) if ch == "f"]
    if not positions or len(positions) > MAX_F:
        return word

    base_freq = zipf_frequency(lower, "en")
    best, best_freq = word, base_freq

    for n in range(1, len(positions) + 1):
        for combo in itertools.combinations(positions, n):
            chars = list(lower)
            for i in combo:
                chars[i] = "s"
            candidate = "".join(chars)
            freq = zipf_frequency(candidate, "en")
            if freq > best_freq:
                # rebuild with original casing
                out = []
                for j, orig in enumerate(word):
                    if j in combo:
                        out.append("S" if orig.isupper() else "s")
                    else:
                        out.append(orig)
                best, best_freq = "".join(out), freq
    return best


def normalize_text(text: str) -> tuple[str, int]:
    """Return (normalized_text, number_of_words_changed)."""
    changed = 0

    # Literal long-s characters are ALWAYS 's' — fix unconditionally first.
    n_literal = text.count("ſ")
    if n_literal:
        text = text.replace("ſ", "s")
        changed += n_literal

    def repl(m: re.Match) -> str:
        nonlocal changed
        fixed = best_variant(m.group(0))
        if fixed != m.group(0):
            changed += 1
        return fixed

    return WORD_RE.sub(repl, text), changed


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    dry = "--dry-run" in sys.argv
    if not args:
        sys.exit(__doc__)

    from pathlib import Path

    for name in args:
        path = Path(name)
        text = path.read_text(encoding="utf-8", errors="replace")
        fixed, changed = normalize_text(text)
        print(f"{path.name}: {changed} words normalized")
        if changed and not dry:
            path.with_suffix(path.suffix + ".bak").write_text(text, encoding="utf-8")
            path.write_text(fixed, encoding="utf-8")
            print(f"  written (original saved as {path.name}.bak)")


if __name__ == "__main__":
    main()
