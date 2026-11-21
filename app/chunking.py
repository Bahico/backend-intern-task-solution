def chunk_text(text: str, size: int = 50, overlap: int = 10) -> list[str]:
    """Split text into overlapping, word-based chunks."""
    if size <= 0:
        raise ValueError("size must be greater than zero")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be at least zero and smaller than size")

    words = text.split()
    if not words:
        return []

    step = size - overlap
    chunks: list[str] = []
    for start in range(0, len(words), step):
        chunk_words = words[start : start + size]
        chunks.append(" ".join(chunk_words))
        if start + size >= len(words):
            break
    return chunks
