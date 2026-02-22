

import math
import re
from collections import Counter
from pathlib import Path

KNOWLEDGE_DIR = Path("knowledge")

# Each chunk: {"text": str, "source": str, "tf": Counter, "norm": float}
_chunks: list[dict] = []

_STOP = {
    "a","an","the","is","are","was","were","be","been","being",
    "have","has","had","do","does","did","will","would","could",
    "should","may","might","shall","can","to","of","in","on",
    "at","by","for","with","about","as","into","from","or","and",
    "but","not","no","it","its","this","that","these","those",
    "i","we","you","he","she","they","their","our","your","his","her",
}

CHUNK_SIZE  = 200   # words per chunk
CHUNK_STEP  = 150   # step between chunk starts (50-word overlap)
TOP_K       = 3     # chunks returned per query
MIN_SCORE   = 1     # minimum keyword hits to be included


def _tokenise(text: str) -> list[str]:
    """Lowercase, remove punctuation, drop stop words."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if t not in _STOP and len(t) > 1]


def _tfidf_norm(tf: Counter, n_docs: int, df: dict) -> float:
    """Pre-compute L2 norm of the TF-IDF vector for cosine similarity."""
    total = 0.0
    for term, count in tf.items():
        idf = math.log((n_docs + 1) / (df.get(term, 0) + 1)) + 1
        total += (count * idf) ** 2
    return math.sqrt(total) or 1.0


def load_knowledge() -> int:
    """
    Load every .txt file in KNOWLEDGE_DIR into memory.
    Call once at server startup. Returns number of chunks loaded.
    """
    global _chunks
    _chunks = []

    if not KNOWLEDGE_DIR.exists():
        print(f"[RAG] Warning: knowledge/ directory not found at {KNOWLEDGE_DIR.resolve()}")
        return 0

    raw_chunks = []
    for path in sorted(KNOWLEDGE_DIR.glob("*.txt")):
        text  = path.read_text(encoding="utf-8", errors="ignore").strip()
        words = text.split()
        for i in range(0, max(1, len(words) - CHUNK_SIZE + 1), CHUNK_STEP):
            chunk_text = " ".join(words[i : i + CHUNK_SIZE])
            raw_chunks.append({"text": chunk_text, "source": path.stem})

    # document-frequency table across all chunks
    df: dict[str, int] = Counter()
    tfs = []
    for chunk in raw_chunks:
        tokens = _tokenise(chunk["text"])
        tf = Counter(tokens)
        tfs.append(tf)
        for term in tf:
            df[term] += 1

    n = len(raw_chunks)
    for chunk, tf in zip(raw_chunks, tfs):
        _chunks.append({
            "text":   chunk["text"],
            "source": chunk["source"],
            "tf":     tf,
            "norm":   _tfidf_norm(tf, n, df),
            "df":     df,   # shared reference
            "n":      n,
        })

    print(f"[RAG] Loaded {len(_chunks)} chunks from {KNOWLEDGE_DIR.resolve()}")
    return len(_chunks)


def retrieve(query: str, top_k: int = TOP_K) -> str:
    """
    Return a formatted string of the most relevant chunks for a query.
    Returns empty string if nothing relevant is found.
    """
    if not _chunks:
        return ""

    q_tokens = _tokenise(query)
    if not q_tokens:
        return ""

    q_tf   = Counter(q_tokens)
    df     = _chunks[0]["df"]
    n      = _chunks[0]["n"]

    # Computing cosine similarity between query and each chunk
    scored = []
    for chunk in _chunks:
        # Dot product
        dot = 0.0
        for term, q_count in q_tf.items():
            if term in chunk["tf"]:
                idf   = math.log((n + 1) / (df.get(term, 0) + 1)) + 1
                dot  += q_count * idf * chunk["tf"][term] * idf

        if dot == 0:
            continue

        # Query norm (computed inline — cheap)
        q_norm = math.sqrt(sum(
            (cnt * (math.log((n + 1) / (df.get(t, 0) + 1)) + 1)) ** 2
            for t, cnt in q_tf.items()
        )) or 1.0

        score = dot / (q_norm * chunk["norm"])
        if score >= MIN_SCORE / 100:   # threshold: ~0.01
            scored.append((score, chunk))

    if not scored:
        return ""

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]

    parts = []
    for _, chunk in top:
        parts.append(f"[Source: {chunk['source'].replace('_', ' ').title()}]\n{chunk['text']}")
    return "\n\n".join(parts)


def is_loaded() -> bool:
    return len(_chunks) > 0